# راهنمای اصلاح nginx server_name

## مشکل:
nginx config هنوز `iranregions.ir` دارد (باید `iranregions.com` باشد)

## راه‌حل:

### 1. ویرایش nginx config:

```bash
sudo nano /etc/nginx/sites-available/regions-map-app
```

### 2. تغییر server_name:

```nginx
server {
    listen 80;
    server_name iranregions.com www.iranregions.com;  # تغییر از .ir به .com

    client_max_body_size 200M;

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

### 3. تست config:

```bash
sudo nginx -t
```

### 4. پاک کردن cache و reload:

```bash
# پاک کردن cache (اگر وجود دارد)
sudo rm -rf /var/cache/nginx/*

# Reload nginx
sudo systemctl reload nginx

# یا restart کامل
sudo systemctl restart nginx
```

### 5. تست:

```bash
# تست route
curl -I "http://171.22.27.42/uploads/logos/1c7011dedec44544ba3fe107704ae874_20251213_080849_jpg"

# باید 200 OK بدهد (نه 404)
```

---

## اگر هنوز 404 می‌دهد:

### بررسی logs:

```bash
# nginx error log
sudo tail -20 /var/log/nginx/error.log

# nginx access log
sudo tail -20 /var/log/nginx/access.log

# Flask/Gunicorn logs
sudo journalctl -u regions-map-app -n 50
```

### تست مستقیم Flask:

```bash
# تست از طریق localhost:8000
curl -I "http://127.0.0.1:8000/uploads/logos/1c7011dedec44544ba3fe107704ae874_20251213_080849_jpg"
```

اگر Flask کار می‌کند اما nginx 404 می‌دهد، مشکل از nginx proxy است.

