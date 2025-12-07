# راهنمای تست API روی کامپیوتر محلی

## 1. فعال کردن Virtual Environment

```bash
cd /Users/akiokaviano/ai/code/regions-map-app
source venv/bin/activate
```

## 2. اجرای برنامه

```bash
python app.py
```

یا:

```bash
flask run --host=0.0.0.0 --port=5003
```

برنامه روی آدرس `http://localhost:5003` اجرا می‌شود.

## 3. تست API با curl

### تست API دریافت عوارض بر اساس موقعیت:

```bash
# GET request
curl "http://localhost:5003/api/features/by-location?neighborhood=نام_محله&city=نام_شهر&district=نام_منطقه"

# POST request
curl -X POST http://localhost:5003/api/features/by-location \
  -H "Content-Type: application/json" \
  -d '{
    "neighborhood": "نام محله",
    "city": "نام شهر",
    "district": "نام منطقه"
  }'
```

### مثال واقعی:

```bash
# اگر شهر شما "تهران" است و محله "ونک"
curl "http://localhost:5003/api/features/by-location?neighborhood=ونک&city=تهران"
```

## 4. تست API با مرورگر

می‌توانید مستقیماً در مرورگر باز کنید:

```
http://localhost:5003/api/features/by-location?neighborhood=نام_محله&city=نام_شهر
```

## 5. تست API با Python

```python
import requests

# GET request
response = requests.get(
    "http://localhost:5003/api/features/by-location",
    params={
        "neighborhood": "نام محله",
        "city": "نام شهر",
        "district": "نام منطقه"  # اختیاری
    }
)
print(response.json())

# POST request
response = requests.post(
    "http://localhost:5003/api/features/by-location",
    json={
        "neighborhood": "نام محله",
        "city": "نام شهر",
        "district": "نام منطقه"
    }
)
print(response.json())
```

## 6. تست API با Postman

1. روش: `GET` یا `POST`
2. URL: `http://localhost:5003/api/features/by-location`
3. برای GET: پارامترها را در Query Params اضافه کنید
4. برای POST: در Body > raw > JSON اضافه کنید:
```json
{
  "neighborhood": "نام محله",
  "city": "نام شهر",
  "district": "نام منطقه"
}
```

## 7. سایر API های موجود

### لیست عوارض یک نقشه:
```
GET http://localhost:5003/api/features/list?map_id=شناسه_نقشه
```

### دریافت یک عارضه:
```
GET http://localhost:5003/api/features/شناسه_عارضه
```

### دریافت محله بر اساس مختصات:
```
GET http://localhost:5003/api/neighborhood?lat=35.6892&lon=51.3890
```

## نکات مهم:

- مطمئن شوید که virtual environment فعال است
- مطمئن شوید که پورت 5003 آزاد است
- اگر خطا داد، لاگ‌های console را بررسی کنید
- برای دیدن تمام لاگ‌ها، برنامه را با `debug=True` اجرا کنید

