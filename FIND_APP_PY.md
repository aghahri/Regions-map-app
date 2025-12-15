# راهنمای پیدا کردن app.py

## مشکل:
فایل‌های زیادی وجود دارد اما `app.py` نیست. یک دایرکتوری `regions-map-app` هم وجود دارد.

## راه‌حل:

### 1. بررسی دایرکتوری regions-map-app:

```bash
# بررسی محتوای دایرکتوری regions-map-app
ls -la /var/www/regions-map-app/regions-map-app/regions-map-app/

# بررسی وجود app.py
ls -la /var/www/regions-map-app/regions-map-app/regions-map-app/app.py
```

### 2. اگر app.py در دایرکتوری داخلی است:

```bash
# بررسی مسیر WorkingDirectory در systemd service
sudo cat /etc/systemd/system/regions-map-app.service | grep WorkingDirectory

# باید این باشد:
# WorkingDirectory=/var/www/regions-map-app/regions-map-app/regions-map-app
```

### 3. اصلاح systemd service (اگر لازم بود):

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

### 4. یا جابجایی فایل‌ها:

```bash
# اگر app.py در دایرکتوری داخلی است، می‌توانید فایل‌ها را جابجا کنید
cd /var/www/regions-map-app/regions-map-app
mv regions-map-app/* .
rmdir regions-map-app
```

### 5. Restart service:

```bash
sudo systemctl daemon-reload
sudo systemctl restart regions-map-app
sudo systemctl status regions-map-app
```

---

## راه‌حل سریع:

```bash
# 1. بررسی دایرکتوری داخلی
ls -la /var/www/regions-map-app/regions-map-app/regions-map-app/app.py

# 2. اگر وجود دارد، اصلاح systemd service
sudo nano /etc/systemd/system/regions-map-app.service
# تغییر WorkingDirectory به: /var/www/regions-map-app/regions-map-app/regions-map-app

# 3. یا جابجایی فایل‌ها
cd /var/www/regions-map-app/regions-map-app
mv regions-map-app/* .
rmdir regions-map-app

# 4. Restart
sudo systemctl daemon-reload
sudo systemctl restart regions-map-app
sudo systemctl status regions-map-app
```

---

**موفق باشید! 🚀**

