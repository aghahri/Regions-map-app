# راهنمای حفظ لینک‌های توت‌اپ بعد از آپدیت

## ✅ لینک‌ها حفظ می‌شوند!

لینک‌های توت‌اپ در فایل‌های JSON در مسیر زیر ذخیره می‌شوند:
```
uploads/regions/links/{map_id}.json
```

این فایل‌ها در `.gitignore` هستند و در git commit نمی‌شوند، بنابراین:
- ✅ با آپدیت کد، لینک‌ها از بین نمی‌روند
- ✅ لینک‌ها روی سرور باقی می‌مانند

## 🔒 اما برای اطمینان بیشتر:

### قبل از آپدیت روی سرور:

1. **بکاپ بگیرید:**
```bash
# روی سرور
cd /path/to/app
tar -czf links_backup_$(date +%Y%m%d).tar.gz uploads/regions/links/
```

2. **یا فایل‌های لینک را کپی کنید:**
```bash
# روی سرور
cp -r uploads/regions/links/ /backup/location/
```

### بعد از آپدیت:

1. **مطمئن شوید که فولدر `uploads/` حفظ شده است:**
```bash
# بررسی کنید که فولدر وجود دارد
ls -la uploads/regions/links/
```

2. **اگر فولدر وجود ندارد، از بکاپ restore کنید:**
```bash
tar -xzf links_backup_YYYYMMDD.tar.gz
```

## 📝 فایل‌های مهم که باید حفظ شوند:

- `uploads/regions/links/*.json` - لینک‌های توت‌اپ
- `uploads/regions/history.json` - تاریخچه نقشه‌ها
- `uploads/regions/storage/*.json` - داده‌های نقشه‌ها
- `uploads/regions/features/*.json` - داده‌های عوارض
- `uploads/regions/features_index.json` - فهرست عوارض
- `uploads/regions/users.json` - اطلاعات کاربران

## ⚠️ نکته مهم:

اگر از `git pull` یا `git clone` استفاده می‌کنید، مطمئن شوید که:
- فولدر `uploads/` روی سرور **حفظ شود**
- فولدر `uploads/` در `.gitignore` است و در git commit نمی‌شود
- بعد از آپدیت، فولدر `uploads/` باید همچنان وجود داشته باشد

## 🔍 بررسی لینک‌ها:

برای بررسی اینکه لینک‌ها حفظ شده‌اند:
```bash
# روی سرور
ls -la uploads/regions/links/
cat uploads/regions/links/{map_id}.json
```

