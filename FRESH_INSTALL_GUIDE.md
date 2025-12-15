# راهنمای نصب مجدد کامل سرور

## ⚠️ هشدار:
این اسکریپت **همه چیز را پاک می‌کند** به جز:
- فایل‌های بک‌آپ (`/var/www/regions-map-app/backups/`)
- فایل‌های uploads (`/var/www/regions-map-app/uploads/`)

## مراحل:

### 1. آپدیت کد از GitHub:

```bash
cd /var/www/regions-map-app/regions-map-app
git pull origin main
```

### 2. دانلود اسکریپت:

```bash
cd /var/www/regions-map-app/regions-map-app
wget https://raw.githubusercontent.com/aghahri/Regions-map-app/main/fresh_install_server.sh
chmod +x fresh_install_server.sh
```

### 3. اجرای اسکریپت:

```bash
./fresh_install_server.sh
```

اسکریپت:
- ✅ فایل‌های بک‌آپ را در مسیر موقت کپی می‌کند
- ✅ همه چیز را پاک می‌کند
- ✅ از GitHub clone می‌کند
- ✅ Virtual environment می‌سازد
- ✅ Dependencies نصب می‌کند
- ✅ فایل‌های بک‌آپ را بازمی‌گرداند
- ✅ سرویس‌ها را راه‌اندازی می‌کند

## یا به صورت دستی:

### 1. توقف سرویس‌ها:

```bash
sudo systemctl stop regions-map-app
sudo systemctl stop nginx
```

### 2. کپی بک‌آپ‌ها:

```bash
# ساخت مسیر موقت
TEMP_BACKUP="/tmp/regions-map-backup-$(date +%Y%m%d_%H%M%S)"
mkdir -p "$TEMP_BACKUP"

# کپی بک‌آپ‌ها
cp -r /var/www/regions-map-app/backups "$TEMP_BACKUP/" 2>/dev/null || true
cp -r /var/www/regions-map-app/uploads "$TEMP_BACKUP/" 2>/dev/null || true
```

### 3. پاک کردن:

```bash
sudo rm -rf /var/www/regions-map-app
```

### 4. Clone از GitHub:

```bash
sudo mkdir -p /var/www/regions-map-app
sudo chown -R $USER:$USER /var/www/regions-map-app
cd /var/www/regions-map-app
git clone https://github.com/aghahri/Regions-map-app.git regions-map-app
cd regions-map-app
```

### 5. ساخت virtual environment:

```bash
python3 -m venv ../venv
source ../venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 6. بازگرداندن بک‌آپ‌ها:

```bash
# بازگرداندن backups
sudo mkdir -p /var/www/regions-map-app/backups
sudo cp -r "$TEMP_BACKUP/backups"/* /var/www/regions-map-app/backups/ 2>/dev/null || true

# بازگرداندن uploads
sudo mkdir -p /var/www/regions-map-app/uploads
sudo cp -r "$TEMP_BACKUP/uploads"/* /var/www/regions-map-app/uploads/ 2>/dev/null || true

# تنظیم دسترسی‌ها
sudo chown -R www-data:www-data /var/www/regions-map-app/uploads
sudo chmod -R 755 /var/www/regions-map-app/uploads
```

### 7. ساخت systemd service:

```bash
sudo tee /etc/systemd/system/regions-map-app.service > /dev/null <<EOF
[Unit]
Description=Regions Map App (Gunicorn)
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/regions-map-app/regions-map-app
Environment="PATH=/var/www/regions-map-app/venv/bin"
ExecStart=/var/www/regions-map-app/venv/bin/gunicorn --workers 2 --bind 127.0.0.1:8000 app:app

[Install]
WantedBy=multi-user.target
EOF
```

### 8. تنظیم nginx:

```bash
sudo tee /etc/nginx/sites-available/regions-map-app > /dev/null <<EOF
server {
    listen 80;
    server_name iranregions.com www.iranregions.com;

    client_max_body_size 200M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# فعال کردن config
sudo ln -sf /etc/nginx/sites-available/regions-map-app /etc/nginx/sites-enabled/regions-map-app

# غیرفعال کردن config‌های دیگر
sudo rm -f /etc/nginx/sites-enabled/00-default-ip 2>/dev/null || true
sudo rm -f /etc/nginx/sites-enabled/iranregions.com 2>/dev/null || true
```

### 9. تست و راه‌اندازی:

```bash
# تست nginx
sudo nginx -t

# تنظیم دسترسی‌ها
sudo chown -R www-data:www-data /var/www/regions-map-app/regions-map-app
sudo chmod -R 755 /var/www/regions-map-app/regions-map-app

# راه‌اندازی سرویس‌ها
sudo systemctl daemon-reload
sudo systemctl enable regions-map-app
sudo systemctl start regions-map-app
sudo systemctl restart nginx
```

### 10. تست:

```bash
# تست Flask
curl -I http://127.0.0.1:8000

# تست nginx
curl -I http://171.22.27.42

# بررسی وضعیت
sudo systemctl status regions-map-app
sudo systemctl status nginx
```

---

## فایل‌هایی که حفظ می‌شوند:

- ✅ `/var/www/regions-map-app/backups/` - همه بک‌آپ‌ها
- ✅ `/var/www/regions-map-app/uploads/` - همه uploads (logos, edits, links)

## فایل‌هایی که پاک می‌شوند:

- ❌ `/var/www/regions-map-app/regions-map-app/` - کد قدیمی
- ❌ `/var/www/regions-map-app/venv/` - virtual environment قدیمی
- ❌ تنظیمات systemd و nginx (بازسازی می‌شوند)

---

**موفق باشید! 🚀**

