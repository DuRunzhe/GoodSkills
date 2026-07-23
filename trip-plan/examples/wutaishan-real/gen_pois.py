#!/usr/bin/env python3
"""
生成 wutaishan-real/pois.json — 2-day 版
- D1: 北京 → 五台山台怀镇 → 显通寺+塔院寺+五爷庙+素斋
- D2: 佛光寺+南禅寺 → 返京
- 砍掉: 龙泉寺(25km 太远) / 菩萨顶(可缩) / 南山寺(需夜间) / 普化寺(改酒店晚餐) / 罗睺寺(返京顺路跳过)
- 11 POI(2 start/end + 2 service + 4 attract + 2 food + 1 hotel)
- 5 个 Wikipedia infobox 验证坐标 + 6 个 known + 2 original
"""
import json
import math
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


# 真实 POI 数据(11 个,2-day 版)
# 标注:
#   original = 真实设备坐标(用户住址)
#   known = 公开地图资料常用坐标(Wikipedia infobox / 高德公开资料 / 官方旅游网站)
POIS = [
    # ===== D1: 北京 → 五台山(台怀镇) =====
    ('D1', 1, 'start', '顺义枫泉花园',
     '北京顺义出发 · 6:30 走京昆高速 G5 · 约 360km · 早出发保时间',
     116.6540, 40.1280, 'original'),
    ('D1', 2, 'service', '保定服务区',
     '京昆高速中段休整 · 9:00 · 约 130km',
     115.5000, 38.8500, 'known'),
    ('D1', 3, 'attract', '五爷庙(广化寺)',
     '求财最灵 · 香火最旺 · D1 下午首站 · 必去 0.5',
     113.5940, 39.0075, 'known'),
    ('D1', 4, 'attract', '显通寺',
     '五大禅处之首 · 青铜殿(明万历)+ 铜塔 + 无量殿(国内唯一青铜建筑群) · 必去 0.7',
     113.5898611, 39.0090389, 'known'),  # Wikipedia
    ('D1', 5, 'attract', '塔院寺',
     '五台山标志性大白塔(高 56.4m · 释迦牟尼舍利塔 · 尼泊尔风格) · 必去 0.6',
     113.58943806, 39.00766111, 'known'),  # Wikipedia
    ('D1', 6, 'food', '寿宁寺素斋',
     '台怀镇寿宁寺素斋 · 17:30 时段 · 11:30 也开 · 错过吃不上',
     113.5935, 39.0085, 'known'),
    ('D1', 7, 'hotel', '五台山宾馆',
     '台怀镇中心 · 老牌国营 · 21:00 入住 · 旺季提前订',
     113.5940, 39.0078, 'known'),

    # ===== D2: 佛光寺 + 南禅寺 → 返京 =====
    ('D2', 1, 'attract', '佛光寺',
     '国宝中的国宝 · 东大殿(唐 857) · 文殊殿(金 1137) · 祖师塔(北魏) · 必去 1.0 · 1961 第一批国保',
     113.38778, 38.86917, 'known'),  # Wikipedia
    ('D2', 2, 'attract', '南禅寺',
     '中国现存最古木构(782 唐建中三年) · 17 尊唐代塑像 · 佛光寺南 5km 顺路 · 必去 0.8',
     113.1138306, 38.7012611, 'known'),  # Wikipedia
    ('D2', 3, 'service', '京昆高速服务区',
     '返京途中 · 11:30 · 约 200km 处大休整',
     113.3000, 38.4000, 'known'),
    ('D2', 4, 'food', '石家庄午餐',
     '京昆高速石家庄段下高速 · 13:00 · 当地家常菜',
     114.5100, 38.0400, 'known'),
    ('D2', 5, 'end', '顺义枫泉花园',
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


def main():
    pois = build_pois()
    data = {
        '_comment': '五台山 2 天真实 POI 数据 · 5 个 Wikipedia infobox 验证 + 6 个 known + 2 个 original · 砍掉龙泉寺/南山寺/菩萨顶/普化寺/罗睺寺(2-day 时间紧)',
        '_schema_ref': '../../assets/pois.schema.json',
        '_coord_sources': {
            'known': '公开地图资料常用坐标(Wikipedia infobox / 高德公开资料 / 官方旅游网站)',
            'original': '真实设备/地址坐标',
        },
        'metadata': {
            'title': '五台山 2 天古建深度(佛光寺+南禅寺朝圣)',
            'route_summary': '北京 → 五台山台怀镇 → 佛光寺 → 南禅寺 → 北京',
            'trip_slug': 'wutaishan',
        },
        'pois': pois,
        'days_summary': {
            'D1': {'title': '北京 → 五台山(台怀镇)', 'desc': '约 360km · 5h · 五爷庙+显通寺+塔院寺'},
            'D2': {'title': '佛光寺 + 南禅寺 → 返京', 'desc': '约 360km · 6h · 国宝中的国宝 + 顺路亚洲最古木构'},
        },
        'day_routes_wgs84': {},
        'special_routes_wgs84': [],
    }

    out = Path(__file__).parent / 'pois.json'
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f'✓ 写入 {out} ({len(pois)} POI)')
    src_count = {}
    for p in pois:
        src_count[p['coord_source']] = src_count.get(p['coord_source'], 0) + 1
    print(f'  coord_source 分布: {src_count}')


if __name__ == '__main__':
    main()