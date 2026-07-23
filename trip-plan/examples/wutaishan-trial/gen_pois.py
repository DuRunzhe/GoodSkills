#!/usr/bin/env python3
"""
生成 wutaishan-trial/pois.json (filled) 或 wutaishan-trial-template/pois.template.json (template)
- WGS-84 近似坐标(基于公开资料 · 五台山寺院群公开数据)
- inline GCJ-02 转换(中国境内 +0.002~0.006 度偏移)
- 20 POI 覆盖 4 必去点 + 5 加分项 + 起返 + 具体餐厅 + 服务区 + 酒店

用法:
  python3 gen_pois.py                       # filled 模式 → wutaishan-trial/pois.json
  python3 gen_pois.py --mode template      # template 模式 → wutaishan-trial-template/pois.template.json
"""
import json
import math
import sys
from pathlib import Path

PI = 3.1415926535897932384626
A = 6378245.0
EE = 0.00669342162296594323


def out_of_china(lng, lat):
    return not (72.004 <= lng <= 137.8347 and 0.8293 <= lat <= 55.8271)


def _transform_lat(x, y):
    ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * math.sqrt(abs(x))
    ret += (20.0 * math.sin(6.0 * x * PI) + 20.0 * math.sin(2.0 * x * PI)) * 2.0 / 3.0
    ret += (20.0 * math.sin(y * PI) + 40.0 * math.sin(y / 3.0 * PI)) * 2.0 / 3.0
    ret += (160.0 * math.sin(y / 12.0 * PI) + 320 * math.sin(y * PI / 30.0)) * 2.0 / 3.0
    return ret


def _transform_lng(x, y):
    ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * math.sqrt(abs(x))
    ret += (20.0 * math.sin(6.0 * x * PI) + 20.0 * math.sin(2.0 * x * PI)) * 2.0 / 3.0
    ret += (20.0 * math.sin(x * PI) + 40.0 * math.sin(x / 3.0 * PI)) * 2.0 / 3.0
    ret += (150.0 * math.sin(x / 12.0 * PI) + 300.0 * math.sin(x / 30.0 * PI)) * 2.0 / 3.0
    return ret


def wgs84_to_gcj02(lng, lat):
    if out_of_china(lng, lat):
        return lng, lat
    dlat = _transform_lat(lng - 105.0, lat - 35.0)
    dlng = _transform_lng(lng - 105.0, lat - 35.0)
    radlat = lat / 180.0 * PI
    magic = math.sin(radlat)
    magic = 1 - EE * magic * magic
    sqrtmagic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((A * (1 - EE)) / (magic * sqrtmagic) * PI)
    dlng = (dlng * 180.0) / (A / sqrtmagic * math.cos(radlat) * PI)
    return lng + dlng, lat + dlat


# POI 数据: (day, idx, tag, name, info, lng_wgs84, lat_wgs84, coord_source)
# 坐标:基于五台山寺院群公开资料(WGS-84)
POIS = [
    # ===== D1: 北京 → 五台山(约 360km, 5h) =====
    ('D1', 1, 'start', '顺义枫泉花园',
     '北京顺义出发 · 7:00 走京昆高速 G5',
     116.6540, 40.1280, 'original'),
    ('D1', 2, 'service', '保定服务区',
     '京昆高速中段休整 · 9:30 · 约 130km',
     115.5000, 38.8500, 'known'),
    ('D1', 3, 'attract', '五爷庙(广化寺)',
     '求财最灵 · 香火最旺 · D1 下午首站 · 必去 0.5',
     113.5936, 39.0824, 'known'),
    ('D1', 4, 'attract', '显通寺',
     '五大禅处之首 · 青铜殿 + 铜塔 + 无量殿(国内唯一青铜建筑群) · 必去 0.7',
     113.5942, 39.0808, 'known'),
    ('D1', 5, 'attract', '塔院寺',
     '五台山标志性大白塔(高 56.4m) · 转塔祈福 · 必去 0.6',
     113.5946, 39.0819, 'known'),
    ('D1', 6, 'food', '寿宁寺素斋',
     '台怀镇寿宁寺素斋 · 17:30 时段 · 11:30 也开 · 错过吃不上',
     113.5940, 39.0820, 'known'),
    ('D1', 7, 'hotel', '五台山宾馆',
     '台怀镇中心 · 老牌国营 · 21:00 入住 · 旺季提前订',
     113.5947, 39.0817, 'known'),

    # ===== D2: 五台山核心 + 佛光寺 + 南禅寺 + 龙泉寺 =====
    ('D2', 1, 'attract', '佛光寺',
     '国宝中的国宝 · 东大殿(唐 857) · 文殊殿(金) · 祖师塔(北魏) · 必去 1.0',
     113.3174, 39.0440, 'known'),
    ('D2', 2, 'attract', '南禅寺',
     '亚洲现存最古木构(782 年) · 17 尊唐代塑像 · 佛光寺南 5km · 必去 0.8',
     113.2695, 39.0218, 'known'),
    ('D2', 3, 'attract', '龙泉寺',
     '汉白玉石雕牌坊(山西第一) · 距佛光寺/南禅寺 25km · 加分项 0.3',
     113.5722, 39.0603, 'known'),
    ('D2', 4, 'food', '台怀镇蒙汉餐厅',
     '返台怀镇午餐 · 12:30 · 手把肉 + 莜面 · 蒙汉兼容',
     113.5952, 39.0830, 'fallback'),  # 餐厅通用 fallback
    ('D2', 5, 'attract', '殊像寺',
     '文殊菩萨最大铜像(5 层楼高 · 9.87m) · 加分 0.4',
     113.5908, 39.0789, 'known'),
    ('D2', 6, 'attract', '菩萨顶',
     '康熙乾隆行宫 · 108 级台阶 · 红墙黄瓦 · 加分 0.3',
     113.5995, 39.0872, 'known'),
    ('D2', 7, 'attract', '南山寺',
     '悬崖石雕 · 夜景 20:00-22:00 免费 · 灯光亮起后最出彩 · 加分 0.5',
     113.5912, 39.0751, 'known'),
    ('D2', 8, 'food', '普化寺素斋',
     'D2 晚餐 · 17:30 时段 · 普化寺素斋 · 错过吃不上',
     113.5933, 39.0832, 'known'),
    ('D2', 9, 'hotel', '五台山宾馆',
     '续住 D1 酒店 · 21:00',
     113.5947, 39.0817, 'known'),

    # ===== D3: 返京 =====
    ('D3', 1, 'attract', '罗睺寺(可选)',
     '返京前 30min 路过 · 唐密佛事 · 看体力',
     113.5958, 39.0848, 'known'),
    ('D3', 2, 'service', '京昆高速服务区',
     '返京途中 · 11:00 · 约 200km 处大休整',
     113.3000, 38.4000, 'fallback'),
    ('D3', 3, 'food', '石家庄午餐',
     '京昆高速石家庄段下高速 · 13:00 · 当地家常菜',
     114.5100, 38.0400, 'fallback'),
    ('D3', 4, 'end', '顺义枫泉花园',
     '抵京 · 17:00 · 全程约 720km',
     116.6540, 40.1280, 'original'),
]


def build_pois():
    result = []
    for day, idx, tag, name, info, lng_w, lat_w, src in POIS:
        lng_g, lat_g = wgs84_to_gcj02(lng_w, lat_w)
        result.append({
            'day': day,
            'idx': idx,
            'tag': tag,
            'name': name,
            'info': info,
            'lng_wgs84': round(lng_w, 6),
            'lat_wgs84': round(lat_w, 6),
            'lng_gcj02': round(lng_g, 6),
            'lat_gcj02': round(lat_g, 6),
            'coord_source': src,
        })
    return result


def build_filled(pois):
    return {
        '_comment': '五台山 3 天试运行数据 · WGS-84 + GCJ-02 双坐标系 · 20 POI(4 必去 + 5 加分 + 起返 + 食宿)· 含 3 fallback 验证兜底',
        '_schema_ref': '../assets/pois.schema.json',
        'metadata': {
            'title': '五台山 3 天古建深度(佛光寺+南禅寺朝圣)',
            'route_summary': '北京 → 保定 → 忻州 → 五台山 → 佛光寺 → 南禅寺 → 龙泉寺 → 北京',
            'trip_slug': 'wutaishan-trial',
        },
        'pois': pois,
        'days_summary': {
            'D1': {'title': '北京 → 五台山(台怀镇)', 'desc': '约 360km · 5h · 五爷庙+显通寺+塔院寺'},
            'D2': {'title': '佛光寺 + 南禅寺 + 龙泉寺 + 台怀镇核心', 'desc': '约 100km · 12h · 国宝中的国宝 + 加分项'},
            'D3': {'title': '返京(顺路罗睺寺)', 'desc': '约 360km · 5h · 13:30 必返,15:00 后易堵'},
        },
        # 由 gen_trip_artifacts.py 自动填
        'day_routes_wgs84': {},
        'special_routes_wgs84': [],
    }


def build_template():
    """LLM 模板:用 {placeholder} 标记需替换的位置
    模板是有效 JSON,GCJ-02 字段为 null,需跑 gcj02_wgs84.py to_gcj02 模式填充
    """
    return {
        '_comment': '五台山 LLM 填充模板 · 用 {placeholder} 标记 LLM 需替换的位置 · GCJ-02 字段为 null,跑 gcj02_wgs84.py 填充',
        '_schema_ref': '../../assets/pois.schema.json',
        'metadata': {
            'title': '{trip_title}',
            'route_summary': '{route_summary}',
            'trip_slug': '{trip-slug}',
        },
        'pois': [
            # 示例:start POI · LLM 按需复制/删除/修改
            {
                'day': 'D1',
                'idx': 1,
                'tag': 'start',  # 可选:start/end/attract/hotel/food/service/stop
                'name': '{POI_NAME}',
                'info': '{POI_INFO · 时段 + 简介 ≤ 100 字}',
                'lng_wgs84': 0.0,  # 替换为 WGS-84 真实坐标
                'lat_wgs84': 0.0,
                'lng_gcj02': None,  # 留 null,跑 gcj02_wgs84.py 自动填
                'lat_gcj02': None,
                'coord_source': '{original|known|fallback}',
            },
            # ... 添加更多 POI ...
        ],
        'days_summary': {
            'D1': {'title': '{D1_title}', 'desc': '{D1_desc}'},
            # 添加 D2/D3 等
        },
        'day_routes_wgs84': {},  # 由 gen_trip_artifacts.py 自动填
        'special_routes_wgs84': [],
        '_template_usage': [
            '1. 复制本文件 → 你的 {trip-slug}.json',
            '2. 替换所有 {placeholder} 为真实数据',
            '3. 添加 POI(每个 Day 按 idx 顺序)',
            '4. python3 scripts/gcj02_wgs84.py your.json your.json --mode to_gcj02',
            '5. python3 scripts/validate.py your.json --strict',
            '6. python3 scripts/gen_trip_nav.py your.json your-nav.html --src {src}',
            '7. python3 scripts/gen_trip_artifacts.py your.json -o ./output --src {src}',
        ],
    }


def main():
    mode = 'filled'
    if '--mode' in sys.argv:
        idx = sys.argv.index('--mode')
        mode = sys.argv[idx + 1]
    if mode not in ('filled', 'template'):
        print(f'Unknown mode: {mode}, use filled or template')
        sys.exit(1)

    script_dir = Path(__file__).parent

    if mode == 'filled':
        pois = build_pois()
        data = build_filled(pois)
        out = script_dir / 'pois.json'
        with open(out, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f'✓ 写入 {out} ({len(pois)} POI)')
        src_count = {}
        for p in pois:
            src_count[p['coord_source']] = src_count.get(p['coord_source'], 0) + 1
        print(f'  coord_source 分布: {src_count}')
    else:
        # template 模式 → 写到 wutaishan-trial-template/pois.template.json
        data = build_template()
        tmpl_dir = script_dir.parent / 'wutaishan-trial-template'
        tmpl_dir.mkdir(exist_ok=True)
        out = tmpl_dir / 'pois.template.json'
        with open(out, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f'✓ 写入 {out} (LLM 模板)')


if __name__ == '__main__':
    main()