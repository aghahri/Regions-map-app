# راهنمای اصلاح مسیر WorkingDirectory

## مشکل:
مسیر پروژه اشتباه است: `/var/www/regions-map-app/regions-map-app/regions-map-app/`
باید: `/var/www/regions-map-app/regions-map-app/`

## راه‌حل:

### 1. بررسی مسیر فعلی و پیدا کردن app.py:

```bash
# بررسی مسیر فعلی
pwd

# پیدا کردن app.py
find /var/www/regions-map-app -name "app.py" -type f
```

### 2. بررسی ساختار دایرکتوری:

```bash
# بررسی ساختار
ls -la /var/www/regions-map-app/
ls -la /var/www/regions-map-app/regions-map-app/
ls -la /var/www/regions-map-app/regions-map-app/regions-map-app/ 2>/dev/null
```

### 3. پیدا کردن مسیر درست app.py:

```bash
# پیدا کردن app.py
find /var/www/regions-map-app -name "app.py" -type f

# بررسی محتوای app.py (برای اطمینان)
head -5 /var/www/regions-map-app/regions-map-app/app.py
```

### 4. اصلاح systemd service:

```bash
sudo nano /etc/systemd/system/regions-map-app.service
```

**تغییر این خط:**
```ini
WorkingDirectory=/var/www/regions-map-app/regions-map-app
```

**به:**
```ini
WorkingDirectory=/var/www/regions-map-app/regions-map-app/regions-map-app
```

**یا اگر app.py در `/var/www/regions-map-app/regions-map-app/` است:**
```ini
WorkingDirectory=/var/www/regions-map-app/regions-map-app
```

### 5. یا اصلاح ساختار دایرکتوری (اگر لازم بود):

```bash
# اگر app.py در `/var/www/regions-map-app/regions-map-app/regions-map-app/` است
# و می‌خواهید آن را به `/var/www/regions-map-app/regions-map-app/` منتقل کنید:

cd /var/www/regions-map-app/regions-map-app/regions-map-app
mv * ../
mv .* ../ 2>/dev/null || true
cd ..
rmdir regions-map-app
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
# 1. پیدا کردن app.py
find /var/www/regions-map-app -name "app.py" -type f

# 2. بررسی مسیر
ls -la /var/www/regions-map-app/regions-map-app/app.py
ls -la /var/www/regions-map-app/regions-map-app/regions-map-app/app.py 2>/dev/null

# 3. اصلاح systemd service
sudo nano /etc/systemd/system/regions-map-app.service
# تغییر WorkingDirectory به مسیر درست

# 4. Restart
sudo systemctl daemon-reload
sudo systemctl restart regions-map-app
sudo systemctl status regions-map-app
```

---

**موفق باشید! 🚀**

