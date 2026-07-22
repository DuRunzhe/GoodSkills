#!/usr/bin/env python3
"""
Day 颜色分配工具(自动避撞色)

5 天以内用固定方案(从 references/layout-styles.md):
  D1 红 / D2 蓝 / D3 绿 / D4 橙 / D5 紫

5 天以上按 Material Design 500 调色板顺延,
从 19 种颜色循环,避免撞色。
"""
import sys


# Material Design 500 调色板(19 色,避开 5 天已用的红蓝绿橙紫)
PALETTE = [
    '#E91E63',  # Pink
    '#9C27B0',  # Purple
    '#673AB7',  # Deep Purple
    '#3F51B5',  # Indigo
    '#2196F3',  # Blue
    '#03A9F4',  # Light Blue
    '#00BCD4',  # Cyan
    '#009688',  # Teal
    '#4CAF50',  # Green
    '#8BC34A',  # Light Green
    '#CDDC39',  # Lime
    '#FFEB3B',  # Yellow
    '#FFC107',  # Amber
    '#FF9800',  # Orange
    '#FF5722',  # Deep Orange
    '#795548',  # Brown
    '#9E9E9E',  # Grey
    '#607D8B',  # Blue Grey
    '#F44336',  # Red
]

# 前 5 天的固定方案(优先于调色板,保证向后兼容)
FIXED_5DAYS = {
    'D1': '#E53935',
    'D2': '#1E88E5',
    'D3': '#43A047',
    'D4': '#FB8C00',
    'D5': '#8E24AA',
}


def assign_day_colors(day_count):
    """返回 {D1: color, D2: color, ...} 字典
    day_count: 行程天数
    """
    result = {}
    # 1-5 天用固定方案
    for i in range(1, min(day_count, 5) + 1):
        result['D' + str(i)] = FIXED_5DAYS['D' + str(i)]
    # 6+ 天用调色板顺延
    palette_idx = 0
    for i in range(6, day_count + 1):
        result['D' + str(i)] = PALETTE[palette_idx % len(PALETTE)]
        palette_idx += 1
    return result


def main():
    if len(sys.argv) < 2:
        print('Usage: assign_day_colors.py <day_count>')
        print('  Output: JSON {"D1": "#color", "D2": "#color", ...}')
        sys.exit(1)

    try:
        n = int(sys.argv[1])
    except ValueError:
        print(f"Error: day_count must be integer, got {sys.argv[1]!r}")
        sys.exit(1)

    if n < 1 or n > 50:
        print(f"Warning: day_count={n} is unusual (typical: 1-14)")

    colors = assign_day_colors(n)
    import json
    print(json.dumps(colors, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
