#!/bin/bash

# اسکریپت بازگرداندن لوگوهای محلات از بک‌آپ

set -e  # در صورت خطا متوقف شود

echo "🔄 شروع بازگرداندن لوگوهای محلات..."
echo ""

# 1. پیدا کردن بک‌آپ
BACKUP_DIR="/root/regions-map-backup-20251214_175002"
UPLOADS_TARGET="/var/www/regions-map-app/uploads/uploads/regions/logos"

echo "1️⃣ پیدا کردن بک‌آپ..."

# بررسی وجود بک‌آپ
if [ ! -d "$BACKUP_DIR" ]; then
    echo "   ❌ بک‌آپ پیدا نشد: $BACKUP_DIR"
    echo "   🔍 جستجوی بک‌آپ‌های دیگر..."
    BACKUP_DIR=$(find /root -name "regions-map-backup-*" -type d | head -1)
    if [ -z "$BACKUP_DIR" ]; then
        echo "   ❌ هیچ بک‌آپی پیدا نشد!"
        exit 1
    fi
    echo "   ✅ بک‌آپ پیدا شد: $BACKUP_DIR"
else
    echo "   ✅ بک‌آپ پیدا شد: $BACKUP_DIR"
fi

# 2. پیدا کردن مسیر uploads در بک‌آپ
echo ""
echo "2️⃣ پیدا کردن لوگوها در بک‌آپ..."

# جستجوی مسیرهای مختلف
POSSIBLE_PATHS=(
    "$BACKUP_DIR/regions-map-app/uploads/uploads/regions/logos"
    "$BACKUP_DIR/regions-map-app/uploads/regions/logos"
    "$BACKUP_DIR/uploads/uploads/regions/logos"
    "$BACKUP_DIR/uploads/regions/logos"
)

LOGO_SOURCE=""
for path in "${POSSIBLE_PATHS[@]}"; do
    if [ -d "$path" ]; then
        LOGO_SOURCE="$path"
        echo "   ✅ لوگوها پیدا شدند در: $LOGO_SOURCE"
        break
    fi
done

if [ -z "$LOGO_SOURCE" ]; then
    echo "   ⚠️  دایرکتوری لوگوها پیدا نشد، جستجوی فایل‌های لوگو..."
    # جستجوی فایل‌های لوگو
    LOGO_FILES=$(find "$BACKUP_DIR" -name "*.jpg" -o -name "*.png" -o -name "*.jpeg" -o -name "*.webp" | grep -i logo | head -5)
    if [ -z "$LOGO_FILES" ]; then
        echo "   ❌ هیچ فایل لوگویی پیدا نشد!"
        exit 1
    else
        echo "   ✅ فایل‌های لوگو پیدا شدند"
        echo "   📋 فایل‌های پیدا شده:"
        echo "$LOGO_FILES" | head -5
    fi
fi

# 3. ساخت دایرکتوری هدف
echo ""
echo "3️⃣ ساخت دایرکتوری هدف..."
sudo mkdir -p "$UPLOADS_TARGET"
echo "   ✅ دایرکتوری ساخته شد: $UPLOADS_TARGET"

# 4. کپی لوگوها
echo ""
echo "4️⃣ کپی لوگوها..."

if [ -n "$LOGO_SOURCE" ]; then
    # اگر دایرکتوری پیدا شد
    echo "   📦 کپی از: $LOGO_SOURCE"
    echo "   📦 به: $UPLOADS_TARGET"
    
    # شمارش فایل‌ها
    FILE_COUNT=$(find "$LOGO_SOURCE" -type f \( -name "*.jpg" -o -name "*.png" -o -name "*.jpeg" -o -name "*.webp" -o -name "*.gif" \) | wc -l)
    echo "   📊 تعداد فایل‌ها: $FILE_COUNT"
    
    # کپی فایل‌ها
    sudo cp -r "$LOGO_SOURCE"/* "$UPLOADS_TARGET/" 2>/dev/null || true
    
    # کپی فایل‌های JSON (metadata)
    JSON_COUNT=$(find "$LOGO_SOURCE" -name "*.json" | wc -l)
    if [ "$JSON_COUNT" -gt 0 ]; then
        echo "   📦 کپی فایل‌های JSON (metadata)..."
        sudo cp "$LOGO_SOURCE"/*.json "$UPLOADS_TARGET/" 2>/dev/null || true
    fi
else
    # اگر دایرکتوری پیدا نشد، جستجوی فایل‌های لوگو
    echo "   📦 جستجو و کپی فایل‌های لوگو..."
    find "$BACKUP_DIR" -type f \( -name "*.jpg" -o -name "*.png" -o -name "*.jpeg" -o -name "*.webp" -o -name "*.gif" \) | while read file; do
        filename=$(basename "$file")
        sudo cp "$file" "$UPLOADS_TARGET/$filename" 2>/dev/null || true
    done
fi

# 5. تنظیم دسترسی‌ها
echo ""
echo "5️⃣ تنظیم دسترسی‌ها..."
sudo chown -R www-data:www-data "$UPLOADS_TARGET"
sudo chmod -R 755 "$UPLOADS_TARGET"
echo "   ✅ دسترسی‌ها تنظیم شد"

# 6. بررسی نتیجه
echo ""
echo "6️⃣ بررسی نتیجه..."
RESTORED_COUNT=$(find "$UPLOADS_TARGET" -type f \( -name "*.jpg" -o -name "*.png" -o -name "*.jpeg" -o -name "*.webp" -o -name "*.gif" \) | wc -l)
echo "   📊 تعداد لوگوهای بازگردانده شده: $RESTORED_COUNT"

if [ "$RESTORED_COUNT" -gt 0 ]; then
    echo ""
    echo "✅ بازگرداندن لوگوها با موفقیت انجام شد!"
    echo ""
    echo "📋 خلاصه:"
    echo "   - تعداد لوگوها: $RESTORED_COUNT"
    echo "   - مسیر: $UPLOADS_TARGET"
    echo ""
    echo "🔍 برای بررسی:"
    echo "   ls -lh $UPLOADS_TARGET | head -10"
else
    echo ""
    echo "⚠️  هیچ لوگویی بازگردانده نشد!"
    echo "   لطفاً بررسی کنید که بک‌آپ درست است."
fi

echo ""
echo "✅ تمام!"

