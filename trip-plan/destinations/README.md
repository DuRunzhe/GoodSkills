# Destinations · 目的地 Playbook 库

LLM 在被 trip-plan skill 唤起后,**第一步就应该读相关的 destinations/<slug>.md**,获取该目的地的本地化知识(分组规则 / 必去点 / 专属提醒 / 季节性)。

## 目录结构

```
destinations/
├── README.md           # 本文件
├── registry.json       # 目的地注册表(LLM 找 playbook 的入口)
└── wutaishan.md        # 五台山(稳定版)
```

## 注册一个目的地

1. 创建 `destinations/<slug>.md`,按下面「Playbook 模板」结构
2. 在 `destinations/registry.json` 加索引
3. 标记 maturity:`draft` / `stable` / `experimental`
4. 至少 3 次实跑后改为 `stable`

## Playbook 模板

```markdown
---
slug: <slug>           # 短英文标识,用作文件名
name: <中文名>          # 显示名
region: <省/市>         # 地理区域
type: <类型>            # 古建筑 / 自然风光 / 美食 / 综合
season: <最佳季节>       # 6-9 月 / 全年 / 等
maturity: <draft|stable|experimental>
last_verified: YYYY-MM-DD
---

# <名称> Playbook

## 概要
- 核心吸引力
- 适合人群
- 不适合人群

## 分组规则
LLM 在 Step 3 生成 Day section 时,按以下规则分组 POI:

| 触发条件 | 分组标题 | emoji |
|---|---|---|

## 专属规则(LLM 必读)
- 餐厅时段限制
- 必去点权重
- 避免项
- 疲劳管理
- 季节性约束

## 专属提醒
| 类型 | 内容 | 来源 |
|---|---|---|

## 必去点
| 名称 | 权重 | 推荐时长 | 时段 |
|---|---|---|---|

## 加分项
| 名称 | 权重 | 备注 |
|---|---|---|

## 季节性
- 最佳月份
- 雨季 / 雪季
- 节庆

## 数据源
- 官网 URL
- 预约电话
- 公众号
- 高德 POI 关键词

## 实跑历史
- YYYY-MM-DD:行程概要(谁 / 几天 / 验证什么)
```

## Maturity 等级

| 等级 | 含义 | 何时升级 |
|---|---|---|
| `experimental` | LLM 自动生成,人工未审 | ≥ 1 次人工审阅 → `draft` |
| `draft` | 起草,待实跑 | ≥ 3 次实跑验证 → `stable` |
| `stable` | 经过 ≥ 3 次实跑验证 | - |

## LLM 使用方式

**Step 1**:先读 `destinations/registry.json` 确认目的地存在

```python
read destinations/registry.json  # 确认 maturity ≥ draft
read destinations/wutaishan.md  # 读具体 playbook
```

**Step 2**:playbook 包含的字段决定 LLM 在 Step 3-4 的推理依据:
- 分组规则 → 决定 POI 怎么分组
- 必去点 → 决定 LLM 必排进去
- 加分项 → 决定 LLM 排进去更好
- 专属提醒 → 决定底部提醒写什么
- 季节性 → 决定时段编排

**Step 3**:LLM 不应该改 playbook,只应该读。如果发现 playbook 有错,提示用户更新。

## 贡献 Playbook

新目的地的 playbook 应包含:
1. **概要**:用 3-5 句话说清楚核心吸引力
2. **分组规则**:这个目的地特有的 POI 分组(基于 tag + 上下文)
3. **专属规则**:这个目的地的硬约束(必去点权重 / 时段限制 / 避雷)
4. **专属提醒**:5-10 条本地化知识(限行 / 门票 / 预约 / 季节)
5. **必去点 + 加分项**:带权重的 POI 列表
6. **数据源**:可查证的来源(官网 / 公众号 / 电话)
7. **实跑历史**:每次实跑后追加一行(谁 / 几天 / 验证什么)

来源要求:
- ✅ 必去点 / 限行规则 / 预约电话 都要有 ≥ 2 个来源
- ❌ 不要 LLM 编造(查不到标 [待核实])
- ✅ 季节性信息要从公开资料 + 实跑经验来