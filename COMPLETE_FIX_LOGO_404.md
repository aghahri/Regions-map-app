# راهنمای کامل حل مشکل 404 برای لوگو

## مشکل:
nginx 404 می‌دهد برای `/uploads/logos/` - فایل آپلود می‌شود اما نمایش داده نمی‌شود

## مراحل حل:

### 1. آپدیت کد از GitHub:

```bash
cd /var/www/regions-map-app/regions-map-app
git pull origin main
```

### 2. اجرای اسکریپت تست:

```bash
chmod +x test_logo_route.sh
./test_logo_route.sh
```

این اسکریپت بررسی می‌کند:
- آیا فایل واقعاً آپلود شده است
- آیا Flask route کار می‌کند
- آیا nginx route کار می‌کند
- آیا config nginx درست است

### 3. بررسی nginx config:

```bash
# بررسی config‌های active
ls -la /etc/nginx/sites-enabled/

# بررسی محتوای config فعال
sudo cat /etc/nginx/sites-enabled/regions-map-app
# یا
sudo cat /etc/nginx/sites-enabled/iranregions.com
```

**مطمئن شوید که:**
- هیچ location خاصی برای `/uploads/` وجود ندارد
- همه route‌ها به Flask proxy می‌شوند (`location /`)

**مثال config درست:**

```nginx
server {
    listen 80;
    server_name iranregions.com www.iranregions.com;

    client_max_body_size 200M;

    # همه route‌ها به Flask (بدون exception)
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 4. اگر location خاصی برای `/uploads/` وجود دارد:

```bash
# پیدا کردن location خاص
sudo grep -r "location.*uploads" /etc/nginx/sites-available/

# حذف یا comment کردن آن
sudo nano /etc/nginx/sites-available/[config-file]
```

**حذف این بخش:**
```nginx
location /uploads/ {
    alias /path/to/uploads/;
    ...
}
```

### 5. اعمال تغییرات nginx:

```bash
# تست config
sudo nginx -t

# اگر OK بود، reload
sudo systemctl reload nginx

# یا restart کامل
sudo systemctl restart nginx
```

### 6. بررسی لاگ‌های Flask:

```bash
# بررسی لاگ‌های Flask برای route /uploads/logos/
sudo journalctl -u regions-map-app -n 50 | grep "درخواست برای لوگو"

# باید ببینید:
# 🔍 درخواست برای لوگو: [filename]
# 🔍 LOGO_DIR: [path]
# 🔍 logo_path.exists(): True/False
```

### 7. تست مستقیم Flask:

```bash
# تست از طریق localhost:8000
curl -I "http://127.0.0.1:8000/uploads/logos/0e646b0e4600ce2bb5dd78845fe5e4f0_20251214_170341_IMG_1253.png"

# اگر این کار کرد (200 OK)، مشکل از nginx است
# اگر این هم 404 داد، مشکل از Flask route است
```

### 8. تست از طریق nginx:

```bash
# تست از طریق nginx
curl -I "http://171.22.27.42/uploads/logos/0e646b0e4600ce2bb5dd78845fe5e4f0_20251214_170341_IMG_1253.png"

# باید 200 OK بدهد
```

### 9. بررسی فایل واقعی:

```bash
# بررسی وجود فایل
ls -lh /var/www/regions-map-app/uploads/uploads/regions/logos/0e646b0e4600ce2bb5dd78845fe5e4f0_20251214_170341_IMG_1253.png

# بررسی دسترسی
ls -l /var/www/regions-map-app/uploads/uploads/regions/logos/0e646b0e4600ce2bb5dd78845fe5e4f0_20251214_170341_IMG_1253.png

# باید دسترسی read داشته باشد برای www-data
```

### 10. اگر فایل پیدا نشد:

```bash
# جستجوی فایل با نام مشابه
find /var/www/regions-map-app -name "*0e646b0e4600ce2bb5dd78845fe5e4f0*" 2>/dev/null

# اگر فایل در مسیر دیگری است، باید به مسیر درست منتقل شود
```

---

## خلاصه دستورات:

```bash
# 1. آپدیت کد
cd /var/www/regions-map-app/regions-map-app
git pull origin main

# 2. تست
./test_logo_route.sh

# 3. بررسی nginx
sudo cat /etc/nginx/sites-enabled/regions-map-app
sudo grep -r "location.*uploads" /etc/nginx/sites-available/

# 4. اصلاح nginx (اگر لازم بود)
sudo nano /etc/nginx/sites-available/regions-map-app
# حذف location خاص /uploads/

# 5. اعمال تغییرات
sudo nginx -t
sudo systemctl reload nginx

# 6. تست
curl -I "http://127.0.0.1:8000/uploads/logos/[filename]"
curl -I "http://171.22.27.42/uploads/logos/[filename]"

# 7. بررسی لاگ
sudo journalctl -u regions-map-app -n 50 | grep "درخواست برای لوگو"
```

---

## اگر هنوز کار نمی‌کند:

### بررسی لاگ‌های nginx:

```bash
# error log
sudo tail -f /var/log/nginx/error.log

# access log
sudo tail -f /var/log/nginx/access.log
```

### بررسی اینکه Flask درست کار می‌کند:

```bash
# بررسی status
sudo systemctl status regions-map-app

# restart
sudo systemctl restart regions-map-app
```

---

**موفق باشید! 🚀**

