# راهنمای سریع رفع خطای 502 Bad Gateway

## 🔍 تشخیص مشکل

خطای 502 معمولاً به این معنی است که nginx نمی‌تواند به application server (gunicorn) متصل شود.

## ✅ راه حل‌های سریع

### 1. بررسی وضعیت gunicorn

```bash
# بررسی اینکه gunicorn در حال اجرا است یا نه
ps aux | grep gunicorn

# یا
pgrep -f gunicorn
```

### 2. اگر gunicorn در حال اجرا نیست، آن را راه‌اندازی کنید

```bash
cd /path/to/regions-map-app

# فعال کردن virtual environment
source venv/bin/activate

# راه‌اندازی gunicorn
gunicorn app:app --bind 127.0.0.1:5003 --workers 2 --timeout 120
```

### 3. اگر از systemd استفاده می‌کنید

```bash
# بررسی وضعیت سرویس
sudo systemctl status your-app-service

# راه‌اندازی سرویس
sudo systemctl start your-app-service

# Restart سرویس
sudo systemctl restart your-app-service

# بررسی لاگ‌ها
sudo journalctl -u your-app-service -f
```

### 4. بررسی لاگ‌های خطا

```bash
# لاگ‌های nginx
sudo tail -f /var/log/nginx/error.log

# لاگ‌های application
# اگر از systemd استفاده می‌کنید:
sudo journalctl -u your-app-service -n 50

# یا اگر gunicorn را دستی اجرا می‌کنید:
# خطاها در console نمایش داده می‌شوند
```

### 5. بررسی پورت

```bash
# بررسی اینکه پورت 5003 در حال استفاده است
sudo netstat -tlnp | grep 5003
# یا
sudo ss -tlnp | grep 5003

# بررسی اینکه application روی پورت درست در حال اجرا است
curl http://127.0.0.1:5003
```

### 6. بررسی configuration nginx

```bash
# بررسی فایل configuration
sudo nginx -t

# بررسی فایل site configuration
sudo cat /etc/nginx/sites-available/your-site

# باید چیزی شبیه این باشد:
# location / {
#     proxy_pass http://127.0.0.1:5003;
#     proxy_set_header Host $host;
#     proxy_set_header X-Real-IP $remote_addr;
# }
```

### 7. Restart nginx

```bash
sudo systemctl restart nginx
```

## 🔧 راه حل کامل (Step by Step)

```bash
# 1. متوقف کردن gunicorn قدیمی (اگر در حال اجرا است)
pkill -f gunicorn

# 2. وارد دایرکتوری برنامه
cd /path/to/regions-map-app

# 3. فعال کردن virtual environment
source venv/bin/activate

# 4. بررسی اینکه همه dependencies نصب شده‌اند
pip install -r requirements.txt

# 5. بررسی کد برای خطاهای syntax
python -m py_compile app.py

# 6. راه‌اندازی gunicorn در background
nohup gunicorn app:app --bind 127.0.0.1:5003 --workers 2 --timeout 120 --access-logfile - --error-logfile - > gunicorn.log 2>&1 &

# 7. بررسی اینکه gunicorn راه‌اندازی شد
sleep 2
ps aux | grep gunicorn

# 8. تست local
curl http://127.0.0.1:5003

# 9. Restart nginx
sudo systemctl restart nginx

# 10. بررسی لاگ‌ها
tail -f gunicorn.log
```

## 🚨 مشکلات رایج

### مشکل 1: Import Error

```bash
# بررسی virtual environment
which python
source venv/bin/activate
which python

# نصب dependencies
pip install -r requirements.txt
```

### مشکل 2: Port در حال استفاده

```bash
# پیدا کردن process که از پورت استفاده می‌کند
sudo lsof -i :5003

# kill کردن process
sudo kill -9 PID
```

### مشکل 3: Permission Error

```bash
# بررسی permission فایل‌ها
ls -la uploads/
chmod -R 755 uploads/
```

### مشکل 4: خطا در کد

```bash
# تست کردن کد
cd /path/to/regions-map-app
source venv/bin/activate
python app.py
# اگر خطا داد، خطا را بررسی کنید
```

## 📝 اسکریپت خودکار برای رفع مشکل

```bash
#!/bin/bash
# fix_502.sh

APP_DIR="/path/to/regions-map-app"
PORT=5003

cd $APP_DIR
source venv/bin/activate

# Kill old processes
pkill -f gunicorn

# Wait a bit
sleep 2

# Start gunicorn
nohup gunicorn app:app --bind 127.0.0.1:$PORT --workers 2 --timeout 120 \
    --access-logfile - --error-logfile - > gunicorn.log 2>&1 &

# Wait and check
sleep 3
if pgrep -f gunicorn > /dev/null; then
    echo "✅ Gunicorn started successfully"
    curl -s http://127.0.0.1:$PORT > /dev/null && echo "✅ App is responding" || echo "❌ App not responding"
else
    echo "❌ Failed to start gunicorn. Check gunicorn.log"
    tail -20 gunicorn.log
fi

# Restart nginx
sudo systemctl restart nginx
echo "✅ Nginx restarted"
```

## 🔍 بررسی نهایی

```bash
# 1. بررسی gunicorn
ps aux | grep gunicorn

# 2. تست local
curl http://127.0.0.1:5003

# 3. بررسی nginx
sudo systemctl status nginx

# 4. بررسی لاگ‌ها
tail -f /var/log/nginx/error.log
tail -f gunicorn.log
```

## 💡 نکات مهم:

1. همیشه ابتدا gunicorn را تست کنید: `curl http://127.0.0.1:5003`
2. اگر gunicorn کار می‌کند اما nginx نمی‌کند، مشکل در nginx configuration است
3. اگر gunicorn کار نمی‌کند، مشکل در کد یا dependencies است
4. همیشه لاگ‌ها را بررسی کنید

