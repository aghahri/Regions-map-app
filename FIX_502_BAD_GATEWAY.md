# راهنمای حل مشکل 502 Bad Gateway

## مشکل:
502 Bad Gateway - nginx نمی‌تواند به Flask (gunicorn) متصل شود

## مراحل حل:

### 1. بررسی وضعیت Flask service:

```bash
# بررسی status
sudo systemctl status regions-map-app

# اگر stopped است، start کنید:
sudo systemctl start regions-map-app

# اگر failed است، لاگ‌ها را ببینید:
sudo journalctl -u regions-map-app -n 50
```

### 2. بررسی اینکه Flask روی پورت 8000 گوش می‌دهد:

```bash
# بررسی پورت 8000
sudo netstat -tlnp | grep 8000
# یا
sudo ss -tlnp | grep 8000

# تست مستقیم Flask
curl -I http://127.0.0.1:8000
```

**اگر پورت 8000 باز نیست:**
- Flask service در حال اجرا نیست
- به مرحله 3 بروید

### 3. بررسی لاگ‌های Flask:

```bash
# بررسی لاگ‌های Flask
sudo journalctl -u regions-map-app -n 100

# بررسی خطاها
sudo journalctl -u regions-map-app -n 100 | grep -i error
```

**خطاهای رایج:**
- `ModuleNotFoundError` - dependencies نصب نشده
- `Permission denied` - مشکل دسترسی
- `Address already in use` - پورت 8000 قبلاً استفاده شده

### 4. بررسی dependencies:

```bash
# بررسی virtual environment
cd /var/www/regions-map-app/regions-map-app
source ../venv/bin/activate

# بررسی نصب بودن dependencies
pip list | grep -E "(flask|gunicorn|geopandas)"

# اگر نصب نشده، نصب کنید:
pip install -r requirements.txt
```

### 5. بررسی دسترسی‌ها:

```bash
# بررسی دسترسی دایرکتوری
ls -la /var/www/regions-map-app/regions-map-app

# باید دسترسی read برای www-data داشته باشد
sudo chown -R www-data:www-data /var/www/regions-map-app/regions-map-app
sudo chmod -R 755 /var/www/regions-map-app/regions-map-app
```

### 6. بررسی systemd service:

```bash
# بررسی service file
sudo cat /etc/systemd/system/regions-map-app.service

# باید این شکلی باشد:
# [Unit]
# Description=Regions Map App (Gunicorn)
# After=network.target
#
# [Service]
# User=www-data
# Group=www-data
# WorkingDirectory=/var/www/regions-map-app/regions-map-app
# Environment="PATH=/var/www/regions-map-app/venv/bin"
# ExecStart=/var/www/regions-map-app/venv/bin/gunicorn --workers 2 --bind 127.0.0.1:8000 app:app
#
# [Install]
# WantedBy=multi-user.target
```

### 7. Restart سرویس‌ها:

```bash
# Reload systemd
sudo systemctl daemon-reload

# Restart Flask
sudo systemctl restart regions-map-app

# بررسی status
sudo systemctl status regions-map-app

# Restart nginx
sudo systemctl restart nginx
```

### 8. تست:

```bash
# تست Flask
curl -I http://127.0.0.1:8000

# تست nginx
curl -I http://171.22.27.42
```

---

## راه‌حل سریع:

```bash
# 1. بررسی status
sudo systemctl status regions-map-app

# 2. اگر stopped است:
sudo systemctl start regions-map-app

# 3. اگر failed است:
sudo journalctl -u regions-map-app -n 50

# 4. بررسی dependencies
cd /var/www/regions-map-app/regions-map-app
source ../venv/bin/activate
pip install -r requirements.txt

# 5. تنظیم دسترسی‌ها
sudo chown -R www-data:www-data /var/www/regions-map-app/regions-map-app
sudo chmod -R 755 /var/www/regions-map-app/regions-map-app

# 6. Restart
sudo systemctl daemon-reload
sudo systemctl restart regions-map-app
sudo systemctl restart nginx

# 7. تست
curl -I http://127.0.0.1:8000
```

---

## اگر هنوز کار نمی‌کند:

### بررسی لاگ‌های nginx:

```bash
# error log
sudo tail -f /var/log/nginx/error.log

# access log
sudo tail -f /var/log/nginx/access.log
```

### تست دستی Flask:

```bash
cd /var/www/regions-map-app/regions-map-app
source ../venv/bin/activate
gunicorn --workers 2 --bind 127.0.0.1:8000 app:app
```

**اگر این کار کرد:**
- مشکل از systemd service است
- service file را بررسی کنید

**اگر این هم کار نکرد:**
- مشکل از کد یا dependencies است
- لاگ‌های خطا را بررسی کنید

---

**موفق باشید! 🚀**

