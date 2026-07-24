#!/usr/bin/env python3
"""
Playwright HTML 截图工具

支持:
  1. Leaflet 综合地图截图(总览 / 按 Day / 批量)
  2. 🌟 高德路线数据获取(首选:AMap.Driving JS API / 兜底:截图)

依赖:
  pip install playwright
  playwright install chromium

用法:
  # 截图类
  python screenshot_html.py inner-mongolia-v5-map.html -o overview.png
  python screenshot_html.py inner-mongolia-v5-map.html -o d1.png --day D1
  python screenshot_html.py inner-mongolia-v5-map.html --batch -o ./screenshots/
  python screenshot_html.py inner-mongolia-v5-map.html -o hi.png --scale 3 --width 1600

  # 🌟 【首选】高德驾车路线数据获取(AMap.Driving API 高速优先)
  python screenshot_html.py --mode gaode-route \
    --from-lng 116.4074 --from-lat 39.9042 --from-name 北京 \
    --to-lng 117.2010 --to-lat 39.0850 --to-name 天津
  # 返回: {"km": 213, "min": 159, "toll": 84}

  # 🌟【首选】从 pois.json 批量获取全部路线数据
  python screenshot_html.py pois.json --mode batch-gaode-routes \
    -o ./output/gaode-route-data.json

  # 🛡️【兜底】高德自驾路线截图(当 API 失败时)
  python screenshot_html.py --mode gaode-screenshot \
    --from-lng 116.4074 --from-lat 39.9042 --from-name 北京 \
    --to-lng 117.2010 --to-lat 39.0850 --to-name 天津 \
    -o route.png
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path
import urllib.parse

try:
    from playwright.async_api import async_playwright
except ImportError:
    print('Error: playwright 未安装,运行 `pip install playwright && playwright install chromium`')
    sys.exit(1)


async def screenshot(
    html_path,
    output_path,
    day=None,
    mode=None,
    width=1280,
    height=900,
    scale=2,
    wait_ms=5000,
):
    """单张截图
    html_path: HTML 文件路径
    output_path: 输出 PNG 路径
    day: 可选 'D1'/'D2'/... 先点击对应按钮再截图
    mode: 可选 'route'/'straight' 切换路径模式
    """
    html = Path(html_path).resolve()
    if not html.exists():
        print(f'Error: HTML 不存在: {html}')
        return False

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
        context = await browser.new_context(
            viewport={'width': width, 'height': height},
            device_scale_factor=scale,
        )
        page = await context.new_page()
        await page.goto(f'file://{html}', wait_until='networkidle', timeout=30000)
        await page.wait_for_timeout(wait_ms)

        # 切换 Day
        if day:
            btn = await page.query_selector(f'button[data-day="{day}"]')
            if btn:
                await btn.click()
                await page.wait_for_timeout(1500)
            else:
                print(f'Warning: 找不到按钮 data-day="{day}"')

        # 切换 mode
        if mode:
            btn = await page.query_selector(f'button[data-mode="{mode}"]')
            if btn:
                await btn.click()
                await page.wait_for_timeout(1000)
            else:
                print(f'Warning: 找不到按钮 data-mode="{mode}"')

        # 截图(优先截 #map div)
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        map_div = await page.query_selector('#map')
        if map_div:
            await map_div.screenshot(path=str(output))
        else:
            await page.screenshot(path=str(output), full_page=False)
        await browser.close()
    print(f'OK: {output}')
    return True


async def screenshot_batch(html_path, output_dir, days=None, scale=2):
    """批量截图:总览 + 每 Day"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. 总览
    overview = output_dir / 'overview.png'
    await screenshot(html_path, overview, day=None, mode=None, scale=scale)

    # 2. 每 Day
    if days is None:
        # 尝试从 HTML 推断 Days(扫描所有 button[data-day])
        html = Path(html_path).read_text(encoding='utf-8')
        import re
        days = sorted(set(re.findall(r'data-day="(D\d+)"', html)))
        if 'all' in days:
            days.remove('all')
    print(f'  Days to screenshot: {days}')

    for day in days:
        out = output_dir / f'{day.lower()}.png'
        await screenshot(html_path, out, day=day, mode=None, scale=scale)


# ============================================================
# 🌟 高德路线截图（GAODE-ROUTE 模式）
#
# 功能：打开高德驾车路线规划网页（高速优先），截图路线概要面板
# 截图内容：导航距离(km) + 预计时长 + 通行费（过路费）
# 产物复用：截图可用于导航点位网页的每个 POI 卡片内嵌路线预览
#
# URL 格式：
#   https://ditu.amap.com/dir?
#     from[lng]=116.4074&from[lat]=39.9042&from[name]=北京&
#     to[lng]=117.2010&to[lat]=39.0850&to[name]=天津&
#     type=car&policy=1
#
# policy=1 = 高速优先
# ============================================================

async def gaode_route_screenshot(
    from_lng: float,
    from_lat: float,
    from_name: str,
    to_lng: float,
    to_lat: float,
    to_name: str,
    output_path: str = None,
    width=1280,
    height=900,
    scale=2,
    wait_ms=12000,
):
    """通过高德 AMap.Driving JS API 获取驾车路线数据（高速优先 policy=LEAST_TIME）

    使用 Playwright 打开高德首页建立 session，然后注入 JavaScript 调用
    AMap.Driving API 获取真实导航距离、时长、通行费。

    Returns:
        dict: {'km': int, 'min': int, 'toll': int, 'from': str, 'to': str}
              或 None（失败时）
    """
    print(f'  Gaode route: {from_name} → {to_name}')

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox',
                  '--disable-blink-features=AutomationControlled'],
        )
        context = await browser.new_context(
            viewport={'width': width, 'height': height},
            device_scale_factor=scale,
            locale='zh-CN',
            user_agent=('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                       'AppleWebKit/537.36 (KHTML, like Gecko) '
                       'Chrome/120.0.0.0 Safari/537.36'),
        )
        page = await context.new_page()
        # 反检测
        await page.add_init_script('''
            Object.defineProperty(navigator,'webdriver',{get:()=>undefined});
            Object.defineProperty(navigator,'plugins',{get:()=>[1,2,3,4,5]});
            window.chrome={runtime:{}};
        ''')

        # 打开高德首页加载 AMap JS API
        await page.goto('https://ditu.amap.com/', wait_until='networkidle', timeout=30000)
        await page.wait_for_timeout(3000)

        # 用 AMap.Driving API 获取真实路线
        route_data = await page.evaluate(f'''
            async () => {{
                const waitForAMap = () => new Promise((resolve) => {{
                    const check = () => {{
                        if (window.AMap && window.AMap.Driving) {{
                            resolve(true);
                        }} else {{
                            setTimeout(check, 500);
                        }}
                    }};
                    check();
                }});

                const loaded = await waitForAMap();
                if (!loaded) return null;

                try {{
                    const driving = new AMap.Driving({{
                        policy: AMap.DrivingPolicy.LEAST_TIME  // 高速优先
                    }});

                    return new Promise((resolve) => {{
                        driving.search(
                            new AMap.LngLat({from_lng}, {from_lat}),
                            new AMap.LngLat({to_lng}, {to_lat}),
                            (status, result) => {{
                                if (status === 'complete' && result.routes && result.routes.length > 0) {{
                                    const route = result.routes[0];
                                    resolve({{
                                        km: Math.round(route.distance / 1000),
                                        min: Math.round(route.time / 60),
                                        toll: Math.round(route.tolls || 0),
                                    }});
                                }} else {{
                                    resolve(null);
                                }}
                            }}
                        );
                    }});
                }} catch(e) {{
                    return null;
                }}
            }}
        ''')

        await browser.close()

    if route_data:
        print(f'  ✅ {route_data["km"]}km, {route_data["min"]}min, toll=¥{route_data["toll"]}')
        route_data['from'] = from_name
        route_data['to'] = to_name
        return route_data
    else:
        print(f'  ❌ Failed to get route data')
        return None


async def _fallback_gaode_screenshot(
    from_lng, from_lat, from_name,
    to_lng, to_lat, to_name,
    output_path, width=1280, height=900, scale=2, wait_ms=15000,
):
    """🏴 兜底方式：截图高德驾车路线网页（API 失败时使用）"""
    print(f'  [fallback screenshot] {from_name} → {to_name}')
    params = {
        'from[lng]': str(from_lng), 'from[lat]': str(from_lat),
        'from[name]': from_name,
        'to[lng]': str(to_lng), 'to[lat]': str(to_lat),
        'to[name]': to_name, 'type': 'car', 'policy': '1',
    }
    query = urllib.parse.urlencode(params, safe='[],')
    url = f'https://ditu.amap.com/dir?{query}'
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
        page = await (await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        )).new_page()
        await page.goto(url, wait_until='networkidle', timeout=30000)
        await page.wait_for_timeout(wait_ms)
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        for sel in ['#route-plan-box', '.plan_wrap', '.dirbox']:
            el = await page.query_selector(sel)
            if el:
                await el.screenshot(path=output_path)
                break
        else:
            await page.screenshot(path=output_path, full_page=False,
                                  clip={'x': 0, 'y': 0, 'width': 1280, 'height': 500})
        await browser.close()
    print(f'  ✅ Fallback screenshot: {output_path}')


async def batch_gaode_routes(pois_json_path, output_dir, scale=2):
    """从 pois.json 批量获取每段导航路线数据

    策略:
      首选: AMap.Driving JS API（返回真实 km / min / toll）
      兜底: 截图高德驾车路线网页

    输出: {key: {from, to, km, min, toll}}（API 模式）
          {key: {from, to, screenshot}}（截图兜底）
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(pois_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    pois = sorted(data['pois'], key=lambda p: (p['day'], p.get('idx', 0)))
    days = sorted(set(p['day'] for p in pois))

    route_data = {}
    prev_poi = None
    use_fallback = False  # 如果 API 连续失败则切截图兜底

    for day in days:
        day_pois = [p for p in pois if p['day'] == day]
        for poi in day_pois:
            day_key = poi['day']
            idx = poi.get('idx', 0)
            tag = poi.get('tag', 'attract')
            lng = poi.get('lng_gcj02', 0.0)
            lat = poi.get('lat_gcj02', 0.0)
            name = poi.get('name', '')

            if (lng == 0.0 and lat == 0.0) or tag == 'start':
                prev_poi = poi
                continue

            if prev_poi is None:
                from_lng = data.get('metadata', {}).get('start_lng', lng)
                from_lat = data.get('metadata', {}).get('start_lat', lat)
                from_name = data.get('metadata', {}).get('start_name', '出发地')
            else:
                from_lng = prev_poi.get('lng_gcj02', 0.0)
                from_lat = prev_poi.get('lat_gcj02', 0.0)
                from_name = prev_poi.get('name', '上一点')

            key = f'{day_key}_{idx}'

            if not use_fallback:
                # 【首选】AMap.Driving JS API
                result = await gaode_route_screenshot(
                    from_lng=from_lng, from_lat=from_lat, from_name=from_name,
                    to_lng=lng, to_lat=lat, to_name=name,
                )
                if result and result.get('km'):
                    route_data[key] = result
                    prev_poi = poi
                    continue
                else:
                    print(f'  ⚠ API failed for {key}, switching to fallback screenshot')
                    use_fallback = True

            # 【兜底】截图高德驾车路线网页
            out_path = str(output_dir / f'{day_key.lower()}-poi{idx:02d}-route.png')
            print(f'  [fallback] {from_name} → {name}')
            # 用旧 screenshot 方法
            try:
                import asyncio
                from playwright.async_api import async_playwright
                params = {
                    'from[lng]': str(from_lng), 'from[lat]': str(from_lat),
                    'from[name]': from_name,
                    'to[lng]': str(lng), 'to[lat]': str(lat),
                    'to[name]': name, 'type': 'car', 'policy': '1',
                }
                query = urllib.parse.urlencode(params, safe='[],')
                url = f'https://ditu.amap.com/dir?{query}'
                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
                    page = await (await browser.new_context()).new_page()
                    await page.goto(url, wait_until='networkidle', timeout=30000)
                    await page.wait_for_timeout(15000)
                    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
                    route_panel = await page.query_selector('#route-plan-box, .plan_wrap, .dirbox')
                    if route_panel:
                        await route_panel.screenshot(path=out_path)
                    else:
                        await page.screenshot(path=out_path, full_page=False)
                    await browser.close()
                route_data[key] = {
                    'from': from_name, 'to': name,
                    'screenshot': str(Path(out_path).relative_to(output_dir.parent)),
                }
            except Exception as e:
                print(f'  ❌ Fallback failed: {e}')

            prev_poi = poi

    # 保存结果
    out_file = output_dir / 'route-screenshots.json'
    out_file.write_text(json.dumps(route_data, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'\n  ✅ Route data saved: {out_file}')
    print(f'  ✅ Total routes: {len(route_data)}')
    return route_data


def main():
    parser = argparse.ArgumentParser(description='Playwright HTML 截图')
    parser.add_argument('input', nargs='?', help='HTML 文件路径 或 pois.json(批量路线模式)')
    parser.add_argument('-o', '--output', help='输出 PNG 路径(单张模式)')
    parser.add_argument('--day', help='点击该 Day 按钮(如 D1/D2)')
    parser.add_argument('--mode', choices=[
            'route', 'straight', 'gaode-route', 'gaode-screenshot',
            'batch-gaode-routes',
        ],
                        help='路线模式(route/straight) | 高德API首选(gaode-route)| 截图兜底(gaode-screenshot)| 批量(batch-gaode-routes)')
    parser.add_argument('--batch', action='store_true', help='批量截总览+每 Day')
    parser.add_argument('--days', help='批量模式下指定 Day,逗号分隔(如 D1,D2,D3)')
    parser.add_argument('--width', type=int, default=1280, help='视口宽度')
    parser.add_argument('--height', type=int, default=900, help='视口高度')
    parser.add_argument('--scale', type=int, default=2,
                        help='device_scale_factor(高清用 2 或 3)')
    parser.add_argument('--wait', type=int, default=12000, help='路线加载等待时间(ms,默认 12s)')

    # 高德路线截图参数
    parser.add_argument('--from-lng', type=float, help='出发地经度(GCJ-02)')
    parser.add_argument('--from-lat', type=float, help='出发地纬度(GCJ-02)')
    parser.add_argument('--from-name', help='出发地名称')
    parser.add_argument('--to-lng', type=float, help='目的地经度(GCJ-02)')
    parser.add_argument('--to-lat', type=float, help='目的地纬度(GCJ-02)')
    parser.add_argument('--to-name', help='目的地名称')

    args = parser.parse_args()

    # ---- 高德路线数据获取（首选：AMap.Driving JS API）----
    if args.mode == 'gaode-route':
        if not all([args.from_lng, args.from_lat, args.from_name,
                    args.to_lng, args.to_lat, args.to_name]):
            print('Error: gaode-route 模式需要 --from-lng --from-lat --from-name '
                  '--to-lng --to-lat --to-name')
            sys.exit(1)
        result = asyncio.run(gaode_route_screenshot(
            from_lng=args.from_lng, from_lat=args.from_lat,
            from_name=args.from_name,
            to_lng=args.to_lng, to_lat=args.to_lat,
            to_name=args.to_name,
        ))
        if result:
            import json
            print(json.dumps(result, ensure_ascii=False))

    # ---- 兜底：高德驾车路线截图 ----
    elif args.mode == 'gaode-screenshot':
        if not all([args.from_lng, args.from_lat, args.from_name,
                    args.to_lng, args.to_lat, args.to_name]):
            print('Error: gaode-screenshot 模式需要 --from-lng --from-lat --from-name '
                  '--to-lng --to-lat --to-name')
            sys.exit(1)
        if not args.output:
            print('Error: gaode-screenshot 模式需要 -o/--output')
            sys.exit(1)
        # 调用旧版截图方法
        asyncio.run(_fallback_gaode_screenshot(
            from_lng=args.from_lng, from_lat=args.from_lat,
            from_name=args.from_name,
            to_lng=args.to_lng, to_lat=args.to_lat,
            to_name=args.to_name,
            output_path=args.output,
            width=args.width, height=args.height,
            scale=args.scale, wait_ms=args.wait,
        ))

    # ---- 批量高德路线截图 ----
    elif args.mode == 'batch-gaode-routes':
        if not args.input:
            print('Error: batch-gaode-routes 模式需要 pois.json 作为第一个参数')
            sys.exit(1)
        out_dir = args.output or './output/screenshots'
        asyncio.run(batch_gaode_routes(args.input, out_dir, scale=args.scale))

    # ---- 普通 HTML 截图模式 ----
    else:
        if not args.input:
            print('Error: 需要 HTML 文件路径')
            sys.exit(1)

        if args.batch:
            days = args.days.split(',') if args.days else None
            out_dir = args.output or './screenshots'
            asyncio.run(screenshot_batch(args.input, out_dir, days=days, scale=args.scale))
        else:
            if not args.output:
                print('Error: 单张模式需要 -o/--output')
                sys.exit(1)
            asyncio.run(screenshot(
                args.input, args.output,
                day=args.day, mode=args.mode,
                width=args.width, height=args.height,
                scale=args.scale, wait_ms=args.wait,
            ))


if __name__ == '__main__':
    main()
