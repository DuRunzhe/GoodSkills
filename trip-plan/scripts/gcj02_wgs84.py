#!/usr/bin/env python3
"""
GCJ-02 ↔ WGS-84 坐标互转工具(中国境内)

国内旅行数据涉及 2 套坐标系:
  - GCJ-02(火星坐标):高德 / 腾讯 / 百度(部分)
  - WGS-84(地球坐标):GPS / Google Maps / OSM / OSRM

同一份数据要存双坐标系,渲染时按场景选。

用法:
  from gcj02_wgs84 import gcj02_to_wgs84, wgs84_to_gcj02
  wgs_lng, wgs_lat = gcj02_to_wgs84(gcj_lng, gcj_lat)
  gcj_lng, gcj_lat = wgs84_to_gcj02(wgs_lng, wgs_lat)

命令行:
  python gcj02_wgs84.py input.json output.json [--mode to_wgs84|to_gcj02]
"""
import json
import sys
import math

PI = 3.1415926535897932384626
A = 6378245.0
EE = 0.00669342162296594323


def out_of_china(lng, lat):
    """判断坐标是否在中国境内(中国境外不做偏移)"""
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


def gcj02_to_wgs84(lng, lat):
    """GCJ-02 → WGS-84(中国境内才转换)"""
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
    mglat = lat + dlat
    mglng = lng + dlng
    return lng * 2 - mglng, lat * 2 - mglat


def wgs84_to_gcj02(lng, lat):
    """WGS-84 → GCJ-02(中国境内才转换)"""
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


def convert_pois(pois, mode='to_wgs84'):
    """批量转换 pois 列表的坐标字段
    mode: 'to_wgs84' (从 GCJ-02 算 WGS-84) 或 'to_gcj02' (从 WGS-84 算 GCJ-02)
    """
    fn = gcj02_to_wgs84 if mode == 'to_wgs84' else wgs84_to_gcj02
    for p in pois:
        # 从已有坐标算缺失的
        if mode == 'to_wgs84' and p.get('lng_gcj02') is not None and p.get('lng_wgs84') is None:
            p['lng_wgs84'], p['lat_wgs84'] = fn(p['lng_gcj02'], p['lat_gcj02'])
        elif mode == 'to_gcj02' and p.get('lng_wgs84') is not None and p.get('lng_gcj02') is None:
            p['lng_gcj02'], p['lat_gcj02'] = fn(p['lng_wgs84'], p['lat_wgs84'])
    return pois


def main():
    if len(sys.argv) < 3:
        print('Usage: gcj02_wgs84.py <input.json> <output.json> [--mode to_wgs84|to_gcj02]')
        print('  input/output JSON 格式: {"pois": [{"day":"D1", "lng_gcj02":x, "lat_gcj02":y, ...}]}')
        sys.exit(1)

    inp, out = sys.argv[1], sys.argv[2]
    mode = 'to_wgs84'
    if '--mode' in sys.argv:
        idx = sys.argv.index('--mode')
        mode = sys.argv[idx + 1]

    with open(inp, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if 'pois' in data:
        data['pois'] = convert_pois(data['pois'], mode=mode)
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Converted {len(data.get('pois', []))} POIs, mode={mode}")
    print(f"Output: {out}")


if __name__ == '__main__':
    main()
