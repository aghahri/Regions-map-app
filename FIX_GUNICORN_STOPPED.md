# رفع مشکل Gunicorn Stopped

## مشکل: Gunicorn service متوقف است

---

## راه حل 1: Start کردن Service

```bash
# Start کردن
sudo systemctl start regions-map-app

# بررسی وضعیت
sudo systemctl status regions-map-app

# اگر start نشد، logs را ببینید
sudo journalctl -u regions-map-app -n 50
```

---

## راه حل 2: بررسی Logs برای پیدا کردن خطا

```bash
# دیدن آخرین خطاها
sudo journalctl -u regions-map-app -n 100 --no-pager

# یا
sudo journalctl -u regions-map-app --since "10 minutes ago"
```

خطاهای رایج:
- `ModuleNotFoundError`: dependency نصب نشده
- `ImportError`: مشکل import
- `Permission denied`: مشکل دسترسی
- `File not found`: فایل پیدا نشد

---

## راه حل 3: بررسی Dependencies

```bash
cd /path/to/Regions-map-app/regions-map-app
source venv/bin/activate

# تست import
python -c "import app; print('OK')"

# اگر خطا داد:
pip install -r requirements.txt
```

---

## راه حل 4: بررسی Systemd Service File

```bash
# بررسی service file
sudo cat /etc/systemd/system/regions-map-app.service

# بررسی مسیرها
# مطمئن شوید که:
# - WorkingDirectory درست است
# - ExecStart path درست است
# - User/Group درست است
```

---

## راه حل 5: اجرای دستی برای تست

```bash
cd /path/to/Regions-map-app/regions-map-app
source venv/bin/activate

# تست مستقیم
gunicorn --bind 127.0.0.1:8000 app:app
```

اگر این کار کرد، مشکل از systemd service است.

---

## راه حل 6: Rebuild Service (اگر نیاز باشد)

```bash
# Stop کردن
sudo systemctl stop regions-map-app

# پیدا کردن مسیر پروژه
APP_PATH=$(find / -name "app.py" -path "*/regions-map-app/*" 2>/dev/null | head -1)
APP_DIR=$(dirname "$APP_PATH")
VENV_PATH="$APP_DIR/venv"

echo "App path: $APP_DIR"
echo "Venv path: $VENV_PATH"

# ساخت service file
sudo tee /etc/systemd/system/regions-map-app.service > /dev/null <<EOF
[Unit]
Description=Gunicorn instance for Regions Map App
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=$APP_DIR
Environment="PATH=$VENV_PATH/bin"
ExecStart=$VENV_PATH/bin/gunicorn \\
          --workers 3 \\
          --bind unix:$APP_DIR/app.sock \\
          app:app

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
sudo systemctl daemon-reload

# Enable و Start
sudo systemctl enable regions-map-app
sudo systemctl start regions-map-app

# بررسی
sudo systemctl status regions-map-app
```

---

## راه حل 7: بررسی Permissions

```bash
# بررسی ownership
ls -la /path/to/Regions-map-app/regions-map-app/

# اگر نیاز باشد:
sudo chown -R www-data:www-data /path/to/Regions-map-app/regions-map-app/
```

---

## راه حل 8: بررسی Python Version

```bash
cd /path/to/Regions-map-app/regions-map-app
source venv/bin/activate

# بررسی Python version
python --version

# باید Python 3.11 یا بالاتر باشد
```

---

## چک‌لیست سریع:

```bash
# 1. Service file موجود است؟
ls -la /etc/systemd/system/regions-map-app.service

# 2. مسیرها درست هستند؟
sudo cat /etc/systemd/system/regions-map-app.service

# 3. Dependencies نصب شده؟
cd /path/to/Regions-map-app/regions-map-app
source venv/bin/activate
pip list | grep -E "flask|gunicorn|geopandas"

# 4. App import می‌شود؟
python -c "import app"

# 5. Logs چه می‌گویند؟
sudo journalctl -u regions-map-app -n 50
```

---

## اگر هنوز مشکل دارید:

خروجی این دستورات را بفرستید:

```bash
# 1. Service file
sudo cat /etc/systemd/system/regions-map-app.service

# 2. Logs
sudo journalctl -u regions-map-app -n 100 --no-pager

# 3. Test import
cd /path/to/Regions-map-app/regions-map-app
source venv/bin/activate
python -c "import app" 2>&1

# 4. Test gunicorn
gunicorn --bind 127.0.0.1:8000 app:app 2>&1 | head -20
```


