# 输入数据格式

本文档说明 trip-plan skill 的**输入端**:支持什么形式、怎么识别、怎么处理成标准 `pois.json`。

> **设计原则**:输入可以是任何形式,但**输出必须归一到 `pois.json`**,后续流程才接得上。
> 不可结构化的输入(图片/语音/PDF)请先 OCR 或手工转文本,再喂进来。

---

## 1. 支持的输入形式(5 类自动识别)

| 形式 | 自动识别条件 | 适用场景 | 抽取精度 |
|---|---|---|---|
| HTML 导航页 | `.html` / `.htm` 且含 `<div class="poi">` | 已有 trip-plan 产物 / 别人共享的同类 HTML | ★★★★★ |
| Markdown 文章 | `.md` / `.markdown` 扩展名 | 博客 `_posts/*.md` 攻略 | ★★★ |
| CSV 表 | `.csv` + 表头含 `day,name` | LLM 辅助抽取后中转 | ★★★★ |
| JSON | `.json` + 含 `pois` 字段 | 已是标准格式,直接透传 | ★★★★★ |
| 自由文本 | 其他扩展名 / 无扩展名 | 笔记 / 对话 / 散文 | ★★(需 LLM 辅助) |

**强制指定形式**:`python parse_input.py input.txt --form csv`(绕过自动识别)

**显式标志**:
- `--form auto` (默认) · 按扩展名 + 内容启发式识别
- `--form html|markdown|csv|json|text` · 强制指定

---

## 2. 端到端工作流

```
[任意输入]
    │
    ├─ HTML / MD / CSV / JSON  ──► parse_input.py ──► pois.json ──┐
    │                                                            │
    └─ 自由文本 ──► LLM 抽 CSV ──► parse_input.py ──► pois.json ─┤
                                                                 │
                                          validate.py 校验 ◄──────┤
                                                                 │
                                          gcj02_wgs84.py 补 WGS-84
                                                                 │
                                          gen_trip_artifacts.py  ◄┘
                                                                 │
                                                                 ▼
                                                          5 类产物(nav/map/kml/...)
```

| 阶段 | 工具 | 输入 | 输出 |
|---|---|---|---|
| 抽取 | `parse_input.py` | 任意文件 | `pois.json` |
| 校验 | `validate.py` | `pois.json` | 错误 / 警告 |
| 补坐标 | `gcj02_wgs84.py` | `pois.json` | 同(补 WGS-84) |
| 生成 | `gen_trip_artifacts.py` | `pois.json` | 5 类产物 |

---

## 3. 各形式处理细节

### 3.1 HTML 导航页(trip-plan nav-template 格式)

**识别条件**:`.html` / `.htm` 且文件含 `<div class="poi">` 节点。

**抽取逻辑**(具体实现见 `scripts/parse_input.py`):

1. 用 stdlib `HTMLParser` 解析 DOM(无需 BS4)
2. 找 `<section class="day" id="dayN">` 节点,记 `day` 编号
3. 找 `.day-info h2` → `days_summary[day].title`
4. 找 `.day-info .meta` → `days_summary[day].desc`
5. 找 `.poi` 节点:
   - name = `.poi-name` 的首个文本节点(去掉 tag span 文字)
   - tag = `.poi-name .tag` 的 class 名(中文标签映射到 enum)
   - info = `.poi-info` 文本
   - 坐标 = 从 `.btn-nav` 的 href 抓 `uri.amap.com/navigation?to=<lng>,<lat>,<name>`
     - `to=0,0` 的标 `coord_source=fallback`
     - 有真实坐标的标 `original`
   - tag 中文 → enum 映射表见 parse_input.py 顶部 `TAG_CN_TO_ENUM`

**输出**:`coord_source` 默认 `original`(坐标来源精确)

**典型用例**:
- 用户已有 trip-plan 产物想反推数据
- 别人共享的同类 HTML 攻略
- 你之前的旧版导航页想重新生成

**局限**:只识别 trip-plan `nav-template.html` 格式的 HTML。其他博客的导航块需走 Markdown 路径。

### 3.2 Markdown 攻略

**识别条件**:`.md` / `.markdown` 扩展名。

**抽取逻辑**:

1. 按行扫描
2. Day 检测:`D1` / `Day 1` / `第一天` / `周六` 等(正则匹配)
3. POI 抽取(按以下优先级):
   - 含 `uri.amap.com/navigation?to=` 链接的列表项 / 标题 → 坐标 known
   - 含 `**名称**` + 时间描述的列表项 → 坐标 fallback
   - 跳过纯描述段落(不含 POI 关键词)
4. tag 默认 `attract`,从上下文关键词推断(hotel / food / service)

**注意**:Markdown 文章里的 POI 通常没有 group 划分,需要从段落上下文推断时段(上午/下午/晚上)

**输出**:`coord_source` 默认 `known`(景点类常带链接)或 `fallback`(无链接)

**典型用例**:
- 自己的 `_posts/*.md` 攻略想沉淀成导航页
- 别人的 markdown 攻略想本地化

### 3.3 CSV

**识别条件**:`.csv` 扩展名 + 表头含 `day,name` 等基础字段。

**格式**(LLM 辅助抽取的中间产物格式):

```csv
day,idx,name,tag,info,lng,lat,coord_source
D1,1,起点,start,早上 8:00 出发,116.000000,40.000000,original
D1,2,服务区 A,service,10:00 第一次休整,116.200000,40.200000,fallback
D1,3,景点 A,attract,12:30 抵达 · 游玩 2h,116.500000,40.500000,known
```

字段说明:
- `day` — Day 编号,形如 `D1`/`D2`/`D3`
- `idx` — Day 内序号,从 1 开始(可省略,自动递增)
- `name` — POI 名称(URL encode 由脚本处理)
- `tag` — enum:`start`/`end`/`attract`/`hotel`/`food`/`service`/`stop`(可省略,默认 `attract`)
- `info` — 时间 + 玩法 + 注意事项
- `lng` / `lat` — GCJ-02 经纬度(可省略 → fallback)
- `coord_source` — `original`/`known`/`fallback`(可省略,默认 `fallback`)

### 3.4 JSON

**识别条件**:`.json` 扩展名且顶层含 `pois` 字段。

**透传**:已是标准格式,直接 `validate.py` 校验即可;`parse_input.py` 仅做最小字段校验后写回。

### 3.5 自由文本

**识别条件**:扩展名 `.txt` / `.text` / 无扩展名 / 不匹配以上。

**处理**:**不在脚本内做 LLM 调用**(成本 + 不可重复)。改走 CSV 中转:

1. 用 §6 的 prompt 模板让 LLM 抽 CSV
2. 保存为 `extracted.csv`
3. `python parse_input.py extracted.csv -o pois.json`

`parse_input.py` 检测到自由文本后,会**打印 LLM prompt 模板**到 stderr,然后 exit(2) 让用户走流程。

---

## 4. JSON 标准格式(canonical)

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

> 注:`day_routes_wgs84` 通常由 `gen_trip_artifacts.py` 拉 OSRM 后填上;如果不跑 OSRM(用直线),这个字段可以空着。

---

## 5. 必含 vs 可选字段

| 字段 | 必含? | 说明 |
|---|---|---|
| `pois` | ✓ | 顶层必含,空数组也允许但会被 `validate.py` 警告 |
| `day_routes_wgs84` | ✓ | 顶层必含,OSRM 跑完才有内容 |
| `days_summary` | ✓ | 顶层必含,顶部 Day 过滤按钮要用 |
| `pois[].day` | ✓ | 不填就没法分组 |
| `pois[].idx` | ✓ | Day 内顺序,影响 marker 编号 |
| `pois[].name` | ✓ | 唤起高德 App 搜索的关键词 |
| `pois[].tag` | ✓ | 影响颜色和图标 |
| `pois[].info` | ✓ | 游玩时间 / 玩法 / 注意事项 |
| `pois[].lng_gcj02` | ✓ | KML / 高德链接用,缺则标 fallback |
| `pois[].lat_gcj02` | ✓ | 同上 |
| `pois[].lng_wgs84` | ✓ | OSM 瓦片 / OSRM 用 |
| `pois[].lat_wgs84` | ✓ | 同上 |
| `pois[].coord_source` | ✓ | 决定渲染时透明度(original=实色,fallback=半透明) |
| `special_routes_wgs84` | △ | 仅 99号公路 / 达达线等需要 |

---

## 6. LLM 辅助抽取 prompt 模板

非结构化输入**不在脚本内做 LLM 调用**。通过以下 prompt 模板中转:

### 6.1 自由文本 → CSV(通用)

```
从下面这段旅行描述里,抽取所有 POI(景点 / 餐厅 / 酒店 / 服务区 / 起点终点)。

要求输出 CSV 格式,字段:day,idx,name,tag,info
- day: D1 / D2 / D3 ...,从"第 X 天"/"D1"等标记推断
- idx: Day 内序号,从 1 开始
- name: POI 名称(直接用文中名字)
- tag: 7 选 1(attract / hotel / food / service / start / end / stop)
- info: 时间 / 玩法 / 注意事项(原文照抄关键信息)

不需要写坐标(脚本会兜底)。仅输出 CSV 内容,不要其他说明。

[原始文本]
<贴文本>
```

### 6.2 长文章 → CSV

把 §6.1 的 prompt 前面加一句:"这是博客攻略长文,可能含大量非 POI 信息(背景 / 情感 / 装备清单),请只提取**实际要去的地方**(含游玩时间)。"

### 6.3 HTML 源码 → CSV(罕见)

如果 HTML 不是 trip-plan 格式,走 §6.1 但喂 HTML 源码,提示词里加"解析 HTML 时跳过所有装饰元素,只保留具体地点名称和时间"。

### 6.4 已知坐标 → CSV(高级)

如果文本里已经有"X 经纬度 / X 的 GPS 是 ..."这类信息,可在 prompt 里要求 LLM 直接填 `lng,lat,coord_source=known`:

```
[在 §6.1 基础上加:]
- 如果文本里提到坐标或地名+GPS,加两列 lng,lat(GCJ-02 坐标系)
- coord_source 三选一:original(原文自带精确坐标)/ known(常见坐标)/ fallback(无)
```

---

## 7. 处理优先级与失败策略

`parse_input.py` 的处理顺序(降级链):

1. **结构化精确抽取**:HTML / JSON / CSV 能精确抽取就用精确结果
2. **启发式正则 fallback**:Markdown / 半结构化文本用关键词 + 正则
3. **失败留痕**:解析不出来的 POI 输出 warning 到 stderr,但不阻断整体流程
4. **LLM 中转**:非结构化文本直接退出并打印 prompt 模板

**质量标记规则**:
- HTML 导航页 `uri.amap.com/navigation?to=<lng>,<lat>,<name>` 且 `lng,lat ≠ 0,0` → `original`
- 知名景点 / 公开资料常用坐标 → `known`
- city 中心 + 抖动 / 缺失坐标 → `fallback`

`validate.py` 会把所有 `attract + fallback` 标为警告,提示真实出行前需用 web_search 校核。

---

## 8. 何时不用 trip-plan

- 1-2 天的短途(不值得写 5 类产物,直接用高德 App 收藏就行)
- 没有 POI 数据的纯背景笔记(直接 Markdown 写)
- 只想要高德收藏导出(用高德 App 自带功能)
- 团队协作需要版本管理(应该用 Notion / Confluence / GitHub Issues,不是 HTML)