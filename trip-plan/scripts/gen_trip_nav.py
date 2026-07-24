#!/usr/bin/env python3
"""
trip-plan 导航点位页生成器(完整实现)

从 pois.json 生成完整 nav.html,支持:
- 按 Day 分组
- 按 tag 自动分组(出发/服务区/景点/住宿/餐厅/返程)
- 有/无坐标 POI 区分(3 按钮 vs 2 按钮)
- 高德直接 href(无 JS 异步)
- 自定义 src(utm 标记)
"""
import json
import math
import urllib.parse
from pathlib import Path
from collections import defaultdict


# ============================================================
# 路线距离/时长/通行费计算（Haversine + 高速估算）
# ============================================================

def _haversine_km(lng1, lat1, lng2, lat2):
    """Haversine 公式计算两点间直线距离(km)"""
    R = 6371.0  # 地球半径 km
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def calc_route_estimate(lng1, lat1, lng2, lat2):
    """估算自驾路线（高速优先）的里程/时长/通行费

    使用 Haversine 直线距离 × 1.35 作为高速路线系数
    时长 = 里程 / 90km/h（高速均速）
    通行费 = 里程 × ¥0.55/km（全国高速均价）
    """
    straight_km = _haversine_km(lng1, lat1, lng2, lat2)
    highway_km = round(straight_km * 1.35)
    minutes = round(highway_km / 90 * 60)
    toll = round(highway_km * 0.55)
    return highway_km, minutes, toll


# 标签分组顺序 + 显示名 + emoji
TAG_GROUP_ORDER = ['start', 'service', 'attract', 'hotel', 'food', 'end', 'stop']
TAG_GROUP_NAMES = {
    'start': '出发',
    'service': '服务区/中转',
    'attract': '景点',
    'hotel': '住宿',
    'food': '餐厅',
    'end': '返程',
    'stop': '驿站',
}
TAG_EMOJI = {
    'start': '🏁',
    'service': '⛽',
    'attract': '🏛',
    'hotel': '🏨',
    'food': '🍜',
    'end': '🏠',
    'stop': '🚏',
}

# 中文 tag 显示(保留原始 HTML 的中文 tag,提升肉眼可读性)
TAG_CN = {
    'start': '起点',
    'end': '回程',
    'attract': '景点',
    'hotel': '首选',
    'food': '餐厅',
    'service': '服务区',
    'stop': '驿站',
}


def _precalc_route_info(day_pois):
    """为某天所有 POI 计算路线距离/时长/通行费(写入 route_km / route_min / route_toll)

    优先使用高德 API 真实数据(route_km 已存在则跳过 Haversine 估算)
    """
    prev = None
    for p in day_pois:
        tag = p.get('tag', '')
        lng = p.get('lng_gcj02', 0.0)
        lat = p.get('lat_gcj02', 0.0)

        # 如果已有高德 API 数据，只更新 prev 指针，不做计算
        if p.get('route_km', 0) > 0:
            prev = p
            continue

        if tag == 'start' or (lng == 0.0 and lat == 0.0):
            prev = p
            continue
        if prev and lng and lat:
            plng = prev.get('lng_gcj02', 0.0)
            plat = prev.get('lat_gcj02', 0.0)
            if plng and plat and not p.get('route_km', 0):
                km, mins, toll = calc_route_estimate(plng, plat, lng, lat)
                p['route_km'] = km
                p['route_min'] = mins
                p['route_toll'] = toll
        prev = p


def gen_poi_card(poi: dict, amap_src: str) -> str:
    """生成单个 POI 卡片(2 按钮 or 3 按钮,取决于是否有坐标)"""
    name = poi.get('name', '未命名')
    name_enc = urllib.parse.quote(name, safe='')
    tag = poi.get('tag', 'attract')
    tag_cn = TAG_CN.get(tag, tag)
    info = poi.get('info', '')
    lng = poi.get('lng_gcj02', 0.0)
    lat = poi.get('lat_gcj02', 0.0)
    coord_source = poi.get('coord_source', 'fallback')

    # 真实坐标判定:坐标非零 + 非 fallback 来源
    has_coord = (lng != 0.0 or lat != 0.0) and coord_source != 'fallback'

    # 路线信息（导航距离/时长/通行费 + 可选路线卡片截图）
    route_info_html = ''
    route_distance = poi.get('route_km', 0)
    route_duration = poi.get('route_min', 0)
    route_toll = poi.get('route_toll', 0)
    route_card = poi.get('route_card_screenshot', '')
    map_shot = poi.get('map_screenshot', '')

    if map_shot:
        # 🌟 地图路线全览截图（含路线 + 距离/时长/通行费浮窗）
        route_info_html = (
            f'      <img class="poi-route-map" src="{map_shot}" '
            f'alt="导航路线" loading="lazy">\n'
        )
    elif route_card:
        # 旧格式：路线信息卡片截图
        route_info_html = (
            f'      <img class="poi-route-img" src="{route_card}" '
            f'alt="导航路线" loading="lazy">\n'
        )
    elif route_distance > 0:
        # 无截图时回退文字信息条
        duration_str = f'{route_duration // 60}h{route_duration % 60:02d}min' if route_duration >= 60 else f'{route_duration}min'
        toll_str = f'¥{route_toll}' if route_toll > 0 else ''
        route_info_html = (
            f'      <div class="poi-route-info">\n'
            f'        <span class="ri-dist">🛣️ {route_distance}km</span>\n'
            f'        <span class="ri-time">⏱️ {duration_str}</span>\n'
        )
        if toll_str:
            route_info_html += f'        <span class="ri-toll">💰 {toll_str}</span>\n'
        route_info_html += f'      </div>\n'

    # 按钮 HTML
    actions = []
    if has_coord:
        # 有坐标:3 按钮
        actions.append(
            f'    <a class="btn-nav" target="_blank" '
            f'href="https://uri.amap.com/navigation?to={lng},{lat},{name_enc}&mode=car&src={amap_src}">🚗 导航</a>\n'
        )
        actions.append(
            f'    <a class="btn-marker" target="_blank" '
            f'href="https://uri.amap.com/marker?markers={lng},{lat},{name_enc}&src={amap_src}">📍 标记位置</a>\n'
        )
        actions.append(
            f'    <a class="btn-search" target="_blank" '
            f'href="https://uri.amap.com/search?keyword={name_enc}&src={amap_src}">🔍 搜索</a>\n'
        )
    else:
        # 无坐标:2 按钮(0,0 替代 + 搜索)
        actions.append(
            f'    <a class="btn-nav" target="_blank" '
            f'href="https://uri.amap.com/navigation?to=0,0,{name_enc}&mode=car&src={amap_src}">🚗 导航</a>\n'
        )
        actions.append(
            f'    <a class="btn-search" target="_blank" '
            f'href="https://uri.amap.com/search?keyword={name_enc}&src={amap_src}">🔍 搜索</a>\n'
        )

    # 半透明标记(fallback 坐标提示)
    opacity_style = ' style="opacity:0.7;"' if coord_source == 'fallback' else ''

    return (
        f'    <div class="poi"{opacity_style}>\n'
        f'      <div class="poi-name">{name}\n'
        f'        <span class="tag {tag}">{tag_cn}</span>\n'
        f'      </div>\n'
        f'      <div class="poi-info">{info}</div>\n'
        + route_info_html +
        f'      <div class="poi-actions">\n'
        + ''.join(actions) +
        f'      </div>\n'
        f'    </div>\n'
    )


def gen_day_section(day_key: str, day_pois: list, data: dict, amap_src: str) -> str:
    """生成单个 Day section(按 tag 自动分组)"""
    _precalc_route_info(day_pois)
    day_num = int(day_key[1:])  # D1 → 1
    day_summary = data.get('days_summary', {}).get(day_key, {})
    day_title = day_summary.get('title', day_key)
    day_desc = day_summary.get('desc', '')

    # 按 tag 分组
    groups = defaultdict(list)
    for p in day_pois:
        groups[p.get('tag', 'attract')].append(p)

    # 按 TAG_GROUP_ORDER 顺序生成 group
    group_html_parts = []
    for tag in TAG_GROUP_ORDER:
        if tag not in groups:
            continue
        tag_pois = groups[tag]
        group_name = TAG_GROUP_NAMES.get(tag, tag)
        emoji = TAG_EMOJI.get(tag, '📍')

        # group title(数量提示)
        count_hint = f'（{len(tag_pois)} 个）' if len(tag_pois) > 1 and tag == 'attract' else ''

        group_html_parts.append(
            f'  <div class="group">\n'
            f'    <div class="group-title"><span class="emoji">{emoji}</span>{group_name}{count_hint}</div>\n'
            + ''.join(gen_poi_card(p, amap_src) for p in tag_pois) +
            f'  </div>\n'
        )

    return (
        f'<section class="day" id="day{day_num}">\n'
        f'  <div class="day-title">\n'
        f'    <span class="day-num">{day_key}</span>\n'
        f'    <div class="day-info">\n'
        f'      <h2>{day_title}</h2>\n'
        f'      <div class="meta">{day_desc}</div>\n'
        f'    </div>\n'
        f'    <span class="route-arrow">→</span>\n'
        f'  </div>\n'
        + ''.join(group_html_parts) +
        f'</section>\n'
    )


# ============================================================
# 模板(内嵌,不依赖外部 nav-template.html)
# ============================================================

NAV_HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<meta name="apple-mobile-web-app-capable" content="yes">
<title>🚗 {trip_title} · 高德导航点位</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
html {{ -webkit-text-size-adjust: 100%; }}

body {{
  font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
  font-size: 15px;
  line-height: 1.5;
  color: #1a1a1a;
  background: #f5f6f8;
  padding-bottom: 60px;
  -webkit-font-smoothing: antialiased;
}}

header {{
  background: linear-gradient(135deg, #FF6F00 0%, #FF8F00 100%);
  color: white;
  padding: 20px 18px 18px;
  position: sticky;
  top: 0;
  z-index: 100;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}}
header h1 {{ font-size: 18px; font-weight: 600; margin-bottom: 6px; }}
header p {{ font-size: 12px; opacity: 0.95; }}
header p .route {{ font-weight: 600; }}

.day-nav {{
  background: white;
  padding: 10px 12px;
  overflow-x: auto;
  white-space: nowrap;
  position: sticky;
  top: 76px;
  z-index: 99;
  border-bottom: 1px solid #e8eaec;
  -webkit-overflow-scrolling: touch;
}}
.day-nav::-webkit-scrollbar {{ display: none; }}
.day-nav a {{
  display: inline-block;
  padding: 6px 12px;
  margin-right: 6px;
  background: #f0f1f3;
  color: #555;
  border-radius: 14px;
  text-decoration: none;
  font-size: 12px;
  font-weight: 500;
  transition: all 0.2s;
}}
.day-nav a.active, .day-nav a:active {{
  background: #FF6F00;
  color: white;
}}

.day {{ padding: 16px 14px; }}

.day-title {{
  display: flex;
  align-items: center;
  margin-bottom: 14px;
  padding: 10px 14px;
  background: linear-gradient(to right, #fff5e6, white);
  border-left: 5px solid #FF6F00;
  border-radius: 4px;
}}
.day-title .day-num {{ font-size: 20px; font-weight: 700; color: #FF6F00; margin-right: 10px; }}
.day-title .day-info {{ flex: 1; }}
.day-title h2 {{ font-size: 15px; font-weight: 600; color: #1a1a1a; margin-bottom: 2px; }}
.day-title .meta {{ font-size: 11px; color: #888; }}
.day-title .route-arrow {{ font-size: 16px; color: #FF6F00; font-weight: 600; }}

.group {{ margin-bottom: 18px; }}
.group-title {{
  font-size: 13px; font-weight: 600; color: #555; margin-bottom: 8px; padding: 0 4px;
  display: flex; align-items: center;
}}
.group-title .emoji {{ margin-right: 6px; font-size: 15px; }}

.poi {{
  background: white;
  border-radius: 10px;
  padding: 12px 14px;
  margin-bottom: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  border: 1px solid #ecedef;
}}

.poi-name {{
  font-size: 15px; font-weight: 600; color: #1a1a1a; margin-bottom: 4px;
  display: flex; align-items: center; justify-content: space-between;
}}
.poi-name .tag {{
  font-size: 10px; font-weight: 500; padding: 2px 7px;
  border-radius: 10px; white-space: nowrap; margin-left: 8px;
}}

.tag.attract   {{ background: #fef0ef; color: #c7392b; }}
.tag.hotel     {{ background: #f0ecfa; color: #6b46c1; }}
.tag.food      {{ background: #fff5e8; color: #d97706; }}
.tag.service   {{ background: #e0f0fc; color: #2563eb; }}
.tag.optional  {{ background: #f0f9ff; color: #0891b2; }}
.tag.peak      {{ background: #fff8e1; color: #f57f17; }}
.tag.stop      {{ background: #e3f2fd; color: #1565c0; }}
.tag.start     {{ background: #e8f5e9; color: #2d7d46; }}
.tag.end       {{ background: #fce4ec; color: #c62828; }}

.poi-info {{
  font-size: 12px;
  color: #888;
  margin-bottom: 10px;
  line-height: 1.5;
}}
.poi-info .price {{ color: #FF6F00; font-weight: 600; }}

.poi-actions {{
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}}
.poi-actions a {{
  flex: 1 1 calc(50% - 3px);
  min-width: 88px;
  display: block;
  text-align: center;
  padding: 8px 4px;
  border-radius: 6px;
  text-decoration: none;
  font-size: 13px;
  font-weight: 500;
  -webkit-tap-highlight-color: transparent;
  transition: opacity 0.2s;
}}
.poi-actions a:active {{ opacity: 0.7; }}

/* ========== 地图路线截图(响应式+lightbox) ========== */
.poi-route-map {{
  width: 100%;
  display: block;
  border-radius: 10px;
  margin: 6px 0 10px;
  border: 1px solid #e8eaec;
  cursor: pointer;
}}
.poi-route-map:active {{ transform: scale(0.97); }}

/* ========== 路线信息卡片截图(旧格式) ========== */
.poi-route-img {{
  width: 100%;
  display: block;
  border-radius: 8px;
  margin: 6px 0 10px;
  border: 1px solid #f0eae2;
}}
.poi-route-info {{
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin: 6px 0 10px;
  padding: 8px 10px;
  background: #fffaf0;
  border-radius: 6px;
  border: 1px solid #fff0d6;
  font-size: 12px;
}}
.poi-route-info span {{
  display: inline-flex;
  align-items: center;
  white-space: nowrap;
}}
.poi-route-info .ri-dist {{ color: #2563eb; font-weight: 600; }}
.poi-route-info .ri-time {{ color: #7B1FA2; font-weight: 600; }}
.poi-route-info .ri-toll {{ color: #c7392b; font-weight: 600; }}

.btn-nav    {{ background: #FF6F00; color: white; }}
.btn-marker {{ background: #f0f1f3; color: #555; }}
.btn-search {{ background: #e8eaec; color: #555; }}

.usage {{
  background: white;
  padding: 16px;
  border-radius: 10px;
  margin: 16px 14px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}}
.usage h3 {{
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 8px;
  color: #FF6F00;
}}
.usage ol {{
  padding-left: 22px;
  font-size: 13px;
  color: #555;
  line-height: 1.7;
}}
.usage .tip {{
  margin-top: 10px;
  font-size: 12px;
  color: #888;
  padding: 8px 10px;
  background: #fff8e1;
  border-radius: 6px;
}}

.to-top {{
  position: fixed;
  bottom: 20px;
  right: 20px;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: #FF6F00;
  color: white;
  border: none;
  font-size: 18px;
  font-weight: 600;
  box-shadow: 0 3px 10px rgba(0, 0, 0, 0.2);
  cursor: pointer;
  z-index: 50;
}}

/* ========== Lightbox 全屏预览 ========== */
.lightbox-overlay {{
  position: fixed;
  top: 0; left: 0; width: 100%; height: 100%;
  background: rgba(0,0,0,0.85);
  z-index: 99999;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: zoom-out;
}}
.lightbox-overlay img {{
  max-width: 95vw;
  max-height: 95vh;
  border-radius: 8px;
  box-shadow: 0 8px 40px rgba(0,0,0,0.4);
}}
</style>
</head>
<body>

<!-- ========== 顶部 ========== -->
<header>
  <h1>🚗 {trip_title}</h1>
  <p><span class="route">{route_summary}</span></p>
  <p style="margin-top:4px;">{day_count} 天 · {poi_count} POI · 点击任意点位 → 高德 App 自动导航</p>
</header>

<!-- 日期快速跳转 -->
<nav class="day-nav" id="dayNav">
{day_nav_links}
</nav>

<!-- ========== Day 区段 ========== -->
{day_sections}

<!-- ========== 使用说明 ========== -->
<section class="usage">
  <h3>📱 使用说明</h3>
  <ol>
    <li><b>🚗 导航</b> · 所有点位都有 · 高德自动 fallback name 搜索定位</li>
    <li><b>🔍 搜索</b> · 所有点位都有 · 查同名 POI / 收藏 / 二次确认</li>
    <li><b>📍 标记位置</b> · 仅坐标精准的点有 · 地图上精准标点</li>
    <li>手机点按钮会唤起高德 App；未装则跳网页版</li>
  </ol>
  <div class="tip">
    💡 <b>坐标质量提示</b> · 半透明的卡片为 fallback 坐标,真实出行前建议用 web_search 校核到 known 级别
  </div>
</section>

<button class="to-top" onclick="window.scrollTo({{top:0,behavior:'smooth'}})">↑</button>

<script>
const navLinks = document.querySelectorAll('.day-nav a');
const sections = document.querySelectorAll('.day');

navLinks.forEach(link => {{
  link.addEventListener('click', (e) => {{
    navLinks.forEach(l => l.classList.remove('active'));
    e.target.classList.add('active');
  }});
}});

const observer = new IntersectionObserver((entries) => {{
  entries.forEach(entry => {{
    if (entry.isIntersecting) {{
      const id = entry.target.id;
      navLinks.forEach(l => {{
        l.classList.toggle('active', l.getAttribute('href') === '#' + id);
      }});
    }}
  }});
}}, {{ rootMargin: '-30% 0px -50% 0px' }});

sections.forEach(s => observer.observe(s));

// Lightbox: 点击地图路线截图全屏查看
const routeImgs = document.querySelectorAll('.poi-route-map');
routeImgs.forEach(img => {{
  img.addEventListener('click', () => {{
    const lb = document.createElement('div');
    lb.className = 'lightbox-overlay';
    const lbImg = document.createElement('img');
    lbImg.src = img.src;
    lb.appendChild(lbImg);
    lb.onclick = () => lb.remove();
    document.body.appendChild(lb);
  }});
}});
</script>

</body>
</html>
'''


def gen_trip_nav(data: dict, output_path, amap_src='yourtag') -> str:
    """从 pois.json 生成完整 nav.html

    Args:
        data: pois.json 解析后的 dict(含 pois / days_summary)
             可选 route_screenshots dict: {"D1_1": {"path": "...", "from": "...", "to": "..."}}
        output_path: 输出 HTML 路径
        amap_src: 高德 utm src 参数

    Returns:
        生成的 HTML 字符串
    """
    pois = sorted(data['pois'], key=lambda p: (p['day'], p.get('idx', 0)))
    days = sorted(set(p['day'] for p in pois))
    n_days = len(days)
    n_pois = len(pois)

    # 按 day 分组
    day_groups = {}
    for p in pois:
        day_groups.setdefault(p['day'], []).append(p)

    # 顶部信息
    metadata = data.get('metadata', {})
    trip_title = metadata.get('title', '示例行程')
    # 去重前缀 emoji(模板会加 🚗)
    import re as _re
    trip_title = _re.sub(r'^[🚗🚙🏍️🚕]+\s*', '', trip_title).strip()
    route_summary = metadata.get('route_summary') or metadata.get('description', '自驾行程')

    # 生成 day-nav 链接
    day_nav_links = []
    for day in days:
        day_title = data.get('days_summary', {}).get(day, {}).get('title', day)
        # 截短标题(避免太长)
        short_title = day_title[:20] + '..' if len(day_title) > 20 else day_title
        day_num = int(day[1:])
        day_nav_links.append(
            f'  <a href="#day{day_num}">{day} {short_title}</a>'
        )
    day_nav_html = '\n'.join(day_nav_links)

    # 生成 Day sections
    day_sections_html = []
    for day in days:
        day_sections_html.append(gen_day_section(day, day_groups[day], data, amap_src))
    day_sections = '\n'.join(day_sections_html)

    # 替换占位符
    html = NAV_HTML_TEMPLATE.format(
        trip_title=trip_title,
        route_summary=route_summary,
        day_count=n_days,
        poi_count=n_pois,
        day_nav_links=day_nav_html,
        day_sections=day_sections,
    )

    # 写入
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(html, encoding='utf-8')

    print(f'  nav: {output_path} ({Path(output_path).stat().st_size // 1024}KB)')
    return html


# ============================================================
# CLI 测试
# ============================================================

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 3:
        print('Usage: gen_trip_nav.py <pois.json> <output.html> [--src TAG]')
        sys.exit(1)

    pois_path = sys.argv[1]
    output_path = sys.argv[2]
    src = 'momotrip'
    if '--src' in sys.argv:
        src = sys.argv[sys.argv.index('--src') + 1]

    with open(pois_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    gen_trip_nav(data, output_path, amap_src=src)