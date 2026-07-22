---
name: "moto-blog-format"
description: "摩托车数据博文排版指南：11列车型速览表+lightbox图、H3/H4章节分级、参数子表、竞品横评、数据源优先级、图片抓取规则"
---

# 🏍️ 摩托车数据博文排版指南

> 用于 `<blog>/moto-comparison.html` 与 `<drafts>/关注的摩托车.md` 的排版规范。
> 适用于：摩托车评测、对比、车型清单类博文。

---

## 1. 章节分级规范（最严执行）

参考 MEMORY.md 第 14 条「父 H3 → 子 H4」。

| 层级 | 用途 | 示例 |
|---|---|---|
| **H1**（博客全文标题）| 只用 1 次 | 整个博文顶部 |
| **H2** | 一级章节（按车型类别分）| `## 🏍️ 入门级 ADV 跨骑` |
| **H3** | 一级章节下的子章节（功能模块）| `### 📋 车型速览` / `### 🔍 详细参数记录` / `### 🏆 综合横评` |
| **H4** | 具体车型小节 | `#### 1. **车型名**——定位 ⭐` |
| **H5** | 车型内部模块 | `##### 💰 价格` / `##### 📐 车体` / `##### ⚙️ 发动机` |

**🚨 严禁同级错乱**：
- ❌ 子项与父项同级别（H3 配 H3 = 错误）
- ✅ 父 H3 → 子 H4 → 孙 H5

**TOC 缩进必须匹配 HTML 渲染层级**（见附录 A）。

---

## 2. 车型速览子章节（最重要）

### 2.1 标准 11 列表格（HTML 格式）

```html
<h3>📋 车型速览</h3>
<table>
<thead>
<tr>
  <th>车型</th>
  <th>车辆图片</th>
  <th>售价</th>
  <th>排量</th>
  <th>动力</th>
  <th>整备质量</th>
  <th>油箱</th>
  <th>座高</th>
  <th>轮胎</th>
  <th>离地间隙</th>
  <th>风格定位</th>
</tr>
</thead>
<tbody><tr>
  <td><strong>五羊本田 CGX150</strong></td>
  <td><a class="lightbox-link" href="img/motos/cgx150.jpg" title="点击看大图"><img alt="五羊本田 CGX150" src="img/motos/cgx150.jpg" style="max-width:120px; height:auto; cursor:pointer;" /></a></td>
  <td>¥10,080-11,680 (标/边包/特别)</td>
  <td>—</td>
  <td>8.8kW/12.5N·m</td>
  <td>125kg</td>
  <td>10L</td>
  <td>740mm</td>
  <td>—</td>
  <td>160mm</td>
  <td>Cafe Racer（真复古）</td>
</tr>
<!-- 更多车型... -->
</tbody>
</table>
```

### 2.2 Markdown 等价（drafts / 未发布草稿）

```markdown
### 📋 车型速览

| 车型 | 车辆图片 | 售价 | 排量 | 动力 | 整备质量 | 油箱 | 座高 | 轮胎 | 离地间隙 | 风格定位 |
|---|---|---|---|---|---|---|---|---|---|---|
| **车型名** | ![车型名](img/motos/xxx.jpg) | ¥XX,XXX | — | XXkW/XXN·m | XXXkg | XXL | XXXmm | — | XXXmm | 风格定位 |
```

### 2.3 关键格式要素

| 元素 | 规则 |
|---|---|
| **列数** | 严格 11 列：车型 / 车辆图片 / 售价 / 排量 / 动力 / 整备质量 / 油箱 / 座高 / 轮胎 / 离地间隙 / 风格定位 |
| **图片宽度** | `max-width:120px; height:auto; cursor:pointer;` |
| **lightbox 链接** | `<a class="lightbox-link" href="..." title="点击看大图">` |
| **图片 alt** | 必须填中文车型名（不是英文文件名） |
| **HTML 包装** | 直接 `<table>`（无需 table-wrap 包装） |
| **车型名加粗** | `<strong>...</strong>` |
| **风格定位** | 一句话定位，如「Cafe Racer（真复古）」 |
| **未查数据** | 用 `—` 占位，待查用 `🔴 待查` |
| **停售车型** | 用 `<del>车型名</del>` 划线，不加图 |

### 2.4 最小示例（2 行展示格式）

| 车型 | 车辆图片 | 售价 | 排量 | 动力 | 整备质量 | 油箱 | 座高 | 轮胎 | 离地间隙 | 风格定位 |
|---|---|---|---|---|---|---|---|---|---|---|
| **示例车型 A** | ![A](img/motos/a.jpg) | ¥XX,XXX | XXXcc | XXkW/XXN·m | XXXkg | XXL | XXXmm | — | XXXmm | 风格定位 |
| **示例车型 B** | ![B](img/motos/b.jpg) | 🔴 待查 | — | — | — | — | — | — | — | 待查占位行 |

> 完整可运行示例见 `examples/moto-blog-format-demo.md`。

## 3. 详细参数记录子章节

### 3.1 车型小节模板

```markdown
#### 1. **车型名**——定位 ⭐
![车型名](img/motos/xxx.jpg)

##### 💰 价格
| 版本 | 售价 | 定位 |
|---|---|---|
| **标准版** | **¥XX,XXX** | 车型定位 |

##### 📐 车体
| 项目 | 参数 |
|---|---|
| 长 × 宽 × 高 | XXXX × XXX × XXXX mm |
| 整备质量 | **XXXkg** |

##### ⚙️ 发动机
| 项目 | 参数 |
|---|---|
| 型式 | X缸 · X排量 |
| 最大功率 | **XXkW** @ XXXX rpm |

##### 🛞 底盘 & 制动
| 项目 | 参数 |
|---|---|
| 前悬挂 | 前叉类型 |
| 轮胎 | 前 XX/XX-XX / 后 XX/XX-XX |

**📌 关键特点**：
- 特点 1
- 特点 2
```

### 3.2 命名编号规范

| 类别 | 编号 |
|---|---|
| 进口车 | 1, 2, 3...（按价格升序）|
| 合资车 | 接续 |
| 国产车 | 接续 |
| 平行进口 | `<span style="color:#999;">` 灰显，`~~划线~~` |

### 3.3 车型小节必备元素

- ✅ H4 标题后插入主图（120px 缩略图 + lightbox）
- ✅ H5 子小节至少 3 个：💰 价格 / 📐 车体 / ⚙️ 发动机
- ✅ 每个 H5 一个小表格，表格第一列为「项目」
- ✅ 关键参数加粗 `**...**`
- ✅ 数据后空格 + 🏆 emoji 标记「同级之最」
- ✅ 段落结尾的「关键特点」用 ul/li

---

## 4. 综合横评子章节

### 4.1 多维度冠军表（必备）

```markdown
#### 🥇 [本章]各维度冠军
| 维度 | 🏆 冠军 | 数据 |
|---|---|---|
| 💰 最便宜 | **车型名** | **¥XX,XXX** 🏆 |
| 🏋️ 最轻 | **车型名** | **XXXkg** 🏆 |
| 💪 动力最强 | **车型名** | XXkW |
| ⛽ 续航最长 | **车型名** | **XXXkm** 🏆 |
```

### 4.2 同价位对比表（可选）

```markdown
#### 🆚 入门级 vs 中排量
| 维度 | 入门级（<300cc）| 中排量（300-650cc）|
|---|---|---|
| 价格 | 1.7-4 万 | 3-7 万 |
| 动力 | 11-21 kW | 30-50 kW |
```

### 4.3 用户决策树（用 pre 块）

```markdown
#### 💡 用户决策树
```
预算 < 2 万？
  ├─ 是 → 车型 A
  └─ 否 ↓
预算 < X 万？
  ├─ 是 → 车型 B
  └─ 否 ↓
```
```

### 4.4 待补全项（章节末尾必备）

```markdown
#### 📌 待补全项
- 待补项 1
- 待补项 2
```

---

## 5. 数据源优先级

| 场景 | 数据源 | 备注 |
|---|---|---|
| 价格、官方规格 | **品牌官网** | 最准 |
| 配置对比、车型库 | **汽车之家** | `car.autohome.com.cn/motorbike/series/{ID}` |
| 跨品牌参数 + 图片 | **摩托范手机 web 版** | 绕过 WAF（见 §6）|
| 销量、车主实测 | **摩托范 SSR 数据** | 询价率、车主评分等 |
| 续航、油耗 | **车主论坛 / 搜狐汽车** | 综合车主实测 |

---

## 6. 图片抓取规则

### 6.1 摩托范 mobile web 版（绕过 WAF）

桌面版有阿里云 WAF 拦截，手机 web 版是 Nuxt SSR 直出 HTML，正常抓。

```bash
curl -sL --max-time 15 \
  -H "User-Agent: Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1" \
  -H "Referer: https://m.58moto.com/" \
  -e "https://m.58moto.com/" \
  "https://imgs.emotofine.com/nowater/{YYYYMMDD}/{YYYYMMDDHHMMSS}_{hash}.jpg!nowater300?_180_180" \
  -o /tmp/moto.jpg
```

关键点：
- URL 格式：`!nowater300?_180_180` 后缀
- Referer 必填：`https://m.58moto.com/`
- User-Agent 必填（iPhone Safari）
- SSR goodPic 字段直接给主图 URL

### 6.2 汽车之家

```bash
curl -sL --max-time 15 \
  -H "User-Agent: Mozilla/5.0 (iPhone; CPU iPhone OS 17_0...)" \
  -H "Referer: https://car.autohome.com.cn/" \
  "https://car2.autoimg.cn/cardfs/motobike/.../{hash}.jpg" \
  -o /tmp/moto.jpg
```

大图（800KB+）需 `sips -Z 400` 缩到 400px 再用 image 工具识别。

### 6.3 ID 映射错位防御（⚠️ 必须）

摩托范 search 返回的 garage ID **不一定等于真实车型**。必须用详情页 SSR `goodsCarName` 二次确认。

**流程**：抓图 → image 工具识别 → 确认车型名 → 才能写入 HTML。

---

## 7. 存储规范

### 7.1 文件位置

| 文件 | 位置 |
|---|---|
| 博文 HTML | `~/blog/moto-comparison.html` |
| 草稿 Markdown | `~/.openclaw/workspace/drafts/关注的摩托车.md` |
| 图片库 | `~/blog/img/motos/` |

### 7.2 Git 提交规范

```
feat: 新增「XXX」章节（N 款车型）
fix: XXX 数据修正
docs: 仅文档改动（不更新数据）
chore: 图片库补充
```

### 7.3 推送

```bash
cd ~/blog && git add ... && git commit -m "..." && git push
```

---

## 8. 完整章节骨架模板

见 `templates/moto-blog-skeleton.md`（复制粘贴用）。

---

## 9. 附录 A：TOC 缩进规范

博客顶部 TOC 必须与章节分级匹配：

```html
<ul>
<li><a href="#sec-N">🏍️ 一级章节名</a>
  <ul style="list-style:none; padding-left:20px; font-size:12px; margin:2px 0; color:#666;">
    <li><a href="#sec-N">📋 车型速览</a></li>
    <li><a href="#sec-N">🔍 详细参数</a></li>
    <li><a href="#sec-N">🏆 综合横评</a></li>
  </ul>
</li>
</ul>
```

---

## 10. 附录 B：常见错误与避坑

| 错误 | 正确做法 |
|---|---|
| ❌ 父 H3 + 子 H3（同级）| ✅ 父 H3 + 子 H4 |
| ❌ 车型速览表用 4 列简表 | ✅ 用 11 列参数完整表 |
| ❌ 图片没 lightbox 链接 | ✅ `<a class="lightbox-link" href="..." title="点击看大图">` |
| ❌ 用摩托范搜索 ID 不验证 | ✅ 必须用详情页 SSR 二次确认 |
| ❌ 图片 alt 写英文文件名 | ✅ 写中文车型名 |
| ❌ 表格外层包多余 `class="table-wrap"` | ✅ 直接用 `<table>` |
| ❌ 没标 🏆 冠军 | ✅ 「同级之最」必须 🏆 标记 |
| ❌ 缺「待补全项」 | ✅ 章节末尾必带「待补全项」 |

---

## 11. 附录：图库数据分离说明

skill 是规范，**不是数据快照**。当前图库清单是任务级数据，不属于 skill 规范。

**数据放哪：**

| 数据类型 | 位置 |
|---|---|
| 当前图库快照 | `git ls-files img/motos/`（单一来源）|
| 孤儿图备份 | `drafts/orphans/<日期>/`（如 `moto-2026-07-15/`）|
| ID 错位记录 | `drafts/moto-image-inventory.md`（待建）|
| 图库维护日志 | 每次 `drafts/orphans/<日期>/README.md` |

**添加新图流程：**
1. 抓图 → 详情页 SSR 二次确认车型名（避免 ID 错位）
2. `git ls-files img/motos/` 看是否已有同车型图
3. 命名：`{型号-slug}.jpg`，小写无空格（如 `nx400.jpg`、`dl250.jpg`）
4. AI 生成图统一加「示意图 · AI生成」水印
5. 替代旧图：旧图移到 `drafts/orphans/<日期>/` 备份，再 `git rm`

---

_本 skill 按 spec vs data 分离原则维护（2026-07-15 清理）。_
