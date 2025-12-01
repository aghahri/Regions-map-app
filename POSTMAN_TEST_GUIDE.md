# راهنمای تست API با Postman

## تنظیمات اولیه

### Base URL
```
http://your-server-ip
# یا
https://your-domain.com
```

---

## 1. تست صفحه اصلی (GET)

### Request:
- **Method**: `GET`
- **URL**: `http://your-server-ip/`
- **Headers**: (نیازی نیست)

### Response:
- باید HTML صفحه اصلی را برگرداند
- Status: `200 OK`

---

## 2. تست مشاهده نقشه خاص (GET)

### Request:
- **Method**: `GET`
- **URL**: `http://your-server-ip/map/{map_id}`
- **Example**: `http://your-server-ip/map/20241128_120000_123456`

### Response:
- Redirect به صفحه اصلی با map_id
- Status: `302 Found` یا `200 OK`

---

## 3. تست Login (POST)

### Request:
- **Method**: `POST`
- **URL**: `http://your-server-ip/admin/login`
- **Headers**:
  ```
  Content-Type: application/x-www-form-urlencoded
  ```
- **Body** (x-www-form-urlencoded):
  ```
  username: admin
  password: your-password
  ```

### Response:
- اگر موفق باشد: Redirect به `/admin`
- اگر ناموفق باشد: HTML با پیام خطا
- Status: `302 Found` (موفق) یا `200 OK` (خطا)

### نکته:
برای تست در Postman، باید **Follow redirects** را غیرفعال کنید تا response واقعی را ببینید.

---

## 4. تست Logout (POST)

### Request:
- **Method**: `POST`
- **URL**: `http://your-server-ip/admin/logout`
- **Headers**: (نیازی نیست - session cookie خودکار است)

### Response:
- Redirect به صفحه اصلی
- Status: `302 Found`

---

## 5. تست پنل ادمین (GET)

### Request:
- **Method**: `GET`
- **URL**: `http://your-server-ip/admin`
- **Headers**: 
  ```
  Cookie: session=your-session-cookie
  ```

### Response:
- HTML پنل ادمین
- Status: `200 OK`

### نکته:
بعد از login، cookie را از response کپی کنید و در headerهای بعدی استفاده کنید.

---

## 6. تست آپلود فایل Shapefile (POST)

### Request:
- **Method**: `POST`
- **URL**: `http://your-server-ip/admin`
- **Headers**:
  ```
  Cookie: session=your-session-cookie
  ```
- **Body** (form-data):
  ```
  shapefile: [Select File] → انتخاب فایل .zip یا .geojson
  map_name: نام نقشه (اختیاری)
  ```

### Response:
- HTML با پیام موفقیت یا خطا
- Status: `200 OK`

### مثال فایل:
- فایل `.zip` حاوی shapefile (`.shp`, `.shx`, `.dbf`, `.prj`)
- یا فایل `.geojson`

---

## 7. تست حذف نقشه (POST)

### Request:
- **Method**: `POST`
- **URL**: `http://your-server-ip/admin/delete/{map_id}`
- **Headers**:
  ```
  Cookie: session=your-session-cookie
  ```
- **Example**: `http://your-server-ip/admin/delete/20241128_120000_123456`

### Response:
- Redirect به `/admin?deleted=1`
- Status: `302 Found`

---

## 8. تست مشاهده لینک‌های نقشه (GET)

### Request:
- **Method**: `GET`
- **URL**: `http://your-server-ip/admin/links/{map_id}`
- **Headers**:
  ```
  Cookie: session=your-session-cookie
  ```

### Response:
- HTML صفحه مدیریت لینک‌ها
- Status: `200 OK`

---

## 9. تست ذخیره لینک توت‌اپ (POST) - API JSON

### Request:
- **Method**: `POST`
- **URL**: `http://your-server-ip/admin/links/{map_id}/save`
- **Headers**:
  ```
  Cookie: session=your-session-cookie
  ```
- **Body** (form-data یا x-www-form-urlencoded):
  ```
  feature_id: feature-0
  link: https://tootapp.ir/join/Tehran3Da
  ```
  یا فقط slug:
  ```
  feature_id: feature-0
  link: Tehran3Da
  ```

### Response (موفق):
```json
{
  "success": true,
  "message": "لینک با موفقیت ذخیره شد"
}
```
- Status: `200 OK`
- Content-Type: `application/json`

### Response (خطا):
```json
{
  "success": false,
  "error": "پیام خطا"
}
```
- Status: `400`, `403`, یا `500`

---

## 10. تست مشاهده لیست کاربران (GET)

### Request:
- **Method**: `GET`
- **URL**: `http://your-server-ip/admin/users`
- **Headers**:
  ```
  Cookie: session=your-session-cookie
  ```

### Response:
- HTML صفحه مدیریت کاربران
- Status: `200 OK`

---

## 11. تست ایجاد کاربر جدید (POST)

### Request:
- **Method**: `POST`
- **URL**: `http://your-server-ip/admin/users/create`
- **Headers**:
  ```
  Content-Type: application/x-www-form-urlencoded
  Cookie: session=your-session-cookie
  ```
- **Body** (x-www-form-urlencoded):
  ```
  username: newuser
  password: password123
  role: editor
  ```

### Response:
- Redirect به `/admin/users`
- Status: `302 Found`

---

## 12. تست تغییر رمز عبور (POST)

### Request:
- **Method**: `POST`
- **URL**: `http://your-server-ip/admin/users/change-password`
- **Headers**:
  ```
  Content-Type: application/x-www-form-urlencoded
  Cookie: session=your-session-cookie
  ```
- **Body** (x-www-form-urlencoded):
  ```
  username: username
  new_password: newpassword123
  ```

### Response:
- Redirect به `/admin/users`
- Status: `302 Found`

---

## 13. تست حذف کاربر (POST)

### Request:
- **Method**: `POST`
- **URL**: `http://your-server-ip/admin/users/delete/{username}`
- **Headers**:
  ```
  Cookie: session=your-session-cookie
  ```

### Response:
- Redirect به `/admin/users`
- Status: `302 Found`

---

## نکات مهم برای Postman:

### 1. مدیریت Session Cookie:
- بعد از login موفق، cookie را از response headers کپی کنید
- در تمام requestهای بعدی، آن را در header `Cookie` قرار دهید

### 2. تست آپلود فایل:
- در Postman، Body را روی `form-data` تنظیم کنید
- Key را `shapefile` بگذارید و نوع را `File` انتخاب کنید
- فایل را انتخاب کنید

### 3. تست API با Response JSON:
- برای endpoint `/admin/links/{map_id}/save` از `form-data` استفاده کنید
- Response به صورت JSON برمی‌گردد

### 4. بررسی Response:
- Status Code را بررسی کنید
- Response Body را بررسی کنید
- Response Headers را بررسی کنید (مخصوصاً برای cookie)

---

## Collection Postman:

می‌توانید این endpointها را در یک Collection در Postman ذخیره کنید:

1. **Environment Variables**:
   - `base_url`: `http://your-server-ip`
   - `session_cookie`: (بعد از login پر می‌شود)

2. **Pre-request Script** (برای requestهای نیازمند login):
   ```javascript
   if (!pm.environment.get("session_cookie")) {
       console.log("⚠️ Session cookie not set. Please login first.");
   }
   ```

3. **Tests** (برای request login):
   ```javascript
   if (pm.response.code === 302) {
       const cookies = pm.response.headers.get("Set-Cookie");
       if (cookies) {
           const sessionCookie = cookies.match(/session=([^;]+)/);
           if (sessionCookie) {
               pm.environment.set("session_cookie", sessionCookie[1]);
               console.log("✅ Session cookie saved");
           }
       }
   }
   ```

---

## مثال تست کامل:

### مرحله 1: Login
```
POST http://your-server-ip/admin/login
Body: username=admin&password=yourpass
→ Cookie را ذخیره کنید
```

### مرحله 2: آپلود فایل
```
POST http://your-server-ip/admin
Headers: Cookie: session=...
Body: form-data
  - shapefile: [file]
  - map_name: Test Map
```

### مرحله 3: ذخیره لینک
```
POST http://your-server-ip/admin/links/{map_id}/save
Headers: 
  Cookie: session=...
Body: form-data
  - feature_id: feature-0
  - link: https://tootapp.ir/join/Test
  (یا فقط: link: Test)
```

---

## Troubleshooting:

### مشکل: 403 Forbidden
- **علت**: Session منقضی شده یا login نشده‌اید
- **راه حل**: دوباره login کنید و cookie جدید را استفاده کنید

### مشکل: 500 Internal Server Error
- **علت**: خطا در سرور (مثلاً فایل نامعتبر)
- **راه حل**: Logs سرور را بررسی کنید

### مشکل: فایل آپلود نمی‌شود
- **علت**: فرمت فایل نامعتبر یا اندازه بزرگ
- **راه حل**: مطمئن شوید فایل `.zip` یا `.geojson` است

