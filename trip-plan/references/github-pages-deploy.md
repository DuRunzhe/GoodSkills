# GitHub Pages 部署流程

把 5 类产物部署到 GitHub Pages(或 Cloudflare Pages)公开访问的标准流程。

---

## 1. 选型:GitHub Pages vs Cloudflare Pages

| 维度 | GitHub Pages | Cloudflare Pages |
|---|---|---|
| 域名 | `username.github.io` 或自定义 | `xxx.pages.dev` 或自定义 |
| 仓库 | 必须 `username/username.github.io` 命名 | 任意仓库 |
| 构建 | Jekyll 原生(无需配置) | 需 `_config.yml` + Gemfile |
| 部署触发 | push main 即部署 | push main 即部署 |
| 强制要求 | 仓库 public(除非 Pro) | 仓库 public 或 Pro |
| 国内访问 | 偶尔被墙 | 偶尔被墙 |

**两者底层完全相同**(都跑 Jekyll),选哪个看域名偏好。

---

## 2. 仓库准备(以 `username/username.github.io` 为例)

```bash
# 1. 在 GitHub 网页上 New repository
#    Repository name: username.github.io
#    Public
#    Add README + MIT License

# 2. 本地 clone
mkdir -p ~/blog && cd ~/blog
git clone git@github.com:username/username.github.io.git .

# 3. 推一个测试文件,确认部署
echo "# test" > index.md
git add index.md
git commit -m "init"
git push origin main
```

部署成功 1-3 分钟后,访问 `https://username.github.io/` 应看到 "test"。

---

## 3. 文件命名规范

| 产物 | 命名 | 公开 URL |
|---|---|---|
| 旅行集合集 | `trips.html` | `/trips.html` |
| 单行程导航页 | `{trip-slug}-trip-map.html` | `/{trip-slug}-trip-map.html` |
| 单行程攻略长文 | `_posts/{YYYY-MM-DD}-{trip-slug}.md` | `/{YYYY}/{MM}/{DD}/{trip-slug}.html` |
| 单行程综合地图 | `{trip-slug}-trip-map-v{n}.html` | `/{trip-slug}-trip-map-v{n}.html` |
| 单行程原始数据 | `drafts/{trip-slug}-pois.json` | (不公开,本地用) |
| 单行程 KML | `drafts/{trip-slug}.kml` | (不公开,本地用) |

### 命名规则
- 用 kebab-case(小写 + 连字符)
- `trip-slug` 用英文短词,如 `inner-mongolia` / `fujian-coast` / `wutaishan`
- 公开 URL 短好记,SEO 友好

### 不要把 `drafts/` 公开
Jekyll 默认会把所有 md/html 渲染。`drafts/` 目录需要 `_config.yml` 里配置 `exclude: [drafts]` 排除。

`_config.yml` 推荐配置:

```yaml
title: {site_title}
description: {site_desc}
theme: minima

# 不发布 drafts 和原始数据
exclude:
  - drafts
  - Gemfile
  - Gemfile.lock
  - README.md
  - "{trip-slug}-pois.json"
```

---

## 4. 5 类产物的部署步骤

### 4.1 旅行集合集(`trips.html`)

1. 复制模板到 `~/blog/trips.html`
2. 替换占位符:行程标题 / 路线 / POI 数 / 链接
3. 每个行程加 `v5 综合地图` 链接(指向 4.3 的文件)
4. 推送

### 4.2 单行程导航页

1. 复制 `nav-template.html` 到 `~/blog/{trip-slug}-trip-map.html`
2. 替换占位符:行程名 / route_summary / day_count / Day 区块 / POI 卡片
3. 替换 src 参数(utm):`src=momotrip`(独家标记,高德后台可看来源)
4. 推送
5. 在 `trips.html` 加 `<a class="trip" href="{trip-slug}-trip-map.html">` 入口

### 4.3 单行程综合地图

1. 复制 `overview-map-template.html` 到 `~/blog/{trip-slug}-trip-map-v{n}.html`
2. 把 `__POIS__` / `__DAY_ROUTES__` 等占位符替换成 JSON 字面量
3. (可选)截图后做 PNG 预览
4. 推送
5. 在 `trips.html` 加 `<a class="trip-read" href="{trip-slug}-trip-map-v{n}.html">` 入口

### 4.4 单行程攻略长文

1. 复制 `guide-template.md` 到 `~/blog/_posts/{YYYY-MM-DD}-{trip-slug}.md`
2. 替换 frontmatter(title / date / categories / tags)
3. 替换正文占位符
4. 在文章开头或结尾加配套产物链接(导航页 + 综合地图)
5. 推送
6. 在 `trips.html` 加 `<a class="trip-read" href="/trip/{category}/{YYYY}/{MM}/{DD}/{trip-slug}.html">` 入口

### 4.5 单行程 KML / JSON(可选公开)

KML 建议**打包成 zip 公开**,因为 XML 文件不能直接当页面访问:

```bash
zip {trip-slug}.kml.zip {trip-slug}.kml
```

JSON 一般**不公开**(体积大 + 不是给人看的),在本地脚本里消费。

如果一定要公开,放到 `drafts/` 之外的目录,比如 `data/{trip-slug}.json`。

---

## 5. 推送流程

```bash
cd ~/blog
git add trips.html {trip-slug}-trip-map.html {trip-slug}-trip-map-v{n}.html _posts/{date}-{trip-slug}.md
git commit -m "feat({trip-slug}): {change_summary}

- {change_1}
- {change_2}"
git push origin main
```

**Commit 信息规范**(Conventional Commits):
- `feat: 新增`
- `fix: 修复`
- `docs: 文档`
- `refactor: 重构`
- `chore: 杂项`

例:`feat(inner-mongolia): 加 v5 综合地图(OSRM 实际路径 + Day toggle)`

---

## 6. 验证清单

推送后 1-3 分钟(Cloudflare)或 1-2 分钟(GitHub Pages),逐一验证:

- [ ] `https://username.github.io/trips.html` 能打开,所有行程卡片正常
- [ ] `https://username.github.io/{trip-slug}-trip-map.html` 能打开,点 POI 唤起高德 App
- [ ] `https://username.github.io/{trip-slug}-trip-map-v{n}.html` 能打开,Leaflet 渲染正常
- [ ] `https://username.github.io/{YYYY}/{MM}/{DD}/{trip-slug}.html` 攻略长文能打开,Frontmatter 正常
- [ ] (如果公开)在手机上点击导航页 POI,能直接打开高德 App 开始导航
- [ ] 在高德地图 App 导入 KML,所有 Day 文件夹 + POI 都显示在正确位置

---

## 7. 注意事项

### 隐私

**不要在公开仓库提交**:
- 真实住址 / 门牌号 / 个人手机号
- API key / token / 密码
- 真实车牌 / 行驶证
- 未脱敏的他人信息(合影需打码)

**KML 文件**最容易暴露住址(POI 里 `info` 字段可能写"家门口"),发布前过一遍。

### 索引

如果不想被 Google / Bing 索引,在 `trips.html` `<head>` 加:

```html
<meta name="robots" content="noindex, nofollow">
```

或者在仓库根放 `robots.txt`:

```
User-agent: *
Disallow: /
```

### 性能

- 单独 HTML 页面最好 < 200KB(Leaflet OSRM 模板 + 内联数据 ~700KB,可接受)
- 如果太大,可以把数据拆到 `data/{trip-slug}.json`,HTML 用 fetch 加载
- 图片用 WebP + lazy load

---

## 8. 一键脚本(可选)

```bash
#!/bin/bash
# ~/bin/publish-trip.sh
set -e

TRIP_SLUG=$1
BLOG_DIR=~/blog

if [ -z "$TRIP_SLUG" ]; then
  echo "Usage: publish-trip.sh {trip-slug}"
  exit 1
fi

cd "$BLOG_DIR"
git add "trips.html" "${TRIP_SLUG}-trip-map.html" "${TRIP_SLUG}-trip-map-v"*.html "_posts/"*"${TRIP_SLUG}"*.md
git status
read -p "commit and push? (y/n) " yn
[ "$yn" = "y" ] && git commit -m "feat(${TRIP_SLUG}): publish trip artifacts" && git push origin main
```

用法:`publish-trip.sh inner-mongolia`
