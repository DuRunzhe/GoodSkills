---
name: trip-plan
description: 旅行游玩攻略全套产物生成。从一份行程原始数据(POI + Day),产出 5 类标准化产物:游玩攻略长文、导航点位网页、OSRM 实际路径交互式综合地图、原始点位 JSON、KML。触发场景:用户要做一趟新的自驾/多日游,需要把这趟旅行沉淀为可在高德 App + GitHub Pages + 高德地图导入的一整套内容。
---

# trip-plan

把一趟多日旅行的 POI 数据,产出 5 类可在不同场景使用的标准化产物。

## 触发条件

满足以下任一即触发本 skill:

- 用户说"做一份 XX 行程 / 旅行攻略 / 自驾路线"
- 用户提供了一组 POI + Day 划分,问"怎么整理成网页/地图/KML"
- 用户要做"导航点位页 / 综合地图 / OSRM 路线 / 高德导入"
- 用户要把一份 markdown 长文配套成可导航的网页

## 产物清单

| 产物 | 文件类型 | 用途 | 模板 |
|---|---|---|---|
| 1. 游玩攻略长文 | Jekyll `_posts/*.md` | 详细长文,含预算/时间表/节点速查,放在博客 | `assets/guide-template.md` |
| 2. 导航点位网页 | 静态 HTML(高德直接 href) | 手机打开即可点任意 POI → 唤起高德 App 导航 | `assets/nav-template.html` |
| 3. OSRM 综合地图 | 静态 HTML(Leaflet) | 浏览器打开,看 5 天实际驾车路径 + Day 切换 | `assets/overview-map-template.html` |
| 4. 原始点位 JSON | `.json` | 程序化消费(脚本/前端) | `assets/pois.schema.json` |
| 5. KML | `.kml` | 导入高德地图 App,看所有点 + 路径 | `assets/trip.kml.template.xml` |

**附加流程**:把这 5 类产物上传到 GitHub Pages 公开访问,见 `references/github-pages-deploy.md`。

## 推荐产出顺序

1. **先定原始数据** — 一个 POI 列表(Day / 名称 / 类别 / 坐标)
2. **先生成 JSON** — 数据是其他 4 类产物的源头
3. **再做导航点位页** — 从 JSON 渲染,需要高德直接 href
4. **再做 KML** — 从 JSON 渲染,简单 XML 包装
5. **再做 OSRM 综合地图** — 需要调用 OSRM 实际路径
6. **最后写攻略长文** — 文字为主,跟 POI 数据松耦合,引用导航页 URL

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
├── references/                       # 5 份参考
│   ├── artifact-checklist.md          # 每种产物的必含/可选要素
│   ├── layout-styles.md               # 布局/编排/样式规范
│   ├── coordinate-systems.md          # GCJ-02 / WGS-84
│   ├── osrm-routing.md                # OSRM 路径规划
│   └── github-pages-deploy.md         # GitHub Pages 部署
└── examples/                         # 脱敏示例
    ├── README.md
    ├── trip-guide.md
    ├── trip-nav.html
    ├── trip-overview-map.html
    ├── pois.json
    └── trip.kml
```

## 关键约定

### 坐标系统
- **国内场景优先 GCJ-02**(高德、腾讯、百度都吃这套)
- **OSM 瓦片 + OSRM 路径规划需要 WGS-84**
- 同一份数据要存两套坐标(`lng_gcj02` / `lat_gcj02` + `lng_wgs84` / `lat_wgs84`)
- 转换公式见 `references/coordinate-systems.md`

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

## 隐私 / 脱敏

- 不在模板或示例里写**真实坐标**、**真实住址**、**真实车牌**
- 不放 **API key / token / 密码**
- 占位符使用 `{placeholder_name}` 或 `__PLACEHOLDER__`
- 公开 URL 用占位符,例如 `https://{username}.github.io/`
- GitHub 仓库地址也用占位符,例如 `git@github.com:{username}/{repo}.git`

## 验证清单

每次生成完,跑一遍以下检查:

- [ ] 5 类产物全部生成,无遗漏
- [ ] JSON 通过 `pois.schema.json` 校验
- [ ] KML 在高德地图 App 能正常导入
- [ ] 导航点位页手机打开,点 POI 能唤起高德 App
- [ ] OSRM 综合地图浏览器打开,5 段路径都有
- [ ] 长文里所有提到的时间/距离/费用和导航页一致
- [ ] 公开 URL 不带 token / 私有坐标
- [ ] 提交信息符合 Conventional Commits(可选)
