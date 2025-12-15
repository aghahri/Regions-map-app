#!/bin/bash

# اسکریپت استخراج فقط links و logos از بک‌آپ
# استخراج: uploads/uploads/regions/links/*.json و uploads/uploads/regions/logos/*

set -e

echo "============================================"
echo "🔄 استخراج links و logos از بک‌آپ..."
echo "============================================"
echo ""

# مسیرهای هدف
LINKS_TARGET="/var/www/regions-map-app/uploads/uploads/regions/links"
LOGO_TARGET="/var/www/regions-map-app/uploads/uploads/regions/logos"

# مسیر بک‌آپ
BACKUP_MAIN="/root/regions-map-backup-20251214_175002"

# ساخت دایرکتوری‌ها
echo "1️⃣ ساخت دایرکتوری‌های هدف..."
sudo mkdir -p "$LINKS_TARGET"
sudo mkdir -p "$LOGO_TARGET"
echo "   ✅ دایرکتوری‌ها ساخته شدند"
echo ""

# ============================================
# بخش 1: استخراج links
# ============================================
echo "============================================"
echo "2️⃣ استخراج links (*.json)..."
echo "============================================"

# جستجوی مسیر links در بک‌آپ
LINKS_SOURCE_PATHS=(
    "$BACKUP_MAIN/regions-map-app/uploads/uploads/regions/links"
    "$BACKUP_MAIN/uploads/uploads/regions/links"
)

LINK_COUNT=0

for source_path in "${LINKS_SOURCE_PATHS[@]}"; do
    if [ -d "$source_path" ]; then
        json_files=$(find "$source_path" -type f -name "*.json" 2>/dev/null)
        if [ -n "$json_files" ]; then
            json_count=$(echo "$json_files" | wc -l)
            echo "   ✅ پیدا شد: $source_path ($json_count فایل)"
            echo "   📦 کپی فایل‌های JSON..."
            
            echo "$json_files" | while read file; do
                filename=$(basename "$file")
                sudo cp "$file" "$LINKS_TARGET/$filename" 2>/dev/null || true
            done
            
            LINK_COUNT=$json_count
            break
        fi
    fi
done

if [ "$LINK_COUNT" -gt 0 ]; then
    echo "   ✅ $LINK_COUNT فایل links کپی شد"
else
    echo "   ⚠️  هیچ فایل link پیدا نشد"
fi

# ============================================
# بخش 2: استخراج logos
# ============================================
echo ""
echo "============================================"
echo "3️⃣ استخراج logos..."
echo "============================================"

# جستجوی مسیر logos در بک‌آپ
LOGO_SOURCE_PATHS=(
    "$BACKUP_MAIN/regions-map-app/uploads/uploads/regions/logos"
    "$BACKUP_MAIN/uploads/uploads/regions/logos"
)

LOGO_COUNT=0

for source_path in "${LOGO_SOURCE_PATHS[@]}"; do
    if [ -d "$source_path" ]; then
        # شمارش فایل‌ها
        file_count=$(find "$source_path" -type f \( -name "*.jpg" -o -name "*.png" -o -name "*.jpeg" -o -name "*.webp" -o -name "*.gif" -o -name "*.json" \) 2>/dev/null | wc -l)
        
        if [ "$file_count" -gt 0 ]; then
            echo "   ✅ پیدا شد: $source_path ($file_count فایل)"
            echo "   📦 کپی لوگوها..."
            
            # کپی همه فایل‌ها
            sudo cp -r "$source_path"/* "$LOGO_TARGET/" 2>/dev/null || true
            
            LOGO_COUNT=$file_count
            break
        fi
    fi
done

if [ "$LOGO_COUNT" -gt 0 ]; then
    echo "   ✅ $LOGO_COUNT فایل لوگو کپی شد"
else
    echo "   ⚠️  هیچ لوگویی پیدا نشد"
fi

# ============================================
# بخش 3: تنظیم دسترسی‌ها
# ============================================
echo ""
echo "============================================"
echo "4️⃣ تنظیم دسترسی‌ها..."
echo "============================================"

sudo chown -R www-data:www-data "$LINKS_TARGET"
sudo chown -R www-data:www-data "$LOGO_TARGET"
sudo chmod -R 755 "$LINKS_TARGET"
sudo chmod -R 755 "$LOGO_TARGET"
echo "   ✅ دسترسی‌ها تنظیم شد"

# ============================================
# بخش 4: بررسی نتیجه
# ============================================
echo ""
echo "============================================"
echo "5️⃣ بررسی نتیجه..."
echo "============================================"

FINAL_LINKS=$(find "$LINKS_TARGET" -type f -name "*.json" 2>/dev/null | wc -l)
FINAL_LOGOS=$(find "$LOGO_TARGET" -type f \( -name "*.jpg" -o -name "*.png" -o -name "*.jpeg" -o -name "*.webp" -o -name "*.gif" -o -name "*.json" \) 2>/dev/null | wc -l)

echo "   📊 فایل‌های links: $FINAL_LINKS"
echo "   📊 فایل‌های logos: $FINAL_LOGOS"

echo ""
echo "============================================"
if [ "$FINAL_LINKS" -gt 0 ] || [ "$FINAL_LOGOS" -gt 0 ]; then
    echo "✅ استخراج با موفقیت انجام شد!"
else
    echo "⚠️  هیچ فایلی استخراج نشد!"
    echo "   لطفاً بررسی کنید که مسیر بک‌آپ درست است."
fi
echo "============================================"
echo ""
echo "📋 خلاصه:"
echo "   - Links: $FINAL_LINKS فایل در $LINKS_TARGET"
echo "   - Logos: $FINAL_LOGOS فایل در $LOGO_TARGET"
echo ""
echo "🔍 برای بررسی:"
echo "   ls -lh $LINKS_TARGET | head -10"
echo "   ls -lh $LOGO_TARGET | head -10"
echo ""
echo "✅ تمام!"

