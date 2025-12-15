# راهنمای حل مشکل Flask Service Failed

## مشکل:
- nginx کار می‌کند ✅
- Flask service failed ❌
- nginx 502 Bad Gateway می‌دهد

## مراحل حل:

### 1. بررسی لاگ‌های Flask:

```bash
sudo journalctl -u regions-map-app -n 50 --no-pager
```

**خطاهای رایج:**
- `ModuleNotFoundError: No module named 'app'` - مسیر اشتباه
- `ModuleNotFoundError: No module named 'xxx'` - dependencies نصب نشده

### 2. بررسی مسیر WorkingDirectory:

```bash
# بررسی service file
sudo cat /etc/systemd/system/regions-map-app.service | grep WorkingDirectory

# باید ببینید:
# WorkingDirectory=/var/www/regions-map-app/regions-map-app
```

### 3. بررسی وجود app.py:

```bash
ls -la /var/www/regions-map-app/regions-map-app/app.py
```

**اگر وجود ندارد:**
- باید از GitHub clone کنید

### 4. بررسی virtual environment:

```bash
# بررسی وجود venv
ls -la /var/www/regions-map-app/venv/bin/gunicorn

# بررسی نصب بودن dependencies
cd /var/www/regions-map-app/regions-map-app
source ../venv/bin/activate
pip list | grep -E "(flask|gunicorn|geopandas)"
```

### 5. تست دستی Flask:

```bash
cd /var/www/regions-map-app/regions-map-app
source ../venv/bin/activate

# تست import
python3 -c "import app; print('OK')"

# اگر OK بود، تست gunicorn
gunicorn --workers 2 --bind 127.0.0.1:8000 app:app
```

### 6. Restart service:

```bash
sudo systemctl daemon-reload
sudo systemctl restart regions-map-app
sudo systemctl status regions-map-app
```

---

## راه‌حل سریع:

```bash
# 1. بررسی لاگ‌ها
sudo journalctl -u regions-map-app -n 50 --no-pager

# 2. بررسی مسیر
ls -la /var/www/regions-map-app/regions-map-app/app.py

# 3. اگر وجود ندارد، clone کنید
cd /var/www/regions-map-app
rm -rf regions-map-app
git clone https://github.com/aghahri/Regions-map-app.git regions-map-app

# 4. بررسی dependencies
cd regions-map-app
source ../venv/bin/activate
pip install flask gunicorn geopandas fiona shapely pyproj

# 5. Restart
sudo systemctl daemon-reload
sudo systemctl restart regions-map-app
sudo systemctl status regions-map-app
```

---

**موفق باشید! 🚀**

