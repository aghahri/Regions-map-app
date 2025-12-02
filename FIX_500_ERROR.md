# رفع خطای 500 Internal Server Error

## مشکل: 500 Internal Server Error در `/admin`

این خطا یعنی Gunicorn در حال اجرا است اما app خطا دارد.

---

## راه حل 1: بررسی Logs Gunicorn

```bash
# دیدن آخرین خطاها
sudo journalctl -u regions-map-app -n 100 --no-pager

# یا live logs
sudo journalctl -u regions-map-app -f
```

خطاهای رایج:
- `ModuleNotFoundError`: dependency نصب نشده
- `ImportError`: مشکل import
- `FileNotFoundError`: فایل پیدا نشد
- `PermissionError`: مشکل دسترسی

---

## راه حل 2: بررسی Dependencies

```bash
cd /var/www/regions-map-app/regions-map-app
source /var/www/regions-map-app/venv/bin/activate

# بررسی dependencies
pip list | grep -E "flask|geopandas|shapely"

# نصب مجدد
pip install -r requirements.txt
```

---

## راه حل 3: تست Import

```bash
cd /var/www/regions-map-app/regions-map-app
source /var/www/regions-map-app/venv/bin/activate

# تست import
python -c "import app; print('OK')"
```

اگر خطا داد، خطای دقیق را ببینید.

---

## راه حل 4: بررسی فایل‌ها

```bash
# بررسی وجود فایل‌های مهم
ls -la /var/www/regions-map-app/regions-map-app/app.py
ls -la /var/www/regions-map-app/regions-map-app/requirements.txt

# بررسی permissions
ls -la /var/www/regions-map-app/regions-map-app/
```

---

## راه حل 5: بررسی Environment Variables

```bash
# بررسی که SECRET_KEY و ADMIN_PASSWORD تنظیم شده‌اند
# در systemd service یا .env file

# اگر در service file نیست، اضافه کنید:
sudo systemctl edit regions-map-app
```

یا در service file:
```ini
Environment="SECRET_KEY=your-secret-key"
Environment="ADMIN_PASSWORD=your-password"
```

---

## راه حل 6: اجرای دستی برای دیدن خطا

```bash
cd /var/www/regions-map-app/regions-map-app
source /var/www/regions-map-app/venv/bin/activate

# اجرای Flask مستقیم
export FLASK_APP=app.py
export SECRET_KEY=test-secret-key
export ADMIN_PASSWORD=test-password
flask run --host=0.0.0.0 --port=5000
```

خطای دقیق را ببینید.

---

## راه حل 7: بررسی Uploads Directory

```bash
# بررسی وجود uploads directory
ls -la /var/www/regions-map-app/regions-map-app/uploads/

# اگر وجود ندارد:
mkdir -p /var/www/regions-map-app/regions-map-app/uploads/regions/storage
chown -R www-data:www-data /var/www/regions-map-app/regions-map-app/uploads
```

---

## چک‌لیست سریع:

```bash
# 1. Logs
sudo journalctl -u regions-map-app -n 100 --no-pager

# 2. Dependencies
cd /var/www/regions-map-app/regions-map-app
source /var/www/regions-map-app/venv/bin/activate
pip list | grep -E "flask|geopandas"

# 3. Test import
python -c "import app" 2>&1

# 4. Test run
python app.py 2>&1 | head -20
```

---

## اگر هنوز مشکل دارید:

خروجی این دستورات را بفرستید:

```bash
# 1. Logs کامل
sudo journalctl -u regions-map-app -n 200 --no-pager

# 2. Test import
cd /var/www/regions-map-app/regions-map-app
source /var/www/regions-map-app/venv/bin/activate
python -c "import app" 2>&1

# 3. Test run
python app.py 2>&1
```

