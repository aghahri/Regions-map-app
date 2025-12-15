#!/bin/bash

# اسکریپت نهایی بازگرداندن لوگوها و لینک‌های توت اپ
# این اسکریپت همه مسیرهای ممکن را بررسی می‌کند

set -e

echo "🔄 شروع بازگرداندن کامل..."
echo ""

# مسیرهای هدف (طبق app.py)
LOGO_TARGET="/var/www/regions-map-app/uploads/uploads/regions/logos"
LINKS_TARGET="/var/www/regions-map-app/uploads/uploads/regions/links"

# ساخت دایرکتوری‌ها
echo "1️⃣ ساخت دایرکتوری‌های هدف..."
sudo mkdir -p "$LOGO_TARGET"
sudo mkdir -p "$LINKS_TARGET"
echo "   ✅ دایرکتوری‌ها ساخته شدند"
echo ""

# ============================================
# بخش 1: پیدا کردن و بازگرداندن لوگوها
# ============================================
echo "============================================"
echo "2️⃣ پیدا کردن و بازگرداندن لوگوها..."
echo "============================================"

# جستجوی لوگوها در همه مسیرهای ممکن
LOGO_SEARCH_PATHS=(
    "/root/regions-map-backup-20251214_175002"
    "/root/regions-backups"
    "/var/www/regions-map-app"
)

LOGO_FOUND=0

for base_path in "${LOGO_SEARCH_PATHS[@]}"; do
    if [ ! -d "$base_path" ]; then
        continue
    fi
    
    echo "   🔍 جستجو در: $base_path"
    
    # جستجوی دایرکتوری logos
    LOGO_DIRS=$(find "$base_path" -type d -name "logos" 2>/dev/null)
    
    if [ -n "$LOGO_DIRS" ]; then
        echo "$LOGO_DIRS" | while read logo_dir; do
            FILE_COUNT=$(find "$logo_dir" -type f \( -name "*.jpg" -o -name "*.png" -o -name "*.jpeg" -o -name "*.webp" -o -name "*.gif" \) 2>/dev/null | wc -l)
            
            if [ "$FILE_COUNT" -gt 0 ]; then
                echo "   ✅ پیدا شد: $logo_dir ($FILE_COUNT فایل)"
                echo "   📦 کپی لوگوها..."
                sudo cp -r "$logo_dir"/* "$LOGO_TARGET/" 2>/dev/null || true
                LOGO_FOUND=1
            fi
        done
    fi
    
    # جستجوی مستقیم فایل‌های لوگو
    LOGO_FILES=$(find "$base_path" -type f \( -name "*.jpg" -o -name "*.png" -o -name "*.jpeg" -o -name "*.webp" -o -name "*.gif" \) 2>/dev/null | head -20)
    
    if [ -n "$LOGO_FILES" ]; then
        FILE_COUNT=$(echo "$LOGO_FILES" | wc -l)
        if [ "$FILE_COUNT" -gt 0 ] && [ "$LOGO_FOUND" -eq 0 ]; then
            echo "   ✅ فایل‌های لوگو پیدا شدند ($FILE_COUNT فایل)"
            echo "   📦 کپی لوگوها..."
            echo "$LOGO_FILES" | while read file; do
                filename=$(basename "$file")
                sudo cp "$file" "$LOGO_TARGET/$filename" 2>/dev/null || true
            done
            LOGO_FOUND=1
        fi
    fi
done

if [ "$LOGO_FOUND" -eq 0 ]; then
    echo "   ⚠️  هیچ لوگویی پیدا نشد"
fi

# ============================================
# بخش 2: پیدا کردن و بازگرداندن لینک‌ها
# ============================================
echo ""
echo "============================================"
echo "3️⃣ پیدا کردن و بازگرداندن لینک‌های توت اپ..."
echo "============================================"

# جستجوی فایل‌های tar.gz
TAR_FILES=$(find /root -name "links_backup_*.tar.gz" 2>/dev/null | sort -r)

if [ -n "$TAR_FILES" ]; then
    LATEST_TAR=$(echo "$TAR_FILES" | head -1)
    echo "   ✅ فایل بک‌آپ پیدا شد: $(basename "$LATEST_TAR")"
    
    # Extract
    TEMP_DIR="/tmp/links_restore_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$TEMP_DIR"
    
    echo "   📦 Extract کردن..."
    if tar -xzf "$LATEST_TAR" -C "$TEMP_DIR" 2>/dev/null; then
        # پیدا کردن فایل‌های JSON
        JSON_FILES=$(find "$TEMP_DIR" -type f -name "*.json" 2>/dev/null)
        
        if [ -n "$JSON_FILES" ]; then
            JSON_COUNT=$(echo "$JSON_FILES" | wc -l)
            echo "   ✅ $JSON_COUNT فایل JSON پیدا شد"
            echo "   📦 کپی لینک‌ها..."
            
            echo "$JSON_FILES" | while read file; do
                filename=$(basename "$file")
                sudo cp "$file" "$LINKS_TARGET/$filename" 2>/dev/null || true
            done
        else
            # اگر JSON پیدا نشد، کل محتوا را کپی می‌کنیم
            echo "   📦 کپی کل محتوا..."
            sudo cp -r "$TEMP_DIR"/* "$LINKS_TARGET/" 2>/dev/null || true
        fi
        
        rm -rf "$TEMP_DIR"
    fi
fi

# جستجوی مستقیم فایل‌های links
LINK_SEARCH_PATHS=(
    "/root/regions-map-backup-20251214_175002"
    "/root/regions-backups"
    "/var/www/regions-map-app"
)

for base_path in "${LINK_SEARCH_PATHS[@]}"; do
    if [ ! -d "$base_path" ]; then
        continue
    fi
    
    # جستجوی دایرکتوری links
    LINK_DIRS=$(find "$base_path" -type d -name "links" 2>/dev/null)
    
    if [ -n "$LINK_DIRS" ]; then
        echo "$LINK_DIRS" | while read link_dir; do
            JSON_COUNT=$(find "$link_dir" -type f -name "*.json" 2>/dev/null | wc -l)
            
            if [ "$JSON_COUNT" -gt 0 ]; then
                echo "   ✅ پیدا شد: $link_dir ($JSON_COUNT فایل)"
                echo "   📦 کپی لینک‌ها..."
                sudo cp "$link_dir"/*.json "$LINKS_TARGET/" 2>/dev/null || true
            fi
        done
    fi
    
    # جستجوی مستقیم فایل‌های JSON links
    LINK_JSON_FILES=$(find "$base_path" -type f -name "*links*.json" -o -name "*.json" 2>/dev/null | head -20)
    
    if [ -n "$LINK_JSON_FILES" ]; then
        echo "   📦 کپی فایل‌های JSON پیدا شده..."
        echo "$LINK_JSON_FILES" | while read file; do
            filename=$(basename "$file")
            sudo cp "$file" "$LINKS_TARGET/$filename" 2>/dev/null || true
        done
    fi
done

# ============================================
# بخش 3: تنظیم دسترسی‌ها
# ============================================
echo ""
echo "============================================"
echo "4️⃣ تنظیم دسترسی‌ها..."
echo "============================================"

sudo chown -R www-data:www-data "$LOGO_TARGET"
sudo chown -R www-data:www-data "$LINKS_TARGET"
sudo chmod -R 755 "$LOGO_TARGET"
sudo chmod -R 755 "$LINKS_TARGET"
echo "   ✅ دسترسی‌ها تنظیم شد"

# ============================================
# بخش 4: بررسی نتیجه
# ============================================
echo ""
echo "============================================"
echo "5️⃣ بررسی نتیجه..."
echo "============================================"

RESTORED_LOGOS=$(find "$LOGO_TARGET" -type f \( -name "*.jpg" -o -name "*.png" -o -name "*.jpeg" -o -name "*.webp" -o -name "*.gif" \) 2>/dev/null | wc -l)
RESTORED_LINKS=$(find "$LINKS_TARGET" -type f -name "*.json" 2>/dev/null | wc -l)

echo "   📊 لوگوهای بازگردانده شده: $RESTORED_LOGOS"
echo "   📊 فایل‌های links بازگردانده شده: $RESTORED_LINKS"

echo ""
echo "============================================"
echo "✅ بازگرداندن کامل شد!"
echo "============================================"
echo ""
echo "📋 خلاصه:"
echo "   - لوگوها: $RESTORED_LOGOS فایل"
echo "   - لینک‌ها: $RESTORED_LINKS فایل"
echo ""
echo "🔍 برای بررسی:"
echo "   ls -lh $LOGO_TARGET | head -10"
echo "   ls -lh $LINKS_TARGET | head -10"
echo ""
echo "✅ تمام!"

