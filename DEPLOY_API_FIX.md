# رفع مشکل 404 برای API

## مشکل: 404 Not Found برای `/api/neighborhood`

این خطا یعنی endpoint جدید روی سرور نیست. باید کد جدید را pull و restart کنید.

---

## راه حل: Deploy کد جدید روی سرور

### مرحله 1: اتصال به سرور
```bash
ssh user@171.22.27.42
```

### مرحله 2: Pull آخرین تغییرات
```bash
cd /path/to/Regions-map-app
git pull origin main
```

### مرحله 3: بررسی تغییرات
```bash
cd regions-map-app
git log --oneline -3
# باید commit جدید "Add API endpoint..." را ببینید
```

### مرحله 4: Restart سرویس
```bash
# Restart Gunicorn
sudo systemctl restart regions-map-app
# یا
sudo systemctl restart gunicorn

# بررسی وضعیت
sudo systemctl status regions-map-app
```

### مرحله 5: Restart Nginx (اگر نیاز باشد)
```bash
sudo systemctl restart nginx
```

### مرحله 6: بررسی Logs
```bash
# بررسی خطاهای Gunicorn
sudo journalctl -u regions-map-app -f --lines=50

# یا
tail -f /var/log/gunicorn/error.log
```

---

## بررسی اینکه API اضافه شده:

### روی سرور:
```bash
cd /path/to/Regions-map-app/regions-map-app
grep -n "api/neighborhood" app.py
```

باید خطی مثل این را ببینید:
```
@app.route("/api/neighborhood", methods=["GET", "POST"])
```

---

## تست سریع روی سرور:

```bash
# تست با curl
curl "http://localhost:5003/api/neighborhood?lat=35.6892&lon=51.3890"

# یا اگر از طریق Nginx است:
curl "http://localhost/api/neighborhood?lat=35.6892&lon=51.3890"
```

---

## اگر هنوز 404 می‌گیرید:

### بررسی 1: مسیر پروژه درست است؟
```bash
pwd
# باید مسیر پروژه را ببینید
```

### بررسی 2: کد جدید pull شده؟
```bash
git status
git log --oneline -5
```

### بررسی 3: سرویس درست restart شده؟
```bash
sudo systemctl status regions-map-app
# باید "active (running)" باشد
```

### بررسی 4: Nginx config درست است؟
```bash
sudo nginx -t
cat /etc/nginx/sites-available/regions-map-app
# باید proxy_pass به Gunicorn باشد
```

---

## اگر مشکل از Nginx است:

مطمئن شوید که Nginx همه مسیرها را به Gunicorn forward می‌کند:

```nginx
location / {
    include proxy_params;
    proxy_pass http://unix:/path/to/Regions-map-app/regions-map-app/app.sock;
    # یا
    # proxy_pass http://127.0.0.1:5003;
}
```

سپس:
```bash
sudo nginx -t
sudo systemctl reload nginx
```

---

## تست نهایی:

بعد از restart، در Postman دوباره تست کنید:

```
GET http://171.22.27.42/api/neighborhood?lat=35.6892&lon=51.3890
```

یا:

```
POST http://171.22.27.42/api/neighborhood
Body (JSON):
{
  "lat": 35.6892,
  "lon": 51.3890
}
```

---

## اگر هنوز مشکل دارید:

### بررسی Python imports:
```bash
cd /path/to/Regions-map-app/regions-map-app
source venv/bin/activate
python -c "from shapely.geometry import Point; print('OK')"
```

اگر خطا داد:
```bash
pip install shapely
```

### بررسی Logs کامل:
```bash
sudo journalctl -u regions-map-app --since "10 minutes ago" | tail -100
```


