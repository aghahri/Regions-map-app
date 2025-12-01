# راهنمای Deploy

## Deploy روی Render.com

### قدم 1: آماده‌سازی

1. مطمئن شوید که همه فایل‌ها commit شده‌اند:
```bash
git add .
git commit -m "Ready for deploy"
git push
```

### قدم 2: ایجاد Web Service در Render

1. به [render.com](https://render.com) بروید و ثبت‌نام کنید
2. "New +" → "Web Service" را انتخاب کنید
3. Repository خود را Connect کنید
4. تنظیمات:
   - **Name**: `regions-map-app`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn --workers 2 --bind 0.0.0.0:$PORT app:app`

### قدم 3: Environment Variables

در بخش "Environment Variables" این متغیرها را اضافه کنید:

```
SECRET_KEY=یک-رشته-تصادفی-قوی-طولانی
ADMIN_PASSWORD=رمز-عبور-قوی-برای-ادمین
```

برای تولید SECRET_KEY:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### قدم 4: Deploy

روی "Create Web Service" کلیک کنید و منتظر بمانید.

---

## Deploy روی Railway.app

1. به [railway.app](https://railway.app) بروید
2. "New Project" → "Deploy from GitHub repo"
3. Repository را انتخاب کنید
4. Environment Variables را تنظیم کنید
5. Railway به صورت خودکار deploy می‌کند

---

## نکات مهم

- ✅ حتماً `SECRET_KEY` و `ADMIN_PASSWORD` را در Environment Variables تنظیم کنید
- ✅ در Production از رمز عبور قوی استفاده کنید
- ✅ پوشه `uploads/` در Render/Railway محدودیت دارد - برای Production بهتر است از Cloud Storage استفاده کنید

