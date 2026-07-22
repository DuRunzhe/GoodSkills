# GoodSkills

好用技能合集

每个子目录是一个独立 skill,目录名即 skill 名称。子目录遵循 OpenClaw 标准 skill 结构:

```
<skill-name>/
├── SKILL.md           # 入口:触发条件、产物清单、流程概览
├── assets/            # 模板(可复用的固定骨架)
├── references/        # 参考(规范、API、规则)
└── examples/          # 脱敏示例
```

## Skills

| Skill | 用途 |
|---|---|
| `trip-plan/` | 旅行游玩攻略全套产物生成(攻略长文 / 导航点位页 / OSRM 综合地图 / JSON / KML) |
| `moto-blog-format/` | 摩托车数据博文排版指南(11列车型速览表+lightbox图、H3/H4章节分级、参数子表、竞品横评) |

## 约定

- 所有产物文件用 UTF-8 编码
- 隐私信息(具体坐标、住址、token、密钥)不出现在模板或示例里
- 占位符用 `{placeholder_name}` 或 `__PLACEHOLDER__` 形式,便于全局替换
- 中文表达保持一致(不要繁体 / 简体混用)
