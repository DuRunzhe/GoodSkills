#!/usr/bin/env python3
"""
Playwright HTML 截图工具(给 Leaflet 综合地图用)

依赖:
  pip install playwright
  playwright install chromium

用法:
  # 截总览
  python screenshot_html.py inner-mongolia-v5-map.html -o overview.png

  # 截某一天
  python screenshot_html.py inner-mongolia-v5-map.html -o d1.png --day D1

  # 批量截全部(总览 + 每天)
  python screenshot_html.py inner-mongolia-v5-map.html --batch -o ./screenshots/

  # 高清 + 自定义视口
  python screenshot_html.py inner-mongolia-v5-map.html -o hi.png --scale 3 --width 1600
"""
import argparse
import asyncio
import sys
from pathlib import Path

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


def main():
    parser = argparse.ArgumentParser(description='Playwright HTML 截图')
    parser.add_argument('html', help='HTML 文件路径')
    parser.add_argument('-o', '--output', help='输出 PNG 路径(单张模式)')
    parser.add_argument('--day', help='点击该 Day 按钮(如 D1/D2)')
    parser.add_argument('--mode', choices=['route', 'straight'], help='切换路径模式')
    parser.add_argument('--batch', action='store_true', help='批量截总览+每 Day')
    parser.add_argument('--days', help='批量模式下指定 Day,逗号分隔(如 D1,D2,D3)')
    parser.add_argument('--width', type=int, default=1280, help='视口宽度')
    parser.add_argument('--height', type=int, default=900, help='视口高度')
    parser.add_argument('--scale', type=int, default=2, help='device_scale_factor(高清用 2 或 3)')
    parser.add_argument('--wait', type=int, default=5000, help='瓦片加载等待时间(ms)')
    args = parser.parse_args()

    if args.batch:
        days = args.days.split(',') if args.days else None
        out_dir = args.output or './screenshots'
        asyncio.run(screenshot_batch(args.html, out_dir, days=days, scale=args.scale))
    else:
        if not args.output:
            print('Error: 单张模式需要 -o/--output')
            sys.exit(1)
        asyncio.run(screenshot(
            args.html, args.output,
            day=args.day, mode=args.mode,
            width=args.width, height=args.height,
            scale=args.scale, wait_ms=args.wait,
        ))


if __name__ == '__main__':
    main()
