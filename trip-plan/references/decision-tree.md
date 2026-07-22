# 决策树:什么时候用 trip-plan?怎么走流程?

trip-plan skill 5 类产物不是"全部都得用",根据场景选。**新版决策入口**:你有什么形式的输入?(任意形式都能跑)

---

## 决策入口(2026-07-23 起)

```
                        你要做一趟新行程(或有现成的旅行内容想沉淀)
                              │
                              ▼
              ┌── 你有真实旅行内容吗?(任意形式)
              │
              ├─ 否 → 高德 App 收藏 / Notion 笔记(见 input-format.md §8)
              │
              └─ 是(任何形式)
                 │
                 ▼
              ┌── 输入形式是什么?
              │
              ├─ HTML 导航页(trip-plan 同类) → 直接 parse_input.py(★★★★★)
              │
              ├─ Markdown 攻略 / _posts/*.md → parse_input.py(★★★)
              │
              ├─ CSV / Excel 表 → parse_input.py(★★★★)
              │
              ├─ JSON(已是标准格式) → parse_input.py 透传(★★★★★)
              │
              └─ 自由文本 / 对话 / 笔记
                 │
                 ▼
              ┌── LLM 辅助抽取可行吗?
              │
                 ├─ 是 → LLM 抽 CSV → parse_input.py 吃 CSV(★★★)
                 │
                 └─ 否 / 图片 / 语音 → 先 OCR / 手工转文本,然后走上面任一路径
                              │
                              ▼
              ┌── 要发到博客公开吗?
              │
              ├─ 否 → 只生成 JSON + KML(本地用)
              │
              └─ 是
                 │
                 ▼
       ┌── 你有精确坐标吗?(从 parse_input 输出读 coord_source 分布)
       │
       ├─ 全部 original / known → 跳过 city 兜底,直接生成
       │
       └─ 大量 fallback(餐厅/服务区)→ 真实出行前必须用 web_search 校核
                     │
                     ▼
              ┌── 要 OSRM 实际路径吗?
              │
              ├─ 否 → 生成 nav.html + kml 即可
              │
              └─ 是(5 天以上长途)→ 跑 OSRM,可能有命名公路 OSRM 不认,需预设 waypoint
                          │
                          ▼
                   ┌── 要截图分享吗?
                   │
                   ├─ 否 → 直接用 HTML
                   │
                   └─ 是(发朋友圈/小红书)→ 跑 Playwright 截图
```

---

## 场景 → 产物推荐

| 场景 | 输入形式 | 推荐产物 | 可选产物 |
|---|---|---|---|
| 已有 trip-plan nav-template HTML 想改 | HTML | nav.html(重生成) | kml |
| 已有博客 _posts/*.md 攻略 | Markdown | nav.html + 攻略长文 | kml / overview-map |
| 已有高德收藏导出 | CSV | nav.html + kml | overview-map |
| 多轮对话聊出来的行程 | 自由文本 → CSV | nav.html + kml | - |
| 周末 2 天短途 | 任意 | nav.html | - |
| 自驾 3-5 天 | 任意 | nav.html + kml | overview-map |
| 自驾 7+ 天 | 任意 | **全部 5 类** + 攻略长文 | - |
| 那达慕 / 花期等节庆行程 | 任意 | 全部 5 类 + 攻略长文(含节庆查询) | - |
| 摩托骑行 | 任意 | nav.html + kml(注意 service / fuel POI) | - |
| 高铁 + 当地租车 | 任意 | nav.html(按城市分 Day) + kml | - |
| 多支线备选 | 任意 | nav.html + kml(含可选 Folder) | overview-map |

---

## "Day 颜色 5 段硬编码"问题

D1-D5 固定方案:
- D1 红 / D2 蓝 / D3 绿 / D4 橙 / D5 紫

超过 5 天怎么办?

**用 `scripts/assign_day_colors.py` 自动分配**:

```bash
python scripts/assign_day_colors.py 7
```

返回:
```json
{
  "D1": "#E53935",
  "D2": "#1E88E5",
  "D3": "#43A047",
  "D4": "#FB8F00",
  "D5": "#8E24AA",
  "D6": "#E91E63",
  "D7": "#9C27B0"
}
```

D6+ 按 Material Design 500 调色板顺延。`gen_trip_artifacts.py` 会自动调用。

---

## "OSRM 走不通"问题

如果你的行程包含:
- 99 号公路 / 达达线 / 热阿线 / 张北草原天路 等**命名景观公路**
- 草原深处 / 山区小路 等 OSRM 数据稀疏路段

OSRM 会算成走高速/国道,丢失景观价值。

**解决方案**:
1. 提前在 `pois.json` 的 `special_routes_wgs84` 字段预设 waypoint 数组
2. 10-15 个点足够(经棚镇 → 半拉山 → 西乌旗 这样的关键节点)
3. `gen_trip_artifacts.py` 会自动在 overview-map 上画预设线 + 弹出提示

---

## "全部 fallback 坐标"问题

如果 `coord_source` 大部分都是 `fallback`,说明:
- 餐厅 / 服务区 / 当地小店没精确坐标
- 出行时高德 App 会**定位到 city 中心**,误差 5-10 km

**真实出行前必须**:
- 用 web_search 把 fallback POI 校核到 known
- 至少把 "景点" 类的 fallback 全部校核
- 餐厅 / 酒店 类的 fallback 可以临时用 city 限定搜索兜底

`scripts/validate.py` 会把所有 `attract + fallback` 标为警告。

---

## "5 天以上,但没空写攻略长文"问题

不是必须!5 类产物是**并行可选**,不是**串行必做**。

最少组合(2 类,15 分钟):
- nav.html(用户手机上现场导航)
- kml(用户提前导入高德 App)

完整组合(5 类,2-3 小时):
- nav.html + kml + overview-map.html + 攻略长文 + 截图 PNG
- 适合做完后 1-2 周内出行的行程(有时间分享给同行者)

---

## "输入是图片 / 语音 / PDF"问题

trip-plan 的 `parse_input.py` 只处理**文本类输入**。

**绕行路径**:
1. 图片 → 截图 OCR(tesseract / 微信图片转文字 / 手机相册 Live Text)
2. 语音 → 飞书妙记 / 通义听悟 / Otter.ai
3. PDF → `pdftotext`(Linux/macOS 自带) / Adobe Acrobat 导出
4. 转出来的文本 → 走自由文本路径(`parse_input.py` 打印 LLM prompt → LLM 抽 CSV → 再喂 parse_input.py)

---

## "反推 HTML 但坐标全是 fallback"问题

如果 HTML 里的导航链接 `to=0,0`(占位),`parse_input.py` 会标 `coord_source=fallback`。

**补救**:
1. 看 HTML 里有没有 `📍 标记位置` 按钮(那种有真实 lng/lat)
2. 看 info 字段有没有地址线索
3. 用 `web_search "POI 名称" "经纬度"` 校核
4. 手动改 `pois.json` 的 `lng_gcj02` / `lat_gcj02`,再跑 `validate.py` + `gcj02_wgs84.py`