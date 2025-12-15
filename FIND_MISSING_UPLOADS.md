# راهنمای پیدا کردن uploads گمشده

## مشکل:
`uploads/` در بک‌آپ نیست اما دایرکتوری اصلی پاک شده است.

## راه‌حل:

### 1. بررسی بک‌آپ قدیمی:

```bash
# بررسی بک‌آپ قدیمی
ls -lh /root/regions-backups/

# بررسی وجود uploads در بک‌آپ قدیمی
find /root/regions-backups -name "uploads" -type d
```

### 2. بررسی مسیرهای دیگر:

```bash
# جستجوی uploads در کل سیستم
find /var/www -name "uploads" -type d 2>/dev/null
find /root -name "uploads" -type d 2>/dev/null
```

### 3. بررسی اینکه آیا uploads در مسیر دیگری بود:

```bash
# بررسی ساختار بک‌آپ
ls -la /root/regions-map-backup-20251214_175002/regions-map-app/

# بررسی اینکه آیا uploads در مسیر دیگری است
find /root/regions-map-backup-20251214_175002 -name "uploads" -type d
```

### 4. اگر uploads پیدا نشد:

احتمالاً `uploads/` در مسیر اصلی وجود نداشت یا در مسیر دیگری بود (مثلاً `/var/www/regions-map-app/uploads/uploads/`).

### 5. ساخت uploads خالی (اگر لازم بود):

```bash
# ساخت uploads خالی برای شروع دوباره
mkdir -p /root/regions-map-backup-20251214_175002/regions-map-app/uploads
mkdir -p /root/regions-map-backup-20251214_175002/regions-map-app/uploads/regions/logos
mkdir -p /root/regions-map-backup-20251214_175002/regions-map-app/uploads/regions/neighborhood_edits
```

---

## خلاصه دستورات:

```bash
# 1. بررسی بک‌آپ قدیمی
ls -lh /root/regions-backups/
find /root/regions-backups -name "uploads" -type d

# 2. جستجوی uploads
find /var/www -name "uploads" -type d 2>/dev/null
find /root -name "uploads" -type d 2>/dev/null

# 3. بررسی ساختار بک‌آپ
ls -la /root/regions-map-backup-20251214_175002/regions-map-app/
find /root/regions-map-backup-20251214_175002 -name "uploads" -type d
```

---

**موفق باشید! 🚀**

