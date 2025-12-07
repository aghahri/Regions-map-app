# راهنمای Deploy روی Render.com

## تنظیمات Render

### 1. تنظیمات اصلی Service:

- **Name**: `regions-map-app`
- **Environment**: `Python 3`
- **Region**: انتخاب کنید
- **Branch**: `main`
- **Root Directory**: `regions-map-app` ⚠️ **مهم!**

### 2. Build & Deploy:

**Build Command:**
```bash
pip install --upgrade pip setuptools wheel && pip install -r requirements.txt
```

**Start Command:**
```bash
gunicorn --workers 2 --bind 0.0.0.0:$PORT app:app
```

### 3. Environment Variables:

```
SECRET_KEY=یک-رشته-تصادفی-قوی-حداقل-32-کاراکتر
ADMIN_PASSWORD=رمز-عبور-قوی-برای-ادمین
```

برای تولید SECRET_KEY:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## نکات مهم:

1. ✅ **Root Directory** باید `regions-map-app` باشد (نه خالی)
2. ✅ Build ممکن است 5-10 دقیقه طول بکشد (به خاطر GeoPandas)
3. ✅ بعد از deploy، URL را تست کنید

---

## تست بعد از Deploy:

1. صفحه اصلی: `https://your-app.onrender.com/`
2. Login: `https://your-app.onrender.com/admin/login`
3. API: `https://your-app.onrender.com/api/neighborhood?lat=35.6892&lon=51.3890`

---

## اگر Build خطا می‌دهد:

1. Build Logs را در Render بررسی کنید
2. مطمئن شوید Root Directory درست است
3. Build Command را کپی کنید و در terminal تست کنید


