# راهنمای کامل Setup در Render

## تنظیمات Render.com

### 1. تنظیمات اصلی:

- **Name**: `regions-map-app`
- **Environment**: `Python 3`
- **Region**: انتخاب کنید (مثلاً Frankfurt یا Oregon)
- **Branch**: `main`

### 2. Build & Deploy:

**Build Command:**
```bash
pip install --upgrade pip setuptools wheel && pip install -r requirements.txt
```

**Start Command:**
```bash
gunicorn --workers 2 --bind 0.0.0.0:$PORT app:app
```

**Root Directory:** (اگر پروژه در subdirectory است)
```
regions-map-app
```

### 3. Environment Variables:

```
SECRET_KEY=یک-رشته-تصادفی-قوی-طولانی-حداقل-32-کاراکتر
ADMIN_PASSWORD=رمز-عبور-قوی-برای-ادمین
```

برای تولید SECRET_KEY:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 4. Advanced Settings:

- **Auto-Deploy**: `Yes` (برای auto-deploy از GitHub)
- **Health Check Path**: `/` (اختیاری)

---

## اگر Build خطا می‌دهد:

### راه حل 1: Build Command را تغییر دهید

```bash
pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt
```

### راه حل 2: Root Directory را تنظیم کنید

اگر فایل‌ها در `regions-map-app/` هستند:
- **Root Directory**: `regions-map-app`

### راه حل 3: بررسی Logs

در داشبورد Render → Logs → Build Logs را بررسی کنید

خطاهای رایج:
- `ModuleNotFoundError`: dependency نصب نشده
- `Command failed`: Build command اشتباه است
- `Port already in use`: مشکل از Start Command

---

## نکات مهم:

1. ✅ GeoPandas نصب آن ممکن است 5-10 دقیقه طول بکشد
2. ✅ مطمئن شوید که `SECRET_KEY` و `ADMIN_PASSWORD` تنظیم شده‌اند
3. ✅ اگر مشکل از GeoPandas است، می‌توانید نسخه خاصی استفاده کنید:
   ```
   geopandas==0.14.1
   ```

---

## تست بعد از Deploy:

1. به URL Render بروید
2. باید صفحه اصلی را ببینید
3. `/admin/login` را تست کنید
4. `/api/neighborhood?lat=35.6892&lon=51.3890` را تست کنید

---

## اگر هنوز مشکل دارید:

1. Logs را در Render بررسی کنید
2. Build Logs را کامل بخوانید
3. خطای دقیق را پیدا کنید
4. اگر نیاز است، dependency مشکل‌ساز را حذف یا تغییر دهید


