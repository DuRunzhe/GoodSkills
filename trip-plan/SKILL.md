---
name: trip-plan
description: 旅行攻略智能生成 skill。基于 SKILL.md + destinations/<slug>.md playbook + LLM 推理,产出 5 件套(导航页/综合地图/KML/JSON/攻略长文)。触发词:行程/攻略/自驾/路线/导航点位/综合地图/KML/高德导入。
---

# trip-plan

把一趟多日旅行的需求,产出 5 类可在不同场景使用的标准化产物。

## 设计原则(skill vs program)

**trip-plan 是一个 skill,不是一个独立的程序或工作流系统**。

| 是什么 | 不是什么 |
|---|---|
| ✅ SKILL.md + scripts + 知识库 | ❌ 有状态机的独立程序 |
| ✅ LLM 是 runtime | ❌ orchestrator 程序 |
| ✅ Scripts 是 LLM 可调用的工具 | ❌ 流水线 stage |
| ✅ Destinations/<slug>.md 是 LLM 可读的知识 | ❌ 一个独立的微服务 |
| ✅ 5 步推理是逻辑顺序 | ❌ 程序模块串行执行 |

**本 skill 的智能来自**:
1. SKILL.md 的详细度(LLM 读后知道做什么)
2. destinations/<slug>.md 知识完整度(LLM 读后知道本地知识)
3. LLM 的推理和创作能力(本来就内置的)
4. Scripts 的能力(LLM 做不好的事才用)

## 触发条件

满足以下任一即触发:

- 用户说「做一份 XX 行程 / 旅行攻略 / 自驾路线」
- 用户提供了任意形式的旅行内容(文章 / HTML / MD / CSV / 自由文本 / 已有攻略 URL)
- 用户说「用 trip-plan 规划 XX」
- 用户要导航点位页 / 综合地图 / OSRM 路线 / 高德 KML 导入

不确定要不要用?看 `references/decision-tree.md`

## 5 步推理指引(核心 ⭐)

被 trip-plan skill 唤起后,LLM 应该**按顺序但可自由跳转**地完成 5 步推理。

### Step 1 · 意图解析

**目标**:理解用户想要什么行程。

**LLM 在这一步做什么**:

1. 读用户输入(任意形式)
2. 拆解要素:目的地 / 天数 / 出行方式 / 预算 / 同行人 / 偏好 / 必去点 / 避雷点
3. 检查必填字段,**缺什么反问用户**
4. 内部结构化(不强制输出 JSON)

**必填字段**(缺一必问):

| 字段 | 说明 | 反问话术 |
|---|---|---|
| 目的地 | 地点 | 「想去哪里?」 |
| 天数 | D1 / D2 / ... | 「玩几天?」 |
| 出行方式 | 自驾 / 高铁 / 飞机 / 徒步 | 「自驾还是公共交通?」 |

**选填字段**(有则用,没则用默认):

| 字段 | 默认值 |
|---|---|
| 出发日期 | 最近周末 |
| 出发城市 | 北京(主人所在地) |
| 预算 | ¥500-800/人/天 |
| 同行人数 | 2 |
| 偏好 | 文化 + 美食 + 轻松 |
| 必去点 / 避雷点 | 自由文本 |

**追问模板**(多字段一起问,不要一个个问):

> "要规划 [X] 的行程吗?我需要确认:
> - 出发城市和日期?
> - 天数?
> - 出行方式(自驾 / 高铁 / 飞机)?
> - 同行人数?
> - 有没有必去点 / 避雷点?
> - 预算范围?"

**反问失败时的默认值**:天数 2 / 自驾 / 北京出发 / 周末 / ¥500-800/人/天 / 2 人

**调用的工具**:

- `parse_input.py <input> -o pois.json` · 用户给的是结构化数据时(HTML / CSV),反推提取
- 直接 `read` 用户给的 MD 文件

---

### Step 2 · 知识检索

**目标**:为 Step 3 行程规划 + Step 4 内容创作准备好所有需要的知识。

**LLM 在这一步做什么**:

1. 读 `destinations/<slug>.md`(若存在)— 已有本地化知识
2. 调 `web_search` 检索目的地最新信息(限行 / 预约 / 季节性)
3. 调 `wechat_spander` 抓公众号攻略(若用户给了 URL)
4. 读用户给的任何已有攻略(HTML / MD / 自由文本)

**LLM 应该查什么**(基于 destinations/<slug>.md 的提示):

- 限行规则(周末 / 节假日 / 单双号)
- 门票预约(电话 / 网址)
- 季节性(雨季 / 高反 / 最佳月份)
- 当地特色(必吃 / 必看 / 必买)
- 交通(路况 / 加油站密度)

**LLM 检索时的避坑**:

- ❌ 不要编造事实(查不到就标 `[待核实]`)
- ✅ 多源交叉(关键事实 ≥ 2 个来源)
- ✅ 缓存复用(同目的地同问题不重复查)

**调用的工具**:

- `web_search "五台山 限行 2026"` · 检索最新政策
- `wechat_spander <公众号 URL>` · 抓公众号文章
- `read destinations/<slug>.md` · 读本地 playbook
- `parse_input.py` · 反推用户已有数据

---

### Step 3 · 行程规划

**目标**:把 POI 列表重排成「实际可走、最优体验」的路线。

**LLM 在这一步做什么**:

1. 根据 Step 1 需求 + Step 2 知识 + 已有 POI,排出每 Day 的 POI 顺序
2. 推理路径合理性(不要走回头路)
3. 推理时段合理性(开放时间 / 用餐时间)
4. 推理约束满足度(必去点 / 限行 / 季节性)
5. 必要时调 `optimize_route.py` 做精确 TSP 路径计算

**LLM 的推理启发式**:

```
1. 先排「必须按时段」的 POI(寺院群 / 夜景 / 日出)
2. 再排「强相关」的 POI(同一区域 / 顺路)
3. 再排「可灵活调整」的 POI(休息 / 餐饮)
4. 最后做时段填充 + 路径最短化
```

**LLM 必须遵守的规则**(通用,所有目的地适用):

- ✅ 每个 Day 至少有 1 个景点 + 1 个餐厅
- ✅ 餐厅时段在 11:30-13:30 或 17:30-19:30
- ✅ 必去点全部出现
- ✅ 连续驾驶不超过 3h(每 2h 强制休整 15min)
- ✅ 当日总时长不超过 14h(早 7 点 ≤ 晚 21 点)
- ✅ 当日返程距酒店 < 50km 或返回出发地
- ✅ 季节性景点在正确时段

**目的地专属规则**:见 `destinations/<slug>.md` 的「专属规则」一节

**调用的工具**:

- `gcj02_wgs84.py pois.json pois.json --mode to_wgs84` · 坐标系互转
- `validate.py pois.json --strict` · 规则引擎校验(可选,LLM 自检也够)
- `optimize_route.py pois.json`(可选) · 当 POI > 15 或路径复杂时

**LLM 输出形式**:

- 内部推理已结构化(每 Day schedule + 路径)
- 选择性产出 `optimized.json`(便于 review)
- 直接进 Step 5 渲染

---

### Step 4 · 内容创作

**目标**:让产物「有人味」——有故事、有提醒、有温度。

**LLM 在这一步做什么**:

1. 写攻略长文(1500-3000 字)
2. 为每个 POI 写「为什么去 / 看什么 / 注意」描述
3. 写底部专属提醒
4. 写 Day 导语 + 路线文案

**LLM 的 Prompt 框架**(自问自答):

```
# 角色
我是经验丰富的本地向导,擅长 [X 类型] 行程设计。

# 输入(LLM 内部推理)
- 已规划的行程(Step 3 输出)
- 已检索的本地知识(Step 2 输出)
- 用户偏好(Step 1 输出)
- 目的地 playbook(destinations/<slug>.md 摘要)

# 任务
1. 写 200-400 字「为什么去」(从 X 独特价值切入)
2. 为每个 POI 写 50-80 字描述(为什么去 / 看什么 / 注意)
3. 写底部专属提醒(从 playbook 专属提醒 + 检索到的本地知识)

# 自检
- 不编造:无法核实标 [待核实]
- 不重复:跨段不抄写
- 不超长:长文 ≤ 3000 字,POI 描述 ≤ 100 字
- 多源交叉:关键事实 ≥ 2 个来源
```

**LLM 输出形式**:

- 直接写产物内容(Markdown / HTML 文案片段)
- 由 Step 5 的渲染工具填入模板

---

### Step 5 · 产物渲染 + 部署

**目标**:把所有信息组织成最终产物 + 部署上线。

**LLM 在这一步做什么**:

1. 整理 POI 数据 + 文案为渲染输入
2. 调 gen_trip_*.py 渲染 HTML
3. 调 validate.py 做质量门
4. 写攻略长文 `_posts/<slug>.md`
5. 截图 + 部署

**调用的工具**:

- `gen_trip_nav.py pois.json -o trip-nav.html` · 导航点位页
- `gen_trip_artifacts.py pois.json -o ./output --src TAG` · 综合地图 + KML
- `validate.py pois.json` · 部署前质量门
- `screenshot_html.py <html>`(可选) · 截图

**🌟 导航距离与过路费测算(高速优先)**:

在生成最终产物前,用两种方式获取每段路线导航距离/时长/通行费:

**首选方式(推荐)**: AMap.Driving JS API（高德驾车规划 API）

用 Playwright 打开高德地图首页建立 session,在页面内注入 JS 调用高德内置的 AMap.Driving API 获取真实路线数据:

```javascript
const driving = new AMap.Driving({policy: AMap.DrivingPolicy.LEAST_TIME});
driving.search(
    new AMap.LngLat(fromLng, fromLat),
    new AMap.LngLat(toLng, toLat),
    (status, result) => {
        if (status === 'complete') {
            const route = result.routes[0];
            // route.distance(米), route.time(秒), route.tolls(元)
        }
    }
);
```

API 返回真实的高速优先导航数据:导航距离(km)、预计时长(min)、通行费(元)。

**兜底方式**: 高德驾车页面截图

如果 JS API 方式失败,用 Playwright 截图高德驾车路线网页:
```
https://ditu.amap.com/dir?
  from[lng]={出发经度}&from[lat]={出发纬度}&from[name]={出发名称}&
  to[lng]={目的经度}&to[lat]={目的纬度}&to[name]={目的名称}&
  type=car&policy=1
```
policy=1=高速优先,2=时间优先,3=距离优先,4=避免拥堵

截图路线概要面板,提取距离/时长/通行费。

**全自动串联**:

1. **批量获取**：`screenshot_html.py` 提供两种模式:
   - `--mode batch-gaode-routes`：批量获取全部路线数据（首选,用 JS API）
   - `--mode batch-gaode-screenshots`：批量截图路线页面（兜底）

2. **数据注入**：将返回的 `{km, min, toll}` 数据写入 pois.json 的每 POI 的 `route_km` / `route_min` / `route_toll` 字段

3. **渲染**：`gen_trip_nav.py` 优先使用已存在的 `route_*` 数据（来自 API）,无则回退 Haversine 估算

4. **gen_trip_artifacts.py** 自动检测并加载路线数据文件

**部署流程**:

```bash
# 1. 复制产物到博客目录
cp output/trip-nav.html ~/blog/<slug>-trip-map.html

# 2. git 提交推送
cd ~/blog
git add <slug>-trip-map.html
git commit -m "feat(trip-map): <目的地>攻略"
git push origin main
```

**质量门(部署前必过)**:见本文末尾「验证清单(部署前质量门)」章节(10 项完整版)

---

## 工具调用清单(完整)

| 工具 | 调用 | 用在 |
|---|---|---|
| `parse_input.py` | `python3 scripts/parse_input.py <input> -o pois.json [--form auto\|html\|md\|csv\|json\|text] [--validate]` | Step 1 反推结构化 |
| `web_search` | OpenClaw 平台工具 | Step 2 检索 |
| `wechat_spander` | 通过 skill 调用 | Step 2 抓公众号 |
| `gcj02_wgs84.py` | `python3 scripts/gcj02_wgs84.py pois.json pois.json --mode to_wgs84` | Step 3 坐标互转 |
| `osrm_route.py` | `python3 scripts/osrm_route.py pois.json -o routes.json` | Step 5 OSRM 路径(由 gen_trip_artifacts.py 自动调) |
| `assign_day_colors.py` | `python3 scripts/assign_day_colors.py <N>` | Step 5 Day 颜色分配(由 gen_trip_artifacts.py 自动调) |
| `validate.py` | `python3 scripts/validate.py pois.json --strict` | Step 3 / Step 5 校验 |
| `gen_trip_nav.py` | `python3 scripts/gen_trip_nav.py pois.json -o nav.html` | Step 5 渲染导航页 |
| `gen_trip_artifacts.py` | `python3 scripts/gen_trip_artifacts.py pois.json -o ./output --src TAG [--no-osrm] [--no-validate]` | Step 5 渲染综合地图+KML |
| `screenshot_html.py` | `python3 scripts/screenshot_html.py <html> [--batch] [--days D1,D2,...] [-o PNG] [--mode route\|straight] [--width N] [--height N] [--scale N] [--wait N]` | Step 5 普通 HTML 截图 |
| `screenshot_html.py`(gaode-route) | `python3 scripts/screenshot_html.py --mode gaode-route --from-lng N --from-lat N --from-name A --to-lng N --to-lat N --to-name B` | Step 5 🌟🌟【首选】单段高德驾车数据(AMap.Driving JS API,高速优先) |
| `screenshot_html.py`(gaode-screenshot) | `python3 scripts/screenshot_html.py --mode gaode-screenshot --from-lng N --from-lat N --from-name A --to-lng N --to-lat N --to-name B -o route.png` | Step 5 🛡️【兜底】单段高德驾车截图(API不可用时) |
| `screenshot_html.py`(batch-gaode-routes) | `python3 scripts/screenshot_html.py pois.json --mode batch-gaode-routes -o ./output/gaode-route-data.json` | Step 5 🌟🌟🌟【批量推荐】批量获取全部POI段路线数据(API首选+截图兜底) |

## Playbook 使用

LLM 在被 trip-plan 唤起后,**先读完本 SKILL.md,再读对应目的地 playbook**(顺序见设计文档 §3.1):

```python
read destinations/<slug>.md     # 对应目的地知识:分组规则 + 必去点 + 专属提醒
```

Playbook 结构 + 注册方法见 `destinations/README.md`。

## 快速开始(LLM 调脚本的标准模板)

```bash
# Step 1: 反推(若有结构化输入)
python3 scripts/parse_input.py <input> -o pois.json

# Step 2: LLM 自己读 destinations/<slug>.md + 检索
# (无脚本调用)

# Step 3: 坐标互转 + 校验
python3 scripts/gcj02_wgs84.py pois.json pois.json --mode to_wgs84
python3 scripts/validate.py pois.json --strict

# Step 4: LLM 自己写内容
# (无脚本调用,LLM 直接产出文案)

# Step 5: 导航距离与路线截图(可选)
python3 scripts/screenshot_html.py pois.json --mode batch-gaode-routes -o ./output/screenshots/
# 此步生成每段路线截图,存于 screenshots/ 目录
# 截图显示:导航距离(km)+预计时长+通行费(元)

# Step 5: 渲染 + 部署(自动嵌入路线截图)
python3 scripts/gen_trip_nav.py pois.json -o output/trip-nav.html
python3 scripts/gen_trip_artifacts.py pois.json -o ./output --src TAG  # 自动读取 route-screenshots.json
python3 scripts/validate.py pois.json  # 部署前质量门

# 部署
cp output/trip-nav.html ~/blog/<slug>-trip-map.html
cd ~/blog && git add . && git commit -m "feat(trip-map): <目的地>" && git push
```

> **注意**:这是示例模板,不是固定流程。LLM 应按 5 步推理灵活调用。

## 关键约定

### 坐标系

- **国内优先 GCJ-02**(高德 / 腾讯 / 百度)
- **OSM 瓦片 + OSRM 用 WGS-84**
- 同份数据存两套坐标(`lng_gcj02` / `lat_gcj02` + `lng_wgs84` / `lat_wgs84`)

### 标签体系

POI 用 7 类 tag:

| tag | 含义 | 颜色 |
|---|---|---|
| `start` | 起点 | `#00C853` 绿 |
| `end` | 终点 | `#D50000` 红 |
| `attract` | 景点 | `#FF6F00` 橙 |
| `hotel` | 酒店 | `#7B1FA2` 紫 |
| `food` | 餐厅 | `#FFB300` 黄 |
| `service` | 服务区 | `#1976D2` 蓝 |
| `stop` | 驿站 / 中转 | `#00838F` 青 |

### 坐标精度分级

| 来源 | 含义 | 透明度 |
|---|---|---|
| `original` | 原文自带精确坐标 | 实色 |
| `known` | 公开资料常用坐标 | 实色 |
| `fallback` | city 中心 + 抖动 / 缺失 | 半透明 0.7 |

**真实出行前**应把 fallback 全部用 web_search 校核到 known 级别。

### 输入形式(自动识别)

| 形式 | 识别 | 抽取精度 |
|---|---|---|
| HTML 导航页 | `<div class="poi">` | ★★★★★ |
| Markdown 文章 | `.md` / `.markdown` | ★★★ |
| CSV 表 | `.csv` | ★★★★ |
| JSON | `.json` + pois 字段 | ★★★★★ |
| 自由文本 | 其他 | ★★(需 LLM 抽 CSV 中转) |

## 产物清单

| 产物 | 文件类型 | 用途 |
|---|---|---|
| 1. 攻略长文 | Jekyll `_posts/*.md` | 详细长文,含预算/时间表/节点速查 |
| 2. 导航点位网页 | 静态 HTML(高德 href) | 手机点任意 POI → 高德 App 导航 |
| 3. OSRM 综合地图 | 静态 HTML(Leaflet) | 浏览器看多日实际驾车路径 + Day 切换 |
| 4. 原始点位 JSON | `.json` | 程序化消费 |
| 5. KML | `.kml` | 导入高德地图 App |

## 文件结构

```
trip-plan/
├── SKILL.md                          # 本文件(LLM 推理操作手册)
├── assets/                           # 模板
│   ├── overview-map-template.html
│   ├── guide-template.md
│   ├── trip.kml.template.xml
│   └── pois.schema.json
├── references/                       # LLM 推理参考
│   ├── input-format.md
│   ├── decision-tree.md
│   ├── layout-styles.md
│   ├── coordinate-systems.md
│   ├── osrm-routing.md
│   ├── github-pages-deploy.md
│   └── artifact-checklist.md
├── destinations/                     # ★ 目的地 playbook(LLM 读这个,按需添加)
│   ├── README.md
│   ├── registry.json
│   └── wutaishan.md
├── scripts/                          # LLM 工具(8 个)
│   ├── parse_input.py                # ★ 输入适配器
│   ├── gcj02_wgs84.py                # 坐标互转
│   ├── osrm_route.py                 # OSRM 路径
│   ├── assign_day_colors.py          # Day 颜色分配
│   ├── validate.py                   # 规则引擎校验
│   ├── gen_trip_nav.py               # ★ 完整 nav.html 生成
│   ├── gen_trip_artifacts.py         # 综合地图 + KML
│   └── screenshot_html.py            # Playwright 截图
├── examples/                         # 示例
│   ├── README.md
│   ├── pois.json
│   ├── trip-guide.md
│   ├── trip-nav.html
│   ├── trip-overview-map.html
│   └── trip.kml
└── docs/
    └── trip-plan-v2-design.md        # v2 设计文档
```

## 脚本依赖

| 脚本 | 依赖 |
|---|---|
| `parse_input.py` | 仅标准库(HTMLParser / csv / json) |
| `gcj02_wgs84.py` | 仅标准库 |
| `assign_day_colors.py` | 仅标准库 |
| `osrm_route.py` | `curl` |
| `validate.py` | 仅标准库 |
| `gen_trip_nav.py` | 仅标准库 |
| `gen_trip_artifacts.py` | 同目录脚本 + `curl` |
| `screenshot_html.py` | `playwright` |

## 隐私 / 脱敏

- 真实住址 / 车牌 / token 不出现在公开产物
- API key 走环境变量,不进 git
- 占位符使用 `{placeholder}` 或 `__PLACEHOLDER__`
- 公开 URL 用占位符(`https://{username}.github.io/`)

## 验证清单(部署前质量门)

LLM 在 Step 5 必须自检:

- [ ] 所有 POI 有有效坐标(`coord_source != fallback` 或已标核实)
- [ ] 所有链接可达(高德 / 官网 / 预约电话)
- [ ] 移动端预览通过(截图自检)
- [ ] LLM 文案无幻觉 / 无重复(关键事实标源)
- [ ] 路线几何完整(D1 / D2 都有 OSRM 路径)
- [ ] 必去点全部出现(对照 destinations/<slug>.md 的"必去点")
- [ ] 时段无冲突(用餐 / 开放时间)
- [ ] 目的地专属提醒完整(从 playbook 抽取 ≥ 3 项)
- [ ] 长文 ≤ 3000 字,POI 描述 ≤ 100 字
- [ ] 攻略长文 + 导航页 + 综合地图 + JSON + KML 全部产出

---

_本文件是 trip-plan skill 的 LLM 推理操作手册。代码变更应严格对齐本文件;任何偏离需更新本文件先。_