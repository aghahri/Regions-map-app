# راهنمای دیباگ Flask که گوش نمی‌دهد

## مشکل:
- Flask service active (running) است ✅
- اما curl به 127.0.0.1:8000 connection refused می‌دهد ❌
- nginx 502 Bad Gateway می‌دهد ❌

## مراحل دیباگ:

### 1. بررسی لاگ‌های Flask:

```bash
sudo journalctl -u regions-map-app -n 50 --no-pager
```

**خطاهای رایج:**
- `ModuleNotFoundError: No module named 'app'` - مسیر اشتباه
- `Address already in use` - پورت قبلاً استفاده شده

### 2. بررسی پورت 8000:

```bash
# بررسی اینکه آیا پورت 8000 باز است
sudo ss -tlnp | grep 8000
# یا
sudo netstat -tlnp | grep 8000
```

**اگر پورت باز نیست:**
- Flask در حال اجرا نیست یا crash کرده

### 3. بررسی وجود app.py:

```bash
ls -la /var/www/regions-map-app/regions-map-app/app.py
```

**اگر وجود ندارد:**
- باید از GitHub pull کنید

### 4. بررسی مسیر WorkingDirectory:

```bash
sudo cat /etc/systemd/system/regions-map-app.service | grep WorkingDirectory
```

**باید ببینید:**
```
WorkingDirectory=/var/www/regions-map-app/regions-map-app
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

---

## راه‌حل سریع:

```bash
# 1. بررسی لاگ‌ها (مهم!)
sudo journalctl -u regions-map-app -n 50 --no-pager

# 2. بررسی وجود app.py
ls -la /var/www/regions-map-app/regions-map-app/app.py

# 3. بررسی مسیر
sudo cat /etc/systemd/system/regions-map-app.service | grep WorkingDirectory

# 4. اگر app.py وجود ندارد، pull کنید
cd /var/www/regions-map-app/regions-map-app
git pull origin main

# 5. Restart
sudo systemctl daemon-reload
sudo systemctl restart regions-map-app
sudo systemctl status regions-map-app
```

---

**موفق باشید! 🚀**

