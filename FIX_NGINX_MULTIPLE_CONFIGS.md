# راهنمای اصلاح مشکل nginx با چند config

## مشکل:
در فایل‌های دیگر nginx (`iranregions.com`, `iranregions.ir`, `00-default-ip`) location خاصی برای `/uploads/` وجود دارد که route را intercept می‌کند.

## راه‌حل:

### 1. بررسی اینکه کدام config active است:

```bash
# بررسی config‌های active
ls -la /etc/nginx/sites-enabled/

# بررسی اینکه کدام config برای domain شما استفاده می‌شود
sudo nginx -T | grep -A 10 "server_name.*iranregions"
```

### 2. بررسی محتوای config‌های دیگر:

```bash
# بررسی config iranregions.com
sudo cat /etc/nginx/sites-available/iranregions.com

# بررسی config iranregions.ir
sudo cat /etc/nginx/sites-available/iranregions.ir

# بررسی config 00-default-ip
sudo cat /etc/nginx/sites-available/00-default-ip
```

### 3. اصلاح config فعال:

**اگر `iranregions.com` یا `iranregions.ir` active است:**

```bash
sudo nano /etc/nginx/sites-available/iranregions.com
# یا
sudo nano /etc/nginx/sites-available/iranregions.ir
```

**حذف یا comment کردن location خاص برای `/uploads/`:**

```nginx
# این را comment کنید یا حذف کنید:
# location /uploads/ {
#     alias /path/to/uploads/;
#     ...
# }

# مطمئن شوید که location / همه route‌ها را handle می‌کند:
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

### 4. اگر `regions-map-app` config باید استفاده شود:

```bash
# غیرفعال کردن config‌های دیگر
sudo rm /etc/nginx/sites-enabled/iranregions.com 2>/dev/null
sudo rm /etc/nginx/sites-enabled/iranregions.ir 2>/dev/null
sudo rm /etc/nginx/sites-enabled/00-default-ip 2>/dev/null

# فعال کردن config regions-map-app
sudo ln -s /etc/nginx/sites-available/regions-map-app /etc/nginx/sites-enabled/regions-map-app
```

### 5. اصلاح server_name در config regions-map-app:

```bash
sudo nano /etc/nginx/sites-available/regions-map-app
```

**تغییر این خط:**
```nginx
server_name iranregions.ir www.iranregions.ir;
```

**به:**
```nginx
server_name iranregions.com www.iranregions.com;
```

### 6. اعمال تغییرات:

```bash
# تست config
sudo nginx -t

# اگر OK بود، reload nginx
sudo systemctl reload nginx

# یا restart کامل
sudo systemctl restart nginx
```

### 7. تست:

```bash
# تست از طریق nginx
curl -I "http://171.22.27.42/uploads/logos/7d76a2f35b14523b046d6c8509a9fb2b_20251214_165016_IMG_1253.png"

# باید 200 OK بدهد (نه 404)
```

---

## خلاصه دستورات:

```bash
# 1. بررسی config‌های active
ls -la /etc/nginx/sites-enabled/

# 2. بررسی محتوای config‌های دیگر
sudo cat /etc/nginx/sites-available/iranregions.com | grep -A 5 "location.*uploads"

# 3. اصلاح config فعال (حذف location /uploads/)
sudo nano /etc/nginx/sites-available/iranregions.com

# 4. اصلاح server_name در regions-map-app
sudo nano /etc/nginx/sites-available/regions-map-app

# 5. تست و reload
sudo nginx -t
sudo systemctl reload nginx
```

---

**موفق باشید! 🚀**

