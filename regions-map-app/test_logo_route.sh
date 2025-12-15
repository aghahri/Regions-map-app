#!/bin/bash

# اسکریپت تست route لوگو

LOGO_FILENAME="0e646b0e4600ce2bb5dd78845fe5e4f0_20251214_170341_IMG_1253.png"
LOGO_DIR="/var/www/regions-map-app/uploads/uploads/regions/logos"

echo "🔍 بررسی فایل لوگو..."
echo ""

# 1. بررسی وجود فایل
echo "1️⃣ بررسی وجود فایل:"
if [ -f "$LOGO_DIR/$LOGO_FILENAME" ]; then
    echo "✅ فایل پیدا شد: $LOGO_DIR/$LOGO_FILENAME"
    ls -lh "$LOGO_DIR/$LOGO_FILENAME"
else
    echo "❌ فایل پیدا نشد: $LOGO_DIR/$LOGO_FILENAME"
    echo ""
    echo "🔍 جستجوی فایل با نام مشابه:"
    find "$LOGO_DIR" -name "*0e646b0e4600ce2bb5dd78845fe5e4f0*" 2>/dev/null
fi

echo ""
echo "2️⃣ بررسی دسترسی فایل:"
if [ -f "$LOGO_DIR/$LOGO_FILENAME" ]; then
    ls -l "$LOGO_DIR/$LOGO_FILENAME"
fi

echo ""
echo "3️⃣ تست Flask route (localhost:8000):"
curl -I "http://127.0.0.1:8000/uploads/logos/$LOGO_FILENAME" 2>&1 | head -5

echo ""
echo "4️⃣ تست nginx route (171.22.27.42):"
curl -I "http://171.22.27.42/uploads/logos/$LOGO_FILENAME" 2>&1 | head -5

echo ""
echo "5️⃣ بررسی nginx config:"
echo "Config active:"
ls -la /etc/nginx/sites-enabled/ | grep -E "(regions|iranregions)"

echo ""
echo "6️⃣ بررسی location /uploads/ در config‌ها:"
grep -r "location.*uploads" /etc/nginx/sites-available/ 2>/dev/null

echo ""
echo "✅ تست کامل شد!"

