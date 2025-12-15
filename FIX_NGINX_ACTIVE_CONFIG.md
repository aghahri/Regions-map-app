# راهنمای اصلاح nginx config فعال

## مشکل:
config `regions-map-app` در `sites-enabled` وجود ندارد. به جای آن، `iranregions.com` و `00-default-ip` active هستند.

## راه‌حل:

### 1. بررسی config فعال:

```bash
# بررسی config iranregions.com
sudo cat /etc/nginx/sites-available/iranregions.com

# بررسی config 00-default-ip
sudo cat /etc/nginx/sites-available/00-default-ip
```

### 2. پیدا کردن location خاص /uploads/:

```bash
# بررسی location خاص در config‌های active
sudo grep -A 10 "location.*uploads" /etc/nginx/sites-available/iranregions.com
sudo grep -A 10 "location.*uploads" /etc/nginx/sites-available/00-default-ip
```

### 3. اصلاح config iranregions.com:

```bash
sudo nano /etc/nginx/sites-available/iranregions.com
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

**اگر location خاصی برای `/uploads/` وجود دارد، حذف کنید:**

```nginx
# این را حذف کنید:
location /uploads/ {
    alias /path/to/uploads/;
    ...
}
```

### 4. اصلاح config 00-default-ip (اگر لازم بود):

```bash
sudo nano /etc/nginx/sites-available/00-default-ip
```

**مطمئن شوید که:**
- همه route‌ها به Flask proxy می‌شوند
- هیچ location خاصی برای `/uploads/` وجود ندارد

### 5. اعمال تغییرات:

```bash
# تست config
sudo nginx -t

# اگر OK بود، reload
sudo systemctl reload nginx

# یا restart کامل
sudo systemctl restart nginx
```

### 6. تست:

```bash
# تست از طریق localhost:8000 (Flask)
curl -I "http://127.0.0.1:8000/uploads/logos/0e646b0e4600ce2bb5dd78845fe5e4f0_20251214_170341_IMG_1253.png"

# تست از طریق nginx
curl -I "http://171.22.27.42/uploads/logos/0e646b0e4600ce2bb5dd78845fe5e4f0_20251214_170341_IMG_1253.png"
```

---

## خلاصه دستورات:

```bash
# 1. بررسی config فعال
sudo cat /etc/nginx/sites-available/iranregions.com
sudo cat /etc/nginx/sites-available/00-default-ip

# 2. پیدا کردن location خاص
sudo grep -A 10 "location.*uploads" /etc/nginx/sites-available/iranregions.com
sudo grep -A 10 "location.*uploads" /etc/nginx/sites-available/00-default-ip

# 3. اصلاح config
sudo nano /etc/nginx/sites-available/iranregions.com
# حذف location خاص /uploads/

# 4. اعمال تغییرات
sudo nginx -t
sudo systemctl reload nginx

# 5. تست
curl -I "http://171.22.27.42/uploads/logos/[filename]"
```

---

**موفق باشید! 🚀**

