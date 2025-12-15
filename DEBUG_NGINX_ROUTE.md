# دیباگ مشکل Route در nginx

## مشکل:
nginx 404 می‌دهد قبل از رسیدن به Flask

## راه‌حل‌ها:

### 1. تست مستقیم Flask (بدون nginx):

```bash
# تست از طریق localhost:8000 (مستقیم Flask)
curl -I "http://127.0.0.1:8000/uploads/logos/1c7011dedec44544ba3fe107704ae874_20251213_080849_jpg"

# یا با نمایش محتوا
curl "http://127.0.0.1:8000/uploads/logos/1c7011dedec44544ba3fe107704ae874_20251213_080849_jpg" | head -20
```

**اگر این کار کرد:** مشکل از nginx configuration است  
**اگر این کار نکرد:** مشکل از Flask route است

---

### 2. بررسی nginx logs:

```bash
# بررسی error log
sudo tail -f /var/log/nginx/error.log

# بررسی access log
sudo tail -f /var/log/nginx/access.log
```

---

### 3. بررسی Flask logs:

```bash
# بررسی logs Flask/Gunicorn
sudo journalctl -u regions-map-app -f
```

---

### 4. تست با نام فایل کامل:

```bash
# تست با نام فایل کامل (با .jpg)
curl -I "http://171.22.27.42/uploads/logos/1c7011dedec44544ba3fe107704ae874_20251213_080849_jpg.jpg"
```

---

### 5. بررسی اینکه route در Flask وجود دارد:

```bash
# بررسی route در app.py
grep -n "uploads/logos" /var/www/regions-map-app/regions-map-app/app.py
```

---

## اگر مشکل از nginx است:

ممکن است nginx فایل‌های static را خودش serve می‌کند. باید مطمئن شویم که `/uploads/logos/` به Flask proxy می‌شود.

