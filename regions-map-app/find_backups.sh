#!/bin/bash

# اسکریپت پیدا کردن مسیرهای بک‌آپ لوگوها و لینک‌ها

echo "============================================"
echo "🔍 جستجوی بک‌آپ‌های لوگوها و لینک‌ها..."
echo "============================================"
echo ""

# ============================================
# بخش 1: پیدا کردن بک‌آپ لوگوها
# ============================================
echo "1️⃣ بک‌آپ لوگوها:"
echo "--------------------------------------------"

# بررسی بک‌آپ اصلی
BACKUP_MAIN="/root/regions-map-backup-20251214_175002"
if [ -d "$BACKUP_MAIN" ]; then
    echo "   ✅ بک‌آپ اصلی: $BACKUP_MAIN"
    
    # جستجوی دایرکتوری logos
    LOGO_DIRS=$(find "$BACKUP_MAIN" -type d -name "logos" 2>/dev/null)
    if [ -n "$LOGO_DIRS" ]; then
        echo "   📁 دایرکتوری‌های logos:"
        echo "$LOGO_DIRS" | while read dir; do
            file_count=$(find "$dir" -type f \( -name "*.jpg" -o -name "*.png" -o -name "*.jpeg" -o -name "*.webp" -o -name "*.gif" \) 2>/dev/null | wc -l)
            echo "      - $dir ($file_count فایل)"
        done
    fi
    
    # جستجوی فایل‌های لوگو
    LOGO_FILES=$(find "$BACKUP_MAIN" -type f \( -name "*.jpg" -o -name "*.png" -o -name "*.jpeg" -o -name "*.webp" -o -name "*.gif" \) 2>/dev/null | wc -l)
    if [ "$LOGO_FILES" -gt 0 ]; then
        echo "   📊 تعداد کل فایل‌های لوگو: $LOGO_FILES"
    fi
else
    echo "   ⚠️  بک‌آپ اصلی پیدا نشد: $BACKUP_MAIN"
fi

# بررسی بک‌آپ قدیمی
BACKUP_OLD="/root/regions-backups"
if [ -d "$BACKUP_OLD" ]; then
    echo ""
    echo "   ✅ بک‌آپ قدیمی: $BACKUP_OLD"
    LOGO_FILES_OLD=$(find "$BACKUP_OLD" -type f \( -name "*.jpg" -o -name "*.png" -o -name "*.jpeg" -o -name "*.webp" -o -name "*.gif" \) 2>/dev/null | wc -l)
    if [ "$LOGO_FILES_OLD" -gt 0 ]; then
        echo "   📊 تعداد فایل‌های لوگو: $LOGO_FILES_OLD"
    fi
fi

# ============================================
# بخش 2: پیدا کردن بک‌آپ لینک‌ها
# ============================================
echo ""
echo "2️⃣ بک‌آپ لینک‌ها:"
echo "--------------------------------------------"

# بررسی فایل‌های tar.gz
TAR_FILES=$(find /root -name "links_backup_*.tar.gz" 2>/dev/null | sort -r)
if [ -n "$TAR_FILES" ]; then
    echo "   ✅ فایل‌های tar.gz:"
    echo "$TAR_FILES" | while read file; do
        size=$(du -h "$file" | cut -f1)
        date=$(stat -c %y "$file" 2>/dev/null | cut -d' ' -f1)
        echo "      - $file"
        echo "        حجم: $size | تاریخ: $date"
    done
else
    echo "   ⚠️  هیچ فایل tar.gz پیدا نشد"
fi

# بررسی بک‌آپ اصلی برای links
if [ -d "$BACKUP_MAIN" ]; then
    echo ""
    echo "   🔍 بررسی بک‌آپ اصلی برای links..."
    
    # جستجوی دایرکتوری links
    LINK_DIRS=$(find "$BACKUP_MAIN" -type d -name "links" 2>/dev/null)
    if [ -n "$LINK_DIRS" ]; then
        echo "   📁 دایرکتوری‌های links:"
        echo "$LINK_DIRS" | while read dir; do
            json_count=$(find "$dir" -type f -name "*.json" 2>/dev/null | wc -l)
            echo "      - $dir ($json_count فایل JSON)"
        done
    fi
    
    # جستجوی فایل‌های JSON
    JSON_FILES=$(find "$BACKUP_MAIN" -type f -name "*.json" 2>/dev/null | wc -l)
    if [ "$JSON_FILES" -gt 0 ]; then
        echo "   📊 تعداد کل فایل‌های JSON: $JSON_FILES"
    fi
fi

# ============================================
# بخش 3: خلاصه
# ============================================
echo ""
echo "============================================"
echo "📋 خلاصه مسیرهای بک‌آپ:"
echo "============================================"
echo ""
echo "بک‌آپ اصلی:"
echo "   $BACKUP_MAIN"
echo ""
echo "بک‌آپ لینک‌ها:"
echo "   $BACKUP_OLD"
echo ""
echo "🔍 برای بررسی محتوا:"
echo "   ls -lh $BACKUP_MAIN/regions-map-app/uploads/uploads/regions/logos/ | head -10"
echo "   ls -lh $BACKUP_OLD/ | head -10"
echo ""
echo "✅ تمام!"

