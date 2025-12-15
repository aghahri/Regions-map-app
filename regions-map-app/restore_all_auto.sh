#!/bin/bash

# اسکریپت کامل و خودکار بازگرداندن لوگوها و لینک‌ها
# این اسکریپت همه چیز را خودکار انجام می‌دهد - فقط اجرا کنید!

set -e

echo "============================================"
echo "🔄 شروع بازگرداندن خودکار لوگوها و لینک‌ها"
echo "============================================"
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
# بخش 1: بازگرداندن لوگوها
# ============================================
echo "============================================"
echo "2️⃣ بازگرداندن لوگوها..."
echo "============================================"

LOGO_COUNT=0

# بررسی بک‌آپ اصلی
BACKUP_MAIN="/root/regions-map-backup-20251214_175002"
if [ -d "$BACKUP_MAIN" ]; then
    echo "   🔍 بررسی بک‌آپ اصلی: $BACKUP_MAIN"
    
    # جستجوی همه مسیرهای ممکن برای logos
    for logo_path in "$BACKUP_MAIN/regions-map-app/uploads/uploads/regions/logos" \
                     "$BACKUP_MAIN/regions-map-app/uploads/regions/logos" \
                     "$BACKUP_MAIN/uploads/uploads/regions/logos" \
                     "$BACKUP_MAIN/uploads/regions/logos"; do
        if [ -d "$logo_path" ]; then
            file_count=$(find "$logo_path" -type f \( -name "*.jpg" -o -name "*.png" -o -name "*.jpeg" -o -name "*.webp" -o -name "*.gif" \) 2>/dev/null | wc -l)
            if [ "$file_count" -gt 0 ]; then
                echo "   ✅ پیدا شد: $logo_path ($file_count فایل)"
                echo "   📦 کپی لوگوها..."
                sudo cp -r "$logo_path"/* "$LOGO_TARGET/" 2>/dev/null || true
                LOGO_COUNT=$((LOGO_COUNT + file_count))
            fi
        fi
    done
    
    # جستجوی مستقیم فایل‌های لوگو
    logo_files=$(find "$BACKUP_MAIN" -type f \( -name "*.jpg" -o -name "*.png" -o -name "*.jpeg" -o -name "*.webp" -o -name "*.gif" \) 2>/dev/null | head -100)
    if [ -n "$logo_files" ] && [ "$LOGO_COUNT" -eq 0 ]; then
        file_count=$(echo "$logo_files" | wc -l)
        echo "   ✅ فایل‌های لوگو پیدا شدند ($file_count فایل)"
        echo "   📦 کپی لوگوها..."
        echo "$logo_files" | while read file; do
            filename=$(basename "$file")
            sudo cp "$file" "$LOGO_TARGET/$filename" 2>/dev/null || true
        done
        LOGO_COUNT=$file_count
    fi
fi

# بررسی بک‌آپ قدیمی
BACKUP_OLD="/root/regions-backups"
if [ -d "$BACKUP_OLD" ] && [ "$LOGO_COUNT" -eq 0 ]; then
    echo "   🔍 بررسی بک‌آپ قدیمی: $BACKUP_OLD"
    logo_files=$(find "$BACKUP_OLD" -type f \( -name "*.jpg" -o -name "*.png" -o -name "*.jpeg" -o -name "*.webp" -o -name "*.gif" \) 2>/dev/null | head -100)
    if [ -n "$logo_files" ]; then
        file_count=$(echo "$logo_files" | wc -l)
        echo "   ✅ فایل‌های لوگو پیدا شدند ($file_count فایل)"
        echo "   📦 کپی لوگوها..."
        echo "$logo_files" | while read file; do
            filename=$(basename "$file")
            sudo cp "$file" "$LOGO_TARGET/$filename" 2>/dev/null || true
        done
        LOGO_COUNT=$file_count
    fi
fi

if [ "$LOGO_COUNT" -gt 0 ]; then
    echo "   ✅ $LOGO_COUNT لوگو بازگردانده شد"
else
    echo "   ⚠️  هیچ لوگویی پیدا نشد"
fi

# ============================================
# بخش 2: بازگرداندن لینک‌ها
# ============================================
echo ""
echo "============================================"
echo "3️⃣ بازگرداندن لینک‌های توت اپ..."
echo "============================================"

LINK_COUNT=0

# بررسی فایل‌های tar.gz
TAR_FILES=$(find /root -name "links_backup_*.tar.gz" 2>/dev/null | sort -r)
if [ -n "$TAR_FILES" ]; then
    LATEST_TAR=$(echo "$TAR_FILES" | head -1)
    echo "   ✅ فایل بک‌آپ پیدا شد: $(basename "$LATEST_TAR")"
    
    TEMP_DIR="/tmp/links_restore_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$TEMP_DIR"
    
    echo "   📦 Extract کردن..."
    if tar -xzf "$LATEST_TAR" -C "$TEMP_DIR" 2>/dev/null; then
        json_files=$(find "$TEMP_DIR" -type f -name "*.json" 2>/dev/null)
        if [ -n "$json_files" ]; then
            json_count=$(echo "$json_files" | wc -l)
            echo "   ✅ $json_count فایل JSON پیدا شد"
            echo "   📦 کپی لینک‌ها..."
            echo "$json_files" | while read file; do
                filename=$(basename "$file")
                sudo cp "$file" "$LINKS_TARGET/$filename" 2>/dev/null || true
            done
            LINK_COUNT=$json_count
        else
            echo "   📦 کپی کل محتوا..."
            sudo cp -r "$TEMP_DIR"/* "$LINKS_TARGET/" 2>/dev/null || true
        fi
        rm -rf "$TEMP_DIR"
    fi
fi

# بررسی بک‌آپ اصلی برای links
if [ -d "$BACKUP_MAIN" ] && [ "$LINK_COUNT" -eq 0 ]; then
    echo "   🔍 بررسی بک‌آپ اصلی برای links..."
    
    for link_path in "$BACKUP_MAIN/regions-map-app/uploads/uploads/regions/links" \
                     "$BACKUP_MAIN/regions-map-app/uploads/regions/links" \
                     "$BACKUP_MAIN/uploads/uploads/regions/links" \
                     "$BACKUP_MAIN/uploads/regions/links"; do
        if [ -d "$link_path" ]; then
            json_count=$(find "$link_path" -type f -name "*.json" 2>/dev/null | wc -l)
            if [ "$json_count" -gt 0 ]; then
                echo "   ✅ پیدا شد: $link_path ($json_count فایل)"
                echo "   📦 کپی لینک‌ها..."
                sudo cp "$link_path"/*.json "$LINKS_TARGET/" 2>/dev/null || true
                LINK_COUNT=$json_count
                break
            fi
        fi
    done
    
    # جستجوی مستقیم فایل‌های JSON
    if [ "$LINK_COUNT" -eq 0 ]; then
        json_files=$(find "$BACKUP_MAIN" -type f -name "*.json" 2>/dev/null | head -50)
        if [ -n "$json_files" ]; then
            json_count=$(echo "$json_files" | wc -l)
            echo "   ✅ فایل‌های JSON پیدا شدند ($json_count فایل)"
            echo "   📦 کپی لینک‌ها..."
            echo "$json_files" | while read file; do
                filename=$(basename "$file")
                sudo cp "$file" "$LINKS_TARGET/$filename" 2>/dev/null || true
            done
            LINK_COUNT=$json_count
        fi
    fi
fi

if [ "$LINK_COUNT" -gt 0 ]; then
    echo "   ✅ $LINK_COUNT فایل links بازگردانده شد"
else
    echo "   ⚠️  هیچ فایل link پیدا نشد"
fi

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
# بخش 4: بررسی نتیجه نهایی
# ============================================
echo ""
echo "============================================"
echo "5️⃣ بررسی نتیجه نهایی..."
echo "============================================"

FINAL_LOGOS=$(find "$LOGO_TARGET" -type f \( -name "*.jpg" -o -name "*.png" -o -name "*.jpeg" -o -name "*.webp" -o -name "*.gif" \) 2>/dev/null | wc -l)
FINAL_LINKS=$(find "$LINKS_TARGET" -type f -name "*.json" 2>/dev/null | wc -l)

echo "   📊 لوگوهای نهایی: $FINAL_LOGOS"
echo "   📊 فایل‌های links نهایی: $FINAL_LINKS"

echo ""
echo "============================================"
if [ "$FINAL_LOGOS" -gt 0 ] || [ "$FINAL_LINKS" -gt 0 ]; then
    echo "✅ بازگرداندن با موفقیت انجام شد!"
else
    echo "⚠️  هیچ فایلی بازگردانده نشد!"
    echo "   لطفاً بررسی کنید که بک‌آپ‌ها درست هستند."
fi
echo "============================================"
echo ""
echo "📋 خلاصه:"
echo "   - لوگوها: $FINAL_LOGOS فایل در $LOGO_TARGET"
echo "   - لینک‌ها: $FINAL_LINKS فایل در $LINKS_TARGET"
echo ""
echo "🔍 برای بررسی:"
echo "   ls -lh $LOGO_TARGET | head -10"
echo "   ls -lh $LINKS_TARGET | head -10"
echo ""
echo "✅ تمام!"

