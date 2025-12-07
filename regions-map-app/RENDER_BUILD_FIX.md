# رفع مشکل Build در Render

## مشکل: Build با خطا مواجه می‌شود

اگر در Render خطای build می‌گیرید، این راه‌حل‌ها را امتحان کنید:

---

## راه حل 1: بررسی Build Command

در تنظیمات Render، Build Command را به این تغییر دهید:

```bash
pip install --upgrade pip && pip install -r requirements.txt
```

---

## راه حل 2: بررسی Root Directory

اگر پروژه در subdirectory `regions-map-app` است:

1. در تنظیمات Render
2. بخش **Root Directory** را پیدا کنید
3. مقدار را به `regions-map-app` تنظیم کنید

یا Build Command را تغییر دهید:

```bash
cd regions-map-app && pip install --upgrade pip && pip install -r requirements.txt
```

و Start Command:

```bash
cd regions-map-app && gunicorn --workers 2 --bind 0.0.0.0:$PORT app:app
```

---

## راه حل 3: بررسی Environment Variables

مطمئن شوید که این متغیرها تنظیم شده‌اند:

```
SECRET_KEY=یک-رشته-تصادفی-قوی
ADMIN_PASSWORD=رمز-عبور-قوی
```

---

## راه حل 4: بررسی Logs

در داشبورد Render:
1. به بخش **Logs** بروید
2. خطاهای دقیق را بررسی کنید
3. معمولاً خطا مربوط به نصب GeoPandas یا dependencies آن است

---

## راه حل 5: استفاده از Python Version خاص

اگر نیاز است، یک `runtime.txt` در `regions-map-app/` بسازید:

```
python-3.11.0
```

---

## نکات مهم:

1. ✅ GeoPandas نیاز به dependencies زیادی دارد - ممکن است build طول بکشد
2. ✅ مطمئن شوید که `requirements.txt` شامل `shapely` و `pyproj` است
3. ✅ اگر مشکل از GeoPandas است، می‌توانید از نسخه‌های قدیمی‌تر استفاده کنید

---

## اگر هنوز مشکل دارید:

Build Command را به این تغییر دهید:

```bash
pip install --upgrade pip setuptools wheel && pip install -r requirements.txt
```

یا برای GeoPandas:

```bash
pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt
```


