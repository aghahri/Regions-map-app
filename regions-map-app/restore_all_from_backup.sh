#!/bin/bash

# اسکریپت بازگرداندن لوگوها و لینک‌های توت اپ از بک‌آپ

set -e  # در صورت خطا متوقف شود

echo "🔄 شروع بازگرداندن لوگوها و لینک‌های توت اپ..."
echo ""

# 1. پیدا کردن بک‌آپ
BACKUP_DIR="/root/regions-map-backup-20251214_175002"
UPLOADS_TARGET="/var/www/regions-map-app/uploads/uploads/regions"
LINKS_TARGET="/var/www/regions-map-app/uploads/regions/links"

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
echo "2️⃣ پیدا کردن uploads در بک‌آپ..."

# جستجوی مسیرهای مختلف
POSSIBLE_UPLOADS_PATHS=(
    "$BACKUP_DIR/regions-map-app/uploads/uploads/regions"
    "$BACKUP_DIR/regions-map-app/uploads/regions"
    "$BACKUP_DIR/uploads/uploads/regions"
    "$BACKUP_DIR/uploads/regions"
)

UPLOADS_SOURCE=""
for path in "${POSSIBLE_UPLOADS_PATHS[@]}"; do
    if [ -d "$path" ]; then
        UPLOADS_SOURCE="$path"
        echo "   ✅ uploads پیدا شد در: $UPLOADS_SOURCE"
        break
    fi
done

if [ -z "$UPLOADS_SOURCE" ]; then
    echo "   ⚠️  دایرکتوری uploads پیدا نشد!"
    echo "   🔍 جستجوی فایل‌های uploads..."
    # جستجوی فایل‌های uploads
    UPLOADS_FILES=$(find "$BACKUP_DIR" -type d -name "uploads" | head -1)
    if [ -n "$UPLOADS_FILES" ]; then
        UPLOADS_SOURCE="$UPLOADS_FILES"
        echo "   ✅ uploads پیدا شد در: $UPLOADS_SOURCE"
    else
        echo "   ❌ هیچ uploads پیدا نشد!"
    fi
fi

# 3. ساخت دایرکتوری‌های هدف
echo ""
echo "3️⃣ ساخت دایرکتوری‌های هدف..."
sudo mkdir -p "$UPLOADS_TARGET/logos"
sudo mkdir -p "$UPLOADS_TARGET/neighborhood_edits"
sudo mkdir -p "$LINKS_TARGET"
echo "   ✅ دایرکتوری‌ها ساخته شدند"

# 4. بازگرداندن لوگوها
echo ""
echo "4️⃣ بازگرداندن لوگوها..."

if [ -n "$UPLOADS_SOURCE" ]; then
    # پیدا کردن دایرکتوری logos
    LOGO_PATHS=(
        "$UPLOADS_SOURCE/logos"
        "$UPLOADS_SOURCE/uploads/regions/logos"
        "$UPLOADS_SOURCE/regions/logos"
    )
    
    LOGO_SOURCE=""
    for path in "${LOGO_PATHS[@]}"; do
        if [ -d "$path" ]; then
            LOGO_SOURCE="$path"
            echo "   ✅ لوگوها پیدا شدند در: $LOGO_SOURCE"
            break
        fi
    done
    
    if [ -n "$LOGO_SOURCE" ]; then
        # شمارش فایل‌ها
        FILE_COUNT=$(find "$LOGO_SOURCE" -type f \( -name "*.jpg" -o -name "*.png" -o -name "*.jpeg" -o -name "*.webp" -o -name "*.gif" \) | wc -l)
        echo "   📊 تعداد فایل‌های لوگو: $FILE_COUNT"
        
        if [ "$FILE_COUNT" -gt 0 ]; then
            # کپی فایل‌ها
            echo "   📦 کپی لوگوها..."
            sudo cp -r "$LOGO_SOURCE"/* "$UPLOADS_TARGET/logos/" 2>/dev/null || true
            echo "   ✅ لوگوها کپی شدند"
        else
            echo "   ⚠️  هیچ فایل لوگویی پیدا نشد"
        fi
    else
        echo "   ⚠️  دایرکتوری logos پیدا نشد"
    fi
else
    echo "   ⚠️  uploads source پیدا نشد"
fi

# 5. بازگرداندن لینک‌های توت اپ
echo ""
echo "5️⃣ بازگرداندن لینک‌های توت اپ..."

if [ -n "$UPLOADS_SOURCE" ]; then
    # پیدا کردن فایل‌های links
    LINK_PATHS=(
        "$UPLOADS_SOURCE/links"
        "$UPLOADS_SOURCE/regions/links"
        "$UPLOADS_SOURCE/uploads/regions/links"
    )
    
    LINK_SOURCE=""
    for path in "${LINK_PATHS[@]}"; do
        if [ -d "$path" ]; then
            LINK_SOURCE="$path"
            echo "   ✅ لینک‌ها پیدا شدند در: $LINK_SOURCE"
            break
        fi
    done
    
    # یا جستجوی فایل‌های JSON links
    if [ -z "$LINK_SOURCE" ]; then
        LINK_FILES=$(find "$BACKUP_DIR" -type f -name "*links*.json" | head -5)
        if [ -n "$LINK_FILES" ]; then
            echo "   ✅ فایل‌های links پیدا شدند"
            echo "$LINK_FILES" | while read file; do
                sudo cp "$file" "$LINKS_TARGET/" 2>/dev/null || true
            done
        fi
    else
        # کپی فایل‌های links
        FILE_COUNT=$(find "$LINK_SOURCE" -type f -name "*.json" | wc -l)
        echo "   📊 تعداد فایل‌های links: $FILE_COUNT"
        
        if [ "$FILE_COUNT" -gt 0 ]; then
            echo "   📦 کپی لینک‌ها..."
            sudo cp "$LINK_SOURCE"/*.json "$LINKS_TARGET/" 2>/dev/null || true
            echo "   ✅ لینک‌ها کپی شدند"
        else
            echo "   ⚠️  هیچ فایل link پیدا نشد"
        fi
    fi
else
    echo "   ⚠️  uploads source پیدا نشد"
fi

# 6. جستجوی فایل‌های links در کل بک‌آپ
echo ""
echo "6️⃣ جستجوی فایل‌های links در کل بک‌آپ..."

LINK_FILES=$(find "$BACKUP_DIR" -type f -name "*links*.json" 2>/dev/null)
if [ -n "$LINK_FILES" ]; then
    echo "   ✅ فایل‌های links پیدا شدند:"
    echo "$LINK_FILES" | head -5
    echo "$LINK_FILES" | while read file; do
        filename=$(basename "$file")
        sudo cp "$file" "$LINKS_TARGET/$filename" 2>/dev/null || true
    done
    echo "   ✅ لینک‌ها کپی شدند"
else
    echo "   ⚠️  هیچ فایل link پیدا نشد"
fi

# 7. تنظیم دسترسی‌ها
echo ""
echo "7️⃣ تنظیم دسترسی‌ها..."
sudo chown -R www-data:www-data "$UPLOADS_TARGET"
sudo chown -R www-data:www-data "$LINKS_TARGET"
sudo chmod -R 755 "$UPLOADS_TARGET"
sudo chmod -R 755 "$LINKS_TARGET"
echo "   ✅ دسترسی‌ها تنظیم شد"

# 8. بررسی نتیجه
echo ""
echo "8️⃣ بررسی نتیجه..."
RESTORED_LOGOS=$(find "$UPLOADS_TARGET/logos" -type f \( -name "*.jpg" -o -name "*.png" -o -name "*.jpeg" -o -name "*.webp" -o -name "*.gif" \) 2>/dev/null | wc -l)
RESTORED_LINKS=$(find "$LINKS_TARGET" -type f -name "*.json" 2>/dev/null | wc -l)

echo "   📊 تعداد لوگوهای بازگردانده شده: $RESTORED_LOGOS"
echo "   📊 تعداد فایل‌های links بازگردانده شده: $RESTORED_LINKS"

echo ""
echo "✅ بازگرداندن کامل شد!"
echo ""
echo "📋 خلاصه:"
echo "   - لوگوها: $RESTORED_LOGOS فایل"
echo "   - لینک‌ها: $RESTORED_LINKS فایل"
echo ""
echo "🔍 برای بررسی:"
echo "   ls -lh $UPLOADS_TARGET/logos | head -10"
echo "   ls -lh $LINKS_TARGET | head -10"

echo ""
echo "✅ تمام!"

