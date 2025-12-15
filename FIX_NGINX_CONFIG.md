# راهنمای اصلاح nginx Configuration

## مشکل:
Flask route درست کار می‌کند (`127.0.0.1:8000` → 200 OK)  
اما nginx 404 می‌دهد (`171.22.27.42` → 404)

## راه‌حل:

### 1. بررسی nginx config فعلی:

```bash
sudo cat /etc/nginx/sites-available/regions-map-app
```

### 2. اصلاح nginx config:

nginx config باید مطمئن شود که همه route‌ها (از جمله `/uploads/logos/`) به Flask proxy می‌شوند.

**Config پیشنهادی:**

```nginx
server {
    listen 80;
    server_name iranregions.ir www.iranregions.ir;

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

### 3. اعمال تغییرات:

```bash
# تست config
sudo nginx -t

# اگر OK بود، reload nginx
sudo systemctl reload nginx
```

### 4. بررسی cache nginx:

اگر nginx cache دارد، ممکن است 404 را cache کرده باشد:

```bash
# پاک کردن cache (اگر وجود دارد)
sudo rm -rf /var/cache/nginx/*

# یا restart کامل
sudo systemctl restart nginx
```

### 5. بررسی nginx logs:

```bash
# بررسی error log
sudo tail -f /var/log/nginx/error.log

# بررسی access log
sudo tail -f /var/log/nginx/access.log
```

---

## اگر هنوز کار نمی‌کند:

### بررسی اینکه آیا nginx فایل‌های static را خودش serve می‌کند:

```bash
# بررسی اینکه آیا location خاصی برای static files وجود دارد
sudo grep -r "location.*static\|location.*uploads" /etc/nginx/
```

اگر location خاصی برای `/uploads/` وجود دارد، باید آن را حذف کنید یا به Flask proxy کنید.

---

## تست نهایی:

```bash
# تست از طریق nginx
curl -I "http://171.22.27.42/uploads/logos/1c7011dedec44544ba3fe107704ae874_20251213_080849_jpg"

# باید 200 OK بدهد (نه 404)
```

