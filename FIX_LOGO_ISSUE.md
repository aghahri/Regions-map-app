# راهنمای حل مشکل لوگوهای محلات

## 🔍 تشخیص مشکل

اگر بعد از آپدیت، لوگوهای محلات نمایش داده نمی‌شوند، این راهنما را دنبال کنید.

---

## 📋 مراحل عیب‌یابی

### مرحله 1: بررسی وجود فایل‌های لوگو

```bash
# اتصال به سرور
ssh user@your-server-ip

# رفتن به دایرکتوری پروژه
cd /var/www/regions-map-app/regions-map-app

# بررسی وجود فولدر logos
ls -la uploads/regions/logos/

# بررسی فایل‌های عکس (نه JSON)
ls -la uploads/regions/logos/*.jpg uploads/regions/logos/*.jpeg uploads/regions/logos/*.png 2>/dev/null

# بررسی فایل‌های JSON
ls -la uploads/regions/logos/*.json
```

**اگر فایل‌های عکس وجود دارند اما JSON ندارند:** → به مرحله 3 بروید  
**اگر فایل‌های JSON وجود دارند اما عکس‌ها نیستند:** → به مرحله 4 بروید  
**اگر هیچکدام وجود ندارند:** → به مرحله 5 بروید

---

### مرحله 2: بررسی دسترسی‌ها

```bash
# بررسی دسترسی‌های فولدر
ls -ld uploads/regions/logos/

# اگر دسترسی مشکل دارد:
sudo chown -R www-data:www-data uploads/regions/logos/
sudo chmod -R 755 uploads/regions/logos/
```

---

### مرحله 3: بازیابی فایل‌های JSON از بکاپ

اگر فایل‌های عکس وجود دارند اما JSON ندارند:

```bash
# پیدا کردن بکاپ
ls -la *.tar.gz | grep logos

# Extract کردن بکاپ
tar -xzf logos_backup_YYYYMMDD_HHMMSS.tar.gz

# بررسی اینکه فایل‌های JSON restore شدند
ls -la uploads/regions/logos/*.json
```

---

### مرحله 4: بازیابی فایل‌های عکس از بکاپ

اگر فایل‌های JSON وجود دارند اما عکس‌ها نیستند:

```bash
# پیدا کردن بکاپ
ls -la *.tar.gz | grep logos

# Extract کردن بکاپ
tar -xzf logos_backup_YYYYMMDD_HHMMSS.tar.gz

# بررسی اینکه فایل‌های عکس restore شدند
ls -la uploads/regions/logos/*.jpg uploads/regions/logos/*.jpeg uploads/regions/logos/*.png 2>/dev/null
```

---

### مرحله 5: بررسی بکاپ کامل

اگر هیچ فایلی وجود ندارد:

```bash
# پیدا کردن تمام بکاپ‌ها
ls -la *.tar.gz

# Extract کردن بکاپ کامل
tar -xzf backup_YYYYMMDD_HHMMSS.tar.gz

# یا اگر بکاپ logos جداگانه دارید:
tar -xzf logos_backup_YYYYMMDD_HHMMSS.tar.gz
```

---

### مرحله 6: بررسی route serve کردن لوگوها

```bash
# تست route در سرور
curl http://localhost:5003/uploads/logos/LOGO_FILENAME.jpg

# یا اگر از nginx استفاده می‌کنید:
curl http://your-domain.com/uploads/logos/LOGO_FILENAME.jpg
```

**اگر 404 می‌دهد:** → به مرحله 7 بروید

---

### مرحله 7: بررسی کد route

```bash
# بررسی اینکه route در app.py وجود دارد
grep -n "uploads/logos" app.py

# باید این خط را ببینید:
# @app.route("/uploads/logos/<filename>")
```

---

### مرحله 8: Restart سرویس

```bash
# Restart Gunicorn
sudo systemctl restart regions-map-app

# Restart Nginx
sudo systemctl restart nginx

# بررسی وضعیت
sudo systemctl status regions-map-app
```

---

## 🔧 راه‌حل سریع (اگر بکاپ دارید)

```bash
# 1. اتصال به سرور
ssh user@your-server-ip

# 2. رفتن به دایرکتوری
cd /var/www/regions-map-app/regions-map-app

# 3. پیدا کردن بکاپ
ls -la *.tar.gz | grep -E "(backup|logos)"

# 4. Extract کردن بکاپ
tar -xzf backup_YYYYMMDD_HHMMSS.tar.gz

# 5. بررسی
ls -la uploads/regions/logos/

# 6. تنظیم دسترسی‌ها
sudo chown -R www-data:www-data uploads/regions/logos/
sudo chmod -R 755 uploads/regions/logos/

# 7. Restart
sudo systemctl restart regions-map-app
sudo systemctl restart nginx
```

---

## 🛠️ اسکریپت بررسی و بازیابی خودکار

یک فایل `fix_logos.sh` بسازید:

```bash
#!/bin/bash

APP_DIR="/var/www/regions-map-app/regions-map-app"
LOGO_DIR="$APP_DIR/uploads/regions/logos"

echo "🔍 بررسی فولدر لوگوها..."
cd "$APP_DIR"

# بررسی وجود فولدر
if [ ! -d "$LOGO_DIR" ]; then
    echo "❌ فولدر logos وجود ندارد. در حال ساخت..."
    mkdir -p "$LOGO_DIR"
fi

# بررسی فایل‌های موجود
echo "📁 فایل‌های موجود:"
echo "   - JSON files: $(ls -1 $LOGO_DIR/*.json 2>/dev/null | wc -l)"
echo "   - Image files: $(ls -1 $LOGO_DIR/*.{jpg,jpeg,png} 2>/dev/null | wc -l)"

# بررسی دسترسی‌ها
echo "🔐 تنظیم دسترسی‌ها..."
sudo chown -R www-data:www-data "$LOGO_DIR"
sudo chmod -R 755 "$LOGO_DIR"

# بررسی بکاپ
echo "💾 جستجوی بکاپ..."
BACKUP_FILE=$(ls -t *.tar.gz | grep -E "(backup|logos)" | head -1)

if [ -n "$BACKUP_FILE" ]; then
    echo "✅ بکاپ پیدا شد: $BACKUP_FILE"
    read -p "آیا می‌خواهید بکاپ را restore کنید؟ (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "📦 در حال extract کردن بکاپ..."
        tar -xzf "$BACKUP_FILE"
        echo "✅ بکاپ restore شد"
    fi
else
    echo "⚠️  بکاپ پیدا نشد"
fi

# Restart سرویس
echo "🔄 در حال restart کردن سرویس‌ها..."
sudo systemctl restart regions-map-app
sudo systemctl restart nginx

echo "✅ تمام! لطفاً سایت را بررسی کنید."
```

**استفاده:**
```bash
chmod +x fix_logos.sh
./fix_logos.sh
```

---

## 🧪 تست بعد از Fix

### 1. تست API:
```bash
curl "http://localhost:5003/api/neighborhood-logo?map_id=YOUR_MAP_ID&neighborhood_name=YOUR_NEIGHBORHOOD_NAME"
```

**باید پاسخ JSON با `success: true` و `logo_filename` ببینید.**

### 2. تست نمایش لوگو:
```bash
curl "http://localhost:5003/uploads/logos/LOGO_FILENAME.jpg"
```

**باید فایل عکس را ببینید (نه 404).**

### 3. تست در مرورگر:
- باز کردن سایت
- کلیک روی یک محله
- بررسی اینکه لوگو در سایدبار نمایش داده می‌شود

---

## 📝 چک‌لیست

- [ ] فولدر `uploads/regions/logos/` وجود دارد
- [ ] فایل‌های عکس (jpg, jpeg, png) وجود دارند
- [ ] فایل‌های JSON وجود دارند
- [ ] دسترسی‌ها درست است (www-data:www-data, 755)
- [ ] Route `/uploads/logos/<filename>` کار می‌کند
- [ ] API `/api/neighborhood-logo` کار می‌کند
- [ ] سرویس‌ها restart شده‌اند
- [ ] لوگو در سایدبار نمایش داده می‌شود

---

## 🚨 اگر هنوز کار نمی‌کند

### بررسی لاگ‌ها:
```bash
# لاگ Gunicorn
sudo journalctl -u regions-map-app -n 50

# لاگ Nginx
sudo tail -f /var/log/nginx/error.log
```

### بررسی Console مرورگر:
1. باز کردن Developer Tools (F12)
2. رفتن به Console
3. کلیک روی محله
4. بررسی خطاها

### بررسی Network:
1. باز کردن Developer Tools (F12)
2. رفتن به Network
3. کلیک روی محله
4. بررسی درخواست `/api/neighborhood-logo` و `/uploads/logos/...`
5. بررسی Status Code (باید 200 باشد)

---

## 💡 نکات مهم

1. ✅ **همیشه قبل از آپدیت بکاپ بگیرید** - مخصوصاً از `uploads/regions/logos/`
2. ✅ **فولدر `uploads/` در `.gitignore` است** - پس با `git pull` از بین نمی‌رود
3. ✅ **بعد از restore بکاپ، حتماً دسترسی‌ها را تنظیم کنید**
4. ✅ **بعد از هر تغییر، سرویس‌ها را restart کنید**

---

**موفق باشید! 🚀**

