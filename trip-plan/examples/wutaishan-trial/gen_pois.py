#!/usr/bin/env python3
"""
生成 wutaishan-trial/pois.json
- WGS-84 近似坐标(基于公开资料)
- inline GCJ-02 转换(中国境内 +0.002~0.006 度偏移)
- 14 个 POI 覆盖必去点 + 加分项 + 起返 + 食宿
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


# POI 数据: (day, idx, tag, name, info, lng_wgs84, lat_wgs84, coord_source)
POIS = [
    # ===== D1: 北京 → 五台山(约 360km, 5h) =====
    ('D1', 1, 'start', '顺义枫泉花园',
     '北京顺义出发 · 7:00 走京昆高速',
     116.6540, 40.1280, 'original'),
    ('D1', 2, 'service', '保定服务区',
     '京昆高速中段休整 · 9:30 · 约 130km',
     115.5000, 38.8500, 'known'),
    ('D1', 3, 'attract', '五爷庙',
     '求财最灵 · 香火最旺 · D1 下午首站',
     113.5935, 39.0825, 'known'),
    ('D1', 4, 'attract', '显通寺',
     '五大禅处之首 · 青铜殿 + 铜塔 + 无量殿(国内唯一青铜建筑群)',
     113.5940, 39.0810, 'known'),
    ('D1', 5, 'attract', '塔院寺',
     '五台山标志性大白塔 · 转塔祈福',
     113.5945, 39.0825, 'known'),
    ('D1', 6, 'food', '素斋晚餐',
     '寿宁寺 / 普化寺素斋 · 17:30 时段',
     113.5930, 39.0805, 'fallback'),  # 故意 fallback,验证兜底
    ('D1', 7, 'hotel', '台怀镇民宿',
     '台内民宿 · 21:00 入住',
     113.5950, 39.0820, 'known'),

    # ===== D2: 五台山核心 + 佛光寺 + 南禅寺 =====
    ('D2', 1, 'attract', '佛光寺',
     '国宝中的国宝 · 东大殿(唐) · 文殊殿(金) · 祖师塔(北魏)',
     113.3160, 39.0445, 'known'),
    ('D2', 2, 'attract', '南禅寺',
     '亚洲现存最古木构(782 年) · 17 尊唐代塑像 · 佛光寺南 5km',
     113.2690, 39.0220, 'known'),
    ('D2', 3, 'food', '台怀镇午餐',
     '返台怀镇午餐 · 12:00 · 蒙汉兼容餐厅',
     113.5940, 39.0820, 'fallback'),  # 故意 fallback
    ('D2', 4, 'attract', '殊像寺',
     '文殊菩萨最大铜像(5 层楼高) · 壮观',
     113.5905, 39.0790, 'known'),
    ('D2', 5, 'attract', '菩萨顶',
     '康熙乾隆行宫 · 108 级台阶 · 红墙黄瓦',
     113.5990, 39.0875, 'known'),
    ('D2', 6, 'hotel', '台怀镇民宿',
     '续住 D1 民宿 · 21:00',
     113.5950, 39.0820, 'known'),

    # ===== D3: 返京 =====
    ('D3', 1, 'service', '京昆高速服务区',
     '返京途中 · 11:00 · 约 200km',
     113.3000, 38.4000, 'fallback'),  # 故意 fallback
    ('D3', 2, 'food', '石家庄午餐',
     '京昆高速石家庄段 · 13:00',
     114.5100, 38.0400, 'fallback'),  # 故意 fallback
    ('D3', 3, 'end', '顺义枫泉花园',
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
        '_comment': '五台山 3 天试运行数据 · WGS-84 + GCJ-02 双坐标系 · 含 4 个 fallback POI 验证兜底路径',
        '_schema_ref': '../assets/pois.schema.json',
        'metadata': {
            'title': '五台山 3 天古建深度(佛光寺+南禅寺朝圣)',
            'route_summary': '北京 → 保定 → 忻州 → 五台山 → 佛光寺 → 南禅寺 → 北京',
            'trip_slug': 'wutaishan-trial',
        },
        'pois': pois,
        'days_summary': {
            'D1': {'title': '北京 → 五台山(台怀镇)', 'desc': '约 360km · 5h · 五爷庙+显通寺+塔院寺'},
            'D2': {'title': '佛光寺 + 南禅寺 + 台怀镇核心', 'desc': '约 80km · 12h · 国宝中的国宝'},
            'D3': {'title': '返京', 'desc': '约 360km · 5h · 13:30 必返,15:00 后易堵'},
        },
        # 暂留空,Phase 5 由 gen_trip_artifacts.py 自动填
        'day_routes_wgs84': {},
        'special_routes_wgs84': [],
    }

    out = Path(__file__).parent / 'pois.json'
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f'✓ 写入 {out} ({len(pois)} POI)')
    # 统计
    src_count = {}
    for p in pois:
        src_count[p['coord_source']] = src_count.get(p['coord_source'], 0) + 1
    print(f'  coord_source 分布: {src_count}')


if __name__ == '__main__':
    main()