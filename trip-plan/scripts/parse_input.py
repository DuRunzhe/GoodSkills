#!/usr/bin/env python3
"""
trip-plan 输入适配器

支持任意形式输入 → pois.json:
  - HTML(trip-plan nav-template 格式)
  - Markdown 文章
  - CSV 表
  - JSON(标准格式,透传)
  - 自由文本(打印 LLM prompt 模板,引导走 LLM 辅助流程)

用法:
  python parse_input.py <input> -o pois.json [--form auto|html|markdown|csv|json|text] [--validate]

设计:
  - 仅依赖 Python 标准库(HTMLParser / csv / json / re)
  - HTML 解析不依赖 BS4(无第三方依赖,环境可移植)
  - 文本不直接调 LLM,通过 CSV 中转(成本 + 可重复)
"""
import argparse
import csv
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))


# ============================================================
# 1. 表单识别
# ============================================================

def detect_form(path: Path) -> str:
    """根据文件扩展名 + 内容启发式识别输入形式"""
    suffix = path.suffix.lower()
    if suffix in ('.html', '.htm'):
        # 二次确认:含 <div class="poi"> 才算 HTML 导航页
        try:
            head = path.read_text(encoding='utf-8', errors='ignore')[:4096]
            if 'class="poi"' in head or 'class="poi ' in head:
                return 'html'
        except Exception:
            pass
        # 即使没识别到 .poi,也按 HTML 处理(让解析器报错给出明确提示)
        return 'html'
    if suffix in ('.md', '.markdown'):
        return 'markdown'
    if suffix == '.csv':
        return 'csv'
    if suffix == '.json':
        return 'json'
    return 'text'


# ============================================================
# 2. HTML 解析(trip-plan nav-template 格式)
# ============================================================

# 中文 tag → enum 映射
TAG_CN_TO_ENUM = {
    '起点': 'start',
    '终点': 'end',
    '回程': 'end',
    '景点': 'attract',
    '必看': 'attract',
    '地标': 'attract',
    '夜景': 'attract',
    '国宝': 'attract',
    '收尾': 'attract',
    '服务区': 'service',
    '加油': 'service',
    '路线': 'service',
    '购票': 'service',
    '购票·停': 'service',
    '餐厅': 'food',
    '首选': 'hotel',
    '住宿': 'hotel',
}

# 高德导航链接坐标提取
COORD_RE = re.compile(r'to=([-\d.]+),([-\d.]+)')


class TripPlanHTMLParser(HTMLParser):
    """trip-plan nav-template 格式的 HTML 解析器

    结构假设:
      <section class="day" id="dayN">
        <div class="day-title">
          <span class="day-num">D1</span>
          <div class="day-info">
            <h2>DAY_TITLE</h2>
            <div class="meta">DAY_DESC</div>
          </div>
        </div>
        <div class="group">...</div>
        <div class="poi">
          <div class="poi-name">POI_NAME <span class="tag TAG_CN">中文</span></div>
          <div class="poi-info">POI_INFO</div>
          <div class="poi-actions">
            <a class="btn-nav" href="uri.amap.com/navigation?to=LNG,LAT,...">...</a>
          </div>
        </div>
      </section>
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.pois = []
        self.days_summary = {}
        self.metadata = {}

        self._current_day = None           # e.g. 'D1'
        self._current_day_idx = 0          # POI 计数器(per day)

        self._in_day_section = False
        self._day_section_depth = 0

        self._current_poi = None
        self._in_poi = False
        self._poi_depth = 0

        self._capture_field = None         # 'poi_name' | 'poi_info' | 'day_title' | 'day_desc' | 'header_h1' | 'header_route' | 'header_meta' | None
        self._capture_buffer = ''

        self._in_header = False
        self._header_depth = 0
        self._in_tag_span = False
        self._tag_span_buffer = ''
        self._tag_span_classes = []

    # --- 元素开始 ---
    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        classes = attrs_dict.get('class', '').split()

        # 1. <section class="day" id="dayN">
        if tag == 'section' and 'day' in classes:
            elem_id = attrs_dict.get('id', '')
            m = re.search(r'day(\d+)', elem_id)
            day_num = m.group(1) if m else str(len(self.days_summary) + 1)
            self._current_day = f'D{day_num}'
            self._current_day_idx = 0
            self._in_day_section = True
            self._day_section_depth = 1
            self.days_summary[self._current_day] = {
                'title': '',
                'desc': '',
                'count': 0,
            }
            return

        # 1.5 <header> · 抽取 trip 标题 / 路线 / 总里程
        if tag == 'header' and not self.metadata.get('title'):
            self._in_header = True
            self._header_depth = 1
            return

        if self._in_header:
            self._header_depth += 1

            # <h1> · trip 标题
            if tag == 'h1':
                self._capture_field = 'header_h1'
                self._capture_buffer = ''

            # <p><span class="route">路线</span></p>
            elif tag == 'span' and 'route' in classes:
                self._capture_field = 'header_route'
                self._capture_buffer = ''

            # <p>总里程 / 时间提示</p>(第二个 p)
            elif tag == 'p' and 'route' not in [c for c in classes]:
                # 只在已经抓完 route 后才开始抓 meta
                if 'route' in self.metadata:
                    self._capture_field = 'header_meta'
                    self._capture_buffer = ''

            return  # header 内的其他标签不额外处理

        if self._in_day_section:
            self._day_section_depth += 1

            # 跟踪 .poi 内部嵌套 div 深度(关键修复)
            if self._in_poi and tag == 'div':
                self._poi_depth += 1

            # === poi handling ===
            # 2. <div class="day-info"> <h2>TITLE</h2>
            if tag == 'div' and 'day-info' in classes:
                self._capture_field = 'day_title'
                self._capture_buffer = ''

            # 3. <div class="meta">DESC</div>(在 day-info 之后)
            elif tag == 'div' and 'meta' in classes and self._capture_field in ('day_title_done', None):
                # 等 day_title 写完后再开始抓 desc
                if self._capture_field == 'day_title_done':
                    self._capture_field = 'day_desc'
                    self._capture_buffer = ''

            # 4. <div class="poi">
            elif tag == 'div' and 'poi' in classes and not self._in_poi:
                self._current_poi = {
                    'day': self._current_day,
                    'idx': self._current_day_idx + 1,
                    'name': '',
                    'tag': 'attract',
                    'info': '',
                    'lng_gcj02': 0.0,
                    'lat_gcj02': 0.0,
                    'lng_wgs84': None,  # 待 gcj02_wgs84.py 转换(None 触发下游填充)
                    'lat_wgs84': None,
                    'coord_source': 'fallback',
                }
                self._in_poi = True
                self._poi_depth = 1

            # 5. <div class="poi-name">...</div>
            elif self._in_poi and tag == 'div' and 'poi-name' in classes:
                self._capture_field = 'poi_name'
                self._capture_buffer = ''

            # 6. <div class="poi-info">...</div>
            elif self._in_poi and tag == 'div' and 'poi-info' in classes:
                self._capture_field = 'poi_info'
                self._capture_buffer = ''

            # 7. <span class="tag TAG_CN">
            elif self._in_poi and tag == 'span' and 'tag' in classes:
                self._in_tag_span = True
                self._tag_span_buffer = ''
                self._tag_span_classes = classes

            # 8. <a class="btn-nav" href="...">
            elif self._in_poi and tag == 'a' and 'btn-nav' in classes:
                href = attrs_dict.get('href', '')
                m = COORD_RE.search(href)
                if m and self._current_poi:
                    lng = float(m.group(1))
                    lat = float(m.group(2))
                    self._current_poi['lng_gcj02'] = lng
                    self._current_poi['lat_gcj02'] = lat
                    if lng != 0.0 or lat != 0.0:
                        self._current_poi['coord_source'] = 'original'

        if self._in_header and tag == 'div':
            self._header_depth += 1

    # --- 元素结束 ---
    def handle_endtag(self, tag):
        # 0. 关闭 tag span(独立处理,span 不影响 div 深度)
        if tag == 'span' and self._in_tag_span:
            tag_text = self._tag_span_buffer.strip()
            if self._current_poi:
                self._current_poi['tag'] = TAG_CN_TO_ENUM.get(tag_text, 'attract')
            self._in_tag_span = False
            self._tag_span_buffer = ''

        # 0.5 header 关闭
        if tag == 'header' and self._in_header:
            self._in_header = False
            self._header_depth = 0
            # 不 return:下面 day section 检查需要
            # 但因为 header 标签,实际上下一个标签可能是 </header> 之后的 <nav> 等
            # 这里依赖 depth 跟踪

        if self._in_header and tag == 'div':
            self._header_depth -= 1
            if self._header_depth == 0:
                self._in_header = False

        # header 内的捕获字段写入
        if self._capture_field == 'header_h1' and tag == 'h1':
            self.metadata['title'] = self._capture_buffer.strip()
            self._capture_field = None
            self._capture_buffer = ''
        elif self._capture_field == 'header_route' and tag == 'span':
            self.metadata['route_summary'] = self._capture_buffer.strip()
            self._capture_field = None
            self._capture_buffer = ''
        elif self._capture_field == 'header_meta' and tag == 'p':
            self.metadata['meta'] = self._capture_buffer.strip()
            self._capture_field = None
            self._capture_buffer = ''

        if self._in_header and tag != 'header':
            return

        if not self._in_day_section:
            return

        # 1. 减少 poi_depth(只在 div close 且在 poi 内时)
        if self._in_poi and tag == 'div':
            self._poi_depth -= 1

        # 2. 减少 day_section_depth
        self._day_section_depth -= 1

        # 3. .poi 自身关闭(poi_depth 归零)
        if self._in_poi and self._poi_depth == 0:
            if self._current_poi:
                # 入栈(name / info 已在 poi-name / poi-info 关闭时写入)
                self.pois.append(self._current_poi)
                self.days_summary[self._current_poi['day']]['count'] += 1
                self._current_day_idx += 1

            self._current_poi = None
            self._in_poi = False
            self._capture_field = None
            self._capture_buffer = ''
            self._tag_span_buffer = ''
            return

        # 4. day section 自身关闭
        if self._day_section_depth == 0 and tag == 'section':
            self._in_day_section = False
            self._current_day = None
            return

        # 5. 关闭 poi-name(在此处直接写入 name,避免 .poi 关闭时 buffer 已被清空)
        if tag == 'div' and self._capture_field == 'poi_name':
            if self._current_poi:
                # name 清洗:去除 tag 文本
                name_text = self._capture_buffer.strip()
                if self._tag_span_buffer:
                    name_text = name_text.replace(self._tag_span_buffer, '').strip()
                # fallback
                if not name_text:
                    name_text = f'未命名 POI {self._current_poi["idx"]}'
                self._current_poi['name'] = name_text
            self._capture_field = None
            self._capture_buffer = ''
            self._tag_span_buffer = ''

        # 6. 关闭 poi-info(直接写入 info)
        elif tag == 'div' and self._capture_field == 'poi_info':
            if self._current_poi:
                self._current_poi['info'] = self._capture_buffer.strip()
            self._capture_field = None
            self._capture_buffer = ''

        # 7. 关闭 day-info 的 h2(写入 title)
        elif tag == 'h2' and self._capture_field == 'day_title':
            if self._current_day:
                self.days_summary[self._current_day]['title'] = self._capture_buffer.strip()
            self._capture_field = 'day_title_done'
            self._capture_buffer = ''

        # 8. 关闭 meta(写入 desc)
        elif tag == 'div' and self._capture_field == 'day_desc':
            if self._current_day:
                self.days_summary[self._current_day]['desc'] = self._capture_buffer.strip()
            self._capture_field = None
            self._capture_buffer = ''

    # --- 文本数据 ---
    def handle_data(self, data):
        if self._in_tag_span:
            self._tag_span_buffer += data
        elif self._capture_field in ('poi_name', 'poi_info', 'day_title', 'day_desc',
                                      'header_h1', 'header_route', 'header_meta'):
            self._capture_buffer += data


def parse_html(content: str) -> dict:
    """解析 trip-plan 格式的 HTML 导航页 → pois.json 结构"""
    parser = TripPlanHTMLParser()
    parser.feed(content)

    if not parser.pois:
        print('WARN: 未抽取到任何 POI。请确认 HTML 含 <div class="poi"> 节点(本解析器只识别 trip-plan nav-template 格式)。', file=sys.stderr)

    return {
        'pois': parser.pois,
        'day_routes_wgs84': {},
        'special_routes_wgs84': [],
        'days_summary': parser.days_summary,
        'metadata': parser.metadata,
    }


# ============================================================
# 3. Markdown 解析
# ============================================================

DAY_MD_RE = re.compile(
    r'(?:^|\s)(D\d+|Day\s*(\d+)|第\s*([一二三四五六七八九十]+)\s*天)(?:[^\n]*)',
    re.IGNORECASE
)
COORD_MD_RE = re.compile(r'uri\.amap\.com/navigation\?to=([-\d.]+),([-\d.]+)')
NAME_MD_RE = re.compile(r'(?:\*\*|##+)\s*([^*\n#]+?)(?:\*\*|$)')

CN_NUM = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
          '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}


def _detect_md_day(text: str) -> str:
    m = DAY_MD_RE.search(text)
    if not m:
        return None
    if m.group(1).lower().startswith('d'):
        return m.group(1).upper()
    if m.group(2):
        return f'D{m.group(2)}'
    if m.group(3) and m.group(3) in CN_NUM:
        return f'D{CN_NUM[m.group(3)]}'
    return None


def _infer_md_tag(line: str) -> str:
    """从上下文推断 tag"""
    if any(kw in line for kw in ('酒店', '民宿', '宾馆', '入住')):
        return 'hotel'
    if any(kw in line for kw in ('餐厅', '饭', '午饭', '晚饭', '早餐', '早餐', '素斋', '吃')):
        return 'food'
    if any(kw in line for kw in ('服务区', '加油', '充电')):
        return 'service'
    if any(kw in line for kw in ('起点', '出发', '起早')):
        return 'start'
    if any(kw in line for kw in ('返', '回程', '终点', '回京')):
        return 'end'
    return 'attract'


def parse_markdown(content: str) -> dict:
    """解析 Markdown 攻略 → pois.json 结构(启发式,精度有限)"""
    pois = []
    current_day = 'D1'
    day_idx = 0

    for line in content.split('\n'):
        line = line.strip()
        if not line:
            continue

        # Day 切换
        detected_day = _detect_md_day(line)
        if detected_day:
            current_day = detected_day
            day_idx = 0
            continue

        # POI 抽取:含高德链接的行
        coord_m = COORD_MD_RE.search(line)
        if coord_m:
            lng = float(coord_m.group(1))
            lat = float(coord_m.group(2))
            coord_source = 'known' if (lng != 0 or lat != 0) else 'fallback'

            # 提取 name
            name_m = NAME_MD_RE.search(line)
            name = name_m.group(1).strip() if name_m else '未命名 POI'

            # 清理 name 里的 URL / 时间标记
            name = re.sub(r'\[.*?\]\(.*?\)', '', name).strip()
            name = re.sub(r'⏰\s*\S+', '', name).strip()

            day_idx += 1
            pois.append({
                'day': current_day,
                'idx': day_idx,
                'name': name,
                'tag': _infer_md_tag(line),
                'info': line,
                'lng_gcj02': lng,
                'lat_gcj02': lat,
                'lng_wgs84': None,  # 待 gcj02_wgs84.py 转换
                'lat_wgs84': None,
                'coord_source': coord_source,
            })
            continue

        # 列表项但没链接:fallback 坐标,候选 POI
        if line.startswith(('-', '*', '+')) or re.match(r'^\d+\.', line):
            # 启发式:含时间或地名的算 POI
            if re.search(r'(\d{1,2}:\d{2}|景点|寺|庙|峰|湖|寺|公园|博物馆|酒店|餐厅|服务区)', line):
                name_m = re.search(r'\*\*([^*]+)\*\*', line)
                if name_m:
                    day_idx += 1
                    pois.append({
                        'day': current_day,
                        'idx': day_idx,
                        'name': name_m.group(1).strip()[:30],
                        'tag': _infer_md_tag(line),
                        'info': line.lstrip('- *+0123456789. ').strip(),
                        'lng_gcj02': 0.0,
                        'lat_gcj02': 0.0,
                        'lng_wgs84': None,  # 待 gcj02_wgs84.py 转换
                        'lat_wgs84': None,
                        'coord_source': 'fallback',
                    })

    # 汇总
    days_summary = {}
    for p in pois:
        d = p['day']
        if d not in days_summary:
            days_summary[d] = {'title': d, 'desc': '', 'count': 0}
        days_summary[d]['count'] += 1

    if not pois:
        print('WARN: 未抽取到任何 POI。建议:(1) 检查 Day 标记格式(支持 D1/Day 1/第一天);(2) 检查是否含高德链接或 POI 名称列表项;(3) 走 LLM 辅助流程。', file=sys.stderr)

    return {
        'pois': pois,
        'day_routes_wgs84': {},
        'special_routes_wgs84': [],
        'days_summary': days_summary,
    }


# ============================================================
# 4. CSV 解析
# ============================================================

def parse_csv(path: Path) -> dict:
    """解析 CSV → pois.json 结构"""
    pois = []
    with path.open('r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, 1):
            lng_str = row.get('lng', '0') or '0'
            lat_str = row.get('lat', '0') or '0'
            try:
                lng = float(lng_str)
                lat = float(lat_str)
            except ValueError:
                lng, lat = 0.0, 0.0

            coord_source = (row.get('coord_source', 'fallback') or 'fallback').strip()
            if coord_source not in ('original', 'known', 'fallback'):
                coord_source = 'fallback'

            tag = (row.get('tag', 'attract') or 'attract').strip()
            if tag not in ('start', 'end', 'attract', 'hotel', 'food', 'service', 'stop'):
                tag = 'attract'

            day = (row.get('day', 'D1') or 'D1').strip()
            if not re.match(r'^D\d+$', day):
                day = 'D1'

            try:
                poi_idx = int(row.get('idx', idx))
            except ValueError:
                poi_idx = idx

            # 判断 WGS-84 是否由 CSV 提供(可省略 → None,待 gcj02_wgs84.py 转换)
            has_wgs = row.get('lng_wgs84') not in (None, '', '0', '0.0')
            lng_wgs = None
            lat_wgs = None
            if has_wgs:
                try:
                    lng_wgs = float(row.get('lng_wgs84'))
                    lat_wgs = float(row.get('lat_wgs84'))
                except (ValueError, TypeError):
                    pass

            pois.append({
                'day': day,
                'idx': poi_idx,
                'name': (row.get('name', '') or '').strip(),
                'tag': tag,
                'info': (row.get('info', '') or '').strip(),
                'lng_gcj02': lng,
                'lat_gcj02': lat,
                'lng_wgs84': lng_wgs,  # None = 待 gcj02_wgs84.py 转换
                'lat_wgs84': lat_wgs,
                'coord_source': coord_source,
            })

    days_summary = {}
    for p in pois:
        d = p['day']
        if d not in days_summary:
            days_summary[d] = {'title': d, 'desc': '', 'count': 0}
        days_summary[d]['count'] += 1

    return {
        'pois': pois,
        'day_routes_wgs84': {},
        'special_routes_wgs84': [],
        'days_summary': days_summary,
    }


# ============================================================
# 5. JSON 透传
# ============================================================

def parse_json(path: Path) -> dict:
    """JSON 透传 + 最小校验"""
    with path.open('r', encoding='utf-8') as f:
        data = json.load(f)

    if not isinstance(data, dict):
        print('ERROR: JSON 顶层必须是 object', file=sys.stderr)
        sys.exit(1)
    if 'pois' not in data:
        print('ERROR: JSON 不含 pois 字段', file=sys.stderr)
        sys.exit(1)
    if 'days_summary' not in data:
        data['days_summary'] = {}
    if 'day_routes_wgs84' not in data:
        data['day_routes_wgs84'] = {}
    if 'special_routes_wgs84' not in data:
        data['special_routes_wgs84'] = []

    return data


# ============================================================
# 6. 自由文本 → LLM prompt 引导
# ============================================================

LLM_PROMPT_TEMPLATE = '''
──────────────────────────────────────────────────────────────
[parse_input] 检测到自由文本,建议走 LLM 辅助抽取流程
──────────────────────────────────────────────────────────────

下面这段文本无法自动结构化。请用 LLM(我 / Claude / GPT)抽成 CSV,然后再喂 parse_input.py。

【Prompt 模板 · 直接复制使用】

从下面这段旅行描述里,抽取所有 POI(景点 / 餐厅 / 酒店 / 服务区 / 起点终点)。

要求输出 CSV 格式,字段:day,idx,name,tag,info
- day: D1 / D2 / D3 ...,从"第 X 天"/"D1"等标记推断
- idx: Day 内序号,从 1 开始
- name: POI 名称(直接用文中名字)
- tag: 7 选 1(attract / hotel / food / service / start / end / stop)
- info: 时间 / 玩法 / 注意事项(原文照抄关键信息)

不需要写坐标(脚本会兜底)。仅输出 CSV 内容,不要其他说明。

[原始文本]
<贴文本>

──────────────────────────────────────────────────────────────

【处理步骤】

1. 把上面的 <贴文本> 替换成你的实际内容
2. 让 LLM 输出 CSV 内容(标准 markdown 代码块)
3. 复制 CSV 内容保存为 extracted.csv
4. 跑:
     python parse_input.py extracted.csv -o pois.json --form csv
5. 走 validate.py → gcj02_wgs84.py → gen_trip_artifacts.py 标准流程

【其他 prompt 变体】

- 长文章:在 prompt 前加 "这是博客攻略长文,请只提取实际要去的地方"
- HTML 源码:加 "解析 HTML 时跳过装饰元素,只保留具体地点名称和时间"
- 含坐标:加 "如有坐标,加 lng,lat 列(GCJ-02);coord_source: original/known/fallback"

详见 references/input-format.md §6
──────────────────────────────────────────────────────────────
'''


def handle_text(path: Path) -> dict:
    """自由文本:打印 LLM prompt 模板,引导用户走 LLM 辅助流程"""
    print(LLM_PROMPT_TEMPLATE, file=sys.stderr)
    print(f'\n输入文件: {path} ({path.stat().st_size} bytes)', file=sys.stderr)
    sys.exit(2)


# ============================================================
# 7. 入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description='trip-plan 输入适配器:任意形式 → pois.json',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='示例:\n'
               '  python parse_input.py trip.html -o pois.json\n'
               '  python parse_input.py trip.md -o pois.json\n'
               '  python parse_input.py trip.csv -o pois.json\n'
               '  python parse_input.py notes.txt   # 打印 LLM prompt 模板\n'
               '  python parse_input.py pois.json --validate\n',
    )
    parser.add_argument('input', help='输入文件路径(HTML / MD / CSV / JSON / 文本)')
    parser.add_argument('-o', '--output', default='pois.json', help='输出 JSON 路径(默认: pois.json)')
    parser.add_argument('--form', choices=['auto', 'html', 'markdown', 'csv', 'json', 'text'],
                        default='auto', help='强制指定输入形式(默认: auto 自动识别)')
    parser.add_argument('--validate', action='store_true', help='生成后立即跑 validate.py 校验')
    parser.add_argument('--src', default='yourtag', help='高德 utm src(占位,生成产物时用)')
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f'ERROR: 输入文件不存在: {input_path}', file=sys.stderr)
        sys.exit(1)

    # 1. 检测形式
    form = args.form if args.form != 'auto' else detect_form(input_path)
    print(f'[parse_input] 检测到形式: {form}', file=sys.stderr)

    # 2. 解析
    if form == 'html':
        content = input_path.read_text(encoding='utf-8')
        data = parse_html(content)
    elif form == 'markdown':
        content = input_path.read_text(encoding='utf-8')
        data = parse_markdown(content)
    elif form == 'csv':
        data = parse_csv(input_path)
    elif form == 'json':
        data = parse_json(input_path)
    elif form == 'text':
        handle_text(input_path)
    else:
        print(f'ERROR: 不支持的 form: {form}', file=sys.stderr)
        sys.exit(1)

    # 3. 输出
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open('w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # 4. 统计
    n_pois = len(data.get('pois', []))
    n_days = len(data.get('days_summary', {}))
    fallback = sum(1 for p in data.get('pois', []) if p.get('coord_source') == 'fallback')
    original = sum(1 for p in data.get('pois', []) if p.get('coord_source') == 'original')
    known = n_pois - fallback - original
    print(f'[parse_input] 输出: {output_path}', file=sys.stderr)
    print(f'[parse_input] POI: {n_pois} | Day: {n_days} | 坐标: original={original} known={known} fallback={fallback}', file=sys.stderr)

    # 5. 可选校验
    if args.validate:
        try:
            from validate import validate_data
            result = validate_data(data)
            if result.errors:
                print(f'[parse_input] validate.py 错误: {len(result.errors)}', file=sys.stderr)
                for e in result.errors:
                    print(f'  ✗ {e}', file=sys.stderr)
            if result.warnings:
                print(f'[parse_input] validate.py 警告: {len(result.warnings)}', file=sys.stderr)
                for w in result.warnings[:10]:  # 只显示前 10 个
                    print(f'  ⚠ {w}', file=sys.stderr)
                if len(result.warnings) > 10:
                    print(f'  ... 还有 {len(result.warnings) - 10} 个警告', file=sys.stderr)
            if result.ok:
                print('[parse_input] ✅ validate.py 通过', file=sys.stderr)
            else:
                print('[parse_input] ❌ validate.py 失败', file=sys.stderr)
        except ImportError:
            print('[parse_input] WARN: validate.py 不可用,跳过', file=sys.stderr)

    # 6. 打印 POI 清单供肉眼复核
    print('\n# POI 清单(供肉眼复核):')
    print(f'{"Day":4s} {"#":3s} {"Tag":10s} {"Name":35s} {"Coord":>22s} {"Src":10s}')
    print('-' * 90)
    for p in data.get('pois', []):
        lng = p.get('lng_gcj02', 0)
        lat = p.get('lat_gcj02', 0)
        coord = f'({lng:.4f}, {lat:.4f})' if (lng or lat) else '(no coord)'
        name = p['name'][:33] + '..' if len(p['name']) > 35 else p['name']
        print(f'{p["day"]:4s} {p["idx"]:<3d} {p["tag"]:10s} {name:35s} {coord:>22s} {p.get("coord_source", ""):10s}')

    return 0


if __name__ == '__main__':
    sys.exit(main() or 0)