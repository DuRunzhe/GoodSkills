# 输入数据格式

本文档说明 trip-plan skill 的**输入端**:从哪儿来、怎么组织、什么字段必填、什么字段选填。

---

## 1. 数据来源(3 种)

### A. 高德地图收藏导出
- 高德 App → 我的 → 收藏 → 批量导出(部分版本支持,无则手动)
- 优点:坐标精确(`coord_source=original`)
- 缺点:导出格式不一定标准,通常要写小脚本转

### B. 现有 Markdown 攻略提取
- 从 `_posts/*.md` 或 `*.html` 攻略里抓 POI 列表
- 模式识别:"D1 ... 9:00 景点 A ... [高德链接](https://uri.amap.com/navigation?to=...)"
- 优点:已有时间安排和分类
- 缺点:无精确坐标,需补 `lng_gcj02` / `lat_gcj02`

### C. 手工建表
- 用 Excel / Numbers / Google Sheets 整理
- 一列 = 一个字段(day, name, tag, time, lng, lat, ...)
- 优点:直观
- 缺点:得自己写脚本导出 JSON

---

## 2. 推荐工作流(对应 A/B/C)

```
[来源] → [原始数据 CSV/MD] → [脚本转 JSON] → [validate.py 校验] → [gen_trip_artifacts.py 生成产物]
```

| 阶段 | 工具 | 输入 | 输出 |
|---|---|---|---|
| 收集 | 手记 / 高德 / 攻略提取 | - | 散落的 POI 列表 |
| 整理 | Excel / Notion | 散落列表 | `trip.csv` 或 `trip.md` |
| 转换 | 自写脚本 / `parse_input.py` | CSV/MD | `pois.json` |
| 校验 | `scripts/validate.py` | `pois.json` | 错误 / 警告列表 |
| 生成 | `scripts/gen_trip_artifacts.py` | `pois.json` | nav.html / overview-map.html / trip.kml |

---

## 3. CSV 格式(简化输入,推荐起步用)

```csv
day,idx,name,tag,info,lng,lat,coord_source
D1,1,起点,start,早上 8:00 出发,116.000000,40.000000,original
D1,2,服务区 A,service,10:00 第一次休整,116.200000,40.200000,fallback
D1,3,景点 A,attract,12:30 抵达 · 游玩 2h,116.500000,40.500000,known
```

字段说明:
- `day` — Day 编号,形如 D1/D2/D3
- `idx` — Day 内序号,从 1 开始
- `name` — POI 名称(URL encode 由脚本处理)
- `tag` — 7 选 1:`start`/`end`/`attract`/`hotel`/`food`/`service`/`stop`
- `info` — 时间 + 玩法 + 注意事项
- `lng` — GCJ-02 经度(高德坐标系)
- `lat` — GCJ-02 纬度
- `coord_source` — 3 选 1:`original` / `known` / `fallback`

写完 CSV 后,用 `parse_input.py` 转换成 `pois.json`:

```bash
python scripts/parse_input.py trip.csv -o pois.json
```

(可选手动)再 `python scripts/gcj02_wgs84.py pois.json pois.json --mode to_wgs84` 补上 WGS-84 坐标。

---

## 4. JSON 格式(canonical)

完整 schema 见 `assets/pois.schema.json`。最小 JSON:

```json
{
  "pois": [
    {
      "day": "D1", "idx": 1, "name": "起点", "tag": "start",
      "info": "早上 8:00 出发",
      "lng_gcj02": 116.0, "lat_gcj02": 40.0,
      "lng_wgs84": 115.995, "lat_wgs84": 39.9956,
      "coord_source": "original"
    }
  ],
  "day_routes_wgs84": {},
  "special_routes_wgs84": [],
  "days_summary": {
    "D1": {"title": "...", "desc": "...", "count": 1}
  }
}
```

> 注:`day_routes_wgs84` 通常由 `gen_trip_artifacts.py` 拉 OSRM 后填上;如果你**不跑 OSRM**(用直线),这个字段可以空着或只填 POI 直线坐标。

---

## 5. 必含 vs 可选字段

| 字段 | 必含? | 说明 |
|---|---|---|
| `day` | ✓ | 不填就没法分组 |
| `idx` | ✓ | Day 内顺序,影响 marker 编号 |
| `name` | ✓ | 唤起高德 App 搜索的关键词 |
| `tag` | ✓ | 影响颜色和图标 |
| `info` | ✓ | 游玩时间 / 玩法 / 注意事项 |
| `lng_gcj02` | ✓ | KML / 高德链接用 |
| `lat_gcj02` | ✓ | 同上 |
| `lng_wgs84` | ✓ | OSM 瓦片 / OSRM 用 |
| `lat_wgs84` | ✓ | 同上 |
| `coord_source` | ✓ | 决定渲染时透明度(original=实色,fallback=半透明) |
| `day_routes_wgs84` | △ | 仅 OSRM 综合地图需要 |
| `special_routes_wgs84` | △ | 仅 99号公路 / 达达线等需要 |
| `days_summary` | ✓ | 顶部 Day 过滤按钮要用 |

---

## 6. 何时不用 trip-plan

- 1-2 天的短途(不值得写 5 类产物,直接用高德 App 收藏就行)
- 没有精确坐标的快速笔记(直接 Markdown 写)
- 只想要高德收藏导出(用高德 App 自带功能)
- 团队协作需要版本管理(应该用 Notion / Confluence / GitHub Issues,不是 HTML)
