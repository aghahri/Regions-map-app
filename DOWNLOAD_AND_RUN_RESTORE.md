# راهنمای دانلود و اجرای اسکریپت بازگرداندن

## مشکل:
دایرکتوری `/var/www/regions-map-app/regions-map-app` وجود ندارد

## راه‌حل:

### روش 1: دانلود مستقیم اسکریپت:

```bash
cd /root
wget https://raw.githubusercontent.com/aghahri/Regions-map-app/main/regions-map-app/restore_final.sh
chmod +x restore_final.sh
./restore_final.sh
```

### روش 2: بررسی مسیر فعلی:

```bash
# بررسی مسیر فعلی
pwd

# پیدا کردن دایرکتوری regions-map-app
find /var/www -name "regions-map-app" -type d 2>/dev/null

# یا
ls -la /var/www/regions-map-app/
```

### روش 3: اگر دایرکتوری در جای دیگری است:

```bash
# پیدا کردن app.py
find /var/www -name "app.py" -type f 2>/dev/null

# سپس به آن مسیر بروید
cd [مسیر پیدا شده]
git pull origin main
chmod +x restore_final.sh
./restore_final.sh
```

---

## خلاصه دستورات (کپی-پیست):

```bash
# روش 1: دانلود مستقیم
cd /root
wget https://raw.githubusercontent.com/aghahri/Regions-map-app/main/regions-map-app/restore_final.sh
chmod +x restore_final.sh
./restore_final.sh

# یا با bash
bash restore_final.sh
```

---

**موفق باشید! 🚀**

