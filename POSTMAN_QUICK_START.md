# راهنمای سریع Postman - رفع خطا

## مشکل: Could not get any response

این خطا معمولاً به این دلایل است:
1. URL اشتباه است
2. Method اشتباه است
3. Body درست تنظیم نشده

---

## راهنمای دقیق Login در Postman:

### مرحله 1: تنظیمات Request

1. **Method**: `POST` را انتخاب کنید
2. **URL**: دقیقاً این را وارد کنید:
   ```
   http://171.22.27.42/admin/login
   ```
   ⚠️ **نکته مهم**: فقط URL را در فیلد URL وارد کنید، نه username و password

### مرحله 2: تنظیمات Headers

در تب **Headers**:
- هیچ header اضافی نیاز نیست
- Postman خودکار `Content-Type` را تنظیم می‌کند

### مرحله 3: تنظیمات Body

1. تب **Body** را باز کنید
2. گزینه **x-www-form-urlencoded** را انتخاب کنید
3. دو فیلد اضافه کنید:

   | Key | Value |
   |-----|-------|
   | username | admin |
   | password | admin123 |

### مرحله 4: ارسال Request

روی دکمه **Send** کلیک کنید

---

## اگر باز هم خطا می‌گیرید:

### بررسی 1: سرور در دسترس است؟
```
GET http://171.22.27.42/
```
این باید صفحه اصلی را برگرداند

### بررسی 2: Port درست است؟
اگر سرور روی port دیگری است:
```
http://171.22.27.42:5000/admin/login
# یا
http://171.22.27.42:8000/admin/login
```

### بررسی 3: HTTPS یا HTTP؟
اگر سرور HTTPS است:
```
https://171.22.27.42/admin/login
```

---

## تصویر راهنما (مراحل):

```
┌─────────────────────────────────────┐
│ POST │ http://171.22.27.42/admin/login │ [Send]
├─────────────────────────────────────┤
│ Params │ Authorization │ Headers │ Body │
├─────────────────────────────────────┤
│ ○ none                              │
│ ● x-www-form-urlencoded  ← این را انتخاب کنید
│ ○ raw                               │
│ ○ binary                            │
│ ○ form-data                         │
│                                     │
│ Key          │ Value                 │
│ username     │ admin                 │
│ password     │ admin123              │
└─────────────────────────────────────┘
```

---

## Response مورد انتظار:

### اگر موفق باشد:
- **Status**: `302 Found` (Redirect)
- **Headers**: شامل `Set-Cookie: session=...`
- **Location**: `/admin`

### اگر ناموفق باشد:
- **Status**: `200 OK`
- **Body**: HTML با پیام خطا

---

## نکات مهم:

1. ✅ URL فقط: `http://171.22.27.42/admin/login`
2. ✅ Method: `POST`
3. ✅ Body: `x-www-form-urlencoded`
4. ✅ Key-Value: `username=admin` و `password=admin123`
5. ❌ URL و Body را با هم مخلوط نکنید

---

## اگر هنوز مشکل دارید:

### تست با curl:
```bash
curl -X POST http://171.22.27.42/admin/login \
  -d "username=admin&password=admin123" \
  -v
```

اگر curl کار کرد، مشکل از Postman است.
اگر curl هم کار نکرد، مشکل از سرور است.

### بررسی سرور:
```bash
ssh user@171.22.27.42
sudo systemctl status regions-map-app
sudo systemctl status nginx
```


