#!/bin/bash

# اسکریپت کامل بازگرداندن لوگوها و لینک‌های توت اپ از بک‌آپ
# این اسکریپت همه چیز را خودکار انجام می‌دهد

set -e  # در صورت خطا متوقف شود

echo "🔄 شروع بازگرداندن کامل لوگوها و لینک‌های توت اپ..."
echo ""

# مسیرها
BACKUP_DIR="/root/regions-map-backup-20251214_175002"
LINKS_BACKUP_DIR="/root/regions-backups"
UPLOADS_TARGET="/var/www/regions-map-app/uploads/uploads/regions"
LINKS_TARGET="/var/www/regions-map-app/uploads/regions/links"

# ============================================
# بخش 1: بازگرداندن لوگوها
# ============================================
echo "============================================"
echo "1️⃣ بازگرداندن لوگوها..."
echo "============================================"

# بررسی وجود بک‌آپ
if [ -d "$BACKUP_DIR" ]; then
    echo "   ✅ بک‌آپ پیدا شد: $BACKUP_DIR"
    
    # جستجوی مسیرهای مختلف برای logos
    LOGO_PATHS=(
        "$BACKUP_DIR/regions-map-app/uploads/uploads/regions/logos"
        "$BACKUP_DIR/regions-map-app/uploads/regions/logos"
        "$BACKUP_DIR/uploads/uploads/regions/logos"
        "$BACKUP_DIR/uploads/regions/logos"
    )
    
    LOGO_SOURCE=""
    for path in "${LOGO_PATHS[@]}"; do
        if [ -d "$path" ] && [ "$(find "$path" -type f \( -name "*.jpg" -o -name "*.png" -o -name "*.jpeg" -o -name "*.webp" -o -name "*.gif" \) 2>/dev/null | wc -l)" -gt 0 ]; then
            LOGO_SOURCE="$path"
            echo "   ✅ لوگوها پیدا شدند در: $LOGO_SOURCE"
            break
        fi
    done
    
    if [ -n "$LOGO_SOURCE" ]; then
        # ساخت دایرکتوری هدف
        sudo mkdir -p "$UPLOADS_TARGET/logos"
        
        # شمارش فایل‌ها
        FILE_COUNT=$(find "$LOGO_SOURCE" -type f \( -name "*.jpg" -o -name "*.png" -o -name "*.jpeg" -o -name "*.webp" -o -name "*.gif" \) 2>/dev/null | wc -l)
        echo "   📊 تعداد فایل‌های لوگو: $FILE_COUNT"
        
        if [ "$FILE_COUNT" -gt 0 ]; then
            # کپی فایل‌ها
            echo "   📦 کپی لوگوها..."
            sudo cp -r "$LOGO_SOURCE"/* "$UPLOADS_TARGET/logos/" 2>/dev/null || true
            
            # تنظیم دسترسی‌ها
            sudo chown -R www-data:www-data "$UPLOADS_TARGET/logos"
            sudo chmod -R 755 "$UPLOADS_TARGET/logos"
            
            echo "   ✅ $FILE_COUNT لوگو بازگردانده شد"
        else
            echo "   ⚠️  هیچ فایل لوگویی پیدا نشد"
        fi
    else
        echo "   ⚠️  دایرکتوری logos پیدا نشد"
    fi
else
    echo "   ⚠️  بک‌آپ اصلی پیدا نشد: $BACKUP_DIR"
fi

# ============================================
# بخش 2: بازگرداندن لینک‌های توت اپ
# ============================================
echo ""
echo "============================================"
echo "2️⃣ بازگرداندن لینک‌های توت اپ..."
echo "============================================"

# بررسی وجود دایرکتوری بک‌آپ links
if [ -d "$LINKS_BACKUP_DIR" ]; then
    echo "   ✅ دایرکتوری بک‌آپ links پیدا شد: $LINKS_BACKUP_DIR"
    
    # پیدا کردن آخرین فایل بک‌آپ
    LATEST_BACKUP=$(ls -t "$LINKS_BACKUP_DIR"/links_backup_*.tar.gz 2>/dev/null | head -1)
    
    if [ -n "$LATEST_BACKUP" ]; then
        echo "   ✅ آخرین بک‌آپ پیدا شد: $(basename "$LATEST_BACKUP")"
        
        # ساخت دایرکتوری هدف
        sudo mkdir -p "$LINKS_TARGET"
        
        # Extract فایل بک‌آپ
        TEMP_DIR="/tmp/links_restore_$(date +%Y%m%d_%H%M%S)"
        mkdir -p "$TEMP_DIR"
        
        echo "   📦 Extract کردن فایل..."
        if tar -xzf "$LATEST_BACKUP" -C "$TEMP_DIR" 2>/dev/null; then
            echo "   ✅ فایل extract شد"
            
            # پیدا کردن فایل‌های JSON
            LINK_FILES=$(find "$TEMP_DIR" -type f -name "*.json" 2>/dev/null)
            
            if [ -n "$LINK_FILES" ]; then
                LINK_COUNT=$(echo "$LINK_FILES" | wc -l)
                echo "   📊 تعداد فایل‌های links: $LINK_COUNT"
                
                # کپی فایل‌ها
                echo "   📦 کپی لینک‌ها..."
                echo "$LINK_FILES" | while read file; do
                    filename=$(basename "$file")
                    sudo cp "$file" "$LINKS_TARGET/$filename" 2>/dev/null || true
                done
                
                # تنظیم دسترسی‌ها
                sudo chown -R www-data:www-data "$LINKS_TARGET"
                sudo chmod -R 755 "$LINKS_TARGET"
                
                echo "   ✅ $LINK_COUNT فایل links بازگردانده شد"
            else
                # اگر فایل JSON پیدا نشد، کل محتوا را کپی می‌کنیم
                echo "   📦 کپی کل محتوا..."
                sudo cp -r "$TEMP_DIR"/* "$LINKS_TARGET/" 2>/dev/null || true
                sudo chown -R www-data:www-data "$LINKS_TARGET"
                sudo chmod -R 755 "$LINKS_TARGET"
                echo "   ✅ محتوا کپی شد"
            fi
            
            # پاک کردن فایل‌های موقت
            rm -rf "$TEMP_DIR"
        else
            echo "   ❌ خطا در extract کردن فایل!"
            rm -rf "$TEMP_DIR"
        fi
    else
        echo "   ⚠️  هیچ فایل بک‌آپی پیدا نشد"
    fi
else
    echo "   ⚠️  دایرکتوری بک‌آپ links پیدا نشد: $LINKS_BACKUP_DIR"
fi

# ============================================
# بخش 3: بررسی نتیجه نهایی
# ============================================
echo ""
echo "============================================"
echo "3️⃣ بررسی نتیجه نهایی..."
echo "============================================"

RESTORED_LOGOS=$(find "$UPLOADS_TARGET/logos" -type f \( -name "*.jpg" -o -name "*.png" -o -name "*.jpeg" -o -name "*.webp" -o -name "*.gif" \) 2>/dev/null | wc -l)
RESTORED_LINKS=$(find "$LINKS_TARGET" -type f -name "*.json" 2>/dev/null | wc -l)

echo "   📊 لوگوهای بازگردانده شده: $RESTORED_LOGOS"
echo "   📊 فایل‌های links بازگردانده شده: $RESTORED_LINKS"

echo ""
echo "============================================"
echo "✅ بازگرداندن کامل شد!"
echo "============================================"
echo ""
echo "📋 خلاصه:"
echo "   - لوگوها: $RESTORED_LOGOS فایل در $UPLOADS_TARGET/logos"
echo "   - لینک‌ها: $RESTORED_LINKS فایل در $LINKS_TARGET"
echo ""
echo "🔍 برای بررسی:"
echo "   ls -lh $UPLOADS_TARGET/logos | head -10"
echo "   ls -lh $LINKS_TARGET | head -10"
echo ""
echo "✅ تمام!"

