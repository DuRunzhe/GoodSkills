---
name: trip-plan
description: 旅行游玩攻略全套产物生成。从一份行程原始数据(POI + Day),产出 5 类标准化产物:游玩攻略长文、导航点位网页、OSRM 实际路径交互式综合地图、原始点位 JSON、KML。触发场景:用户要做一趟新的自驾/多日游,需要把这趟旅行沉淀为可在高德 App + GitHub Pages + 高德地图导入的一整套内容。
---

# trip-plan

把一趟多日旅行的 POI 数据,产出 5 类可在不同场景使用的标准化产物。

## 快速开始

```bash
# 1. 从任意输入提取 POI 数据(自动识别 HTML / MD / CSV / JSON / 自由文本)
#    详见 references/input-format.md
python scripts/parse_input.py <input> -o pois.json
#    例:
#      python scripts/parse_input.py trip.html -o pois.json
#      python scripts/parse_input.py trip.csv -o pois.json
#      python scripts/parse_input.py trip.md -o pois.json
#      python scripts/parse_input.py notes.txt -o pois.json  # 走 LLM 辅助流程
#      python scripts/parse_input.py pois.json --validate   # 已有 JSON 时校验+透传

# 2. 补 WGS-84 坐标(GCJ-02 → WGS-84,供 OSM 瓦片 / OSRM 用)
python scripts/gcj02_wgs84.py pois.json pois.json --mode to_wgs84

# 3. 校验 schema / 必含字段 / 坐标质量
python scripts/validate.py pois.json --strict

# 4. 一键生成 5 类产物
python scripts/gen_trip_artifacts.py pois.json -o ./output/ --src momotrip

# 5. 截图(用于分享,需 playwright)
python scripts/screenshot_html.py ./output/trip-overview-map.html --batch -o ./screenshots/

# 6. 部署到 GitHub Pages
#    详见 references/github-pages-deploy.md
```

## 触发条件

满足以下任一即触发本 skill:

- 用户说"做一份 XX 行程 / 旅行攻略 / 自驾路线"
- 用户提供了一组 POI + Day 划分,问"怎么整理成网页/地图/KML"
- 用户要做"导航点位页 / 综合地图 / OSRM 路线 / 高德导入"
- 用户要把一份 markdown 长文配套成可导航的网页
- **用户给了任何形式的旅行内容**(文章 / HTML / Markdown / CSV / JSON / 自由文本 / 对话片段 / Notion 导出),想沉淀成完整产物

**不确定要不要用?看** `references/decision-tree.md`

---

## 输入端(任意形式 → POI 数据)

**核心约束**:输入可以是任何形式,但**输出必须归一到 `pois.json`**(标准 schema),后续流程才接得上。

```
[任意输入]  ──parse_input.py──►  [pois.json]  ──validate.py──►  [5 类产物]
                                    │
                                    ├─ gcj02_wgs84.py 补 WGS-84
                                    └─ 可选:人工微调 fallback 坐标
```

**支持的输入形式**(自动识别,详见 `references/input-format.md`):

| 形式 | 识别 | 适用场景 | 坐标质量 |
|---|---|---|---|
| HTML 导航页 | 文件含 `<div class="poi">` + 高德 href | 已有现成 trip-plan 产物想改 | original |
| Markdown 文章 | `.md` / `.markdown` 扩展名 | 博客攻略 _posts/*.md | known / fallback |
| CSV 表 | `.csv` 扩展名 + 表头匹配 | LLM 辅助抽取后中转 | 视上游 |
| JSON | `.json` 扩展名 + schema 校验 | 已是标准格式 | 视上游 |
| 自由文本 | 其他 | 一段文字描述 / 聊天 / 笔记 | fallback |

**非结构化输入**(长文 / 自由文本 / 多轮对话)的处理路径:

1. 先用 LLM 把文本抽取成结构化 CSV(模板见 `references/input-format.md` §6)
2. CSV 喂给 `parse_input.py --form csv` 输出 `pois.json`
3. 走标准流程

**输入端不可处理的**:图片 / 语音 / PDF(请先 OCR 或手工转文本)

## 产物清单

| 产物 | 文件类型 | 用途 | 模板 |
|---|---|---|---|
| 1. 游玩攻略长文 | Jekyll `_posts/*.md` | 详细长文,含预算/时间表/节点速查,放在博客 | `assets/guide-template.md` |
| 2. 导航点位网页 | 静态 HTML(高德直接 href) | 手机打开即可点任意 POI → 唤起高德 App 导航 | `assets/nav-template.html` |
| 3. OSRM 综合地图 | 静态 HTML(Leaflet) | 浏览器打开,看 5 天实际驾车路径 + Day 切换 | `assets/overview-map-template.html` |
| 4. 原始点位 JSON | `.json` | 程序化消费(脚本/前端) | `assets/pois.schema.json` |
| 5. KML | `.kml` | 导入高德地图 App,看所有点 + 路径 | `assets/trip.kml.template.xml` |

**附加流程**:把这 5 类产物上传到 GitHub Pages 公开访问,见 `references/github-pages-deploy.md`。

## 文件结构

```
trip-plan/
├── SKILL.md                          # 本文件
├── assets/                           # 5 个模板
│   ├── guide-template.md             # 游玩攻略长文
│   ├── nav-template.html              # 导航点位网页
│   ├── overview-map-template.html     # OSRM 综合地图
│   ├── pois.schema.json               # JSON Schema
│   └── trip.kml.template.xml          # KML
├── references/                       # 7 份参考
│   ├── artifact-checklist.md          # 每种产物的必含/可选要素
│   ├── layout-styles.md               # 布局/编排/样式规范
│   ├── coordinate-systems.md          # GCJ-02 / WGS-84
│   ├── osrm-routing.md                # OSRM 路径规划
│   ├── github-pages-deploy.md         # GitHub Pages 部署
│   ├── input-format.md                # 输入端:数据从哪来,什么格式
│   └── decision-tree.md               # 决策树:什么时候用哪种产物
├── scripts/                          # 7 个可执行脚本
│   ├── parse_input.py                 # ★ 输入适配器:任意形式(HTML/MD/CSV/JSON/文本) → pois.json
│   ├── gcj02_wgs84.py                 # 坐标互转(GCJ-02 ↔ WGS-84)
│   ├── osrm_route.py                  # OSRM 公共 API 封装
│   ├── assign_day_colors.py           # Day 颜色自动分配
│   ├── validate.py                    # 用 schema 校验产物
│   ├── gen_trip_artifacts.py          # 端到端产物生成器(吃 pois.json)
│   └── screenshot_html.py             # Playwright HTML 截图
└── examples/                         # 脱敏示例
    ├── README.md
    ├── pois.json
    ├── trip-guide.md
    ├── trip-nav.html
    ├── trip-overview-map.html          # 已预填数据,可直接打开
    └── trip.kml
```

## 脚本依赖

| 脚本 | 依赖 |
|---|---|
| `parse_input.py` | HTML 解析:`beautifulsoup4`(可选);其他格式:仅标准库 |
| `gcj02_wgs84.py` | 仅标准库 |
| `assign_day_colors.py` | 仅标准库 |
| `osrm_route.py` | `curl` |
| `validate.py` | 仅标准库 |
| `gen_trip_artifacts.py` | 同目录其他脚本 + `curl` |
| `screenshot_html.py` | `playwright` (`pip install playwright && playwright install chromium`) |

## 关键约定

### 坐标系统
- **国内场景优先 GCJ-02**(高德、腾讯、百度都吃这套)
- **OSM 瓦片 + OSRM 路径规划需要 WGS-84**
- 同一份数据要存两套坐标(`lng_gcj02` / `lat_gcj02` + `lng_wgs84` / `lat_wgs84`)
- 转换公式见 `references/coordinate-systems.md`,工具见 `scripts/gcj02_wgs84.py`

### 坐标精度分级
POI 的坐标获取质量分 3 档,在数据里用 `coord_source` 标记:

| 来源 | 含义 | 典型场景 |
|---|---|---|
| `original` | 原始博客自带的精确坐标 | 起点 / 已确认的景点 |
| `known` | 公开资料里的常见坐标 | 知名景点(公主湖/将军泡子/达达线起点等) |
| `fallback` | city 中心 + 抖动 | 当地小店/餐厅/服务区等无精确坐标的地方 |

**真实出行前**应把 fallback 全部用 web_search 校核到 known 级别。

### 标签体系
POI 用 7 类 tag:

| tag | 含义 | 建议颜色 |
|---|---|---|
| `start` | 起点 | `#00C853` 绿 |
| `end` | 终点 | `#D50000` 红 |
| `attract` | 景点 | `#FF6F00` 橙 |
| `hotel` | 酒店 | `#7B1FA2` 紫 |
| `food` | 餐厅 | `#FFB300` 黄 |
| `service` | 服务区 | `#1976D2` 蓝 |
| `stop` | 驿站 / 中转点 | `#00838F` 青 |

详见 `references/layout-styles.md`。

### 输入端处理原则

`parse_input.py` 的处理优先级:

1. **结构化优先**:HTML / JSON / CSV 能精确抽取就用精确结果
2. **启发式 fallback**:Markdown / 半结构化文本用正则 + 关键词匹配
3. **失败留痕**:解析不出来的 POI 输出 warning 到 stderr,但不阻断整体流程;坐标缺失的标 `coord_source=fallback`
4. **LLM 辅助中转**:非结构化文本不在脚本内做 LLM 调用(成本 + 不可重复),而是通过 CSV 中转,模板见 `references/input-format.md` §6

**重要**:从 HTML / Markdown 抽取的 POI 必须输出可读清单到 stdout,用户可肉眼复核后用 `--filter` 或人工编辑 `pois.json` 微调。

### 标签扩展(2026-07-23 起)
实测使用中发现部分场景的 tag 超出 7 类基础集,在现有 nav-template 颜色体系中已实装:

| tag | 含义 | 颜色 |
|---|---|---|
| `peak` | 山顶 / 制高点 | `#f57f17` 黄 |
| `optional` | 可选 / 收尾 | `#0891b2` 青 |

新 tag 加进 `assets/pois.schema.json` 时要同步更新 nav-template 的 `.tag.<name>` CSS 块。

## 隐私 / 脱敏

- 不在模板或示例里写**真实坐标**、**真实住址**、**真实车牌**
- 不放 **API key / token / 密码**
- 占位符使用 `{placeholder_name}` 或 `__PLACEHOLDER__`
- 公开 URL 用占位符,例如 `https://{username}.github.io/`
- GitHub 仓库地址也用占位符,例如 `git@github.com:{username}/{repo}.git`

## 验证清单

每次生成完,跑一遍以下检查:

- [ ] `python scripts/validate.py pois.json` 全部错误为空
- [ ] 5 类产物全部生成,无遗漏
- [ ] JSON 通过 `pois.schema.json` 校验
- [ ] KML 在高德地图 App 能正常导入
- [ ] 导航点位页手机打开,点 POI 能唤起高德 App
- [ ] OSRM 综合地图浏览器打开,5 段路径都有
- [ ] 长文里所有提到的时间/距离/费用和导航页一致
- [ ] 公开 URL 不带 token / 私有坐标
- [ ] 提交信息符合 Conventional Commits(可选)
