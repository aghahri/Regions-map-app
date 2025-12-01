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

### Nginx + Gunicorn:
```bash
git pull origin main
cd regions-map-app
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart gunicorn
sudo systemctl restart nginx
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

