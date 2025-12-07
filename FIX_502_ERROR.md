# رفع خطای 502 Bad Gateway

## مشکل: 502 Bad Gateway

این خطا یعنی Nginx نمی‌تواند به Gunicorn وصل شود.

---

## راه حل 1: بررسی وضعیت Gunicorn

```bash
# بررسی وضعیت service
sudo systemctl status regions-map-app
# یا
sudo systemctl status gunicorn

# اگر running نیست، start کنید
sudo systemctl start regions-map-app
```

---

## راه حل 2: بررسی Logs Gunicorn

```bash
# Logs systemd
sudo journalctl -u regions-map-app -f --lines=50

# یا اگر log file دارید
tail -f /var/log/gunicorn/error.log
```

خطاهای رایج:
- `ModuleNotFoundError`: dependency نصب نشده
- `ImportError`: مشکل import
- `Permission denied`: مشکل دسترسی

---

## راه حل 3: بررسی Nginx Config

```bash
# تست config
sudo nginx -t

# بررسی config
sudo cat /etc/nginx/sites-available/regions-map-app
```

مطمئن شوید که:
- `proxy_pass` به درستی تنظیم شده
- Socket file یا port درست است
- User و Group درست هستند

---

## راه حل 4: بررسی Socket File

اگر از Unix socket استفاده می‌کنید:

```bash
# بررسی وجود socket
ls -la /path/to/Regions-map-app/regions-map-app/app.sock

# بررسی permissions
# باید قابل خواندن/نوشتن برای www-data باشد
sudo chown www-data:www-data /path/to/Regions-map-app/regions-map-app/app.sock
sudo chmod 666 /path/to/Regions-map-app/regions-map-app/app.sock
```

---

## راه حل 5: Restart کامل

```bash
# Stop Gunicorn
sudo systemctl stop regions-map-app

# Stop Nginx
sudo systemctl stop nginx

# Start Gunicorn
sudo systemctl start regions-map-app

# بررسی وضعیت
sudo systemctl status regions-map-app

# Start Nginx
sudo systemctl start nginx

# بررسی وضعیت
sudo systemctl status nginx
```

---

## راه حل 6: تست Gunicorn مستقیم

```bash
cd /path/to/Regions-map-app/regions-map-app
source venv/bin/activate

# تست اجرای app
python -c "import app; print('OK')"

# اجرای دستی Gunicorn
gunicorn --bind 127.0.0.1:8000 app:app
```

اگر این کار کرد، مشکل از Nginx config است.

---

## راه حل 7: بررسی Port

اگر از TCP port استفاده می‌کنید:

```bash
# بررسی port
netstat -tlnp | grep 8000
# یا
ss -tlnp | grep 8000

# بررسی firewall
sudo ufw status
```

---

## راه حل 8: بررسی Nginx Error Logs

```bash
# Error logs
sudo tail -f /var/log/nginx/error.log

# Access logs
sudo tail -f /var/log/nginx/access.log
```

خطاهای رایج:
- `connect() to unix:/path/to/app.sock failed (2: No such file or directory)`
- `connect() to 127.0.0.1:8000 failed (111: Connection refused)`
- `Permission denied`

---

## راه حل 9: بررسی Systemd Service

```bash
# بررسی service file
sudo cat /etc/systemd/system/regions-map-app.service

# Reload systemd
sudo systemctl daemon-reload

# Restart service
sudo systemctl restart regions-map-app
```

---

## راه حل 10: تغییر به TCP (اگر socket مشکل دارد)

در Nginx config:
```nginx
# به جای:
proxy_pass http://unix:/path/to/app.sock;

# استفاده کنید:
proxy_pass http://127.0.0.1:8000;
```

در Systemd service:
```ini
# به جای:
--bind unix:/path/to/app.sock

# استفاده کنید:
--bind 127.0.0.1:8000
```

---

## چک‌لیست سریع:

```bash
# 1. Gunicorn running?
sudo systemctl status regions-map-app

# 2. Nginx running?
sudo systemctl status nginx

# 3. Socket/Port موجود؟
ls -la /path/to/app.sock
# یا
netstat -tlnp | grep 8000

# 4. Permissions درست؟
ls -la /path/to/app.sock

# 5. Logs چه می‌گویند؟
sudo journalctl -u regions-map-app -n 50
sudo tail -20 /var/log/nginx/error.log
```

---

## اگر هنوز مشکل دارید:

1. تمام logs را بررسی کنید
2. Config files را دوباره بررسی کنید
3. مطمئن شوید که app.py بدون خطا اجرا می‌شود
4. Dependencies را دوباره نصب کنید


