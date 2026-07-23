# trip-plan v2 设计文档

> 把 trip-plan 从「数据格式转换器」升级为「生产级混合智能工作流」
>
> 状态: Draft v0.1 · 2026-07-23 · 作者: Claude (via 比特匠协作)

---

## 1. 背景与目标

### 1.1 当前痛点

v1 (现状) 的核心局限:**数据完整 ≠ 产品可用**。脚本能正确生成 HTML,但产物有以下问题:

| 维度 | v1 表现 | 生产级要求 |
|---|---|---|
| 分组粒度 | 按 tag 自动粗分(出发/景点/餐厅) | 按行程语义精分(出发/服务区/购票/寺院群/素斋/住宿) |
| 路线顺序 | 按 POI idx 自然顺序 | 严格按行程预期(最短/环线/单程/区域聚焦) |
| 专属提醒 | 通用「坐标质量提示」 | 目的地专属(五台山限行/拉萨高反/318 路况) |
| 内容创作 | 仅拼接已有字段 | 有「为什么去 / 看什么 / 注意」的引导文案 |
| 实时数据 | 无 | 天气/限行/路况/门票余量实时更新 |
| 校验 | schema + 坐标范围 | 开放时间冲突/路线可达性/门票可订/季节性 |

### 1.2 目标

**生产级 = 工业可复用 + 个人出行真用**。具体:

1. **可复用**:同一套流程支持任意目的地(国内 → 国外延伸)
2. **真用**:产物能让主人出门不踩坑,不返工
3. **可演进**:知识库 + 评分模型能持续学习
4. **可量化**:每次产出有质量分(后续可对比)

### 1.3 非目标

- ❌ 不做 OTA/票务交易(只在 meta 层引用,不接订单)
- ❌ 不做实时聊天机器人(只在脚本/CLI 里跑)
- ❌ 不做移动 App(产物是 GitHub Pages 静态站)

### 1.4 设计原则(skill vs program)

**trip-plan 是一个 skill,不是一个独立的程序或工作流系统**。这是最重要的架构约束。

| 是什么 | 不是什么 |
|---|---|
| ✅ 一份 SKILL.md + 配套 scripts + 知识库 | ❌ 一个有自己状态机的独立程序 |
| ✅ LLM (我) 在被调用时阅读 SKILL.md 并执行规划 | ❌ 一个 orchestrator 程序调度子模块 |
| ✅ Scripts 是 LLM 可调用的工具 | ❌ 流水线 stage 互相传递 JSON |
| ✅ Destinations/<slug>.md 是 LLM 可读的知识 | ❌ 一个独立的微服务 |
| ✅ 5 个 "phase" 是 LLM 推理步骤的逻辑顺序 | ❌ 程序模块的串行执行 |

**本 skill 的"智能"来自**:
1. SKILL.md 的详细度和清晰度(我读后知道做什么)
2. Destinations/<slug>.md 知识完整度(我读后知道目的地的本地知识)
3. LLM 的推理和创作能力(本来就内置的)
4. Scripts 的能力(必要的工具我做不好的事交给脚本)

**本 skill 不需要**:
- 独立的状态管理(LLM 会话就是状态)
- 复杂的 IPC 机制(LLM 调脚本就是 IPC)
- 持久化数据库(playbooks 就是持久化)
- 调度系统(LLM 调用就是调度)

---

## 2. 现状评估(v1 架构)

```
[任意输入] → parse_input.py → pois.json → validate.py → gen_trip_*.py → 5 类产物
                                         ↑
                              gcj02_wgs84.py (坐标互转)
```

**缺失的三层**:

| 层 | 状态 | 影响 |
|---|---|---|
| 🧠 LLM 编排层 | ❌ 无 | 不知道用户想要什么、不知道目的地知识 |
| 🔌 数据源层 | ❌ 无 | 没有实时信息、没有本地化知识 |
| ⚙️ 规则引擎层 | ⚠️ 零散 | 只校验 schema,不校验行程合理性 |

---

## 3. Skill 执行模型(不是「流水线」)

### 3.1 触发与生命周期

```
┌─────────────────────────────────────────────────────────┐
│  触发:用户说「用 trip-plan 规划 XX」或上传任意旅行内容    │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  LLM (我) 被唤起,作为 trip-plan 的 runtime              │
│                                                         │
│  会话开始时,LLM 按顺序读:                               │
│    1. SKILL.md     ← 知道做什么、怎么做、产出什么        │
│    2. destinations/<slug>.md  ← 读相关目的地 playbook     │
│    3. references/*.md        ← 按需读参考文档            │
│                                                         │
│  然后 LLM 依次进行 5 个推理步骤(可自由跳转):            │
│    Step 1. 意图解析(必要时反问用户)                     │
│    Step 2. 知识检索(LLM 调 web_search / wechat_spander) │
│    Step 3. 行程规划(LLM 推理 + 必要时调 optimize_route.py)│
│    Step 4. 内容创作(LLM 自己写攻略 + 提醒)              │
│    Step 5. 产物渲染(LLM 调 gen_trip_*.py)               │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  产出:5 件套(nav.html / overview-map.html / kml / guide / JSON)│
└─────────────────────────────────────────────────────────┘
```

**关键洞察**:
- 这 5 步是**逻辑顺序**,不是**程序顺序**。LLM 在同一会话内可随时跳回任一步骤(比如发现 POI 信息不全就回到 Step 2 检索)
- LLM 不需要先把 Step 1 输出存为 JSON 才能进 Step 2 — LLM 内部推理就是「持久化」
- Scripts 只是 LLM 可调用的工具,不是流水线上的 stage

### 3.2 LLM 与脚本的协作模式

```
LLM 推理 ──────────────────────► 输出产物
    │
    ├── 调 web_search(keyword) ────► 返回搜索摘要
    ├── 调 wechat_spander(url) ────► 返回公众号正文
    ├── 调 parse_input.py(input) ──► 返回 pois.json
    ├── 调 optimize_route.py(pois) ► 返回 optimized.json
    ├── 调 gcj02_wgs84.py(json) ──► 返回坐标转换
    ├── 调 gen_trip_nav.py(data) ──► 返回 nav.html
    └── 调 gen_trip_map.py(data) ──► 返回 map.html
```

**LLM 的工具箱 = 现有 skill 可调用的所有脚本 + 平台能力**(web_search / image / music_generate 等)

---

## 4. 5 个推理步骤详细设计

### Step 1 · LLM 意图解析

**目标**:把用户的任意输入转成 LLM 内部推理可用的「行程需求」理解(不强制落到 JSON 文件)。

**LLM 在这一步做什么**:
1. 读用户输入(自然语言 / HTML / MD / 任意形式)
2. 拆解要素:目的地 / 天数 / 出行方式 / 预算 / 同行人 / 偏好 / 必去点 / 避雷点
3. 检查要素是否齐备,**缺什么就反问用户**(LLM 直接追问,不需要单独脚本)
4. 输出:LLM 内部已结构化,不强制产出 trip_requirement.json

**SKILL.md 在这一步指引 LLM**:
- 必填字段清单(目的地/天数/出行方式)
- 追问模板(用什么话术问)
- 模糊需求的合理默认(没指定天数 → 默认 2 天 / 自驾)

**LLM 可调用工具**:
- 直接读已有攻略(HTML / MD),自己抽取要素
- 调 `parse_input.py` 反推结构化数据(可选,简单输入可跳过)

---

### Step 2 · LLM 知识检索 + 数据增强

**目标**:给每个 POI 补充「开放时间/门票/评分/专属提醒」字段,让产物有信息密度。

**输入**:`trip_requirement.json` + Phase 1 输出

**输出**:`pois.enriched.json`(在 pois.json 基础上加字段)

```json
{
  "pois": [
    {
      "day": "D1", "idx": 4, "name": "五爷庙", "tag": "attract",
      "lng_gcj02": 113.596592, "lat_gcj02": 39.007809,
      "coord_source": "original",
      // === 新增字段 ===
      "open_hours": {"weekday": "08:00-18:00", "weekend": "07:30-19:00"},
      "ticket": {"price": 0, "currency": "CNY", "booking_required": false},
      "rating": {"score": 4.6, "source": "高德", "review_count": 8234},
      "visit_duration_min": 30,
      "best_time": "上午(光线好 + 香火旺)",
      "tips": ["求财最灵", "工作日上午人少", "殿内禁止拍照"],
      "source_refs": [
        {"url": "https://www.example.com/wutai-wuyemiao", "type": "公众号"}
      ]
    }
  ],
  "destination_meta": {
    "name": "五台山",
    "current_weather": {"temp": "18°C", "condition": "晴", "wind": "3级"},
    "weather_forecast": [...],
    "current_alerts": [
      {"type": "限行", "rule": "周末单双号", "check_url": "..."},
      {"type": "预约", "rule": "佛光寺需电话预约", "phone": "0350-6554009"}
    ],
    "season_info": {
      "season": "夏季",
      "altitude_warning": "海拔 1500-2500m,凌晨 10°C,需带冲锋衣",
      "best_months": ["6-9月"]
    }
  }
}
```

**数据源优先级**:

| 优先级 | 数据源 | 用途 | 成本 |
|---|---|---|---|
| P0 | 高德 Web API | POI / 路径 / 限行 | API key |
| P1 | OSRM 公共 API | 备用路径 | 免费 |
| P1 | wechat_spander(公众号) | 深度攻略 / 本地知识 | 免费 |
| P2 | web_search(小红书/抖音) | 真实评价 / 最新打卡 | token |
| P3 | wttr.in / 高德天气 API | 天气 | 免费/低成本 |
| P4 | 政府公告 / 官网 | 限行 / 预约规则 | 免费 |

**实现策略**:
- 新增 `scripts/enrich_pois.py`,接收 pois.json + 目的地 → 输出 enriched.json
- 按 P0-P4 优先级依次填充,已有数据不覆盖
- 缓存策略:同一目的地 24h 内不重复检索
- 失败处理:某数据源失败时降级到下一优先级

**失败模式**:
- API 限流 → 等待 Retry-After 重试,3 次后降级
- 数据缺失 → 标 `null` + 警告,不阻塞
- 检索冲突(多源不一致)→ 取最新 + 加备注

---

### Step 3 · LLM 行程规划

**目标**:把 POI 列表重排成「实际可走、最优体验」的路线。

**LLM 在这一步做什么**:
1. 根据 Step 2 的检索结果 + Step 1 的需求,排出每 Day 的 POI 顺序
2. 推理路径合理性(不要走回头路)
3. 推理时段合理性(开放时间 / 用餐时间)
4. 推理约束满足度(必去点 / 限行 / 季节性)
5. 必要时调 `optimize_route.py` 做精确的 TSP / 路径几何计算

**LLM 可调用工具**:
- 读 `destinations/<slug>.md` playbook(获取该目的地的分组规则 + 评分加权)
- 调 `optimize_route.py pois.json` 算精确路径(可选,简单行程 LLM 直接推)
- 调 `gcj02_wgs84.py` 做坐标系互转
- 调 `validate.py` 做规则引擎校验(冲突检测 / 必备项检查)

**LLM 的推理启发式**(写在 SKILL.md 里):

```
1. 先排「必须按时段」的 POI(寺院群/夜景/日出)
2. 再排「强相关」的 POI(同一区域 / 顺路)
3. 再排「可灵活调整」的 POI(休息 / 餐饮)
4. 最后做时段填充 + 路径最短化
```

**LLM 的规则引擎**(也写在 SKILL.md 里,让 LLM 自检):

- ✅ 每个 Day 至少有 1 个景点 + 1 个餐厅
- ✅ 餐厅时段在 11:30-13:30 或 17:30-19:30
- ✅ 必去点(must_haves)全部出现在对应 Day
- ✅ 连续驾驶不超过 3h(每 2h 强制休整 15min)
- ✅ 当日总时长不超过 14h(早 7 点出发 ≤ 晚 21 点)
- ✅ 当日返程距酒店 < 50km 或返回出发地

**LLM 输出**:LLM 内部已结构化(每 Day schedule + 路径),可选择性产出 optimized.json(便于 review)

---

### Step 4 · LLM 内容创作

**目标**:在结构化数据之上,生成「有人味」的文案:攻略长文、POI 描述、专属提醒。

**输入**:`optimized.json` + `pois.enriched.json` + 检索到的本地知识

**输出**:`trip_content.md` + 各产物的文案片段

**LLM 在这一步做什么**:
1. 写攻略长文(1500-3000 字,基于已规划的行程 + 检索到的本地知识)
2. 为每个 POI 写「为什么去 / 看什么 / 注意」描述
3. 写底部专属提醒(从 playbook + 检索中提炼)
4. 写 Day 导语 + 路线文案

**LLM 的 Prompt 框架**(写在 SKILL.md 里):

```
# 角色
你是经验丰富的本地向导,擅长 [X 类型] 行程设计。

# 输入(LLM 直接从内部推理取)
- 已规划的行程结构(Step 3 输出)
- 已检索的本地知识(Step 2 输出)
- 用户偏好(Step 1 输出)
- 目的地 playbook 摘要(destinations/<slug>.md)

# 任务
1. 写一段 200-400 字的「为什么去」
2. 为每个 POI 写 50-80 字描述
3. 写底部专属提醒(基于目的地的限行/预约/季节性规则)

# 输出形式
直接写产物内容,后续由 gen_trip_*.py 填入模板
```

**LLM 自检清单**(写时同时检查):
- ✅ 不编造:无法核实的信息必须标 `[待核实]`
- ✅ 不重复:每段内容独立,避免跨段抄写
- ✅ 不超长:长文 1500-3000 字,POI 描述 ≤ 100 字
- ✅ 多源交叉:关键事实(限行时间/预约电话)至少 2 个来源

**LLM 输出**:直接在产物里(Markdown / HTML 文案片段)

---

### Step 5 · LLM 产物渲染 + 部署

**目标**:把结构化数据 + 文案渲染成最终产物,并保证质量。

**输入**:Phase 1-4 全部输出

**输出**:5 类产物 + 部署链接

**模板分层**:

```
templates/
├── base/                    # 通用基础
│   ├── nav.html             # 导航点位页骨架
│   ├── overview-map.html    # 综合地图骨架
│   └── kml.xml
├── styles/                  # 视觉风格
│   ├── minimal.md           # 朴素风(默认)
│   ├── elegant.md           # 精致风
│   └── epic.md              # 史诗风(自驾长途)
└── destinations/            # 目的地专属
    ├── wutaishan.md         # 五台山专属分组逻辑 + 提醒
    ├── lhasa.md             # 拉萨专属
    └── sichuan-tibet.md     # 318 川藏专属
```

**模板 vs 规则 vs LLM 分工**:

| 内容 | 谁负责 | 实现 |
|---|---|---|
| HTML 结构 | 模板 | nav.html 骨架 |
| CSS 样式 | 模板 | styles/minimal.css |
| POI 分组标题 | 模板 + destinations | destinations/wutaishan.md 提供分组规则 |
| POI 排序 | Phase 3 算法 | optimized.json |
| POI 文案 | Phase 4 LLM | trip_content.md |
| 底部专属提醒 | Phase 4 LLM + 模板 | trip_content.md + destinations/*.md |
| 时段编排 | 规则引擎 | scripts/rule_engine.py |

**质量门(部署前必过,完整 10 项)**:

- [ ] 所有 POI 有有效坐标(`coord_source != fallback` 或已标注核实)
- [ ] 所有链接可达(高德 / 官网 / 预约电话)
- [ ] 移动端预览通过(截图自检)
- [ ] LLM 文案无幻觉 / 无重复(关键事实标源)
- [ ] 路线几何完整(D1 / D2 都有 OSRM 路径)
- [ ] 必去点全部出现(对照 destinations/<slug>.md 的"必去点")
- [ ] 时段无冲突(用餐 / 开放时间)
- [ ] 目的地专属提醒完整(从 playbook 抽取 ≥ 3 项)
- [ ] 长文 ≤ 3000 字,POI 描述 ≤ 100 字
- [ ] 攻略长文 + 导航页 + 综合地图 + JSON + KML 全部产出

**LLM 在这一步做什么**:
1. 把前面所有信息(POI 数据 + 文案)组织成结构化输入
2. 调 `gen_trip_nav.py`(给数据,接收 HTML)
3. 调 `gen_trip_map.py`(给数据 + 路径几何,接收地图 HTML)
4. 调 `gen_trip_kml.py`(给数据,接收 KML)
5. 调 `validate.py` 校验产物质量
6. 写攻略长文 `_posts/YYYY-MM-DD-<slug>.md`
7. 截图 + 部署(用 `openclaw message send` 或 `git push`)

**LLM 不做的事**:
- ❌ 自己写 HTML(让 gen_trip_*.py 写,LLM 只提供数据)
- ❌ 自己跑服务器(用 GitHub Pages 静态部署)

## 4.6 数据约定(LLM 在 Step 1-5 必须遵守)

### 4.6.1 标签体系

POI 用 7 类基础 tag + 2 类扩展 tag:

| tag | 含义 | 颜色 |
|---|---|---|
| `start` | 起点 | `#00C853` 绿 |
| `end` | 终点 | `#D50000` 红 |
| `attract` | 景点 | `#FF6F00` 橙 |
| `hotel` | 酒店 | `#7B1FA2` 紫 |
| `food` | 餐厅 | `#FFB300` 黄 |
| `service` | 服务区 | `#1976D2` 蓝 |
| `stop` | 驿站 / 中转 | `#00838F` 青 |
| `peak` | 山顶 / 制高点(扩展) | `#f57f17` |
| `optional` | 可选 / 收尾(扩展) | `#0891b2` |

### 4.6.2 坐标精度分级

| 来源 | 含义 | 透明度 |
|---|---|---|
| `original` | 原文自带精确坐标 | 实色 |
| `known` | 公开资料常用坐标 | 实色 |
| `fallback` | city 中心 + 抖动 / 缺失 | 半透明 0.7 |

**真实出行前**应把 fallback 全部用 web_search 校核到 known 级别。

### 4.6.3 输入形式(自动识别)

| 形式 | 识别 | 抽取精度 |
|---|---|---|
| HTML 导航页 | `<div class="poi">` | ★★★★★ |
| Markdown 文章 | `.md` / `.markdown` | ★★★ |
| CSV 表 | `.csv` | ★★★★ |
| JSON | `.json` + pois 字段 | ★★★★★ |
| 自由文本 | 其他 | ★★(需 LLM 抽 CSV 中转) |

---

## 5. 目的地知识库(playbook)

**目标**:把本地化知识(五台山限行/拉萨高反)沉淀成可复用资产。

**结构**:`destinations/<slug>.md`(以实际为准,当前只有 .md,无 .json)

```yaml
# destinations/wutaishan.md
slug: wutaishan
name: 五台山
region: 山西省忻州市
type: 古建筑 + 佛教文化
season: 夏季最佳(6-9月)

分组规则:
  - { title: "🏁 出发", pattern: "tag=start" }
  - { title: "⛽ 高速服务区（自选）", pattern: "tag=service AND driving_path" }
  - { title: "🎫 游客中心（购票）", pattern: "name ~ 游客中心 OR 售票" }
  - { title: "🏛 核心寺院群（时段）", pattern: "tag=attract AND time_slot=核心时段" }
  - { title: "🍜 素斋（推荐）", pattern: "tag=food AND type=素斋" }
  - { title: "🏨 住宿 · 台内民宿（21:00 入住）", pattern: "tag=hotel AND arrive_time >= 21:00" }

专属提醒:
  - 限行:周末单双号,出发前 1 天查「五台山自驾最新政策」
  - 门票:自驾必买 ¥135,台内查到无票罚款 200+ 补票
  - 预约:佛光寺 0350-6554009,出发前 1 周必打
  - 季节:海拔 1500-2500m,凌晨 10°C,需带冲锋衣
  - 返程:13:30 必须返,15:00 后京昆易堵

必去点(权重 1.0):
  - 佛光寺
  - 南禅寺
  - 显通寺
  - 塔院寺

加分项(权重 0.5):
  - 南山寺(夜景)
  - 龙泉寺(汉白玉石雕)
```

**注册机制**:`destinations/registry.json` 索引所有目的地:

```json
{
  "wutaishan": {"playbook": "destinations/wutaishan.md", "maturity": "stable"},
  "lhasa": {"playbook": "destinations/lhasa.md", "maturity": "draft"},
  "sichuan-tibet": {"playbook": "destinations/sichuan-tibet.md", "maturity": "draft"}
}
```

**成熟度等级**:
- `stable`:playbook 经过 ≥3 次实跑验证
- `draft`:playbook 起草,待实跑
- `experimental`:playbook 由 LLM 自动生成,人工未审

---

## 6. 实施路线图(skill 内部能力升级)

### Phase A(已完成)· 写厚 SKILL.md + 一个示例 playbook

**目标**:让 LLM 读 SKILL.md + playbook 后就能独立产出生产级产物,不依赖新增脚本。

| 任务 | 工作量 | 产出 |
|---|---|---|
| A.1 重写 SKILL.md:加完整的「5 步推理指引」+ 「工具调用清单」+ 「规则引擎自检清单」 | 2d | SKILL.md v2(估计 300-400 行) |
| A.2 写 destinations/wutaishan.md(playbook v1) | 0.5d | 五台山 playbook |

**验收**:SKILL.md v2 + 五台山 playbook 完成。LLM 读这两份文档后,能独立产出符合 §4.6 数据约定 + §4.5 质量门(完整 10 项)的生产级产物。

### Phase B(本月)· 加少量工具脚本(LLM 做不好的事)

| 任务 | 工作量 | 为什么是脚本(不是 LLM) |
|---|---|---|
| B.1 `optimize_route.py`(可选)— 当 POI > 15 时调 | 1d | LLM 算 TSP 不可靠,数学算法更准 |
| B.2 `enrich_pois.py`(可选)— 自动调 web_search + wechat_spander | 1d | LLM 检索 token 成本高,脚本可缓存 |
| B.3 扩 `gen_trip_*.py` 支持精细分组 + 多套视觉风格 | 1d | 模板渲染是机械活 |

**不新增的内容**:
- ❌ 独立的 intent parser 脚本(LLM 自己解析)
- ❌ 独立的 content generator 脚本(LLM 自己写)
- ❌ 独立的 orchestrator(LLM 会话就是)

### Phase C(季度)· 工业化打磨

| 任务 | 工作量 | 产出 |
|---|---|---|
| C.1 多目的地联动(川藏 + 拉萨 + 纳木错) | 3d | 跨区域行程 playbook |
| C.2 视觉模板库(朴素/精致/史诗) | 2d | assets/styles/* |
| C.3 质量门脚本(发布前自动跑) | 1d | quality_gate.py |
| C.4 知识库 v2:用户偏好学习 | 3d | 偏好模型(playbook 增强) |
| C.5 多语言支持(英 / 日 / 韩) | 2d | i18n templates |

---

## 7. 开放问题(待讨论)

### 7.1 ~~LLM 编排层放在哪?~~ ✅ 已解答

**答案**:LLM 编排层就是 LLM(我)在被 trip-plan skill 唤起时的会话本身。
- 这是 skill 模型的核心 —— LLM 就是 runtime
- 不需要单独的 orchestrator 进程 / sub-agent
- 不是开放问题,是设计前提

### 7.2 行程优化算法深度

简单 TSP vs Google OR-Tools,投入产出比如何?

- 五台山这类 2-5 天 15-20 POI,LLM 直接推理够用
- 川藏 10+ 天 50+ POI,需要脚本辅助(Phase B.1)
- **建议**:先靠 LLM 推理,验证不够用再写 optimize_route.py

### 7.3 数据源成本

| 数据源 | 成本 | 必要性 |
|---|---|---|
| 高德 API | 免费 6000 次/日 | P0 必须 |
| 小红书 RSS | 免费但不稳定 | P1 重要 |
| 公众号抓取 | 免费但 ToS 风险 | P2 谨慎 |
| LLM 调用 | token 成本 | P0 必须 |

**建议**:LLM 走 web_search(便宜)、脚本做缓存复用、API 调用按月限额

### 7.4 私密信息保护

按 MEMORY.md「隐私 / 脱敏」规范:
- 真实住址/车牌/token 不出现在公开产物
- API key 走环境变量,不进 git
- 检索日志脱敏后存储

### 7.5 工业化 vs 个人用的边界

| 维度 | 个人用 | 工业化 |
|---|---|---|
| 目的地数量 | 1-3 | 不限 |
| 行程长度 | 2-7 天 | 任意 |
| 用户数 | 1 | 多 |
| 部署 | GitHub Pages | 多渠道 |
| 性能 | 单次 < 1min | 批量 < 10min |
| 质量门 | 跳过 | 全跑 |

**建议**:先做到「个人用极致」,再扩展工业化。路线图已按这个分层。

---

## 8. 成功指标

3 个月后回看,看是否达到目标:

| 指标 | 目标 |
|---|---|
| 产物质量分(vs v1) | +50% |
| 必去点覆盖率 | 100% |
| 时段冲突率 | 0% |
| 专属提醒完整度 | ≥ 5 项/目的地 |
| 主人实际出行使用率 | ≥ 80%(「产出了真用」) |
| Playbook 数量 | 按需添加(不属 skill 必做流程,属路线图快照) |
| 行程算法可处理 POI 数 | ≥ 50 |

---

## 附录 A · 词汇表

| 术语 | 含义 |
|---|---|
| POI | Point of Interest,行程点 |
| Playbook | 目的地专属规则 + 知识库 |
| TSP | 旅行商问题(路径优化经典问题) |
| WGS-84 | GPS 坐标系(国际标准) |
| GCJ-02 | 火星坐标(中国加密,高德用) |
| Enriched POI | 含评分/开放时间/提醒的扩展 POI |
| Optimized Itinerary | 算法重排后的行程 |

## 附录 B · 与现有 skill 的关系

| 现有 | v2 调整 |
|---|---|
| `SKILL.md` | **大幅重写**,加入 5 步推理指引 + 工具调用清单 + 规则引擎自检(核心) |
| `references/input-format.md` | 保留,作为 LLM 推理时的参考 |
| `references/decision-tree.md` | 保留,作为 LLM 推理时的参考 |
| `scripts/parse_input.py` | **保留**,LLM 在 Step 1 / Step 2 可选用 |
| `scripts/gcj02_wgs84.py` | 保留,坐标互转 |
| `scripts/validate.py` | **核心**,作为规则引擎,LLM 在 Step 3 / Step 5 都调 |
| `scripts/gen_trip_*.py` | 保留 + 扩(gen_trip_nav.py / gen_trip_map.py / gen_trip_kml.py) |
| `scripts/assign_day_colors.py` | 保留 |
| `scripts/osrm_route.py` | 保留,作为 LLM 在 Step 3 调用的工具 |
| `scripts/optimize_route.py` | **新增(可选)**,只有 POI > 15 时 LLM 才调 |
| `destinations/<slug>.md` | **新增**(核心),playbook 是 LLM 推理的依据 |
| `assets/styles/*.css` | **新增**,多套视觉风格供 LLM 选用 |

**关键变化**:
- ✅ `destinations/` 是**新增的核心数据**,不是辅助
- ✅ `optimize_route.py` 是**可选工具**,不是必需
- ✅ `extract_intent.py` / `enrich_pois.py` / `generate_content.py` **都不新增**(LLM 内置)
- ✅ `SKILL.md` 升级成 300+ 行的「推理操作手册」

## 附录 C · 与其他 skill 的协作

- **wechat_spander**:Phase 2 公众号抓取(已存在)
- **web_search / web_fetch**:Phase 1-2 通用检索
- **memory_search**:Playbook 命中率 / 历史行程参考
- **session_summary**:行程结束后归档
- **update_goal**:多日行程的进度跟踪

---

_本文档是 trip-plan v2 升级的「设计契约」。代码实现应严格对齐本文档,任何偏离需更新本文档先。_