# راهنمای حل مشکل Missing app.py

## مشکل:
- `ModuleNotFoundError: No module named 'app'`
- `app.py` پیدا نمی‌شود
- دایرکتوری git repository نیست

## راه‌حل:

### 1. بررسی ساختار دایرکتوری:

```bash
# بررسی اینکه آیا دایرکتوری وجود دارد
ls -la /var/www/regions-map-app/regions-map-app/

# بررسی محتوا
ls -la /var/www/regions-map-app/regions-map-app/*.py
```

### 2. اگر دایرکتوری خالی است یا git repository نیست:

```bash
# حذف و clone مجدد
cd /var/www/regions-map-app
rm -rf regions-map-app
git clone https://github.com/aghahri/Regions-map-app.git regions-map-app
cd regions-map-app
ls -la app.py
```

### 3. اگر دایرکتوری وجود دارد اما app.py نیست:

```bash
cd /var/www/regions-map-app/regions-map-app
git init
git remote add origin https://github.com/aghahri/Regions-map-app.git
git pull origin main
ls -la app.py
```

### 4. Restart service:

```bash
sudo systemctl daemon-reload
sudo systemctl restart regions-map-app
sudo systemctl status regions-map-app
```

---

## راه‌حل سریع (کپی-پیست):

```bash
# 1. بررسی ساختار
ls -la /var/www/regions-map-app/regions-map-app/

# 2. حذف و clone مجدد
cd /var/www/regions-map-app
rm -rf regions-map-app
git clone https://github.com/aghahri/Regions-map-app.git regions-map-app
cd regions-map-app

# 3. بررسی وجود app.py
ls -la app.py

# 4. Restart
sudo systemctl daemon-reload
sudo systemctl restart regions-map-app
sudo systemctl status regions-map-app

# 5. تست
curl -I http://127.0.0.1:8000
```

---

**موفق باشید! 🚀**

