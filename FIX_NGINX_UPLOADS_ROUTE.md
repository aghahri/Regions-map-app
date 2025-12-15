# راهنمای اصلاح nginx برای route /uploads/logos/

## مشکل:
nginx 404 می‌دهد برای `/uploads/logos/` - یعنی route را به Flask proxy نمی‌کند

## راه‌حل:

### 1. بررسی nginx config فعلی:

```bash
sudo cat /etc/nginx/sites-available/regions-map-app
```

### 2. اصلاح nginx config:

nginx config باید مطمئن شود که **همه** route‌ها (از جمله `/uploads/`) به Flask proxy می‌شوند.

**Config پیشنهادی:**

```nginx
server {
    listen 80;
    server_name iranregions.com www.iranregions.com;

    client_max_body_size 200M;

    # مطمئن شوید که همه route‌ها به Flask proxy می‌شوند
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # اضافه کردن headers برای فایل‌های عکس
        proxy_set_header X-Forwarded-Host $server_name;
        proxy_buffering off;
    }
}
```

**⚠️ مهم:** نباید location خاصی برای `/uploads/` وجود داشته باشد که فایل‌ها را مستقیماً serve کند.

### 3. بررسی اینکه location خاصی برای uploads وجود ندارد:

```bash
# بررسی اینکه آیا location خاصی برای /uploads/ وجود دارد
sudo grep -r "location.*uploads" /etc/nginx/
```

**اگر location خاصی برای `/uploads/` وجود دارد، باید آن را حذف کنید یا comment کنید.**

### 4. اعمال تغییرات:

```bash
# تست config
sudo nginx -t

# اگر OK بود، reload nginx
sudo systemctl reload nginx

# یا restart کامل
sudo systemctl restart nginx
```

### 5. بررسی cache nginx:

```bash
# پاک کردن cache (اگر وجود دارد)
sudo rm -rf /var/cache/nginx/*

# Restart nginx
sudo systemctl restart nginx
```

### 6. تست:

```bash
# تست از طریق nginx
curl -I "http://171.22.27.42/uploads/logos/7d76a2f35b14523b046d6c8509a9fb2b_20251214_165016_IMG_1253.png"

# باید 200 OK بدهد (نه 404)
```

---

## اگر هنوز کار نمی‌کند:

### بررسی لاگ‌های nginx:

```bash
# بررسی error log
sudo tail -f /var/log/nginx/error.log

# بررسی access log
sudo tail -f /var/log/nginx/access.log
```

### تست مستقیم Flask:

```bash
# تست از طریق localhost:8000
curl -I "http://127.0.0.1:8000/uploads/logos/7d76a2f35b14523b046d6c8509a9fb2b_20251214_165016_IMG_1253.png"

# اگر این کار کرد، مشکل از nginx است
```

---

## مثال config کامل:

```nginx
server {
    listen 80;
    server_name iranregions.com www.iranregions.com;

    client_max_body_size 200M;

    # همه route‌ها به Flask
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $server_name;
        proxy_buffering off;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
}
```

---

**موفق باشید! 🚀**

