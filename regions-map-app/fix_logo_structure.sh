#!/bin/bash

# اسکریپت برای اصلاح ساختار فایل‌های لوگو روی سرور
# این اسکریپت فایل‌های لوگو را از مسیرهای مختلف پیدا کرده و به مسیر درست منتقل می‌کند

APP_DIR="/var/www/regions-map-app/regions-map-app"
TARGET_DIR="$APP_DIR/../uploads/uploads/regions/logos"

echo "=========================================="
echo "🔧 اصلاح ساختار فایل‌های لوگو"
echo "=========================================="
echo ""

# بررسی دایرکتوری‌های مختلف
SEARCH_DIRS=(
    "$APP_DIR/uploads/regions/logos"
    "$APP_DIR/../uploads/regions/logos"
    "$APP_DIR/../uploads/uploads/regions/logos"
    "$APP_DIR/uploads/uploads/regions/logos"
)

echo "🔍 جستجوی فایل‌های لوگو در مسیرهای مختلف..."
echo ""

# پیدا کردن مسیر واقعی فایل‌ها
FOUND_DIR=""
for dir in "${SEARCH_DIRS[@]}"; do
    if [ -d "$dir" ] && [ "$(ls -A $dir 2>/dev/null)" ]; then
        file_count=$(find "$dir" -type f \( -name "*.jpg" -o -name "*.jpeg" -o -name "*.png" -o -name "*.gif" -o -name "*.webp" -o -name "*.svg" \) 2>/dev/null | wc -l)
        if [ "$file_count" -gt 0 ]; then
            echo "✅ پیدا شد: $dir ($file_count فایل عکس)"
            if [ -z "$FOUND_DIR" ]; then
                FOUND_DIR="$dir"
            fi
        fi
    fi
done

if [ -z "$FOUND_DIR" ]; then
    echo "❌ هیچ فایل لوگویی پیدا نشد!"
    exit 1
fi

echo ""
echo "📁 مسیر هدف: $TARGET_DIR"
echo "📁 مسیر منبع: $FOUND_DIR"
echo ""

# ساخت مسیر هدف
mkdir -p "$TARGET_DIR"
echo "✅ مسیر هدف ساخته شد"

# کپی فایل‌ها
if [ "$FOUND_DIR" != "$TARGET_DIR" ]; then
    echo ""
    echo "📦 در حال کپی کردن فایل‌ها..."
    
    # کپی فایل‌های عکس
    copied_images=0
    for ext in jpg jpeg png gif webp svg; do
        for file in "$FOUND_DIR"/*.$ext "$FOUND_DIR"/*.${ext^^} 2>/dev/null; do
            if [ -f "$file" ]; then
                filename=$(basename "$file")
                if [ ! -f "$TARGET_DIR/$filename" ]; then
                    cp "$file" "$TARGET_DIR/$filename"
                    ((copied_images++))
                    echo "   ✓ $filename"
                fi
            fi
        done
    done
    
    # کپی فایل‌های JSON
    copied_json=0
    for file in "$FOUND_DIR"/*.json 2>/dev/null; do
        if [ -f "$file" ]; then
            filename=$(basename "$file")
            if [ ! -f "$TARGET_DIR/$filename" ]; then
                cp "$file" "$TARGET_DIR/$filename"
                ((copied_json++))
                echo "   ✓ $filename (JSON)"
            fi
        fi
    done
    
    echo ""
    echo "✅ $copied_images فایل عکس و $copied_json فایل JSON کپی شدند"
else
    echo "✅ فایل‌ها در مسیر درست هستند"
fi

# تنظیم دسترسی‌ها
echo ""
echo "🔐 تنظیم دسترسی‌ها..."
chown -R www-data:www-data "$TARGET_DIR" 2>/dev/null || echo "⚠️  نیاز به sudo برای تنظیم دسترسی‌ها"
chmod -R 755 "$TARGET_DIR" 2>/dev/null || echo "⚠️  نیاز به sudo برای تنظیم دسترسی‌ها"

# بررسی نهایی
echo ""
echo "📊 بررسی نهایی:"
total_files=$(find "$TARGET_DIR" -type f 2>/dev/null | wc -l)
image_files=$(find "$TARGET_DIR" -type f \( -name "*.jpg" -o -name "*.jpeg" -o -name "*.png" -o -name "*.gif" -o -name "*.webp" -o -name "*.svg" \) 2>/dev/null | wc -l)
json_files=$(find "$TARGET_DIR" -type f -name "*.json" 2>/dev/null | wc -l)

echo "   - کل فایل‌ها: $total_files"
echo "   - فایل‌های عکس: $image_files"
echo "   - فایل‌های JSON: $json_files"
echo ""

echo "=========================================="
echo "✅ تمام!"
echo "=========================================="
echo ""
echo "📝 مراحل بعدی:"
echo "   1. Restart سرویس: sudo systemctl restart regions-map-app"
echo "   2. بررسی لاگ‌ها: sudo journalctl -u regions-map-app -n 20"
echo "   3. تست در مرورگر"
echo ""

