# Examples · 脱敏示例

本目录是一份**完整但脱敏**的示例,展示 5 类产物长什么样。所有数据都是占位符,**不是真实坐标 / 真实地名**。

## 内容

- `trip-guide.md` — 游玩攻略长文(3 天 9 POI)
- `trip-nav.html` — 导航点位网页
- `trip-overview-map.html` — OSRM 综合地图(用 `__DATA_PLACEHOLDER__` 标记数据插入点)
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

## 怎么看示例

1. **想看数据结构** → 打开 `pois.json`
2. **想看最终 HTML 效果** → 浏览器打开 `trip-nav.html` 和 `trip-overview-map.html`
3. **想看攻略长文格式** → 打开 `trip-guide.md` 源码
4. **想看 KML 格式** → 打开 `trip.kml` 源码
5. **想做自己的行程** → 复制模板,按真实数据替换

## 重命名建议

复制示例到自己的项目目录时,建议重命名为:

| 示例文件 | 你的文件名 |
|---|---|
| `pois.json` | `{your-trip-slug}.pois.json` |
| `trip-nav.html` | `{your-trip-slug}-trip-map.html` |
| `trip-overview-map.html` | `{your-trip-slug}-trip-map-v1.html` |
| `trip.kml` | `{your-trip-slug}.kml` |
| `trip-guide.md` | `_posts/{YYYY-MM-DD}-{your-trip-slug}.md` |
