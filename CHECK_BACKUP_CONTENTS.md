# راهنمای بررسی محتوای بک‌آپ

## بررسی بک‌آپ‌های موجود:

### 1. بررسی محتوای بک‌آپ‌ها:

```bash
# بررسی محتوای بک‌آپ جدید
ls -lh /root/regions-map-backup-20251214_175002/

# بررسی محتوای بک‌آپ قدیمی
ls -lh /root/regions-backups/
```

### 2. بررسی اینکه همه فایل‌ها بک‌آپ شده‌اند:

```bash
# بررسی وجود دایرکتوری اصلی
ls -lh /root/regions-map-backup-20251214_175002/regions-map-app/

# بررسی وجود uploads
ls -lh /root/regions-map-backup-20251214_175002/regions-map-app/uploads/

# بررسی وجود systemd service
ls -lh /root/regions-map-backup-20251214_175002/regions-map-app.service

# بررسی وجود nginx config
ls -lh /root/regions-map-backup-20251214_175002/regions-map-app
```

### 3. بررسی حجم بک‌آپ:

```bash
# بررسی حجم کل
du -sh /root/regions-map-backup-20251214_175002/

# بررسی حجم هر بخش
du -sh /root/regions-map-backup-20251214_175002/*
```

### 4. اگر همه چیز درست است، می‌توانید سرور را پاک کنید:

```bash
# پاک کردن دایرکتوری اصلی
sudo rm -rf /var/www/regions-map-app

# غیرفعال کردن systemd service
sudo systemctl disable regions-map-app
sudo systemctl stop regions-map-app
```

---

## خلاصه دستورات:

```bash
# 1. بررسی محتوا
ls -lh /root/regions-map-backup-20251214_175002/

# 2. بررسی حجم
du -sh /root/regions-map-backup-20251214_175002/

# 3. بررسی uploads
ls -lh /root/regions-map-backup-20251214_175002/regions-map-app/uploads/

# 4. اگر همه چیز OK است، پاک کردن
sudo rm -rf /var/www/regions-map-app
sudo systemctl disable regions-map-app
```

---

**موفق باشید! 🚀**

