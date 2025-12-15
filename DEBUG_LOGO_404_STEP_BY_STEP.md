# راهنمای دیباگ مشکل 404 لوگو - قدم به قدم

## مشکل:
nginx 404 می‌دهد برای `/uploads/logos/`

## مراحل دیباگ:

### 1. تست Flask route (localhost:8000):

```bash
# تست مستقیم Flask
curl -I "http://127.0.0.1:8000/uploads/logos/0e646b0e4600ce2bb5dd78845fe5e4f0_20251214_170341_IMG_1253.png"
```

**اگر این کار کرد (200 OK):**
- مشکل از nginx است
- به مرحله 2 بروید

**اگر این هم 404 داد:**
- مشکل از Flask route است
- به مرحله 3 بروید

---

### 2. بررسی nginx config (اگر Flask کار می‌کند):

```bash
# بررسی config فعال
sudo cat /etc/nginx/sites-available/iranregions.com

# پیدا کردن location خاص
sudo grep -A 10 "location.*uploads" /etc/nginx/sites-available/iranregions.com
sudo grep -A 10 "location.*uploads" /etc/nginx/sites-available/00-default-ip
```

**اگر location خاصی برای `/uploads/` وجود دارد:**
- حذف کنید یا comment کنید
- reload nginx

---

### 3. بررسی Flask route (اگر Flask 404 می‌دهد):

```bash
# بررسی لاگ‌های Flask
sudo journalctl -u regions-map-app -n 50 | grep "درخواست برای لوگو"

# باید ببینید:
# 🔍 درخواست برای لوگو: [filename]
# 🔍 LOGO_DIR: [path]
# 🔍 logo_path.exists(): True/False
```

**اگر لاگ نشان می‌دهد که فایل پیدا نشد:**
- به مرحله 4 بروید

---

### 4. بررسی فایل واقعی:

```bash
# بررسی وجود فایل
ls -lh /var/www/regions-map-app/uploads/uploads/regions/logos/0e646b0e4600ce2bb5dd78845fe5e4f0_20251214_170341_IMG_1253.png

# اگر فایل پیدا نشد، جستجو کنید:
find /var/www/regions-map-app -name "*0e646b0e4600ce2bb5dd78845fe5e4f0*" 2>/dev/null

# بررسی دسترسی
ls -l /var/www/regions-map-app/uploads/uploads/regions/logos/0e646b0e4600ce2bb5dd78845fe5e4f0_20251214_170341_IMG_1253.png
```

**اگر فایل پیدا نشد:**
- فایل آپلود نشده است
- باید دوباره آپلود کنید

**اگر فایل پیدا شد اما در مسیر دیگری:**
- باید به مسیر درست منتقل شود

---

### 5. بررسی LOGO_DIR در Flask:

```bash
# بررسی لاگ‌های Flask برای LOGO_DIR
sudo journalctl -u regions-map-app -n 50 | grep "LOGO_DIR"

# باید ببینید:
# ✅ مسیر LOGO_DIR: /var/www/regions-map-app/uploads/uploads/regions/logos
# ✅ مسیر LOGO_DIR وجود دارد: True
```

**اگر مسیر درست نیست:**
- باید app.py را بررسی کنید
- یا فایل را به مسیر درست منتقل کنید

---

## خلاصه دستورات:

```bash
# 1. تست Flask
curl -I "http://127.0.0.1:8000/uploads/logos/0e646b0e4600ce2bb5dd78845fe5e4f0_20251214_170341_IMG_1253.png"

# 2. بررسی لاگ Flask
sudo journalctl -u regions-map-app -n 50 | grep "درخواست برای لوگو"

# 3. بررسی فایل
ls -lh /var/www/regions-map-app/uploads/uploads/regions/logos/0e646b0e4600ce2bb5dd78845fe5e4f0_20251214_170341_IMG_1253.png

# 4. جستجوی فایل
find /var/www/regions-map-app -name "*0e646b0e4600ce2bb5dd78845fe5e4f0*" 2>/dev/null

# 5. بررسی nginx config
sudo cat /etc/nginx/sites-available/iranregions.com
sudo grep -A 10 "location.*uploads" /etc/nginx/sites-available/iranregions.com
```

---

**موفق باشید! 🚀**

