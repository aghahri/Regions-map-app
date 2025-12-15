#!/bin/bash

# اسکریپت بک‌آپ همه فایل‌ها و پاک کردن کامل سرور
# ⚠️ هشدار: این اسکریپت همه چیز را پاک می‌کند بعد از بک‌آپ

set -e  # در صورت خطا متوقف شود

echo "⚠️  هشدار: این اسکریپت همه فایل‌ها را بک‌آپ می‌گیرد و سپس همه چیز را پاک می‌کند!"
echo ""
read -p "آیا مطمئن هستید؟ (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ عملیات لغو شد."
    exit 1
fi

echo ""
echo "🚀 شروع بک‌آپ و پاک کردن..."
echo ""

# 1. توقف سرویس‌ها
echo "1️⃣ توقف سرویس‌ها..."
sudo systemctl stop regions-map-app 2>/dev/null || true
sudo systemctl stop nginx 2>/dev/null || true

# 2. ساخت مسیر بک‌آپ خارجی
BACKUP_ROOT="/root/regions-map-backup-$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_ROOT"

echo "2️⃣ ساخت مسیر بک‌آپ: $BACKUP_ROOT"
echo ""

# 3. بک‌آپ همه فایل‌ها
echo "3️⃣ بک‌آپ همه فایل‌ها..."

# بک‌آپ کل دایرکتوری
if [ -d "/var/www/regions-map-app" ]; then
    echo "   📦 بک‌آپ کل دایرکتوری..."
    sudo cp -r /var/www/regions-map-app "$BACKUP_ROOT/" 2>/dev/null || true
    echo "   ✅ کل دایرکتوری بک‌آپ شد"
fi

# بک‌آپ systemd service
if [ -f "/etc/systemd/system/regions-map-app.service" ]; then
    echo "   📦 بک‌آپ systemd service..."
    sudo cp /etc/systemd/system/regions-map-app.service "$BACKUP_ROOT/" 2>/dev/null || true
    echo "   ✅ systemd service بک‌آپ شد"
fi

# بک‌آپ nginx config
if [ -f "/etc/nginx/sites-available/regions-map-app" ]; then
    echo "   📦 بک‌آپ nginx config..."
    sudo cp /etc/nginx/sites-available/regions-map-app "$BACKUP_ROOT/" 2>/dev/null || true
    echo "   ✅ nginx config بک‌آپ شد"
fi

# بک‌آپ nginx enabled configs
if [ -d "/etc/nginx/sites-enabled" ]; then
    echo "   📦 بک‌آپ nginx enabled configs..."
    sudo cp -r /etc/nginx/sites-enabled "$BACKUP_ROOT/nginx-sites-enabled" 2>/dev/null || true
    echo "   ✅ nginx enabled configs بک‌آپ شد"
fi

# تنظیم دسترسی‌ها
sudo chown -R $USER:$USER "$BACKUP_ROOT"

echo ""
echo "   ✅ همه فایل‌ها بک‌آپ شدند به: $BACKUP_ROOT"
echo ""

# 4. لیست فایل‌های بک‌آپ شده
echo "4️⃣ لیست فایل‌های بک‌آپ شده:"
ls -lh "$BACKUP_ROOT"
echo ""

# 5. پاک کردن دایرکتوری اصلی
echo "5️⃣ پاک کردن دایرکتوری اصلی..."
read -p "آیا می‌خواهید همه چیز را پاک کنید؟ (yes/no): " cleanup_confirm

if [ "$cleanup_confirm" == "yes" ]; then
    if [ -d "/var/www/regions-map-app" ]; then
        sudo rm -rf /var/www/regions-map-app
        echo "   ✅ دایرکتوری اصلی پاک شد"
    fi
    
    # غیرفعال کردن systemd service (نه حذف)
    sudo systemctl disable regions-map-app 2>/dev/null || true
    echo "   ✅ systemd service غیرفعال شد"
    
    echo ""
    echo "✅ پاک کردن کامل شد!"
else
    echo "   ⚠️  پاک کردن لغو شد"
fi

echo ""
echo "✅ بک‌آپ کامل شد!"
echo ""
echo "📋 خلاصه:"
echo "   - همه فایل‌ها بک‌آپ شدند به: $BACKUP_ROOT"
echo "   - شامل:"
echo "     • کل دایرکتوری /var/www/regions-map-app"
echo "     • systemd service"
echo "     • nginx configs"
echo ""
echo "📦 برای بازگرداندن:"
echo "   sudo cp -r $BACKUP_ROOT/regions-map-app /var/www/"
echo "   sudo cp $BACKUP_ROOT/regions-map-app.service /etc/systemd/system/"
echo "   sudo cp $BACKUP_ROOT/regions-map-app /etc/nginx/sites-available/"
echo ""

