# راهنمای Clone و نصب مجدد

## مشکل:
فولدر `regions-map-app` وجود ندارد

## راه‌حل:

### 1. Clone از GitHub:

```bash
cd /var/www/regions-map-app
git clone https://github.com/aghahri/Regions-map-app.git regions-map-app
cd regions-map-app
```

### 2. ساخت virtual environment:

```bash
cd /var/www/regions-map-app
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install flask gunicorn geopandas fiona shapely pyproj
```

### 3. بررسی وجود app.py:

```bash
ls -la /var/www/regions-map-app/regions-map-app/app.py
```

### 4. Restart service:

```bash
sudo systemctl daemon-reload
sudo systemctl restart regions-map-app
sudo systemctl status regions-map-app
```

---

## راه‌حل کامل (کپی-پیست):

```bash
# 1. ساخت دایرکتوری (اگر وجود ندارد)
sudo mkdir -p /var/www/regions-map-app
sudo chown -R $USER:$USER /var/www/regions-map-app

# 2. Clone از GitHub
cd /var/www/regions-map-app
git clone https://github.com/aghahri/Regions-map-app.git regions-map-app
cd regions-map-app

# 3. ساخت virtual environment
cd /var/www/regions-map-app
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install flask gunicorn geopandas fiona shapely pyproj

# 4. بررسی وجود app.py
ls -la /var/www/regions-map-app/regions-map-app/app.py

# 5. ساخت دایرکتوری‌های لازم
sudo mkdir -p /var/www/regions-map-app/uploads/uploads/regions/logos
sudo mkdir -p /var/www/regions-map-app/uploads/uploads/regions/neighborhood_edits
sudo mkdir -p /var/www/regions-map-app/backups

# 6. تنظیم دسترسی‌ها
sudo chown -R www-data:www-data /var/www/regions-map-app/regions-map-app
sudo chown -R www-data:www-data /var/www/regions-map-app/uploads
sudo chmod -R 755 /var/www/regions-map-app/regions-map-app
sudo chmod -R 755 /var/www/regions-map-app/uploads

# 7. Restart service
sudo systemctl daemon-reload
sudo systemctl restart regions-map-app
sudo systemctl status regions-map-app

# 8. تست
curl -I http://127.0.0.1:8000
```

---

**موفق باشید! 🚀**

