# راهنمای پاک کردن کامل سرور (به جز آخرین بک‌آپ)

## ⚠️ هشدار:
این اسکریپت **همه چیز را پاک می‌کند** به جز:
- آخرین فایل بک‌آپ
- فایل‌های uploads (logos, edits, links)

## مراحل:

### 1. دانلود اسکریپت:

```bash
cd /var/www/regions-map-app/regions-map-app
wget https://raw.githubusercontent.com/aghahri/Regions-map-app/main/clean_server_keep_last_backup.sh
chmod +x clean_server_keep_last_backup.sh
```

### 2. اجرای اسکریپت:

```bash
./clean_server_keep_last_backup.sh
```

اسکریپت:
- ✅ آخرین فایل بک‌آپ را پیدا می‌کند
- ✅ فایل‌های uploads را کپی می‌کند
- ✅ همه چیز را پاک می‌کند
- ✅ آخرین بک‌آپ را بازمی‌گرداند
- ✅ uploads را بازمی‌گرداند

## یا به صورت دستی:

### 1. توقف سرویس‌ها:

```bash
sudo systemctl stop regions-map-app
sudo systemctl stop nginx
```

### 2. پیدا کردن آخرین بک‌آپ:

```bash
# پیدا کردن آخرین فایل بک‌آپ
LAST_BACKUP=$(find /var/www/regions-map-app/backups -type f -name "*.zip" -o -name "*.tar.gz" -o -name "*.tar" | sort -r | head -1)
echo "آخرین بک‌آپ: $LAST_BACKUP"
```

### 3. کپی بک‌آپ و uploads:

```bash
# ساخت مسیر موقت
TEMP_BACKUP="/tmp/regions-map-last-backup-$(date +%Y%m%d_%H%M%S)"
mkdir -p "$TEMP_BACKUP"

# کپی آخرین بک‌آپ
if [ -n "$LAST_BACKUP" ]; then
    cp "$LAST_BACKUP" "$TEMP_BACKUP/last_backup$(basename "$LAST_BACKUP")"
fi

# کپی uploads
cp -r /var/www/regions-map-app/uploads "$TEMP_BACKUP/" 2>/dev/null || true
```

### 4. پاک کردن:

```bash
sudo rm -rf /var/www/regions-map-app
```

### 5. ساخت دایرکتوری جدید:

```bash
sudo mkdir -p /var/www/regions-map-app
sudo chown -R $USER:$USER /var/www/regions-map-app
```

### 6. بازگرداندن بک‌آپ و uploads:

```bash
# بازگرداندن آخرین بک‌آپ
sudo mkdir -p /var/www/regions-map-app/backups
sudo cp "$TEMP_BACKUP"/last_backup* /var/www/regions-map-app/backups/

# بازگرداندن uploads
sudo mkdir -p /var/www/regions-map-app/uploads
sudo cp -r "$TEMP_BACKUP/uploads"/* /var/www/regions-map-app/uploads/ 2>/dev/null || true

# تنظیم دسترسی‌ها
sudo chown -R www-data:www-data /var/www/regions-map-app/uploads
sudo chmod -R 755 /var/www/regions-map-app/uploads
```

---

## فایل‌هایی که حفظ می‌شوند:

- ✅ آخرین فایل بک‌آپ در `/var/www/regions-map-app/backups/`
- ✅ فایل‌های uploads در `/var/www/regions-map-app/uploads/`

## فایل‌هایی که پاک می‌شوند:

- ❌ `/var/www/regions-map-app/regions-map-app/` - کد
- ❌ `/var/www/regions-map-app/venv/` - virtual environment
- ❌ همه بک‌آپ‌های قدیمی (به جز آخرین)
- ❌ تنظیمات systemd و nginx

---

**موفق باشید! 🚀**

