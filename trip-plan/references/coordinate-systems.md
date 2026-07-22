# 坐标系统说明

国内旅行数据涉及 2 套坐标系(GCJ-02 / WGS-84),混淆会导致 POI 偏移 100-700 米。本 skill 的数据存**双坐标系**,渲染时按场景选用。

---

## 1. 坐标系定义

| 坐标系 | 别名 | 谁用 | 偏移情况 |
|---|---|---|---|
| **WGS-84** | 地球坐标系 | GPS 设备 / Google Maps / OSM / OpenStreetMap / OSRM | 国际标准,无偏移 |
| **GCJ-02** | 火星坐标 / 国测局坐标 | 高德地图 / 腾讯地图 / 百度地图(部分) | 相对 WGS-84 偏移 100-700m,中国境内 |
| **BD-09** | 百度坐标 | 百度地图 | 相对 GCJ-02 再加密,本 skill 不直接用 |

### 关键点

- **WGS-84** 是国际标准,GPS 直接输出
- **GCJ-02** 是国内合规要求,高德 / 腾讯吃这套
- **OSM 瓦片 + OSRM** 用 WGS-84
- **高德 App / 网页** 用 GCJ-02
- **百度地图** 用 BD-09(本 skill 不覆盖)

---

## 2. 转换公式

GCJ-02 ↔ WGS-84 互转(国内境内):

```python
import math

PI = 3.1415926535897932384626
A = 6378245.0           # 长半轴
EE = 0.00669342162296594323  # 偏心率平方

def out_of_china(lng, lat):
    """判断坐标是否在中国境内(中国境外不做偏移)"""
    return not (72.004 <= lng <= 137.8347 and 0.8293 <= lat <= 55.8271)

def _transform_lat(x, y):
    ret = (-100.0 + 2.0*x + 3.0*y + 0.2*y*y + 0.1*x*y
           + 0.2*math.sqrt(abs(x)))
    ret += (20.0 * math.sin(6.0*x*PI) + 20.0 * math.sin(2.0*x*PI)) * 2.0 / 3.0
    ret += (20.0 * math.sin(y*PI) + 40.0 * math.sin(y/3.0*PI)) * 2.0 / 3.0
    ret += (160.0 * math.sin(y/12.0*PI) + 320*math.sin(y*PI/30.0)) * 2.0 / 3.0
    return ret

def _transform_lng(x, y):
    ret = (300.0 + x + 2.0*y + 0.1*x*x + 0.1*x*y
           + 0.1*math.sqrt(abs(x)))
    ret += (20.0 * math.sin(6.0*x*PI) + 20.0 * math.sin(2.0*x*PI)) * 2.0 / 3.0
    ret += (20.0 * math.sin(x*PI) + 40.0 * math.sin(x/3.0*PI)) * 2.0 / 3.0
    ret += (150.0 * math.sin(x/12.0*PI) + 300.0*math.sin(x/30.0*PI)) * 2.0 / 3.0
    return ret

def gcj02_to_wgs84(lng, lat):
    """GCJ-02 → WGS-84"""
    if out_of_china(lng, lat):
        return lng, lat
    dlat = _transform_lat(lng - 105.0, lat - 35.0)
    dlng = _transform_lng(lng - 105.0, lat - 35.0)
    radlat = lat / 180.0 * PI
    magic = math.sin(radlat)
    magic = 1 - EE * magic * magic
    sqrtmagic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((A * (1 - EE)) / (magic * sqrtmagic) * PI)
    dlng = (dlng * 180.0) / (A / sqrtmagic * math.cos(radlat) * PI)
    mglat = lat + dlat
    mglng = lng + dlng
    return lng * 2 - mglng, lat * 2 - mglat

def wgs84_to_gcj02(lng, lat):
    """WGS-84 → GCJ-02"""
    if out_of_china(lng, lat):
        return lng, lat
    dlat = _transform_lat(lng - 105.0, lat - 35.0)
    dlng = _transform_lng(lng - 105.0, lat - 35.0)
    radlat = lat / 180.0 * PI
    magic = math.sin(radlat)
    magic = 1 - EE * magic * magic
    sqrtmagic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((A * (1 - EE)) / (magic * sqrtmagic) * PI)
    dlng = (dlng * 180.0) / (A / sqrtmagic * math.cos(radlat) * PI)
    return lng + dlng, lat + dlat
```

### 精度说明

- 转换公式是**有损的**(WGS-84 → GCJ-02 官方不公布,只能反推)
- 转换后误差在 0.5-1 米(肉眼基本看不出)
- 所以**存双坐标系**比"任意时刻单方面转"更准

---

## 3. 数据存储规范

每个 POI 存 4 个坐标字段:

```json
{
  "lng_gcj02": 116.548094,
  "lat_gcj02": 40.084943,
  "lng_wgs84": 116.543300,
  "lat_wgs84": 40.083437,
  "coord_source": "original"  // 原始坐标来源
}
```

### coord_source 三档

| 值 | 含义 | 来源 |
|---|---|---|
| `original` | 原始博客自带的精确坐标 | 起点 / 已确认的景点,直接是 GCJ-02 |
| `known` | 公开资料里的常见坐标 | 知名景点(公主湖/将军泡子/达达线起点),用公开坐标 |
| `fallback` | city 中心 + 抖动 | 当地小店/餐厅/服务区等无精确坐标的地方 |

`known` 坐标建议精度 1-50m,`fallback` 精度约 5km(city 中心 + 0.05° 抖动)。

---

## 4. 渲染场景选坐标系

| 场景 | 用哪个 | 例子 |
|---|---|---|
| 高德直接 href 链接 | **GCJ-02** | `uri.amap.com/navigation?to={lng_gcj02},{lat_gcj02}` |
| KML 文件(给高德导入) | **GCJ-02** | `<coordinates>{lng_gcj02},{lat_gcj02},0</coordinates>` |
| Leaflet 底图(OSM 瓦片) | **WGS-84** | `L.marker([lat_wgs84, lng_wgs84])` |
| OSRM 路径规划请求 | **WGS-84** | `router.project-osrm.org/route/v1/driving/{lng_wgs84},{lat_wgs84};...` |
| OSRM 返回的 geometry | **WGS-84** | 直接画到 Leaflet 上 |

---

## 5. 校验方法

### 视觉检查
- 在 OSM 地图(用 WGS-84)上点一个 POI,目测位置是否在中国境内正确地点
- 在高德地图(用 GCJ-02)上点同一个 POI,两者应该都正确但**视觉上偏移 100-700m**
- 偏移方向不固定,GCJ-02 是非线性的,所以"两图都看"才能确认坐标没填错

### 数量级检查
- 中国境内:经度 73-135,纬度 3-54
- 内蒙草原:经度 115-120,纬度 41-46
- 北京:经度 ~116.4,纬度 ~39.9
- 超出这些范围 = 填错坐标系了

### 工具
- `https://epsg.io/transform` 在线转换工具
- QGIS / Google Earth Pro 看 KML 是否正确

---

## 6. 常见坑

| 坑 | 后果 | 解决 |
|---|---|---|
| 把 WGS-84 坐标当 GCJ-02 写进 KML | 高德地图里所有点都偏移到 100-700m 外 | 转换后存双坐标,渲染时按场景选 |
| 把 GCJ-02 坐标当 WGS-84 喂给 OSRM | OSRM 算出来的路径偏 100-700m,绕远路 | 严格按 4 区分场景 |
| 城市中心 + 抖动 fallback 没标注 | 用户不知道这个坐标不准 | 渲染时 fallback 半透明,长文里说"需核实" |
| 转换公式里没判 `out_of_china` | 国外坐标(日本/欧洲)被错误偏移 | 必须判断中国境内才转换 |
| 转换时浮点精度丢失 | 转换后坐标小数点后 4 位精度(11m)不够 | 保留 6 位小数(11cm) |
