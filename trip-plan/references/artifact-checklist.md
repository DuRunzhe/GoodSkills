# 产物要素清单

5 类产物各自必含 / 可选的元素清单。生成时按本清单自检。

---

## 1. 游玩攻略长文(Jekyll `_posts/*.md`)

### 必含

| 元素 | 说明 |
|---|---|
| Frontmatter | `layout: post`、`title`、`date`、`categories: [trip, transport_mode]`、`tags: [...]` |
| "为什么去"段 | 2-3 段,200-400 字,说明这趟旅行的核心吸引力 |
| 路线总览段 | 1 段 + 1 张总览图(OSRM 综合地图截图) |
| 行前必带清单 | 4 类:证件 / 装备 / 衣物 / 药品 |
| Day × N 详述 | 每天一节,包含:概览表 + 上午段 + 下午段 + 黄昏+晚段 |
| 总预算 | 按类别(油费 / 住宿 / 餐饮 / 门票 / 其他)+ 合计 |
| 节点速查表 | 5 列:Day / 里程 / 时间 / 主题 / 关键 POI |
| 配套产物链接 | 导航页 URL + 综合地图 URL + JSON URL |

### 可选

- 备选加点(可放弃的扩展 POI)
- 节庆查询清单(那达慕 / 花期 / 封路)
- 行前照片 / 装备清单图片
- 攻略写完后引用导航页

### 不要

- 不要把所有 POI 都堆进长文(留给导航页)
- 不要在长文里放具体坐标(交给数据文件)

---

## 2. 导航点位网页(高德直接 href HTML)

### 必含

| 元素 | 说明 |
|---|---|
| 顶部 header | 标题 + 路线概要 + 提示语("点击任意点位 → 高德 App 自动导航") |
| day-nav 锚点栏 | sticky,水平滚动,每个 Day 一个链接 |
| Day × N section | `id="day1"` / `id="day2"` / ... |
| day-title | Day 编号 + 日期 + 长标题 + 里程/时长/主题 |
| group 分类 | 按时段(上午/下午/晚上)或按类别(景点/餐厅/酒店) |
| poi 卡片 | name + tag 徽章 + info + 2-3 个 action 按钮 |
| 有坐标 POI 3 按钮 | 🚗 导航 / 📍 标记位置 / 🔍 搜索 |
| 无坐标 POI 2 按钮 | 🚗 导航(0,0)+ 🔍 搜索(带 city) |
| usage 区块 | 使用说明 + tip |
| to-top 按钮 | fixed 右下角,滚动 200px 后显示 |

### 可选

- 🖼 **POI 路线预览截图**：每张 POI 卡片嵌入可折叠的高德路线截图(显示距离/时长/通行费)
  - 截图路径记录在 `route_screenshots` 数据中
  - 点击「📍 导航路线」标签展开/收起
  - 截图来自 `screenshot_html.py --mode batch-gaode-routes`
- day-nav 当前 active 高亮(JS 监听 scroll)
- 搜索框(快速定位 POI)

### 不要

- 不要用 JS 异步加载地图(高德 App 唤起需用直接 href)
- 不要用 JS data-attr 拼 URL(直接写 href)
- 不要把 📍 标记位置给 0,0 坐标的点(会标到几内亚湾)

---

## 3. OSRM 综合地图(Leaflet HTML)

### 必含

| 元素 | 说明 |
|---|---|
| header | 标题 + 简介 |
| controls | Day 过滤按钮 + 路径模式切换(导航/直线) |
| map div | 全屏高度(`calc(100vh - 130px)`) |
| Leaflet 1.9.x | CDN(unpkg) + integrity hash |
| 底图瓦片 | OSM(`https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png`) |
| POI marker | divIcon,圆圈+数字,按 tag 颜色 |
| Day 路径 | L.polyline,OSRM geometry(实线)或直线(虚线) |
| Day 颜色 | 5 段不同色(D1 红 / D2 蓝 / D3 绿 / D4 橙 / D5 紫) |
| Popup | 含高德导航链接(GCJ-02 坐标拼 uri.amap.com) |
| 图例 | 类别 + Day + 特殊路线 |

### 可选

- 99 号公路等特殊路线(L.polyline + 自定义颜色)
- coord_source 透明度区分(原始/已知/兜底)
- 截图按钮

### 不要

- 不要用高德瓦片(要 key,公开不便)
- 不要把 WGS-84 坐标当 GCJ-02 渲染(国内偏移 100-700m)
- 不要忽略 OSRM 限速(每段 sleep 1.1s)

---

## 4. 原始点位 JSON(`.json`)

### 必含(顶层)

| 字段 | 类型 | 说明 |
|---|---|---|
| `pois` | Array | 所有 POI,每项有 day / idx / name / tag / info / 双坐标 / coord_source |
| `day_routes_wgs84` | Object | 每 Day 的 OSRM 路径(WGS-84),key=day_id,value=[[lng,lat],...] |
| `days_summary` | Object | 每 Day 的 title / desc / count |

### 可选(顶层)

- `special_routes_wgs84`: 99 号公路等 OSRM 不识别的命名公路
- `metadata`: 行程名 / 起点 / 终点 / 总里程 / 总天数

### 不要

- 不要只存一种坐标系(GPS 设备 / 高德 / OSM 都需要)
- 不要把 `info` 留空(后续生成描述都用得上)

---

## 5. KML(`.kml`)

### 必含

| 元素 | 说明 |
|---|---|
| `<?xml version="1.0" encoding="UTF-8"?>` | XML 头 |
| `<kml xmlns="http://www.opengis.net/kml/2.2">` | KML 命名空间 |
| `<Document>` 顶层 | KML 2.2 标准结构 |
| `<name>` 行程名 | 文档名 |
| `<description>` 描述 | 简介 |
| 每 Day 一个 `<Folder>` | 包含行程连线 + 所有 POI |
| 行程连线 `<Placemark>` | `<LineString>` 包含当日所有 POI 坐标 |
| POI `<Placemark>` | `<Point>` + `<name>` + `<description>` + `<Style>` |
| 高德导航链接 | 嵌在 `<description>` 的 CDATA 里 |

### 可选

- 特殊路线 Folder(99 号公路)
- 网络链接 `<NetworkLink>` 引用其他 KML(本 skill 不强求)

### 不要

- 不要用 WGS-84 坐标(高德会偏移到几内亚湾,必须用 GCJ-02)
- 不要忘了 `<Style>` 部分(没样式 KML 在高德里所有点都是默认黄)
- 不要忘了 CDATA 包裹 description(否则含 `<br/>` 的 HTML 会破坏 XML)

---

## 通用

### 必含(所有产物)

- 行程名 / 标题
- 文字描述 + emoji 图标(让手机读起来不累)
- 标签/分类色彩
- 配套产物链接(互相导流)

### 必含(发布版本)

- 隐私检查:不出现真实住址 / 车牌 / token
- 占位符检查:`{placeholder}` 必须全部替换
- 坐标质量检查:fallback 坐标的 POI 至少在文中标注"需核实"
