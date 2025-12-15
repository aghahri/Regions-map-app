# راهنمای اصلاح ساختار فایل‌های لوگو روی سرور

## مشکل:
روی سرور، فایل‌های لوگو در مسیرهای مختلف پراکنده شده‌اند و ساختار فایل‌ها مشکل دارد.

## راه‌حل:

### مرحله 1: آپدیت کد

```bash
cd /var/www/regions-map-app/regions-map-app
git pull origin main
```

### مرحله 2: اجرای اسکریپت اصلاح ساختار

```bash
# اجرای اسکریپت
chmod +x fix_logo_structure.sh
sudo ./fix_logo_structure.sh
```

این اسکریپت:
- فایل‌های لوگو را از مسیرهای مختلف پیدا می‌کند
- همه را به مسیر درست (`/var/www/regions-map-app/uploads/uploads/regions/logos`) منتقل می‌کند
- دسترسی‌ها را تنظیم می‌کند

### مرحله 3: بررسی نتیجه

```bash
# بررسی فایل‌های موجود
ls -la /var/www/regions-map-app/uploads/uploads/regions/logos/ | head -20

# بررسی تعداد فایل‌ها
find /var/www/regions-map-app/uploads/uploads/regions/logos -type f | wc -l
```

### مرحله 4: Restart سرویس

```bash
sudo systemctl restart regions-map-app
sudo systemctl restart nginx
```

### مرحله 5: بررسی لاگ‌ها

```bash
# بررسی لاگ‌های Flask
sudo journalctl -u regions-map-app -n 30 | grep -E "مسیر LOGO_DIR|درخواست برای لوگو"

# باید ببینید:
# ✅ مسیر LOGO_DIR: /var/www/regions-map-app/uploads/uploads/regions/logos
# ✅ مسیر LOGO_DIR وجود دارد: True
```

---

## اگر اسکریپت کار نکرد:

### روش دستی:

```bash
# 1. پیدا کردن فایل‌های لوگو
find /var/www/regions-map-app -name "*.jpg" -o -name "*.png" -o -name "*.jpeg" | grep logos

# 2. ساخت مسیر هدف
mkdir -p /var/www/regions-map-app/uploads/uploads/regions/logos

# 3. کپی فایل‌ها از مسیرهای مختلف
# اگر فایل‌ها در regions-map-app/uploads/regions/logos هستند:
cp -r /var/www/regions-map-app/regions-map-app/uploads/regions/logos/* /var/www/regions-map-app/uploads/uploads/regions/logos/ 2>/dev/null

# اگر فایل‌ها در uploads/regions/logos هستند:
cp -r /var/www/regions-map-app/uploads/regions/logos/* /var/www/regions-map-app/uploads/uploads/regions/logos/ 2>/dev/null

# 4. تنظیم دسترسی‌ها
sudo chown -R www-data:www-data /var/www/regions-map-app/uploads/uploads/regions/logos
sudo chmod -R 755 /var/www/regions-map-app/uploads/uploads/regions/logos
```

---

## تست نهایی:

### 1. تست route:

```bash
# تست مستقیم Flask
curl -I "http://127.0.0.1:8000/uploads/logos/99ac02a55349a097c0042375833d7c61_20251214_160809_IMG_1253.png"

# باید 200 OK بدهد
```

### 2. تست در مرورگر:

1. به پنل ادمین بروید
2. یک لوگو آپلود کنید
3. لوگو باید فوراً نمایش داده شود

4. در صفحه اصلی:
   - روی یک محله کلیک کنید
   - لوگو باید در سایدبار نمایش داده شود

---

## اگر هنوز کار نمی‌کند:

### بررسی nginx:

```bash
# بررسی nginx config
sudo cat /etc/nginx/sites-available/regions-map-app

# مطمئن شوید که همه route‌ها به Flask proxy می‌شوند:
# location / {
#     proxy_pass http://127.0.0.1:8000;
#     ...
# }
```

### بررسی لاگ‌های nginx:

```bash
sudo tail -f /var/log/nginx/error.log
```

---

## خلاصه دستورات:

```bash
# 1. آپدیت
cd /var/www/regions-map-app/regions-map-app
git pull origin main

# 2. اجرای اسکریپت
chmod +x fix_logo_structure.sh
sudo ./fix_logo_structure.sh

# 3. Restart
sudo systemctl restart regions-map-app
sudo systemctl restart nginx

# 4. تست
curl -I "http://127.0.0.1:8000/uploads/logos/99ac02a55349a097c0042375833d7c61_20251214_160809_IMG_1253.png"
```

---

**موفق باشید! 🚀**

