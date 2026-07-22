# 布局 / 编排 / 样式规范

5 类产物在视觉风格上要保持一致,这样用户在不同产物间切换时不会觉得是"两个产品"。

---

## 1. 配色体系

### 品牌主色
- 主色:`#FF6F00`(橙色,顶栏 / 按钮 / 标题)
- 渐变:`linear-gradient(135deg, #FF6F00 0%, #FF8F00 100%)`(顶栏背景)

### POI 标签色(tag → 颜色)
| tag | 颜色 | 说明 |
|---|---|---|
| `start` | `#00C853` 绿 | 起点 |
| `end` | `#D50000` 红 | 终点 |
| `attract` | `#FF6F00` 橙 | 景点 |
| `hotel` | `#7B1FA2` 紫 | 酒店 |
| `food` | `#FFB300` 黄 | 餐厅(浅底,所以文字用 #1a1a1a 黑) |
| `service` | `#1976D2` 蓝 | 服务区 |
| `stop` | `#00838F` 青 | 驿站 / 中转点 |

### Day 路线色
| Day | 颜色 |
|---|---|
| D1 | `#E53935` 红 |
| D2 | `#1E88E5` 蓝 |
| D3 | `#43A047` 绿 |
| D4 | `#FB8C00` 橙 |
| D5 | `#8E24AA` 紫 |

(超过 5 天的话,按 Material Design palette 500 系列顺延)

### 底色 / 文字
- 背景:`#f5f6f8`(浅灰)
- 卡片:`white` + `box-shadow: 0 1px 3px rgba(0,0,0,0.05)`
- 正文:`#1a1a1a`(近黑)
- 副文:`#666`
- 提示:`#888`
- 分割线:`#e8eaec`

---

## 2. 字体规范

```css
font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
```

- 数字 / 英文:`-apple-system`(苹方 / SF Pro)
- 中文:优先 `PingFang SC`(macOS / iOS),降级 `Hiragino Sans GB` / `Microsoft YaHei`

### 字号

| 用途 | 字号 | 字重 |
|---|---|---|
| 标题(h1) | 18-22px | 600 |
| 二级标题(h2) | 15-16px | 600 |
| 标签(tag) | 10-12px | 500 |
| 正文 | 15px | normal |
| 副文 | 12px | normal |
| 提示 | 11px | normal |

---

## 3. 布局规范

### 导航点位页

```
+--------------------------------+
|  HEADER(渐变橙,sticky)         |  ← top: 0, z-index: 100
+--------------------------------+
|  DAY-NAV(白底,sticky)         |  ← top: 76px, z-index: 99
|  [D1] [D2] [D3] ...            |
+--------------------------------+
|  PADDING 16px                   |
|  DAY-TITLE(渐变橙左边框)        |
|  D1  日期 · 标题                |
|  GROUP × N                      |
|    POI × N(name / info / btn)   |
+--------------------------------+
|  USAGE 区块(白底,圆角)         |
+--------------------------------+
|  TO-TOP 按钮(fixed 右下)       |
+--------------------------------+
```

### OSRM 综合地图

```
+--------------------------------+
|  HEADER(渐变橙)                |
+--------------------------------+
|  CONTROLS(白底,圆角)           |
|  📅 Day: [全部][D1][D2]...      |
|  🛣 路径: [导航][直线]         |
+--------------------------------+
|  MAP DIV(占满剩余高度)         |
|  + 底图瓦片(OSM)               |
|  + POI markers(divIcon)        |
|  + Day 路径(实线 / 虚线)        |
|  + Legend(右下角)              |
+--------------------------------+
```

### 攻略长文(Jekyll)

按 `moto-blog-format` 等已有 skill 的样式规范:
- `max-width: 38em`(适合阅读)
- `line-height: 1.85`(行高宽松)
- 标题 H2 加大 / 加橙色 / 底部 3px 橙色边
- TOC 浮动按钮(右下角),点击展开侧边栏

---

## 4. 卡片规范

### POI 卡片(导航页)

```css
.poi {
  background: white;
  border-radius: 10px;
  padding: 12px 14px;
  margin-bottom: 10px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  border: 1px solid #ecedef;
}
```

### Trip 卡片(旅行集合集页)

```css
.trip {
  background: white;
  border-radius: 12px;
  padding: 14px 16px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  border: 1px solid #ecedef;
}
.trip:active { background: #fafafa; transform: scale(0.99); }
```

### Tag 徽章

```css
.tag {
  display: inline-block;
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  margin-left: 6px;
  font-weight: 500;
  color: white;
  vertical-align: middle;
}
```

### Action 按钮(导航页)

```css
.poi-actions a {
  flex: 1; min-width: 90px;
  text-align: center; padding: 7px 6px;
  font-size: 12px; border-radius: 6px;
  text-decoration: none; font-weight: 500;
  background: #FFF3E0; color: #E65100; border: 1px solid #FFE0B2;
}
.btn-search { background: #E3F2FD; color: #1565C0; border-color: #BBDEFB; }
.btn-marker { background: #F3E5F5; color: #6A1B9A; border-color: #E1BEE7; }
```

---

## 5. 移动端适配

```css
* { box-sizing: border-box; margin: 0; padding: 0; }
html { -webkit-text-size-adjust: 100%; }
body {
  -webkit-font-smoothing: antialiased;
  -webkit-tap-highlight-color: transparent;
}
```

要点:
- viewport meta 加 `maximum-scale=1.0, user-scalable=no`(防误触缩放)
- touch 元素加 `-webkit-tap-highlight-color: transparent`(去除高亮)
- horizontal scroll 用 `-webkit-overflow-scrolling: touch`(iOS 顺滑)
- 隐藏滚动条:`::-webkit-scrollbar { display: none; }`

---

## 6. emoji 使用

- 🚗 自驾 / 导航
- 📍 位置
- 🔍 搜索
- 🚗+📍+🔍 三个按钮分别对应
- 🌅 上午段
- 🌞 下午段
- 🌆 黄昏+晚段
- 🏛 景点
- 🍜 餐厅
- 🏨 酒店
- ⛽ 服务区
- 📅 时间 / Day
- 🛣 路线
- 💰 预算
- 🎯 节点
- ⭐ 重点
- 🆕 新版
- 📎 配套
- 🖼 截图 / 图

---

## 7. 一致性 checklist

- [ ] 同一份行程的 5 类产物使用相同的 emoji 标记
- [ ] 同一份行程的 5 类产物使用相同的 day 颜色
- [ ] 同一份行程的 5 类产物的标题格式一致(`{emoji} {title} · {subtitle}`)
- [ ] 长文里引用的 POI 名称 = 导航页里的 POI 名称 = JSON 里的 name 字段
- [ ] 配套产物链接在 5 个产物里都放(至少放 2 个,长文必放)
