# راهنمای تست لوگو روی سرور

## 🔍 بررسی وضعیت سرویس

### 1. بررسی وضعیت سرویس regions-map-app:

```bash
sudo systemctl status regions-map-app
```

**اگر running است:** ✅ سرویس در حال اجرا است  
**اگر failed است:** ❌ سرویس متوقف شده - باید restart کنید

---

### 2. بررسی وضعیت nginx:

```bash
sudo systemctl status nginx
```

**اگر running است:** ✅ nginx در حال اجرا است  
**اگر failed است:** ❌ nginx متوقف شده - باید restart کنید

---

### 3. بررسی پورت‌های باز:

```bash
# بررسی پورت 5003
sudo netstat -tlnp | grep 5003

# یا
sudo ss -tlnp | grep 5003

# بررسی socket file (اگر از socket استفاده می‌کنید)
ls -la /var/www/regions-map-app/regions-map-app/*.sock
```

---

## 🧪 روش‌های تست

### روش 1: تست از طریق nginx (پیشنهادی)

اگر از nginx استفاده می‌کنید، باید از طریق domain یا IP تست کنید:

```bash
# تست از طریق IP
curl "http://171.22.27.42/uploads/logos/1c7011dedec44544ba3fe107704ae874_20251213_080849_jpg"

# یا اگر domain دارید:
curl "http://your-domain.com/uploads/logos/1c7011dedec44544ba3fe107704ae874_20251213_080849_jpg"
```

---

### روش 2: تست از طریق socket (اگر از socket استفاده می‌کنید)

```bash
# پیدا کردن socket file
find /var/www/regions-map-app -name "*.sock"

# تست از طریق curl با socket
curl --unix-socket /path/to/app.sock "http://localhost/uploads/logos/1c7011dedec44544ba3fe107704ae874_20251213_080849_jpg"
```

---

### روش 3: تست مستقیم از gunicorn (اگر در حال اجرا است)

```bash
# پیدا کردن process gunicorn
ps aux | grep gunicorn

# بررسی پورت واقعی
sudo netstat -tlnp | grep gunicorn
```

---

### روش 4: بررسی فایل مستقیماً

```bash
# بررسی وجود فایل
ls -la /var/www/regions-map-app/regions-map-app/uploads/regions/logos/1c7011dedec44544ba3fe107704ae874_20251213_080849_jpg

# اگر فایل وجود ندارد، جستجو برای فایل‌های مشابه
ls -la /var/www/regions-map-app/regions-map-app/uploads/regions/logos/ | grep "1c7011dedec44544ba3fe107704ae874"

# بررسی فایل‌های JSON
cat /var/www/regions-map-app/regions-map-app/uploads/regions/logos/*.json | grep "1c7011dedec44544ba3fe107704ae874"
```

---

## 🔧 راه‌حل‌های احتمالی

### مشکل 1: سرویس در حال اجرا نیست

```bash
# Restart سرویس
sudo systemctl restart regions-map-app

# بررسی دوباره
sudo systemctl status regions-map-app
```

---

### مشکل 2: nginx در حال اجرا نیست

```bash
# Restart nginx
sudo systemctl restart nginx

# بررسی دوباره
sudo systemctl status nginx
```

---

### مشکل 3: فایل واقعاً وجود ندارد

```bash
# بررسی فایل‌های موجود
ls -la /var/www/regions-map-app/regions-map-app/uploads/regions/logos/

# اجرای اسکریپت fix
cd /var/www/regions-map-app/regions-map-app
python3 fix_logo_filenames.py
```

---

### مشکل 4: مشکل از nginx configuration

```bash
# بررسی nginx config
sudo nginx -t

# بررسی config file
sudo cat /etc/nginx/sites-available/regions-map-app
# یا
sudo cat /etc/nginx/sites-enabled/regions-map-app
```

---

## 📋 چک‌لیست کامل

```bash
# 1. بررسی سرویس
sudo systemctl status regions-map-app
sudo systemctl status nginx

# 2. بررسی فایل
ls -la /var/www/regions-map-app/regions-map-app/uploads/regions/logos/ | grep "1c7011dedec44544ba3fe107704ae874"

# 3. بررسی JSON
cat /var/www/regions-map-app/regions-map-app/uploads/regions/logos/*.json | grep -A 2 "1c7011dedec44544ba3fe107704ae874"

# 4. تست از طریق nginx
curl -I "http://171.22.27.42/uploads/logos/1c7011dedec44544ba3fe107704ae874_20251213_080849_jpg"

# 5. بررسی لاگ‌ها
sudo journalctl -u regions-map-app -n 50
sudo tail -f /var/log/nginx/error.log
```

---

## 🎯 تست نهایی

بعد از بررسی همه موارد، از مرورگر تست کنید:

1. باز کردن سایت: `http://171.22.27.42`
2. انتخاب نقشه
3. کلیک روی محله
4. بررسی اینکه لوگو نمایش داده می‌شود

---

## 💡 نکات مهم

1. ✅ **همیشه از طریق nginx تست کنید** - نه مستقیم از localhost:5003
2. ✅ **بررسی کنید که سرویس‌ها running هستند**
3. ✅ **بررسی کنید که فایل واقعاً وجود دارد**
4. ✅ **اگر فایل وجود ندارد، اسکریپت fix را اجرا کنید**

