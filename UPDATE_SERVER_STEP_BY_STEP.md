# راهنمای قدم به قدم آپدیت سرور از گیت‌هاب

## 📋 پیش‌نیازها

1. دسترسی SSH به سرور
2. اطلاعات اتصال سرور (IP و username)
3. دسترسی sudo برای restart کردن سرویس‌ها

---

## 🚀 مراحل آپدیت (قدم به قدم)

### مرحله 1: اتصال به سرور

```bash
ssh user@your-server-ip
```

**مثال:**
```bash
ssh user@171.22.27.42
```

---

### مرحله 2: رفتن به دایرکتوری پروژه

```bash
cd /var/www/regions-map-app/regions-map-app
```

**یا اگر مسیر متفاوت است:**
```bash
# پیدا کردن مسیر پروژه
find / -name "app.py" -path "*/regions-map-app/*" 2>/dev/null
```

---

### مرحله 3: بکاپ از داده‌های مهم (اختیاری اما توصیه می‌شود)

```bash
# بکاپ از لینک‌های توت‌اپ
tar -czf links_backup_$(date +%Y%m%d_%H%M%S).tar.gz uploads/regions/links/

# بکاپ از لوگوها
tar -czf logos_backup_$(date +%Y%m%d_%H%M%S).tar.gz uploads/regions/logos/

# بکاپ از ویرایش‌های محلات
tar -czf edits_backup_$(date +%Y%m%d_%H%M%S).tar.gz uploads/regions/neighborhood_edits/
```

---

### مرحله 4: بررسی وضعیت Git

```bash
# بررسی وضعیت
git status

# دیدن آخرین commit
git log --oneline -1
```

---

### مرحله 5: دریافت آخرین تغییرات از گیت‌هاب

```bash
# دریافت تغییرات
git fetch origin

# آپدیت کد
git pull origin main
```

**اگر conflict داشتید:**
```bash
# ذخیره تغییرات محلی (اگر نیاز دارید)
git stash

# Pull دوباره
git pull origin main

# یا اگر می‌خواهید remote را قبول کنید:
git fetch origin
git reset --hard origin/main
```

---

### مرحله 6: بررسی حفظ شدن فولدر uploads

```bash
# بررسی وجود فولدرها
ls -la uploads/regions/links/
ls -la uploads/regions/logos/
ls -la uploads/regions/neighborhood_edits/

# اگر فولدرها وجود ندارند، از بکاپ restore کنید:
# tar -xzf links_backup_YYYYMMDD_HHMMSS.tar.gz
```

---

### مرحله 7: به‌روزرسانی Dependencies (اگر نیاز باشد)

```bash
# فعال کردن virtual environment
source venv/bin/activate

# یا اگر venv در مسیر دیگری است:
source /var/www/regions-map-app/venv/bin/activate

# نصب/به‌روزرسانی dependencies
pip install -r requirements.txt
```

---

### مرحله 8: Restart کردن سرویس‌ها

```bash
# Restart Gunicorn
sudo systemctl restart regions-map-app

# یا اگر service نام دیگری دارد:
sudo systemctl restart gunicorn

# Restart Nginx
sudo systemctl restart nginx
```

---

### مرحله 9: بررسی وضعیت سرویس‌ها

```bash
# بررسی وضعیت Gunicorn
sudo systemctl status regions-map-app

# بررسی وضعیت Nginx
sudo systemctl status nginx

# بررسی لاگ‌ها (اگر مشکلی بود)
sudo journalctl -u regions-map-app -f --lines=50
```

---

## ⚡ روش سریع (یک خطی)

اگر همه چیز درست است و فقط می‌خواهید سریع آپدیت کنید:

```bash
cd /var/www/regions-map-app/regions-map-app && git pull origin main && source venv/bin/activate && pip install -r requirements.txt && sudo systemctl restart regions-map-app && sudo systemctl restart nginx
```

---

## 🔍 بررسی بعد از آپدیت

### 1. بررسی لینک‌ها:
```bash
ls -la uploads/regions/links/
cat uploads/regions/links/{map_id}.json
```

### 2. بررسی لوگوها:
```bash
ls -la uploads/regions/logos/
```

### 3. بررسی ویرایش‌های محلات:
```bash
ls -la uploads/regions/neighborhood_edits/
cat uploads/regions/neighborhood_edits/{map_id}.json
```

### 4. تست سایت:
- باز کردن سایت در مرورگر
- بررسی اینکه نقشه‌ها کار می‌کنند
- تست پنل ادمین
- تست سایدبار محلات

---

## 🚨 حل مشکلات

### مشکل 1: "Permission denied"
```bash
# بررسی دسترسی‌ها
ls -la uploads/regions/

# اگر نیاز باشد:
sudo chown -R www-data:www-data uploads/
sudo chmod -R 755 uploads/
```

### مشکل 2: "Service failed to start"
```bash
# بررسی لاگ‌ها
sudo journalctl -u regions-map-app -n 50

# بررسی مسیرها در service file
sudo systemctl cat regions-map-app
```

### مشکل 3: "Dependencies not found"
```bash
# فعال کردن venv و نصب مجدد
source venv/bin/activate
pip install -r requirements.txt --force-reinstall
```

### مشکل 4: "Git pull failed"
```bash
# بررسی اتصال به گیت‌هاب
git remote -v

# اگر نیاز باشد:
git config --global --add safe.directory /var/www/regions-map-app
```

---

## 📝 چک‌لیست آپدیت

- [ ] اتصال به سرور
- [ ] بکاپ از داده‌های مهم
- [ ] `git pull origin main`
- [ ] بررسی حفظ شدن `uploads/`
- [ ] `pip install -r requirements.txt`
- [ ] `sudo systemctl restart regions-map-app`
- [ ] `sudo systemctl restart nginx`
- [ ] بررسی وضعیت سرویس‌ها
- [ ] تست سایت در مرورگر

---

## 💡 نکات مهم

1. ✅ **همیشه قبل از آپدیت بکاپ بگیرید** - مخصوصاً از `uploads/regions/`
2. ✅ **فولدر `uploads/` در `.gitignore` است** - پس با `git pull` از بین نمی‌رود
3. ✅ **بعد از pull، حتماً restart کنید** - تغییرات اعمال نمی‌شوند مگر restart
4. ✅ **بررسی کنید که سرویس‌ها running هستند** - با `systemctl status`
5. ✅ **اگر مشکلی بود، لاگ‌ها را بررسی کنید** - `journalctl -u regions-map-app`

---

## 🎯 خلاصه دستورات

```bash
# 1. اتصال
ssh user@your-server-ip

# 2. رفتن به دایرکتوری
cd /var/www/regions-map-app/regions-map-app

# 3. بکاپ (اختیاری)
tar -czf backup_$(date +%Y%m%d_%H%M%S).tar.gz uploads/regions/

# 4. Pull
git pull origin main

# 5. بررسی uploads
ls -la uploads/regions/

# 6. Update dependencies
source venv/bin/activate
pip install -r requirements.txt

# 7. Restart
sudo systemctl restart regions-map-app
sudo systemctl restart nginx

# 8. بررسی
sudo systemctl status regions-map-app
```

---

**موفق باشید! 🚀**

