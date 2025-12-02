# رفع مشکل سرور - مسیر venv اشتباه

## مشکل: 
- venv در `/var/www/regions-map-app/venv` است
- Service file به مسیر اشتباه اشاره می‌کند
- Gunicorn با exit code 3 متوقف می‌شود

---

## راه حل: اصلاح Service File

### روی سرور این دستورات را اجرا کنید:

```bash
# 1. بررسی service file فعلی
sudo cat /etc/systemd/system/regions-map-app.service

# 2. ساخت service file جدید با مسیر درست
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

# 4. بررسی dependencies
cd /var/www/regions-map-app/regions-map-app
source /var/www/regions-map-app/venv/bin/activate
pip install -r requirements.txt

# 5. تست import
python -c "import app; print('OK')"

# 6. Start service
sudo systemctl start regions-map-app

# 7. بررسی وضعیت
sudo systemctl status regions-map-app
```

---

## اگر هنوز خطا می‌دهد:

### بررسی Logs دقیق:
```bash
sudo journalctl -xeu regions-map-app.service -n 50 --no-pager
```

### تست دستی Gunicorn:
```bash
cd /var/www/regions-map-app/regions-map-app
source /var/www/regions-map-app/venv/bin/activate
gunicorn --bind 127.0.0.1:8000 app:app
```

خطای دقیق را ببینید و بفرستید.

---

## بررسی Nginx Config:

```bash
# بررسی که proxy_pass به port 8000 اشاره می‌کند
sudo grep -r "proxy_pass" /etc/nginx/sites-enabled/

# باید چیزی مثل این باشد:
# proxy_pass http://127.0.0.1:8000;
```

اگر socket استفاده می‌کند، باید به TCP تغییر دهید یا socket را درست کنید.

