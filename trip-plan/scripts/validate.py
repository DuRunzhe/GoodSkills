#!/usr/bin/env python3
"""
trip-plan 产物校验工具

校验 pois.json 格式 + 各产物的内部一致性。

用法:
  python validate.py pois.json [--strict]
"""
import json
import re
import sys
from pathlib import Path

DEFAULT_SCHEMA = Path(__file__).parent.parent / 'assets' / 'pois.schema.json'

REQUIRED_POI_FIELDS = [
    'day', 'idx', 'name', 'tag', 'info',
    'lng_gcj02', 'lat_gcj02', 'lng_wgs84', 'lat_wgs84', 'coord_source'
]

VALID_TAGS = {'start', 'end', 'attract', 'hotel', 'food', 'service', 'stop'}
VALID_COORD_SOURCES = {'original', 'known', 'fallback'}

# 中国境内大致范围
CHINA_LNG = (72.0, 137.9)
CHINA_LAT = (0.8, 55.9)


class ValidationResult:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def add_error(self, msg):
        self.errors.append(msg)

    def add_warning(self, msg):
        self.warnings.append(msg)

    @property
    def ok(self):
        return len(self.errors) == 0

    def report(self):
        print('\n=== 校验结果 ===')
        print('错误: {0}'.format(len(self.errors)))
        for e in self.errors:
            print('  ✗ {0}'.format(e))
        print('警告: {0}'.format(len(self.warnings)))
        for w in self.warnings:
            print('  ⚠ {0}'.format(w))
        if self.ok:
            print('\n✅ 校验通过')
        else:
            print('\n❌ 校验失败')


def validate_pois(pois, strict=False):
    """校验 POI 列表
    strict=True: 警告也视为失败
    """
    result = ValidationResult()
    if not pois:
        result.add_error('pois 列表为空')
        return result

    seen_ids = set()
    for i, p in enumerate(pois):
        prefix = 'POI[{0}] {1}'.format(i, p.get('name', '?'))

        # 必含字段
        for field in REQUIRED_POI_FIELDS:
            if field not in p:
                result.add_error('{0}: 缺字段 {1}'.format(prefix, field))
                continue
            if p[field] is None:
                result.add_error('{0}: 字段 {1} 为 None'.format(prefix, field))

        # day 格式
        if not re.match(r'^D\d+$', str(p.get('day', ''))):
            result.add_error('{0}: day 必须形如 D1/D2 ({1})'.format(prefix, p.get('day')))

        # tag 合法
        if p.get('tag') not in VALID_TAGS:
            result.add_error('{0}: tag 不合法 ({1})'.format(prefix, p.get('tag')))

        # coord_source 合法
        if p.get('coord_source') not in VALID_COORD_SOURCES:
            result.add_error('{0}: coord_source 不合法 ({1})'.format(prefix, p.get('coord_source')))

        # 坐标范围(中国境内)
        for cfield in ['lng_gcj02', 'lat_gcj02', 'lng_wgs84', 'lat_wgs84']:
            v = p.get(cfield)
            if v is None:
                continue
            if cfield.startswith('lng') and not (CHINA_LNG[0] <= v <= CHINA_LNG[1]):
                result.add_warning('{0}: {1}={2} 超出中国经度范围 {3}'.format(
                    prefix, cfield, v, CHINA_LNG))
            elif cfield.startswith('lat') and not (CHINA_LAT[0] <= v <= CHINA_LAT[1]):
                result.add_warning('{0}: {1}={2} 超出中国纬度范围 {3}'.format(
                    prefix, cfield, v, CHINA_LAT))

        # GCJ-02 / WGS-84 偏移应 < 0.01 度
        if p.get('lng_gcj02') is not None and p.get('lng_wgs84') is not None:
            dx = abs(p['lng_gcj02'] - p['lng_wgs84'])
            dy = abs(p['lat_gcj02'] - p['lat_wgs84'])
            if dx > 0.01 or dy > 0.01:
                result.add_warning('{0}: GCJ-02/WGS-84 偏移过大 ({1:.5f}, {2:.5f})'.format(
                    prefix, dx, dy))

        # (day, idx) 唯一
        if 'day' in p and 'idx' in p:
            key = (p['day'], p['idx'])
            if key in seen_ids:
                result.add_error('{0}: 重复的 (day={1}, idx={2})'.format(
                    prefix, p['day'], p['idx']))
            seen_ids.add(key)

        # fallback 提示
        if p.get('coord_source') == 'fallback' and p.get('tag') == 'attract':
            result.add_warning('{0}: 景点用了 fallback 坐标,真实出行前需核实'.format(prefix))

    return result


def validate_data(data, schema_path=None):
    """校验完整数据(pois + day_routes + special_routes)"""
    result = ValidationResult()

    # 顶层必含
    for field in ['pois', 'day_routes_wgs84', 'days_summary']:
        if field not in data:
            result.add_error('顶层缺字段 {0}'.format(field))

    # POI 校验
    if 'pois' in data:
        poi_result = validate_pois(data['pois'])
        result.errors.extend(poi_result.errors)
        result.warnings.extend(poi_result.warnings)

    # day_routes_wgs84 一致性
    if 'pois' in data and 'day_routes_wgs84' in data:
        poi_days = set(p['day'] for p in data['pois'])
        route_days = set(data['day_routes_wgs84'].keys())
        missing = poi_days - route_days
        extra = route_days - poi_days
        if missing:
            result.add_warning('day_routes_wgs84 缺 Day: {0}'.format(sorted(missing)))
        if extra:
            result.add_warning('day_routes_wgs84 多余 Day: {0}'.format(sorted(extra)))

    # days_summary 一致性
    if 'pois' in data and 'days_summary' in data:
        poi_days = set(p['day'] for p in data['pois'])
        summary_days = set(data['days_summary'].keys())
        if poi_days != summary_days:
            result.add_warning(
                'days_summary 与 pois 数量不一致:pois={0}, summary={1}'.format(
                    sorted(poi_days), sorted(summary_days)))

    return result


def main():
    if len(sys.argv) < 2:
        print('Usage: validate.py <pois.json> [--schema <schema.json>] [--strict]')
        sys.exit(1)

    data_path = Path(sys.argv[1])
    strict = '--strict' in sys.argv

    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    result = validate_data(data)
    result.report()
    sys.exit(0 if result.ok or not strict else 1)


if __name__ == '__main__':
    main()
