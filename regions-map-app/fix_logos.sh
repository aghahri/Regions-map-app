#!/bin/bash

# اسکریپت بررسی و رفع مشکل لوگوهای محلات
# استفاده: ./fix_logos.sh

APP_DIR="/var/www/regions-map-app/regions-map-app"
LOGO_DIR="$APP_DIR/uploads/regions/logos"

echo "=========================================="
echo "🔍 بررسی و رفع مشکل لوگوهای محلات"
echo "=========================================="
echo ""

# بررسی اینکه در دایرکتوری درست هستیم
if [ ! -f "app.py" ]; then
    echo "❌ خطا: فایل app.py پیدا نشد"
    echo "   لطفاً این اسکریپت را از دایرکتوری regions-map-app اجرا کنید"
    exit 1
fi

cd "$(dirname "$0")"
APP_DIR="$(pwd)"
LOGO_DIR="$APP_DIR/uploads/regions/logos"

echo "📁 دایرکتوری پروژه: $APP_DIR"
echo "📁 دایرکتوری لوگوها: $LOGO_DIR"
echo ""

# بررسی وجود فولدر
if [ ! -d "$LOGO_DIR" ]; then
    echo "⚠️  فولدر logos وجود ندارد. در حال ساخت..."
    mkdir -p "$LOGO_DIR"
    echo "✅ فولدر ساخته شد"
else
    echo "✅ فولدر logos وجود دارد"
fi

echo ""

# بررسی فایل‌های موجود
JSON_COUNT=$(ls -1 "$LOGO_DIR"/*.json 2>/dev/null | wc -l)
IMAGE_COUNT=$(ls -1 "$LOGO_DIR"/*.{jpg,jpeg,png} 2>/dev/null | wc -l)

echo "📊 آمار فایل‌ها:"
echo "   - فایل‌های JSON: $JSON_COUNT"
echo "   - فایل‌های عکس: $IMAGE_COUNT"
echo ""

# بررسی دسترسی‌ها
echo "🔐 بررسی دسترسی‌ها..."
CURRENT_USER=$(whoami)
if [ "$CURRENT_USER" = "root" ] || sudo -n true 2>/dev/null; then
    echo "   تنظیم دسترسی‌ها..."
    sudo chown -R www-data:www-data "$LOGO_DIR" 2>/dev/null || chown -R www-data:www-data "$LOGO_DIR" 2>/dev/null
    sudo chmod -R 755 "$LOGO_DIR" 2>/dev/null || chmod -R 755 "$LOGO_DIR" 2>/dev/null
    echo "✅ دسترسی‌ها تنظیم شدند"
else
    echo "⚠️  نیاز به دسترسی sudo برای تنظیم دسترسی‌ها"
    echo "   می‌توانید دستی اجرا کنید:"
    echo "   sudo chown -R www-data:www-data $LOGO_DIR"
    echo "   sudo chmod -R 755 $LOGO_DIR"
fi

echo ""

# بررسی بکاپ
echo "💾 جستجوی بکاپ..."
BACKUP_FILE=$(ls -t "$APP_DIR"/*.tar.gz 2>/dev/null | grep -E "(backup|logos)" | head -1)

if [ -n "$BACKUP_FILE" ] && [ -f "$BACKUP_FILE" ]; then
    echo "✅ بکاپ پیدا شد: $(basename "$BACKUP_FILE")"
    echo ""
    read -p "آیا می‌خواهید بکاپ را restore کنید؟ (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "📦 در حال extract کردن بکاپ..."
        cd "$APP_DIR"
        tar -xzf "$BACKUP_FILE"
        echo "✅ بکاپ restore شد"
        
        # بررسی مجدد
        JSON_COUNT_AFTER=$(ls -1 "$LOGO_DIR"/*.json 2>/dev/null | wc -l)
        IMAGE_COUNT_AFTER=$(ls -1 "$LOGO_DIR"/*.{jpg,jpeg,png} 2>/dev/null | wc -l)
        echo ""
        echo "📊 آمار بعد از restore:"
        echo "   - فایل‌های JSON: $JSON_COUNT_AFTER"
        echo "   - فایل‌های عکس: $IMAGE_COUNT_AFTER"
    fi
else
    echo "⚠️  بکاپ پیدا نشد"
    echo "   اگر بکاپ دارید، می‌توانید دستی extract کنید:"
    echo "   tar -xzf backup_YYYYMMDD_HHMMSS.tar.gz"
fi

echo ""

# بررسی route در app.py
echo "🔍 بررسی route در app.py..."
if grep -q "@app.route(\"/uploads/logos" app.py; then
    echo "✅ Route برای serve کردن لوگوها وجود دارد"
else
    echo "❌ Route برای serve کردن لوگوها پیدا نشد!"
fi

echo ""

# پیشنهاد restart
echo "🔄 پیشنهاد: سرویس‌ها را restart کنید"
if [ "$CURRENT_USER" = "root" ] || sudo -n true 2>/dev/null; then
    read -p "آیا می‌خواهید سرویس‌ها را restart کنید؟ (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "   در حال restart کردن regions-map-app..."
        sudo systemctl restart regions-map-app 2>/dev/null || echo "   ⚠️  نتوانست regions-map-app را restart کند"
        echo "   در حال restart کردن nginx..."
        sudo systemctl restart nginx 2>/dev/null || echo "   ⚠️  نتوانست nginx را restart کند"
        echo "✅ سرویس‌ها restart شدند"
    fi
else
    echo "   می‌توانید دستی اجرا کنید:"
    echo "   sudo systemctl restart regions-map-app"
    echo "   sudo systemctl restart nginx"
fi

echo ""
echo "=========================================="
echo "✅ بررسی کامل شد!"
echo "=========================================="
echo ""
echo "📝 مراحل بعدی:"
echo "   1. سایت را در مرورگر باز کنید"
echo "   2. روی یک محله کلیک کنید"
echo "   3. بررسی کنید که لوگو نمایش داده می‌شود"
echo ""
echo "🧪 تست API:"
echo "   curl \"http://localhost:5003/api/neighborhood-logo?map_id=YOUR_MAP_ID&neighborhood_name=YOUR_NEIGHBORHOOD_NAME\""
echo ""

