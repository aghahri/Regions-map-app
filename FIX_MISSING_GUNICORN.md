# راهنمای حل مشکل Missing Gunicorn

## مشکل:
- `gunicorn` پیدا نمی‌شود: `Failed to locate executable /var/www/regions-map-app/venv/bin/gunicorn`
- `requirements.txt` پیدا نمی‌شود

## راه‌حل:

### 1. بررسی virtual environment:

```bash
# بررسی وجود virtual environment
ls -la /var/www/regions-map-app/venv

# اگر وجود ندارد، بسازید:
cd /var/www/regions-map-app
python3 -m venv venv
```

### 2. بررسی requirements.txt:

```bash
# بررسی وجود requirements.txt
ls -la /var/www/regions-map-app/regions-map-app/requirements.txt

# اگر وجود ندارد، بسازید یا از GitHub بگیرید:
cd /var/www/regions-map-app/regions-map-app
git pull origin main
```

### 3. ساخت virtual environment (اگر وجود ندارد):

```bash
cd /var/www/regions-map-app
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
```

### 4. نصب dependencies:

```bash
cd /var/www/regions-map-app/regions-map-app
source ../venv/bin/activate

# نصب dependencies
pip install flask gunicorn geopandas fiona shapely pyproj
# یا اگر requirements.txt وجود دارد:
pip install -r requirements.txt
```

### 5. بررسی نصب gunicorn:

```bash
# بررسی نصب gunicorn
source /var/www/regions-map-app/venv/bin/activate
which gunicorn
# باید: /var/www/regions-map-app/venv/bin/gunicorn

# تست gunicorn
gunicorn --version
```

### 6. تنظیم دسترسی‌ها:

```bash
sudo chown -R www-data:www-data /var/www/regions-map-app/venv
sudo chown -R www-data:www-data /var/www/regions-map-app/regions-map-app
sudo chmod -R 755 /var/www/regions-map-app/venv
sudo chmod -R 755 /var/www/regions-map-app/regions-map-app
```

### 7. Restart service:

```bash
sudo systemctl daemon-reload
sudo systemctl restart regions-map-app
sudo systemctl status regions-map-app
```

### 8. تست:

```bash
# تست Flask
curl -I http://127.0.0.1:8000
```

---

## راه‌حل کامل (کپی-پیست):

```bash
# 1. بررسی و ساخت virtual environment
cd /var/www/regions-map-app
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# 2. فعال کردن و نصب dependencies
source venv/bin/activate
pip install --upgrade pip
pip install flask gunicorn geopandas fiona shapely pyproj

# 3. بررسی نصب gunicorn
which gunicorn
gunicorn --version

# 4. تنظیم دسترسی‌ها
sudo chown -R www-data:www-data /var/www/regions-map-app/venv
sudo chown -R www-data:www-data /var/www/regions-map-app/regions-map-app
sudo chmod -R 755 /var/www/regions-map-app/venv
sudo chmod -R 755 /var/www/regions-map-app/regions-map-app

# 5. Restart service
sudo systemctl daemon-reload
sudo systemctl restart regions-map-app
sudo systemctl status regions-map-app

# 6. تست
curl -I http://127.0.0.1:8000
```

---

**موفق باشید! 🚀**

