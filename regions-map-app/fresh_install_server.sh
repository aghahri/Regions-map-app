#!/bin/bash

# اسکریپت نصب مجدد کامل سرور (به جز بک‌آپ‌ها)
# ⚠️ هشدار: این اسکریپت همه چیز را پاک می‌کند به جز فایل‌های بک‌آپ

set -e  # در صورت خطا متوقف شود

echo "⚠️  هشدار: این اسکریپت همه چیز را پاک می‌کند به جز فایل‌های بک‌آپ!"
echo "📦 فایل‌های بک‌آپ حفظ می‌شوند:"
echo "   - /var/www/regions-map-app/backups/"
echo "   - /var/www/regions-map-app/uploads/"
echo ""
read -p "آیا مطمئن هستید؟ (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ عملیات لغو شد."
    exit 1
fi

echo ""
echo "🚀 شروع نصب مجدد..."
echo ""

# 1. توقف سرویس‌ها
echo "1️⃣ توقف سرویس‌ها..."
sudo systemctl stop regions-map-app 2>/dev/null || true
sudo systemctl stop nginx 2>/dev/null || true

# 2. پیدا کردن مسیر بک‌آپ
BACKUP_DIR="/var/www/regions-map-app/backups"
UPLOADS_DIR="/var/www/regions-map-app/uploads"
APP_DIR="/var/www/regions-map-app/regions-map-app"

# 3. ساخت مسیر موقت برای بک‌آپ
TEMP_BACKUP="/tmp/regions-map-backup-$(date +%Y%m%d_%H%M%S)"
mkdir -p "$TEMP_BACKUP"

echo "2️⃣ کپی فایل‌های بک‌آپ به مسیر موقت..."

# کپی بک‌آپ‌ها
if [ -d "$BACKUP_DIR" ]; then
    echo "   📦 کپی بک‌آپ‌ها..."
    cp -r "$BACKUP_DIR" "$TEMP_BACKUP/backups" 2>/dev/null || true
fi

# کپی uploads (شامل logos, edits, links)
if [ -d "$UPLOADS_DIR" ]; then
    echo "   📦 کپی uploads..."
    cp -r "$UPLOADS_DIR" "$TEMP_BACKUP/uploads" 2>/dev/null || true
fi

echo "   ✅ فایل‌های بک‌آپ کپی شدند به: $TEMP_BACKUP"
echo ""

# 4. پاک کردن دایرکتوری اصلی
echo "3️⃣ پاک کردن دایرکتوری اصلی..."
if [ -d "/var/www/regions-map-app" ]; then
    sudo rm -rf /var/www/regions-map-app
    echo "   ✅ دایرکتوری اصلی پاک شد"
fi

# 5. ساخت دایرکتوری جدید
echo "4️⃣ ساخت دایرکتوری جدید..."
sudo mkdir -p /var/www/regions-map-app
sudo chown -R $USER:$USER /var/www/regions-map-app
cd /var/www/regions-map-app

# 6. Clone از GitHub
echo "5️⃣ Clone از GitHub..."
git clone https://github.com/aghahri/Regions-map-app.git regions-map-app
cd regions-map-app

# 7. ساخت virtual environment
echo "6️⃣ ساخت virtual environment..."
python3 -m venv ../venv
source ../venv/bin/activate

# 8. نصب dependencies
echo "7️⃣ نصب dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# 9. بازگرداندن فایل‌های بک‌آپ
echo "8️⃣ بازگرداندن فایل‌های بک‌آپ..."

# بازگرداندن backups
if [ -d "$TEMP_BACKUP/backups" ]; then
    echo "   📦 بازگرداندن بک‌آپ‌ها..."
    sudo mkdir -p /var/www/regions-map-app/backups
    sudo cp -r "$TEMP_BACKUP/backups"/* /var/www/regions-map-app/backups/ 2>/dev/null || true
fi

# بازگرداندن uploads
if [ -d "$TEMP_BACKUP/uploads" ]; then
    echo "   📦 بازگرداندن uploads..."
    sudo mkdir -p /var/www/regions-map-app/uploads
    sudo cp -r "$TEMP_BACKUP/uploads"/* /var/www/regions-map-app/uploads/ 2>/dev/null || true
fi

# تنظیم دسترسی‌ها
echo "   🔐 تنظیم دسترسی‌ها..."
sudo chown -R www-data:www-data /var/www/regions-map-app/uploads
sudo chmod -R 755 /var/www/regions-map-app/uploads

# 10. ساخت systemd service
echo "9️⃣ ساخت systemd service..."
sudo tee /etc/systemd/system/regions-map-app.service > /dev/null <<EOF
[Unit]
Description=Regions Map App (Gunicorn)
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/regions-map-app/regions-map-app
Environment="PATH=/var/www/regions-map-app/venv/bin"
ExecStart=/var/www/regions-map-app/venv/bin/gunicorn --workers 2 --bind 127.0.0.1:8000 app:app

[Install]
WantedBy=multi-user.target
EOF

# 11. تنظیم nginx
echo "🔟 تنظیم nginx..."
sudo tee /etc/nginx/sites-available/regions-map-app > /dev/null <<EOF
server {
    listen 80;
    server_name iranregions.com www.iranregions.com;

    client_max_body_size 200M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# فعال کردن config
sudo ln -sf /etc/nginx/sites-available/regions-map-app /etc/nginx/sites-enabled/regions-map-app

# غیرفعال کردن config‌های دیگر (اگر لازم بود)
sudo rm -f /etc/nginx/sites-enabled/00-default-ip 2>/dev/null || true
sudo rm -f /etc/nginx/sites-enabled/iranregions.com 2>/dev/null || true
sudo rm -f /etc/nginx/sites-enabled/iranregions.ir 2>/dev/null || true

# 12. تست nginx config
echo "1️⃣1️⃣ تست nginx config..."
sudo nginx -t

# 13. تنظیم دسترسی‌ها
echo "1️⃣2️⃣ تنظیم دسترسی‌ها..."
sudo chown -R www-data:www-data /var/www/regions-map-app/regions-map-app
sudo chmod -R 755 /var/www/regions-map-app/regions-map-app

# 14. فعال کردن و شروع سرویس‌ها
echo "1️⃣3️⃣ فعال کردن و شروع سرویس‌ها..."
sudo systemctl daemon-reload
sudo systemctl enable regions-map-app
sudo systemctl start regions-map-app
sudo systemctl restart nginx

# 15. بررسی وضعیت
echo ""
echo "1️⃣4️⃣ بررسی وضعیت سرویس‌ها..."
sudo systemctl status regions-map-app --no-pager | head -10
sudo systemctl status nginx --no-pager | head -10

# 16. پاک کردن فایل‌های موقت
echo ""
read -p "آیا می‌خواهید فایل‌های موقت بک‌آپ را پاک کنید؟ (yes/no): " cleanup
if [ "$cleanup" == "yes" ]; then
    rm -rf "$TEMP_BACKUP"
    echo "   ✅ فایل‌های موقت پاک شدند"
else
    echo "   📦 فایل‌های موقت در: $TEMP_BACKUP"
fi

echo ""
echo "✅ نصب مجدد کامل شد!"
echo ""
echo "📋 خلاصه:"
echo "   - کد از GitHub clone شد"
echo "   - Virtual environment ساخته شد"
echo "   - Dependencies نصب شدند"
echo "   - فایل‌های بک‌آپ بازگردانده شدند"
echo "   - سرویس‌ها راه‌اندازی شدند"
echo ""
echo "🔍 تست:"
echo "   curl -I http://127.0.0.1:8000"
echo "   curl -I http://171.22.27.42"

