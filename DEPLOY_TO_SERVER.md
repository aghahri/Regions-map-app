# راهنمای Deploy روی سرور 171.22.27.42

## دستورات کامل برای اجرای آخرین نسخه:

### 1. اتصال به سرور:
```bash
ssh user@171.22.27.42
```

### 2. رفتن به دایرکتوری پروژه:
```bash
cd /path/to/Regions-map-app
# یا اگر در home directory است:
cd ~/Regions-map-app
```

### 3. Pull آخرین تغییرات:
```bash
git pull origin main
```

### 4. رفتن به پوشه app:
```bash
cd regions-map-app
```

### 5. فعال کردن virtual environment:
```bash
source venv/bin/activate
# یا
source .venv/bin/activate
```

### 6. به‌روزرسانی Dependencies (اگر نیاز باشد):
```bash
pip install -r requirements.txt
```

### 7. Restart Gunicorn:
```bash
sudo systemctl restart regions-map-app
# یا
sudo systemctl restart gunicorn
```

### 8. Restart Nginx:
```bash
sudo systemctl restart nginx
```

### 9. بررسی وضعیت:
```bash
sudo systemctl status regions-map-app
sudo systemctl status nginx
```

---

## اسکریپت یک خطی (سریع):

```bash
cd /path/to/Regions-map-app && git pull origin main && cd regions-map-app && source venv/bin/activate && pip install -r requirements.txt && sudo systemctl restart regions-map-app && sudo systemctl restart nginx
```

---

## اگر اولین بار است (Clone):

```bash
cd ~
git clone https://github.com/aghahri/Regions-map-app.git
cd Regions-map-app/regions-map-app
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## بررسی اینکه آخرین نسخه است:

### تست 1: بررسی commit:
```bash
cd /path/to/Regions-map-app
git log --oneline -1
# باید ببینید: "Final setup for Render: all files ready for deployment"
```

### تست 2: بررسی تغییرات:
```bash
git log --oneline -5
```

### تست 3: تست API:
```bash
curl "http://localhost/api/neighborhood?lat=35.6892&lon=51.3890"
```

یا در مرورگر:
```
http://171.22.27.42/api/neighborhood?lat=35.6892&lon=51.3890
```

---

## بررسی Logs (اگر مشکلی بود):

```bash
# Logs Gunicorn
sudo journalctl -u regions-map-app -f --lines=50

# Logs Nginx
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log
```

---

## اگر مشکل از مسیر است:

### پیدا کردن مسیر پروژه:
```bash
find / -name "app.py" -path "*/regions-map-app/*" 2>/dev/null
```

یا:
```bash
ps aux | grep gunicorn
# مسیر را از output پیدا کنید
```

---

## تنظیمات Systemd Service (اگر نیاز باشد):

اگر service ندارید، یک فایل `/etc/systemd/system/regions-map-app.service` بسازید:

```ini
[Unit]
Description=Gunicorn instance for Regions Map App
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/path/to/Regions-map-app/regions-map-app
Environment="PATH=/path/to/Regions-map-app/regions-map-app/venv/bin"
ExecStart=/path/to/Regions-map-app/regions-map-app/venv/bin/gunicorn \
          --workers 3 \
          --bind unix:/path/to/Regions-map-app/regions-map-app/app.sock \
          app:app

[Install]
WantedBy=multi-user.target
```

سپس:
```bash
sudo systemctl daemon-reload
sudo systemctl enable regions-map-app
sudo systemctl start regions-map-app
```

---

## نکات مهم:

1. ✅ مسیر `/path/to/Regions-map-app` را با مسیر واقعی جایگزین کنید
2. ✅ اگر virtual environment ندارید، باید بسازید
3. ✅ بعد از pull، حتماً restart کنید
4. ✅ بررسی کنید که دکمه "اطلاعات محله" را می‌بینید (نه "نمایش ویژگی‌های لایه")

