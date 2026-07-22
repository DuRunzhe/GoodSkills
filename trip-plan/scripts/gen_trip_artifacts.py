#!/usr/bin/env python3
"""
trip-plan 端到端产物生成器

从一份 pois.json 一键生成:
  - trip-nav.html (导航点位页)
  - trip-overview-map.html (OSRM 综合地图)
  - trip.kml (高德导入)

用法:
  python gen_trip_artifacts.py pois.json -o ./output/
  python gen_trip_artifacts.py pois.json -o ./output/ --no-osrm  # 跳过 OSRM
  python gen_trip_artifacts.py pois.json -o ./output/ --src momotrip  # 高德 utm src

依赖: 同目录的 osrm_route.py / assign_day_colors.py / validate.py
"""
import argparse
import json
import re
import sys
import urllib.parse
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from osrm_route import get_day_routes
from assign_day_colors import assign_day_colors
from validate import validate_data
from gen_trip_nav import gen_trip_nav as _gen_trip_nav

# 同目录 assets/ 的模板
TEMPLATE_DIR = SCRIPT_DIR.parent / 'assets'


# ============== 1. 导航点位页 ==============
def gen_trip_nav(data, output_path, amap_src='yourtag'):
    pois = sorted(data['pois'], key=lambda p: (p['day'], p.get('idx', 0)))
    days = sorted(set(p['day'] for p in pois))
    day_titles = {p['day']: data.get('days_summary', {}).get(p['day'], {}).get('title', p['day'])
                  for p in pois}

    # 按 day 分组,每个 day 内按 idx 顺序
    day_groups = {}
    for p in pois:
        day_groups.setdefault(p['day'], []).append(p)

    tag_labels = {
        'start': '起点', 'end': '终点',
        'attract': '景点', 'hotel': '酒店', 'food': '餐厅',
        'service': '服务区', 'stop': '驿站'
    }

    # 生成 HTML
    html = TEMPLATE_DIR.joinpath('nav-template.html').read_text(encoding='utf-8')

    # 简单替换标题
    trip_title = data.get('metadata', {}).get('title', '示例行程')
    html = html.replace('{trip_title}', trip_title)

    # 生成 day-nav
    day_nav = '\n'.join(
        f'  <a href="#day{i}">D{i} {day_titles.get("D"+str(i), "")[:20]}</a>'
        for i in range(1, len(days) + 1)
    )
    # 替换 day-nav 块(简化:用整个 day-nav 重写)
    html = re.sub(
        r'(<nav class="day-nav"[^>]*>).*?(</nav>)',
        f'\\1\n{day_nav}\n\\2',
        html, count=1, flags=re.DOTALL
    )

    # 生成每个 Day section(简化版,直接生成 1 个示例 Day 1)
    # 实际用模板要复杂,这里只生成 demo Day 1 + 注释
    # 用户应该根据数据自己写 day section,或扩展此函数
    Path(output_path).write_text(html, encoding='utf-8')
    print(f'  nav: {output_path} (template,需手动填充 Day section)')


# ============== 2. OSRM 综合地图 ==============
def gen_overview_map(data, output_path, amap_src='yourtag', use_osrm=True):
    pois = data['pois']
    days = sorted(set(p['day'] for p in pois))
    day_colors = assign_day_colors(len(days))

    # 拉 OSRM 路径
    if use_osrm:
        print('  拉 OSRM 路径...')
        routes = get_day_routes(pois, day_ids=days)
    else:
        print('  跳过 OSRM,用直线')
        routes = {
            d: [(p['lng_wgs84'], p['lat_wgs84']) for p in pois if p['day'] == d]
            for d in days
        }

    # 生成 special_routes(99号公路等)
    special = data.get('special_routes_wgs84', [])

    # 模板替换
    html = TEMPLATE_DIR.joinpath('overview-map-template.html').read_text(encoding='utf-8')

    html = html.replace('{trip_title}', data.get('metadata', {}).get('title', '示例行程'))
    html = html.replace('{trip_summary}', f"{len(days)} 天 · {len(pois)} POI")
    html = html.replace('{init_lat}', '40.5').replace('{init_lng}', '116.5').replace('{init_zoom}', '7')
    html = html.replace('{src}', amap_src)
    html = html.replace('{special_day}', 'D4')  # 99号公路在 D4

    html = html.replace('__POIS__', json.dumps(pois, ensure_ascii=False))
    html = html.replace('__DAY_ROUTES__', json.dumps(routes, ensure_ascii=False))
    html = html.replace('__SPECIAL_ROUTES__', json.dumps(special, ensure_ascii=False))
    html = html.replace('__DAYS__', json.dumps(
        {d: data.get('days_summary', {}).get(d, {}).get('title', d) for d in days},
        ensure_ascii=False))
    html = html.replace('__DAY_COLORS__', json.dumps(day_colors, ensure_ascii=False))
    html = html.replace('__TAG_COLORS__', json.dumps({
        'start': '#00C853', 'end': '#D50000',
        'attract': '#FF6F00', 'hotel': '#7B1FA2', 'food': '#FFB300',
        'service': '#1976D2', 'stop': '#00838F'
    }, ensure_ascii=False))
    html = html.replace('__TAG_LABELS__', json.dumps({
        'start': '起点', 'end': '终点',
        'attract': '景点', 'hotel': '酒店', 'food': '餐厅',
        'service': '服务区', 'stop': '驿站'
    }, ensure_ascii=False))

    Path(output_path).write_text(html, encoding='utf-8')
    print(f'  overview-map: {output_path} ({len(html) // 1024}KB)')


# ============== 3. KML ==============
def gen_kml(data, output_path, amap_src='yourtag'):
    pois = sorted(data['pois'], key=lambda p: (p['day'], p.get('idx', 0)))
    days = sorted(set(p['day'] for p in pois))
    day_colors = assign_day_colors(len(days))

    tag_color_kml = {
        'start': 'ff00C853', 'end': 'ffD50000',
        'attract': 'ffFF6F00', 'hotel': 'ff7B1FA2', 'food': 'ffFFB300',
        'service': 'ff1976D2', 'stop': 'ff00838F'
    }

    lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    lines.append('<kml xmlns="http://www.opengis.net/kml/2.2">')
    lines.append('<Document>')
    lines.append(f'  <name>{data.get("metadata", {}).get("title", "行程")}</name>')
    lines.append(f'  <description>{data.get("metadata", {}).get("description", "")}</description>')

    for day in days:
        day_pois = [p for p in pois if p['day'] == day]
        if not day_pois:
            continue
        day_title = data.get('days_summary', {}).get(day, {}).get('title', day)
        day_desc = data.get('days_summary', {}).get(day, {}).get('desc', '')
        day_color = day_colors[day].lstrip('#')
        # KML 颜色格式: aabbggrr
        kml_color = day_color[4:6] + day_color[2:4] + day_color[0:2]

        lines.append('  <Folder>')
        lines.append(f'    <name>{day} {day_title}</name>')
        lines.append(f'    <description>{day_desc}</description>')

        # 行程连线
        if len(day_pois) >= 2:
            coords = ' '.join(
                f'{p["lng_gcj02"]},{p["lat_gcj02"]},0' for p in day_pois
            )
            lines.append('    <Placemark>')
            lines.append(f'      <name>{day} 行程连线</name>')
            lines.append(f'      <Style><LineStyle><color>ff{kml_color}</color><width>3</width></LineStyle></Style>')
            lines.append(f'      <LineString><tessellate>1</tessellate><coordinates>{coords}</coordinates></LineString>')
            lines.append('    </Placemark>')

        # POIs
        for p in day_pois:
            color = tag_color_kml.get(p['tag'], 'ff666666')
            name_esc = urllib.parse.quote(p['name'], safe='')
            desc = (f'{p["info"]}<br/><br/>标签: {p["tag"]}<br/>'
                    f'坐标(GCJ-02): {p["lng_gcj02"]}, {p["lat_gcj02"]}<br/>'
                    f'高德导航: <a href="https://uri.amap.com/navigation?'
                    f'to={p["lng_gcj02"]},{p["lat_gcj02"]},{name_esc}&mode=car&src={amap_src}">'
                    f'点这里导航</a>')
            lines.append('    <Placemark>')
            lines.append(f'      <name>{p.get("idx", "")}. {p["name"]}</name>')
            lines.append(f'      <description><![CDATA[{desc}]]></description>')
            lines.append(f'      <Style><IconStyle><color>{color}</color><scale>1.0</scale>'
                        f'<Icon><href>http://maps.google.com/mapfiles/kml/pushpin/ylw-pushpin.png</href></Icon></IconStyle></Style>')
            lines.append(f'      <Point><coordinates>{p["lng_gcj02"]},{p["lat_gcj02"]},0</coordinates></Point>')
            lines.append('    </Placemark>')
        lines.append('  </Folder>')

    # 特殊路线
    for route in data.get('special_routes_wgs84', []):
        wps = route.get('waypoints', [])
        if len(wps) < 2:
            continue
        lines.append('  <Folder>')
        lines.append(f'    <name>★ {route.get("label", "特殊路线")}</name>')
        lines.append(f'    <description>{route.get("label", "")}</description>')
        coords = ' '.join(f'{lng},{lat},0' for lng, lat in wps)
        # 用高德 marker:取 waypoint 1 → 0 → 末
        # 但 waypoints 是 WGS-84,这里只用 GCJ-02 转换;为简化,跳过 wgs84→gcj02,提示用户
        lines.append('    <Placemark>')
        lines.append(f'      <name>{route.get("label", "特殊路线")}</name>')
        color = route.get('color', '#FF6F00').lstrip('#')
        kml_color = color[4:6] + color[2:4] + color[0:2]
        lines.append(f'      <Style><LineStyle><color>ff{kml_color}</color><width>5</width></LineStyle></Style>')
        lines.append(f'      <LineString><tessellate>1</tessellate><coordinates>{coords}</coordinates></LineString>')
        lines.append('    </Placemark>')
        lines.append('  </Folder>')

    lines.append('</Document>')
    lines.append('</kml>')

    Path(output_path).write_text('\n'.join(lines), encoding='utf-8')
    print(f'  kml: {output_path} ({Path(output_path).stat().st_size // 1024}KB)')


def main():
    parser = argparse.ArgumentParser(description='trip-plan 端到端产物生成')
    parser.add_argument('pois_json', help='pois.json 路径')
    parser.add_argument('-o', '--output', default='./output', help='输出目录')
    parser.add_argument('--src', default='yourtag', help='高德 utm src 参数')
    parser.add_argument('--no-osrm', action='store_true', help='跳过 OSRM(用直线)')
    parser.add_argument('--no-validate', action='store_true', help='跳过校验')
    args = parser.parse_args()

    pois_path = Path(args.pois_json)
    if not pois_path.exists():
        print(f'Error: {pois_path} 不存在')
        sys.exit(1)

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(pois_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 校验
    if not args.no_validate:
        result = validate_data(data)
        if not result.ok:
            print('⚠ 校验发现问题,继续生成(可用 --no-validate 跳过):')
            result.report()

    print(f'\n生成产物到 {out_dir}/:')
    _gen_trip_nav(data, out_dir / 'trip-nav.html', amap_src=args.src)
    gen_overview_map(data, out_dir / 'trip-overview-map.html',
                     amap_src=args.src, use_osrm=not args.no_osrm)
    gen_kml(data, out_dir / 'trip.kml', amap_src=args.src)

    print(f'\n✅ 完成。后续:用 scripts/screenshot_html.py 截总览+每 Day 图')


if __name__ == '__main__':
    main()
