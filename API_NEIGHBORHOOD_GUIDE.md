# راهنمای تست API دریافت نام محله از مختصات

## Endpoint

```
GET/POST /api/neighborhood
```

---

## روش 1: استفاده از GET (Query Parameters)

### تنظیمات در Postman:

1. **Method**: `GET`
2. **URL**: 
   ```
   http://171.22.27.42/api/neighborhood?lat=35.6892&lon=51.3890
   ```
   یا با map_id:
   ```
   http://171.22.27.42/api/neighborhood?lat=35.6892&lon=51.3890&map_id=20241128_120000_123456
   ```

3. **Params** (در Postman):
   - `lat`: `35.6892` (عرض جغرافیایی)
   - `lon`: `51.3890` (طول جغرافیایی)
   - `map_id`: (اختیاری) شناسه نقشه خاص

### مثال کامل:
```
GET http://171.22.27.42/api/neighborhood?lat=35.6892&lon=51.3890
```

---

## روش 2: استفاده از POST (JSON Body)

### تنظیمات در Postman:

1. **Method**: `POST`
2. **URL**: 
   ```
   http://171.22.27.42/api/neighborhood
   ```

3. **Headers**:
   ```
   Content-Type: application/json
   ```

4. **Body** (raw - JSON):
   ```json
   {
     "lat": 35.6892,
     "lon": 51.3890
   }
   ```
   
   یا با map_id:
   ```json
   {
     "lat": 35.6892,
     "lon": 51.3890,
     "map_id": "20241128_120000_123456"
   }
   ```

---

## روش 3: استفاده از POST (Form Data)

### تنظیمات در Postman:

1. **Method**: `POST`
2. **URL**: 
   ```
   http://171.22.27.42/api/neighborhood
   ```

3. **Body** (x-www-form-urlencoded):
   | Key | Value |
   |-----|-------|
   | `lat` | `35.6892` |
   | `lon` | `51.3890` |
   | `map_id` | (اختیاری) `20241128_120000_123456` |

---

## Response موفق (200 OK):

```json
{
  "success": true,
  "neighborhood": "داوودیه",
  "district": "3",
  "city": "تهران",
  "map_id": "20241128_120000_123456",
  "map_name": "نقشه تهران",
  "tootapp_url": "https://tootapp.ir/join/Tehran3Da",
  "coordinates": {
    "lat": 35.6892,
    "lon": 51.3890
  }
}
```

---

## Response خطا - محله پیدا نشد (404):

```json
{
  "success": false,
  "error": "محله‌ای برای این مختصات پیدا نشد",
  "coordinates": {
    "lat": 35.6892,
    "lon": 51.3890
  }
}
```

---

## Response خطا - پارامترهای نامعتبر (400):

```json
{
  "success": false,
  "error": "پارامترهای lat و lon الزامی هستند"
}
```

یا:

```json
{
  "success": false,
  "error": "lat و lon باید عدد باشند"
}
```

---

## Response خطا - خطای سرور (500):

```json
{
  "success": false,
  "error": "خطا در پردازش درخواست: ..."
}
```

---

## مثال‌های مختصات:

### تهران - میدان آزادی:
```
lat: 35.6997
lon: 51.3381
```

### تهران - میدان ولیعصر:
```
lat: 35.7614
lon: 51.4113
```

### تهران - داوودیه:
```
lat: 35.6892
lon: 51.3890
```

---

## نکات مهم:

1. **ترتیب مختصات**: 
   - `lat` = عرض جغرافیایی (latitude)
   - `lon` = طول جغرافیایی (longitude)
   - در GeoJSON از `[lon, lat]` استفاده می‌شود

2. **map_id اختیاری است**:
   - اگر `map_id` ندهید، در همه نقشه‌های آپلود شده جستجو می‌کند
   - اگر `map_id` بدهید، فقط در آن نقشه خاص جستجو می‌کند

3. **نام‌های جایگزین پارامترها**:
   - `lat` یا `latitude`
   - `lon` یا `longitude` یا `lng`

4. **اولین محله پیدا شده**:
   - اگر چند محله شامل این نقطه باشند، اولین محله برگردانده می‌شود

---

## تست سریع با curl:

```bash
# GET
curl "http://171.22.27.42/api/neighborhood?lat=35.6892&lon=51.3890"

# POST JSON
curl -X POST http://171.22.27.42/api/neighborhood \
  -H "Content-Type: application/json" \
  -d '{"lat": 35.6892, "lon": 51.3890}'

# POST Form
curl -X POST http://171.22.27.42/api/neighborhood \
  -d "lat=35.6892&lon=51.3890"
```

---

## تصویر راهنما در Postman (GET):

```
┌─────────────────────────────────────────────────────┐
│ [GET ▼] http://171.22.27.42/api/neighborhood        │ [Send]
├─────────────────────────────────────────────────────┤
│ Params ● Query Params                               │
│                                                      │
│ Key          │ Value        │ Description           │
│ lat          │ 35.6892      │                      │
│ lon          │ 51.3890      │                      │
│ map_id       │ (optional)   │                      │
└─────────────────────────────────────────────────────┘
```

---

## تصویر راهنما در Postman (POST JSON):

```
┌─────────────────────────────────────────────────────┐
│ [POST ▼] http://171.22.27.42/api/neighborhood       │ [Send]
├─────────────────────────────────────────────────────┤
│ Headers                                              │
│ Content-Type: application/json                      │
├─────────────────────────────────────────────────────┤
│ Body ● raw ▼ JSON                                    │
│                                                      │
│ {                                                    │
│   "lat": 35.6892,                                    │
│   "lon": 51.3890                                     │
│ }                                                    │
└─────────────────────────────────────────────────────┘
```

