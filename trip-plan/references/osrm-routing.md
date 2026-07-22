# OSRM 路径规划使用说明

OSRM(Open Source Routing Machine)是基于 OSM 数据的开源路径规划引擎。本 skill 用它的**公共 HTTP API** 给每日 POI 拉真实驾车路径,避免 Leaflet 上画直线。

---

## 1. 为什么需要 OSRM

Leaflet 默认画直线(L.polyline 连两个点),看起来不真实:
- 直线穿过山体 / 河流
- 直线忽略单行道 / 立交
- 直线不区分高速 / 国道 / 乡道

OSRM 拿 OSM 路网算**真实驾车路线**,返回 GeoJSON LineString,直接画到 Leaflet 上就是真实路径。

---

## 2. 公共 API

### 端点

```
http://router.project-osrm.org/route/v1/driving/{lng,lat;lng,lat;...}?overview=full&geometries=geojson
```

- `driving`:驾车模式(也支持 walking / cycling)
- `{lng,lat;lng,lat;...}`:多个 waypoint,用 `;` 分隔
- `overview=full`:返回完整 geometry(不止起终点)
- `geometries=geojson`:格式(也支持 polyline / polyline6)

### 示例

```bash
curl 'http://router.project-osrm.org/route/v1/driving/116.54,40.08;117.28,42.25;117.16,42.44?overview=full&geometries=geojson'
```

返回:

```json
{
  "code": "Ok",
  "routes": [{
    "geometry": {
      "type": "LineString",
      "coordinates": [[116.54, 40.08], [116.55, 40.10], ..., [117.16, 42.44]]
    },
    "distance": 460000,
    "duration": 24000
  }]
}
```

### 限速

公共服务器**严格 1 请求/秒**,超过会被限流。
本 skill 每天只发 1 个请求(传当日所有 POI),所以 5 天行程最多 5 个请求,加 0.5s sleep 留 buffer。

---

## 3. Python 调用封装

```python
import subprocess
import json

def osrm_route(coords):
    """coords = [(lng_wgs84, lat_wgs84), ...]"""
    if len(coords) < 2:
        return coords
    coords_str = ';'.join('{0},{1}'.format(*c) for c in coords)
    url = ('http://router.project-osrm.org/route/v1/driving/{0}'
           '?overview=full&geometries=geojson').format(coords_str)
    try:
        result = subprocess.run(
            ['curl', '-s', '--max-time', '30',
             '-H', 'User-Agent: Mozilla/5.0',
             url],
            capture_output=True, text=True, timeout=35
        )
        if result.returncode != 0:
            return coords
        data = json.loads(result.stdout)
        if data.get('code') != 'Ok' or not data.get('routes'):
            return coords
        return data['routes'][0]['geometry']['coordinates']
    except Exception as e:
        print('OSRM error:', e)
        return coords
```

要点:
- `User-Agent` 必带(裸 curl 会被拒)
- 失败 / 超时 / 限流时**回退到直线**(不阻塞流程)
- 返回的是 WGS-84 坐标数组 `[[lng, lat], ...]`

---

## 4. 中国境内限制

### 已知问题
- **OSM 在中国境内数据稀疏**:二三线城市的乡道 / 县道经常缺失
- **限速 / 单行道等交通规则不全**:OSM 数据更新滞后
- **高速 / 国道数据较准**:主干道一般 OK

### 实用建议
- 知名景区(5A / 4A)OSRM 都能算
- 偏僻景点(自驾越野 / 草原深处)OSRM 可能直接 fallback 到直线
- 这种情况下用**预设 waypoint 数组**作为兜底(见 `trip.kml.template.xml` 和 `overview-map-template.html` 的 specialRoutes)

### 何时必须用预设线
- 99 号公路 / 达达线 / 热阿线等**命名景观公路**
- 这些公路在 OSM 数据里可能有路网,但 OSRM 不知道它"更美",会给你走 G207 高速
- 解决方案:手动记录这条公路的 5-10 个关键点,作为 polyline 画出来

---

## 5. 替代方案

如果 OSRM 不可用,可以用这些:

| 方案 | 优 | 劣 |
|---|---|---|
| **OSRM 公共 API** | 免费,无需 key | 限速 1 req/s,中国数据稀疏 |
| **GraphHopper** | 中国数据稍好 | 免费额度有限,5 req/min |
| **Mapbox Directions** | 准确 | 需要 token,按调用计费 |
| **高德路径规划 API** | 中国数据准 | 需要 key,合规要求 |
| **手画预设线** | 完全可控 | 维护成本 |

本 skill 默认用 OSRM,失败/特殊路段用预设线兜底。

---

## 6. OSRM vs Leaflet 直线模式

在 OSRM 综合地图模板里,顶部有一个切换按钮:

| 模式 | 用途 |
|---|---|
| 导航路线 (OSRM) | 真实驾车路径,主推 |
| 直线 | 仅做空间关系展示,不要相信其路径合理性 |

数据存在 `day_routes_wgs84` 字段里,Leaflet 用 `L.polyline(day_routes_wgs84[day].map(c => [c[1], c[0]]))` 渲染。
直线模式用 `dayPois.map(p => [p.lat_wgs84, p.lng_wgs84])` 渲染。
