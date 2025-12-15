# راهنمای دیباگ مشکل نمایش لوگو

## مشکل:
لوگو نه در صفحه آپلود بعد از آپلود نمایش داده می‌شود و نه در سایدبار محله

## مراحل دیباگ:

### 1. بررسی مسیر LOGO_DIR:

```bash
# بررسی لاگ‌های Flask
sudo journalctl -u regions-map-app -n 50 | grep "استفاده از مسیر"

# باید ببینید:
# ✅ استفاده از مسیر: /var/www/regions-map-app/uploads/uploads/regions/logos
```

### 2. تست route `/uploads/logos/`:

```bash
# تست مستقیم Flask
curl -I "http://127.0.0.1:8000/uploads/logos/1c7011dedec44544ba3fe107704ae874_20251213_080849_jpg"

# باید 200 OK بدهد
```

### 3. تست از طریق nginx:

```bash
# تست از طریق nginx
curl -I "http://171.22.27.42/uploads/logos/1c7011dedec44544ba3fe107704ae874_20251213_080849_jpg"

# باید 200 OK بدهد (نه 404)
```

### 4. بررسی Console مرورگر (F12):

**در صفحه آپلود:**
1. Developer Tools را باز کنید (F12)
2. به تب Console بروید
3. یک لوگو آپلود کنید
4. لاگ‌ها را بررسی کنید:
   - `Uploading logo for neighborhood:` - باید neighborhoodId و neighborhoodName را نشان دهد
   - `Upload result:` - باید `success: true` و `logo_filename` را نشان دهد
   - `Looking for logo_preview div:` - باید div را پیدا کند
   - `Setting logo image URL:` - باید URL را نشان دهد
   - `Logo image loaded successfully` - باید این پیام را ببینید

**در صفحه اصلی (سایدبار):**
1. Developer Tools را باز کنید (F12)
2. به تب Console بروید
3. روی یک محله کلیک کنید
4. لاگ‌ها را بررسی کنید:
   - `Loading logo:` - باید selectedMapId و neighborhoodName را نشان دهد
   - `Logo API response:` - باید `success: true` و `logo_filename` را نشان دهد
   - `Loading logo image from:` - باید URL را نشان دهد
   - `Logo image loaded successfully in sidebar` - باید این پیام را ببینید

### 5. بررسی Network Tab:

**در صفحه آپلود:**
1. Developer Tools را باز کنید (F12)
2. به تب Network بروید
3. یک لوگو آپلود کنید
4. درخواست `/admin/neighborhoods/{map_id}/upload-logo` را پیدا کنید
5. Response را بررسی کنید - باید `success: true` و `logo_filename` داشته باشد
6. درخواست `/uploads/logos/{filename}` را پیدا کنید
7. Status Code را بررسی کنید - باید 200 باشد

**در صفحه اصلی (سایدبار):**
1. Developer Tools را باز کنید (F12)
2. به تب Network بروید
3. روی یک محله کلیک کنید
4. درخواست `/api/neighborhood-logo` را پیدا کنید
5. Response را بررسی کنید - باید `success: true` و `logo_filename` داشته باشد
6. درخواست `/uploads/logos/{filename}` را پیدا کنید
7. Status Code را بررسی کنید - باید 200 باشد

### 6. بررسی فایل واقعی:

```bash
# بررسی وجود فایل
ls -la /var/www/regions-map-app/uploads/uploads/regions/logos/ | grep "1c7011dedec44544ba3fe107704ae874"

# بررسی JSON
cat /var/www/regions-map-app/uploads/uploads/regions/logos/1c7011dedec44544ba3fe107704ae874.json
```

---

## مشکلات رایج و راه‌حل‌ها:

### مشکل 1: route `/uploads/logos/` 404 می‌دهد

**علت:** nginx route را به Flask proxy نمی‌کند

**راه‌حل:**
```bash
# بررسی nginx config
sudo cat /etc/nginx/sites-available/regions-map-app

# مطمئن شوید که همه route‌ها به Flask proxy می‌شوند:
# location / {
#     proxy_pass http://127.0.0.1:8000;
#     ...
# }
```

### مشکل 2: `logo_preview` div پیدا نمی‌شود

**علت:** `neighborhoodId` درست پیدا نمی‌شود

**راه‌حل:**
- در Console بررسی کنید که `neighborhoodId` چیست
- مطمئن شوید که `feature_id` در form وجود دارد

### مشکل 3: لوگو در Console load می‌شود اما نمایش داده نمی‌شود

**علت:** مشکل از CSS یا JavaScript

**راه‌حل:**
- در Console بررسی کنید که آیا error وجود دارد
- در Network Tab بررسی کنید که آیا درخواست 200 می‌دهد

---

## تست نهایی:

بعد از بررسی همه موارد:

1. **در صفحه آپلود:**
   - یک لوگو آپلود کنید
   - لوگو باید فوراً نمایش داده شود (با preview)
   - بعد از آپلود، لوگو باید با URL واقعی نمایش داده شود

2. **در صفحه اصلی:**
   - روی یک محله کلیک کنید
   - لوگو باید در سایدبار نمایش داده شود

---

## اگر هنوز کار نمی‌کند:

لطفاً این اطلاعات را ارسال کنید:

1. **Console logs** (از F12)
2. **Network Tab** (درخواست `/uploads/logos/` و Status Code)
3. **خروجی لاگ Flask:**
   ```bash
   sudo journalctl -u regions-map-app -n 50 | grep "استفاده از مسیر"
   ```
4. **تست route:**
   ```bash
   curl -I "http://127.0.0.1:8000/uploads/logos/1c7011dedec44544ba3fe107704ae874_20251213_080849_jpg"
   ```

