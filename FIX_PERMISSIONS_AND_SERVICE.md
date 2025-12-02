# رفع مشکل Permission و Service

## مشکلات:
1. `ModuleNotFoundError: No module named 'app'` - WorkingDirectory اشتباه
2. `PermissionError` - www-data نمی‌تواند در uploads بنویسد

---

## راه حل کامل:

### روی سرور این دستورات را اجرا کنید:

```bash
# 1. اصلاح Permissions برای uploads
sudo mkdir -p /var/www/regions-map-app/regions-map-app/uploads/regions/storage
sudo mkdir -p /var/www/regions-map-app/regions-map-app/uploads/regions/links
sudo chown -R www-data:www-data /var/www/regions-map-app/regions-map-app/uploads
sudo chmod -R 755 /var/www/regions-map-app/regions-map-app/uploads

# 2. اصلاح Service File
sudo tee /etc/systemd/system/regions-map-app.service > /dev/null <<'EOF'
[Unit]
Description=Gunicorn instance for Regions Map App
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/regions-map-app/regions-map-app
Environment="PATH=/var/www/regions-map-app/venv/bin"
ExecStart=/var/www/regions-map-app/venv/bin/gunicorn \
          --workers 3 \
          --bind 127.0.0.1:8000 \
          app:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# 3. Reload systemd
sudo systemctl daemon-reload

# 4. بررسی وجود app.py
ls -la /var/www/regions-map-app/regions-map-app/app.py

# 5. بررسی permissions
ls -la /var/www/regions-map-app/regions-map-app/uploads/

# 6. Start service
sudo systemctl start regions-map-app

# 7. بررسی وضعیت
sudo systemctl status regions-map-app
```

---

## اگر هنوز مشکل دارد:

### بررسی دقیق:
```bash
# 1. بررسی app.py
ls -la /var/www/regions-map-app/regions-map-app/app.py

# 2. تست import به عنوان www-data
sudo -u www-data /var/www/regions-map-app/venv/bin/python -c "import sys; sys.path.insert(0, '/var/www/regions-map-app/regions-map-app'); import app; print('OK')"

# 3. بررسی permissions uploads
sudo -u www-data touch /var/www/regions-map-app/regions-map-app/uploads/test.txt
sudo rm /var/www/regions-map-app/regions-map-app/uploads/test.txt
```

---

## اگر app.py در مسیر دیگری است:

```bash
# پیدا کردن app.py
find /var/www -name "app.py" -type f

# اگر در مسیر دیگری است، WorkingDirectory را تغییر دهید
```

