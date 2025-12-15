#!/bin/bash

# اسکریپت نصب مجدد کامل از GitHub و تنظیم nginx
# این اسکریپت همه چیز را از GitHub می‌گیرد و تنظیم می‌کند

set -e  # در صورت خطا متوقف شود

echo "🚀 شروع نصب مجدد از GitHub..."
echo ""

# 1. ساخت دایرکتوری اصلی
echo "1️⃣ ساخت دایرکتوری اصلی..."
sudo mkdir -p /var/www/regions-map-app
sudo chown -R $USER:$USER /var/www/regions-map-app
cd /var/www/regions-map-app

# 2. Clone از GitHub
echo "2️⃣ Clone از GitHub..."
if [ -d "regions-map-app" ]; then
    echo "   ⚠️  دایرکتوری regions-map-app وجود دارد، حذف می‌شود..."
    rm -rf regions-map-app
fi

git clone https://github.com/aghahri/Regions-map-app.git regions-map-app
cd regions-map-app

# 3. ساخت virtual environment
echo "3️⃣ ساخت virtual environment..."
if [ -d "../venv" ]; then
    echo "   ⚠️  virtual environment وجود دارد، حذف می‌شود..."
    rm -rf ../venv
fi

python3 -m venv ../venv
source ../venv/bin/activate

# 4. نصب dependencies
echo "4️⃣ نصب dependencies..."
pip install --upgrade pip
pip install flask gunicorn geopandas fiona shapely pyproj

# 5. ساخت systemd service
echo "5️⃣ ساخت systemd service..."
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
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# 6. تنظیم nginx
echo "6️⃣ تنظیم nginx..."
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
        proxy_set_header X-Forwarded-Host \$server_name;
        proxy_buffering off;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
}
EOF

# فعال کردن config
sudo ln -sf /etc/nginx/sites-available/regions-map-app /etc/nginx/sites-enabled/regions-map-app

# غیرفعال کردن config‌های دیگر
sudo rm -f /etc/nginx/sites-enabled/00-default-ip 2>/dev/null || true
sudo rm -f /etc/nginx/sites-enabled/iranregions.com 2>/dev/null || true
sudo rm -f /etc/nginx/sites-enabled/iranregions.ir 2>/dev/null || true

# 7. ساخت دایرکتوری‌های لازم
echo "7️⃣ ساخت دایرکتوری‌های لازم..."
sudo mkdir -p /var/www/regions-map-app/uploads/uploads/regions/logos
sudo mkdir -p /var/www/regions-map-app/uploads/uploads/regions/neighborhood_edits
sudo mkdir -p /var/www/regions-map-app/backups

# 8. تنظیم دسترسی‌ها
echo "8️⃣ تنظیم دسترسی‌ها..."
sudo chown -R www-data:www-data /var/www/regions-map-app/regions-map-app
sudo chown -R www-data:www-data /var/www/regions-map-app/uploads
sudo chmod -R 755 /var/www/regions-map-app/regions-map-app
sudo chmod -R 755 /var/www/regions-map-app/uploads

# 9. تست nginx config
echo "9️⃣ تست nginx config..."
sudo nginx -t

# 10. فعال کردن و شروع سرویس‌ها
echo "🔟 فعال کردن و شروع سرویس‌ها..."
sudo systemctl daemon-reload
sudo systemctl enable regions-map-app
sudo systemctl restart regions-map-app
sudo systemctl restart nginx

# 11. بررسی وضعیت
echo ""
echo "1️⃣1️⃣ بررسی وضعیت سرویس‌ها..."
echo ""
echo "📋 وضعیت Flask:"
sudo systemctl status regions-map-app --no-pager | head -10
echo ""
echo "📋 وضعیت nginx:"
sudo systemctl status nginx --no-pager | head -10

# 12. تست
echo ""
echo "1️⃣2️⃣ تست..."
echo ""
echo "🔍 تست Flask (localhost:8000):"
curl -I http://127.0.0.1:8000 2>&1 | head -3
echo ""
echo "🔍 تست nginx (171.22.27.42):"
curl -I http://171.22.27.42 2>&1 | head -3

echo ""
echo "✅ نصب مجدد کامل شد!"
echo ""
echo "📋 خلاصه:"
echo "   - کد از GitHub clone شد"
echo "   - Virtual environment ساخته شد"
echo "   - Dependencies نصب شدند"
echo "   - systemd service تنظیم شد"
echo "   - nginx config تنظیم شد"
echo "   - سرویس‌ها راه‌اندازی شدند"
echo ""
echo "🌐 آدرس سایت: http://171.22.27.42"
echo ""

