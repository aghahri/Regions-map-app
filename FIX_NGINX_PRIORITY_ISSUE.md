# راهنمای حل مشکل nginx priority

## مشکل:
Flask route کار می‌کند (200 OK) اما nginx 404 می‌دهد. احتمالاً config دیگری (00-default-ip) route را intercept می‌کند.

## راه‌حل:

### 1. بررسی config 00-default-ip:

```bash
sudo cat /etc/nginx/sites-available/00-default-ip
```

**اگر این config route `/uploads/` را intercept می‌کند:**
- باید آن را غیرفعال کنید
- یا location خاص `/uploads/` را حذف کنید

### 2. بررسی priority config‌ها:

```bash
# بررسی اینکه کدام config اول اجرا می‌شود
ls -la /etc/nginx/sites-enabled/ | sort

# معمولاً config‌هایی که با 00 شروع می‌شوند اول اجرا می‌شوند
```

### 3. غیرفعال کردن 00-default-ip (اگر لازم بود):

```bash
# غیرفعال کردن
sudo rm /etc/nginx/sites-enabled/00-default-ip

# یا comment کردن location خاص
sudo nano /etc/nginx/sites-available/00-default-ip
```

### 4. اصلاح 00-default-ip (اگر نمی‌خواهید غیرفعال کنید):

```bash
sudo nano /etc/nginx/sites-available/00-default-ip
```

**مطمئن شوید که:**
- هیچ location خاصی برای `/uploads/` وجود ندارد
- همه route‌ها به Flask proxy می‌شوند

**مثال config درست:**

```nginx
server {
    listen 80 default_server;
    server_name _;

    client_max_body_size 200M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 5. پاک کردن cache nginx:

```bash
# پاک کردن cache
sudo rm -rf /var/cache/nginx/*

# Restart nginx
sudo systemctl restart nginx
```

### 6. اعمال تغییرات:

```bash
# تست config
sudo nginx -t

# اگر OK بود، reload
sudo systemctl reload nginx

# یا restart کامل
sudo systemctl restart nginx
```

### 7. تست:

```bash
# تست از طریق nginx
curl -I "http://171.22.27.42/uploads/logos/0e646b0e4600ce2bb5dd78845fe5e4f0_20251214_170341_IMG_1253.png"

# باید 200 OK بدهد
```

---

## خلاصه دستورات:

```bash
# 1. بررسی config 00-default-ip
sudo cat /etc/nginx/sites-available/00-default-ip

# 2. بررسی priority
ls -la /etc/nginx/sites-enabled/ | sort

# 3. غیرفعال کردن (اگر لازم بود)
sudo rm /etc/nginx/sites-enabled/00-default-ip

# 4. یا اصلاح config
sudo nano /etc/nginx/sites-available/00-default-ip
# حذف location خاص /uploads/

# 5. پاک کردن cache
sudo rm -rf /var/cache/nginx/*
sudo systemctl restart nginx

# 6. تست
curl -I "http://171.22.27.42/uploads/logos/[filename]"
```

---

**موفق باشید! 🚀**

