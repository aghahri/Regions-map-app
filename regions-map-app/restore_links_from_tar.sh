#!/bin/bash

# اسکریپت بازگرداندن لینک‌های توت اپ از فایل‌های tar.gz

set -e  # در صورت خطا متوقف شود

echo "🔄 شروع بازگرداندن لینک‌های توت اپ..."
echo ""

# 1. پیدا کردن بک‌آپ‌های links
BACKUP_DIR="/root/regions-backups"
LINKS_TARGET="/var/www/regions-map-app/uploads/regions/links"

echo "1️⃣ پیدا کردن بک‌آپ‌های links..."

# بررسی وجود دایرکتوری
if [ ! -d "$BACKUP_DIR" ]; then
    echo "   ❌ دایرکتوری بک‌آپ پیدا نشد: $BACKUP_DIR"
    exit 1
fi

# پیدا کردن آخرین فایل بک‌آپ
LATEST_BACKUP=$(ls -t "$BACKUP_DIR"/links_backup_*.tar.gz 2>/dev/null | head -1)

if [ -z "$LATEST_BACKUP" ]; then
    echo "   ❌ هیچ فایل بک‌آپی پیدا نشد!"
    exit 1
fi

echo "   ✅ آخرین بک‌آپ پیدا شد: $LATEST_BACKUP"

# 2. ساخت دایرکتوری هدف
echo ""
echo "2️⃣ ساخت دایرکتوری هدف..."
sudo mkdir -p "$LINKS_TARGET"
echo "   ✅ دایرکتوری ساخته شد: $LINKS_TARGET"

# 3. Extract فایل بک‌آپ
echo ""
echo "3️⃣ Extract فایل بک‌آپ..."

TEMP_DIR="/tmp/links_restore_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$TEMP_DIR"

echo "   📦 Extract کردن: $LATEST_BACKUP"
tar -xzf "$LATEST_BACKUP" -C "$TEMP_DIR" 2>/dev/null || {
    echo "   ❌ خطا در extract کردن فایل!"
    exit 1
}

echo "   ✅ فایل extract شد"

# 4. پیدا کردن فایل‌های links
echo ""
echo "4️⃣ پیدا کردن فایل‌های links..."

# جستجوی فایل‌های JSON
LINK_FILES=$(find "$TEMP_DIR" -type f -name "*.json" 2>/dev/null)

if [ -z "$LINK_FILES" ]; then
    echo "   ⚠️  هیچ فایل JSON پیدا نشد"
    echo "   🔍 بررسی محتوای extract شده..."
    ls -la "$TEMP_DIR"
else
    LINK_COUNT=$(echo "$LINK_FILES" | wc -l)
    echo "   ✅ $LINK_COUNT فایل links پیدا شد"
fi

# 5. کپی فایل‌های links
echo ""
echo "5️⃣ کپی فایل‌های links..."

if [ -n "$LINK_FILES" ]; then
    echo "$LINK_FILES" | while read file; do
        filename=$(basename "$file")
        echo "   📦 کپی: $filename"
        sudo cp "$file" "$LINKS_TARGET/$filename" 2>/dev/null || true
    done
    echo "   ✅ فایل‌ها کپی شدند"
else
    # اگر فایل JSON پیدا نشد، کل محتوا را کپی می‌کنیم
    echo "   📦 کپی کل محتوا..."
    sudo cp -r "$TEMP_DIR"/* "$LINKS_TARGET/" 2>/dev/null || true
    echo "   ✅ محتوا کپی شد"
fi

# 6. تنظیم دسترسی‌ها
echo ""
echo "6️⃣ تنظیم دسترسی‌ها..."
sudo chown -R www-data:www-data "$LINKS_TARGET"
sudo chmod -R 755 "$LINKS_TARGET"
echo "   ✅ دسترسی‌ها تنظیم شد"

# 7. بررسی نتیجه
echo ""
echo "7️⃣ بررسی نتیجه..."
RESTORED_LINKS=$(find "$LINKS_TARGET" -type f -name "*.json" 2>/dev/null | wc -l)
echo "   📊 تعداد فایل‌های links بازگردانده شده: $RESTORED_LINKS"

if [ "$RESTORED_LINKS" -gt 0 ]; then
    echo ""
    echo "✅ بازگرداندن لینک‌ها با موفقیت انجام شد!"
    echo ""
    echo "📋 خلاصه:"
    echo "   - تعداد فایل‌های links: $RESTORED_LINKS"
    echo "   - مسیر: $LINKS_TARGET"
    echo ""
    echo "🔍 برای بررسی:"
    echo "   ls -lh $LINKS_TARGET | head -10"
else
    echo ""
    echo "⚠️  هیچ فایل link بازگردانده نشد!"
    echo "   لطفاً بررسی کنید که فایل بک‌آپ درست است."
fi

# 8. پاک کردن فایل‌های موقت
echo ""
read -p "آیا می‌خواهید فایل‌های موقت را پاک کنید؟ (yes/no): " cleanup
if [ "$cleanup" == "yes" ]; then
    rm -rf "$TEMP_DIR"
    echo "   ✅ فایل‌های موقت پاک شدند"
else
    echo "   📦 فایل‌های موقت در: $TEMP_DIR"
fi

echo ""
echo "✅ تمام!"

