# راهنمای دیباگ Connection Refused

## مشکل:
`curl: (7) Failed to connect to 127.0.0.1 port 8000 after 0 ms: Connection refused`

این یعنی Flask service در حال اجرا نیست یا روی پورت 8000 گوش نمی‌دهد.

## مراحل دیباگ:

### 1. بررسی وضعیت service:

```bash
sudo systemctl status regions-map-app
```

**اگر stopped است:**
```bash
sudo systemctl start regions-map-app
```

**اگر failed است:**
```bash
# بررسی لاگ‌ها
sudo journalctl -u regions-map-app -n 100
```

### 2. بررسی پورت 8000:

```bash
# بررسی اینکه آیا پورت 8000 باز است
sudo netstat -tlnp | grep 8000
# یا
sudo ss -tlnp | grep 8000
```

**اگر پورت باز نیست:**
- Service در حال اجرا نیست
- به مرحله 3 بروید

### 3. بررسی لاگ‌های service:

```bash
# بررسی لاگ‌های کامل
sudo journalctl -u regions-map-app -n 100 --no-pager

# بررسی خطاها
sudo journalctl -u regions-map-app -n 100 | grep -i error
```

**خطاهای رایج:**
- `ModuleNotFoundError` - dependencies نصب نشده
- `ImportError` - مشکل import
- `Permission denied` - مشکل دسترسی
- `Address already in use` - پورت قبلاً استفاده شده

### 4. تست دستی Flask:

```bash
cd /var/www/regions-map-app/regions-map-app
source ../venv/bin/activate

# تست import
python3 -c "import app; print('OK')"

# اگر OK بود، تست gunicorn
gunicorn --workers 2 --bind 127.0.0.1:8000 app:app
```

**اگر این کار کرد:**
- مشکل از systemd service است
- service file را بررسی کنید

**اگر این هم کار نکرد:**
- مشکل از کد یا dependencies است
- لاگ‌های خطا را بررسی کنید

### 5. بررسی service file:

```bash
sudo cat /etc/systemd/system/regions-map-app.service
```

**باید این شکلی باشد:**
```ini
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
```

### 6. بررسی دسترسی‌ها:

```bash
# بررسی دسترسی دایرکتوری
ls -la /var/www/regions-map-app/regions-map-app

# بررسی دسترسی app.py
ls -la /var/www/regions-map-app/regions-map-app/app.py

# تنظیم دسترسی‌ها (اگر لازم بود)
sudo chown -R www-data:www-data /var/www/regions-map-app/regions-map-app
sudo chmod -R 755 /var/www/regions-map-app/regions-map-app
```

### 7. بررسی dependencies:

```bash
cd /var/www/regions-map-app/regions-map-app
source ../venv/bin/activate

# بررسی نصب بودن dependencies
pip list | grep -E "(flask|gunicorn|geopandas)"

# اگر نصب نشده، نصب کنید:
pip install flask gunicorn geopandas fiona shapely pyproj
```

### 8. Restart service:

```bash
sudo systemctl daemon-reload
sudo systemctl restart regions-map-app
sudo systemctl status regions-map-app
```

---

## راه‌حل سریع:

```bash
# 1. بررسی status
sudo systemctl status regions-map-app

# 2. بررسی لاگ‌ها
sudo journalctl -u regions-map-app -n 100 --no-pager

# 3. تست دستی
cd /var/www/regions-map-app/regions-map-app
source ../venv/bin/activate
python3 -c "import app; print('OK')"
gunicorn --workers 2 --bind 127.0.0.1:8000 app:app

# 4. اگر کار کرد، restart service
sudo systemctl daemon-reload
sudo systemctl restart regions-map-app

# 5. تست
curl -I http://127.0.0.1:8000
```

---

**موفق باشید! 🚀**

