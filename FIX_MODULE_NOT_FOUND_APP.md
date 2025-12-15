# راهنمای حل مشکل ModuleNotFoundError: No module named 'app'

## مشکل:
`ModuleNotFoundError: No module named 'app'` - فایل `app.py` پیدا نمی‌شود

## مراحل حل:

### 1. بررسی وجود فایل app.py:

```bash
# بررسی وجود فایل
ls -la /var/www/regions-map-app/regions-map-app/app.py

# اگر وجود ندارد:
cd /var/www/regions-map-app/regions-map-app
ls -la
```

**اگر فایل وجود ندارد:**
- باید از GitHub clone کنید
- یا فایل را از جای دیگری کپی کنید

### 2. Clone از GitHub (اگر فایل وجود ندارد):

```bash
cd /var/www/regions-map-app
rm -rf regions-map-app  # اگر دایرکتوری خالی است
git clone https://github.com/aghahri/Regions-map-app.git regions-map-app
cd regions-map-app
```

### 3. بررسی WorkingDirectory در systemd service:

```bash
sudo cat /etc/systemd/system/regions-map-app.service
```

**باید این شکلی باشد:**
```ini
[Service]
WorkingDirectory=/var/www/regions-map-app/regions-map-app
```

**اگر درست نیست، اصلاح کنید:**
```bash
sudo nano /etc/systemd/system/regions-map-app.service
```

### 4. تست import دستی:

```bash
cd /var/www/regions-map-app/regions-map-app
source ../venv/bin/activate

# تست import
python3 -c "import app; print('OK')"
```

**اگر کار کرد:**
- مشکل از systemd service است
- WorkingDirectory را بررسی کنید

**اگر کار نکرد:**
- فایل `app.py` وجود ندارد یا مشکل دارد
- به مرحله 2 بروید

### 5. بررسی محتوای دایرکتوری:

```bash
cd /var/www/regions-map-app/regions-map-app
ls -la
```

**باید فایل‌های زیر را ببینید:**
- `app.py`
- `requirements.txt` (اختیاری)

### 6. Restart service:

```bash
sudo systemctl daemon-reload
sudo systemctl restart regions-map-app
sudo systemctl status regions-map-app
```

---

## راه‌حل سریع:

```bash
# 1. بررسی وجود فایل
ls -la /var/www/regions-map-app/regions-map-app/app.py

# 2. اگر وجود ندارد، clone از GitHub
cd /var/www/regions-map-app
rm -rf regions-map-app
git clone https://github.com/aghahri/Regions-map-app.git regions-map-app
cd regions-map-app

# 3. بررسی WorkingDirectory
sudo cat /etc/systemd/system/regions-map-app.service | grep WorkingDirectory

# 4. تست import
source ../venv/bin/activate
python3 -c "import app; print('OK')"

# 5. Restart service
sudo systemctl daemon-reload
sudo systemctl restart regions-map-app
sudo systemctl status regions-map-app
```

---

**موفق باشید! 🚀**

