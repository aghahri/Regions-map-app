# دستورات Deploy روی سرور

## Pull آخرین ورژن از GitHub

### 1. اتصال به سرور
```bash
ssh user@your-server-ip
```

### 2. رفتن به دایرکتوری پروژه
```bash
cd /path/to/your/project
# یا اگر در home directory است:
cd ~/Regions-map-app
```

### 3. Pull آخرین تغییرات
```bash
# اگر اولین بار است:
git clone https://github.com/aghahri/Regions-map-app.git
cd Regions-map-app

# اگر قبلاً clone کرده‌اید:
git pull origin main
```

### 4. نصب/به‌روزرسانی Dependencies
```bash
# اگر virtual environment دارید:
source venv/bin/activate  # یا .venv/bin/activate

# نصب requirements
pip install -r requirements.txt

# برای regions-map-app:
cd regions-map-app
pip install -r requirements.txt
```

### 5. Restart سرویس (اگر با systemd اجرا می‌شود)
```bash
# برای Flask/Gunicorn:
sudo systemctl restart your-app-name
# یا
sudo systemctl restart regions-map-app

# بررسی وضعیت:
sudo systemctl status your-app-name
```

### 6. اگر با PM2 اجرا می‌شود:
```bash
pm2 restart regions-map-app
# یا
pm2 reload regions-map-app
```

### 7. اگر با Supervisor اجرا می‌شود:
```bash
sudo supervisorctl restart regions-map-app
```

---

## اسکریپت خودکار برای Deploy

می‌توانید یک فایل `deploy.sh` بسازید:

```bash
#!/bin/bash
# deploy.sh

echo "🔄 Pulling latest changes..."
git pull origin main

echo "📦 Installing dependencies..."
cd regions-map-app
source venv/bin/activate
pip install -r requirements.txt

echo "🔄 Restarting service..."
sudo systemctl restart regions-map-app

echo "✅ Deploy completed!"
```

سپس:
```bash
chmod +x deploy.sh
./deploy.sh
```

---

## نکات مهم:

1. **Backup قبل از Deploy:**
```bash
cp -r regions-map-app regions-map-app-backup-$(date +%Y%m%d)
```

2. **بررسی تغییرات قبل از Pull:**
```bash
git fetch origin
git log HEAD..origin/main --oneline
```

3. **اگر conflict دارید:**
```bash
git stash
git pull origin main
git stash pop
```

4. **اگر می‌خواهید به ورژن خاصی برگردید:**
```bash
git checkout <commit-hash>
```

---

## برای سرورهای مختلف:

### Nginx + Gunicorn (راهنمای کامل):

#### 1. Pull آخرین تغییرات:
```bash
cd /path/to/Regions-map-app
git pull origin main
```

#### 2. به‌روزرسانی Dependencies:
```bash
cd regions-map-app
source venv/bin/activate  # یا .venv/bin/activate
pip install -r requirements.txt
```

#### 3. Restart Gunicorn:
```bash
# اگر با systemd اجرا می‌شود:
sudo systemctl restart regions-map-app
# یا
sudo systemctl restart gunicorn

# بررسی وضعیت:
sudo systemctl status regions-map-app
```

#### 4. Restart Nginx:
```bash
sudo systemctl restart nginx

# بررسی وضعیت:
sudo systemctl status nginx

# تست تنظیمات Nginx:
sudo nginx -t
```

#### 5. بررسی Logs:
```bash
# Logs Gunicorn:
sudo journalctl -u regions-map-app -f
# یا
tail -f /var/log/gunicorn/error.log

# Logs Nginx:
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log
```

---

### تنظیمات Systemd Service برای Gunicorn:

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

### تنظیمات Nginx:

فایل `/etc/nginx/sites-available/regions-map-app`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        include proxy_params;
        proxy_pass http://unix:/path/to/Regions-map-app/regions-map-app/app.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /path/to/Regions-map-app/regions-map-app/static;
    }

    location /uploads {
        alias /path/to/Regions-map-app/regions-map-app/uploads;
    }
}
```

فعال کردن:
```bash
sudo ln -s /etc/nginx/sites-available/regions-map-app /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Apache + mod_wsgi:
```bash
git pull origin main
cd regions-map-app
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart apache2
```

### Docker:
```bash
git pull origin main
docker-compose down
docker-compose up -d --build
```

