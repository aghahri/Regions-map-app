# راهنمای دانلود صحیح اسکریپت

## مشکل:
- فایل `backup_and_clean_all.sh` پیدا نمی‌شود
- URL دانلود 404 می‌دهد

## راه‌حل:

### روش 1: بررسی مسیر فایل در GitHub:

فایل در مسیر `regions-map-app/backup_and_clean_all.sh` است، پس URL درست:

```bash
cd /var/www/regions-map-app/regions-map-app
wget https://raw.githubusercontent.com/aghahri/Regions-map-app/main/regions-map-app/backup_and_clean_all.sh
chmod +x backup_and_clean_all.sh
./backup_and_clean_all.sh
```

### روش 2: بررسی مسیر فعلی:

```bash
# بررسی مسیر فعلی
pwd

# بررسی ساختار دایرکتوری
ls -la /var/www/regions-map-app/regions-map-app/

# اگر فایل در مسیر دیگری است:
find /var/www/regions-map-app -name "backup_and_clean_all.sh"
```

### روش 3: Clone کامل از GitHub:

```bash
cd /var/www/regions-map-app
rm -rf regions-map-app
git clone https://github.com/aghahri/Regions-map-app.git regions-map-app
cd regions-map-app/regions-map-app
chmod +x backup_and_clean_all.sh
./backup_and_clean_all.sh
```

---

## URL درست برای دانلود:

```bash
wget https://raw.githubusercontent.com/aghahri/Regions-map-app/main/regions-map-app/backup_and_clean_all.sh
```

---

**موفق باشید! 🚀**

