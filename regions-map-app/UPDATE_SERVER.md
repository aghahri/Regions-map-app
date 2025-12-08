# راهنمای آپدیت سرور از GitHub

## ⚠️ مهم: قبل از آپدیت

لینک‌های توت‌اپ در فولدر `uploads/regions/links/` ذخیره می‌شوند که در `.gitignore` است و در git commit نمی‌شود. بنابراین با آپدیت کد، لینک‌ها حفظ می‌شوند.

## 📋 دستورات آپدیت روی سرور

### روش 1: اگر از git pull استفاده می‌کنید

```bash
# 1. وارد دایرکتوری برنامه شوید
cd /path/to/regions-map-app

# 2. بکاپ از لینک‌ها (برای اطمینان)
tar -czf links_backup_$(date +%Y%m%d_%H%M%S).tar.gz uploads/regions/links/

# 3. بررسی وضعیت git
git status

# 4. دریافت آخرین تغییرات از GitHub
git fetch origin

# 5. آپدیت کد (بدون overwrite کردن فایل‌های local)
git pull origin main

# 6. بررسی اینکه فولدر uploads حفظ شده است
ls -la uploads/regions/links/

# 7. اگر از virtual environment استفاده می‌کنید، dependencies را آپدیت کنید
source venv/bin/activate
pip install -r requirements.txt

# 8. restart کردن سرویس (بسته به نوع deployment)
# برای systemd:
sudo systemctl restart your-app-service

# یا برای gunicorn:
pkill -f gunicorn
gunicorn app:app --bind 0.0.0.0:5003
```

### روش 2: اگر از git clone استفاده می‌کنید (اولین بار)

```bash
# 1. بکاپ از دایرکتوری قدیمی
cd /path/to
mv regions-map-app regions-map-app-backup

# 2. clone کردن آخرین نسخه
git clone https://github.com/aghahri/Regions-map-app.git regions-map-app

# 3. کپی کردن فولدر uploads از بکاپ
cp -r regions-map-app-backup/uploads regions-map-app/

# 4. کپی کردن فایل‌های مهم دیگر
cp regions-map-app-backup/.env regions-map-app/ 2>/dev/null || true
cp regions-map-app-backup/venv regions-map-app/ -r 2>/dev/null || true

# 5. وارد دایرکتوری جدید
cd regions-map-app

# 6. فعال کردن virtual environment
source venv/bin/activate

# 7. نصب dependencies
pip install -r requirements.txt

# 8. بررسی لینک‌ها
ls -la uploads/regions/links/

# 9. restart کردن سرویس
```

### روش 3: آپدیت امن با حفظ همه داده‌ها

```bash
#!/bin/bash
# اسکریپت آپدیت امن

APP_DIR="/path/to/regions-map-app"
BACKUP_DIR="/backup/regions-map-app"

# 1. ایجاد بکاپ کامل
echo "Creating backup..."
mkdir -p $BACKUP_DIR
tar -czf $BACKUP_DIR/backup_$(date +%Y%m%d_%H%M%S).tar.gz -C $APP_DIR \
    uploads/ \
    .env \
    venv/ 2>/dev/null || true

# 2. وارد دایرکتوری
cd $APP_DIR

# 3. بکاپ از لینک‌ها
echo "Backing up links..."
cp -r uploads/regions/links/ $BACKUP_DIR/links_backup_$(date +%Y%m%d_%H%M%S)/

# 4. آپدیت از git
echo "Updating from GitHub..."
git fetch origin
git pull origin main

# 5. بررسی حفظ شدن uploads
if [ ! -d "uploads/regions/links" ]; then
    echo "ERROR: uploads folder missing! Restoring from backup..."
    tar -xzf $BACKUP_DIR/backup_*.tar.gz
fi

# 6. بررسی لینک‌ها
echo "Checking links..."
ls -la uploads/regions/links/

# 7. آپدیت dependencies
echo "Updating dependencies..."
source venv/bin/activate
pip install -r requirements.txt --upgrade

# 8. Restart سرویس
echo "Restarting service..."
sudo systemctl restart your-app-service

echo "Update completed!"
```

## 🔍 بررسی بعد از آپدیت

```bash
# بررسی لینک‌ها
ls -la uploads/regions/links/
cat uploads/regions/links/{map_id}.json

# بررسی تاریخچه نقشه‌ها
cat uploads/regions/history.json

# بررسی عوارض
ls -la uploads/regions/features/
cat uploads/regions/features_index.json

# تست API
curl http://localhost:5003/api/features/list?map_id=YOUR_MAP_ID
```

## ⚠️ نکات مهم:

1. **فولدر `uploads/` در `.gitignore` است** - پس با `git pull` از بین نمی‌رود
2. **همیشه قبل از آپدیت بکاپ بگیرید** - برای اطمینان بیشتر
3. **بعد از آپدیت، فولدر `uploads/` را بررسی کنید** - مطمئن شوید که وجود دارد
4. **اگر از `git reset --hard` استفاده می‌کنید** - مراقب باشید! این دستور فایل‌های untracked را حذف نمی‌کند اما بهتر است از آن استفاده نکنید

## 🚨 اگر لینک‌ها از بین رفتند:

```bash
# Restore از بکاپ
cd /path/to/regions-map-app
tar -xzf /backup/location/links_backup_YYYYMMDD_HHMMSS.tar.gz
```

## 📝 دستورات سریع (Copy-Paste):

```bash
# آپدیت ساده
cd /path/to/regions-map-app
git fetch origin
git pull origin main
ls -la uploads/regions/links/  # بررسی لینک‌ها
sudo systemctl restart your-app-service
```

