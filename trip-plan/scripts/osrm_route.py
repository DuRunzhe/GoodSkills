#!/usr/bin/env python3
"""
OSRM 路径规划封装(公共 HTTP API,免 key)

官方文档: http://project-osrm.org/docs/v5.5.1/api/#route-service
公共端点: http://router.project-osrm.org
限速: 1 请求/秒(超出会被限流)

返回 GeoJSON LineString,直接给 Leaflet 画。
"""
import json
import subprocess
import time


OSRM_BASE = 'http://router.project-osrm.org'
SLEEP_BETWEEN = 1.1  # 限速 1 req/s,留 0.1s buffer


def get_route(coords, timeout=30, max_retries=2):
    """获取驾车路径
    coords: [(lng_wgs84, lat_wgs84), ...]
    返回: [[lng, lat], ...] (WGS-84) 或 None(失败)

    失败时不抛异常,返回 None — 调用方决定 fallback。
    """
    if len(coords) < 2:
        return coords

    coords_str = ';'.join('{0},{1}'.format(*c) for c in coords)
    url = '{0}/route/v1/driving/{1}?overview=full&geometries=geojson'.format(
        OSRM_BASE, coords_str
    )

    for attempt in range(max_retries):
        try:
            result = subprocess.run(
                ['curl', '-s', '--max-time', str(timeout),
                 '-H', 'User-Agent: Mozilla/5.0 trip-planner/1.0',
                 url],
                capture_output=True, text=True, timeout=timeout + 5
            )
            if result.returncode != 0:
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return None

            data = json.loads(result.stdout)
            if data.get('code') == 'Ok' and data.get('routes'):
                return data['routes'][0]['geometry']['coordinates']
            # 非 Ok,可能是 'NoRoute' / 'InvalidUrl' / 'InvalidQuery'
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            return None
        except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception) as e:
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            print('OSRM error: {0}'.format(e))
            return None


def get_day_routes(pois, day_ids=None, sleep=SLEEP_BETWEEN):
    """批量获取多 Day 的路径(自动节流)
    pois: POI 列表
    day_ids: 要查询的 Day 列表(默认全部)
    返回: {D1: [[lng,lat],...], D2: [...], ...}
    """
    if day_ids is None:
        day_ids = sorted(set(p['day'] for p in pois))

    result = {}
    for i, day in enumerate(day_ids):
        day_pois = sorted(
            [p for p in pois if p['day'] == day],
            key=lambda p: p.get('idx', 0)
        )
        coords = [(p['lng_wgs84'], p['lat_wgs84']) for p in day_pois]
        if not coords:
            continue
        print('  {0} ({1} POIs)...'.format(day, len(coords)), end=' ', flush=True)
        route = get_route(coords)
        if route and len(route) > len(coords):
            print('OK {0} waypoints'.format(len(route)))
            result[day] = route
        else:
            print('fallback straight')
            result[day] = coords  # fallback 到直线
        if i < len(day_ids) - 1:
            time.sleep(sleep)
    return result


if __name__ == '__main__':
    # CLI: 测两点
    if len(sys.argv) >= 3:
        coords = [(float(sys.argv[1]), float(sys.argv[2]))]
    else:
        coords = [(116.548094, 40.084943), (117.284168, 42.248837)]

    import sys
    route = get_route(coords)
    if route:
        print('Got {0} waypoints'.format(len(route)))
        print('First: {0}'.format(route[0]))
        print('Last: {0}'.format(route[-1]))
    else:
        print('Failed')
