# راهنمای بک‌آپ همه فایل‌ها و پاک کردن کامل سرور

## ⚠️ هشدار:
این اسکریپت **همه فایل‌ها را بک‌آپ می‌گیرد** و سپس **همه چیز را پاک می‌کند**

## مراحل:

### 1. دانلود اسکریپت:

```bash
cd /var/www/regions-map-app/regions-map-app
wget https://raw.githubusercontent.com/aghahri/Regions-map-app/main/backup_and_clean_all.sh
chmod +x backup_and_clean_all.sh
```

### 2. اجرای اسکریپت:

```bash
./backup_and_clean_all.sh
```

اسکریپت:
- ✅ همه فایل‌ها را در `/root/regions-map-backup-[timestamp]/` بک‌آپ می‌گیرد
- ✅ شامل:
  - کل دایرکتوری `/var/www/regions-map-app`
  - systemd service
  - nginx configs
- ✅ سپس همه چیز را پاک می‌کند (با تایید شما)

---

## فایل‌هایی که بک‌آپ می‌شوند:

- ✅ کل دایرکتوری `/var/www/regions-map-app/`
  - کد (`regions-map-app/`)
  - virtual environment (`venv/`)
  - uploads (`uploads/`)
  - backups (`backups/`)
- ✅ systemd service (`/etc/systemd/system/regions-map-app.service`)
- ✅ nginx configs (`/etc/nginx/sites-available/regions-map-app`)
- ✅ nginx enabled configs (`/etc/nginx/sites-enabled/`)

---

## بازگرداندن بک‌آپ:

```bash
# بازگرداندن دایرکتوری اصلی
sudo cp -r /root/regions-map-backup-[timestamp]/regions-map-app /var/www/

# بازگرداندن systemd service
sudo cp /root/regions-map-backup-[timestamp]/regions-map-app.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable regions-map-app
sudo systemctl start regions-map-app

# بازگرداندن nginx config
sudo cp /root/regions-map-backup-[timestamp]/regions-map-app /etc/nginx/sites-available/
sudo ln -sf /etc/nginx/sites-available/regions-map-app /etc/nginx/sites-enabled/regions-map-app
sudo nginx -t
sudo systemctl restart nginx

# تنظیم دسترسی‌ها
sudo chown -R www-data:www-data /var/www/regions-map-app/regions-map-app
sudo chown -R www-data:www-data /var/www/regions-map-app/uploads
sudo chmod -R 755 /var/www/regions-map-app/regions-map-app
sudo chmod -R 755 /var/www/regions-map-app/uploads
```

---

## یا به صورت دستی:

### 1. توقف سرویس‌ها:

```bash
sudo systemctl stop regions-map-app
sudo systemctl stop nginx
```

### 2. ساخت مسیر بک‌آپ:

```bash
BACKUP_ROOT="/root/regions-map-backup-$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_ROOT"
```

### 3. بک‌آپ همه فایل‌ها:

```bash
# بک‌آپ کل دایرکتوری
sudo cp -r /var/www/regions-map-app "$BACKUP_ROOT/"

# بک‌آپ systemd service
sudo cp /etc/systemd/system/regions-map-app.service "$BACKUP_ROOT/"

# بک‌آپ nginx config
sudo cp /etc/nginx/sites-available/regions-map-app "$BACKUP_ROOT/"

# تنظیم دسترسی‌ها
sudo chown -R $USER:$USER "$BACKUP_ROOT"
```

### 4. پاک کردن:

```bash
sudo rm -rf /var/www/regions-map-app
sudo systemctl disable regions-map-app
```

---

**موفق باشید! 🚀**

