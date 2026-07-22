# Examples · 脱敏示例

本目录是一份**完整但脱敏**的示例,展示 5 类产物长什么样。所有数据都是占位符,**不是真实坐标 / 真实地名**。

## 内容

- `trip-guide.md` — 游玩攻略长文(3 天 9 POI)
- `trip-nav.html` — 导航点位网页(模板,需要填 Day section)
- `trip-overview-map.html` — OSRM 综合地图(已预填数据,可直接浏览器打开)
- `pois.json` — 原始点位 JSON
- `trip.kml` — KML 文件

## 数据说明

| 字段 | 示例值 | 说明 |
|---|---|---|
| 行程名 | "示例行程" | 通用占位 |
| POI 名 | 起点 / 景点 A / 餐厅 A / 酒店 A | 语义化占位,非真实地名 |
| 坐标 | 116.000000, 40.000000 | 任意数字,无地理含义 |
| 时长 | 100km · 2h | 占位数值 |
| tag | start/end/attract/hotel/food/service/stop | 真实分类 |

## 一键试跑

```bash
# 校验
cd ../scripts && python validate.py ../examples/pois.json

# 一键生成产物(输出到 ./output/)
cd ../scripts && python gen_trip_artifacts.py ../examples/pois.json -o ../examples/_output/

# 截图
cd ../scripts && python screenshot_html.py ../examples/_output/trip-overview-map.html --batch -o ../examples/_screenshots/

# 看截图
open ../examples/_screenshots/overview.png
open ../examples/_screenshots/d1.png
```

`gen_trip_artifacts.py` 会:
- 读 `pois.json`
- 拉 OSRM 路径(1 req/s,5 段约 6 秒)
- 生成 `trip-overview-map.html`(OSRM 注入)和 `trip.kml`

## 重命名建议

复制示例到自己的项目目录时,建议重命名为:

| 示例文件 | 你的文件名 |
|---|---|
| `pois.json` | `{your-trip-slug}.pois.json` |
| `trip-nav.html` | `{your-trip-slug}-trip-map.html` |
| `trip-overview-map.html` | `{your-trip-slug}-trip-map-v1.html` |
| `trip.kml` | `{your-trip-slug}.kml` |
| `trip-guide.md` | `_posts/{YYYY-MM-DD}-{your-trip-slug}.md` |

## 看 example 渲染效果

直接浏览器打开 `trip-overview-map.html` 即可看到 3 Day 地图:
- D1 红色虚线 / 实线(切换)
- D2 蓝色
- D3 绿色
- 切换按钮:📅 Day / 🛣 路径
- 特殊路线(示例景观公路)在 D2 显示
