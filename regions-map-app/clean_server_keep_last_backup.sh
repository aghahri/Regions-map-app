#!/bin/bash

# اسکریپت پاک کردن کامل سرور (به جز آخرین بک‌آپ)
# ⚠️ هشدار: این اسکریپت همه چیز را پاک می‌کند به جز آخرین فایل بک‌آپ

set -e  # در صورت خطا متوقف شود

echo "⚠️  هشدار: این اسکریپت همه چیز را پاک می‌کند به جز آخرین فایل بک‌آپ!"
echo ""
read -p "آیا مطمئن هستید؟ (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ عملیات لغو شد."
    exit 1
fi

echo ""
echo "🚀 شروع پاک کردن..."
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
TEMP_BACKUP="/tmp/regions-map-last-backup-$(date +%Y%m%d_%H%M%S)"
mkdir -p "$TEMP_BACKUP"

echo "2️⃣ پیدا کردن آخرین فایل بک‌آپ..."

# پیدا کردن آخرین فایل بک‌آپ
if [ -d "$BACKUP_DIR" ]; then
    LAST_BACKUP=$(find "$BACKUP_DIR" -type f -name "*.zip" -o -name "*.tar.gz" -o -name "*.tar" | sort -r | head -1)
    
    if [ -n "$LAST_BACKUP" ]; then
        echo "   📦 آخرین بک‌آپ: $LAST_BACKUP"
        cp "$LAST_BACKUP" "$TEMP_BACKUP/last_backup$(basename "$LAST_BACKUP")"
        echo "   ✅ آخرین بک‌آپ کپی شد"
    else
        echo "   ⚠️  هیچ فایل بک‌آپی پیدا نشد"
    fi
fi

# 4. کپی uploads (شامل logos, edits, links)
echo "3️⃣ کپی uploads..."
if [ -d "$UPLOADS_DIR" ]; then
    echo "   📦 کپی uploads..."
    cp -r "$UPLOADS_DIR" "$TEMP_BACKUP/uploads" 2>/dev/null || true
    echo "   ✅ uploads کپی شد"
fi

echo "   ✅ فایل‌های مهم کپی شدند به: $TEMP_BACKUP"
echo ""

# 5. پاک کردن دایرکتوری اصلی
echo "4️⃣ پاک کردن دایرکتوری اصلی..."
if [ -d "/var/www/regions-map-app" ]; then
    sudo rm -rf /var/www/regions-map-app
    echo "   ✅ دایرکتوری اصلی پاک شد"
fi

# 6. ساخت دایرکتوری جدید
echo "5️⃣ ساخت دایرکتوری جدید..."
sudo mkdir -p /var/www/regions-map-app
sudo chown -R $USER:$USER /var/www/regions-map-app

# 7. بازگرداندن آخرین بک‌آپ
echo "6️⃣ بازگرداندن آخرین بک‌آپ..."
if [ -f "$TEMP_BACKUP/last_backup"* ]; then
    sudo mkdir -p /var/www/regions-map-app/backups
    sudo cp "$TEMP_BACKUP"/last_backup* /var/www/regions-map-app/backups/
    echo "   ✅ آخرین بک‌آپ بازگردانده شد"
fi

# 8. بازگرداندن uploads
echo "7️⃣ بازگرداندن uploads..."
if [ -d "$TEMP_BACKUP/uploads" ]; then
    sudo mkdir -p /var/www/regions-map-app/uploads
    sudo cp -r "$TEMP_BACKUP/uploads"/* /var/www/regions-map-app/uploads/ 2>/dev/null || true
    echo "   ✅ uploads بازگردانده شد"
fi

# تنظیم دسترسی‌ها
echo "8️⃣ تنظیم دسترسی‌ها..."
sudo chown -R www-data:www-data /var/www/regions-map-app/uploads 2>/dev/null || true
sudo chmod -R 755 /var/www/regions-map-app/uploads 2>/dev/null || true

echo ""
echo "✅ پاک کردن کامل شد!"
echo ""
echo "📋 خلاصه:"
echo "   - آخرین بک‌آپ حفظ شد در: /var/www/regions-map-app/backups/"
echo "   - uploads حفظ شد در: /var/www/regions-map-app/uploads/"
echo "   - همه چیز دیگر پاک شد"
echo ""
echo "📦 فایل‌های موقت در: $TEMP_BACKUP"
read -p "آیا می‌خواهید فایل‌های موقت را پاک کنید؟ (yes/no): " cleanup
if [ "$cleanup" == "yes" ]; then
    rm -rf "$TEMP_BACKUP"
    echo "   ✅ فایل‌های موقت پاک شدند"
else
    echo "   📦 فایل‌های موقت در: $TEMP_BACKUP"
fi

echo ""
echo "✅ تمام!"

