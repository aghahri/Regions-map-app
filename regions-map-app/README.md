# نقشه محلات ایران - Regions Map App

برنامه وب برای آپلود و نمایش نقشه‌های محلات شهرهای ایران با استفاده از Shapefile و GeoJSON.

## ویژگی‌ها

- ✅ آپلود فایل Shapefile (Zip) یا GeoJSON
- ✅ نمایش نقشه روی نقشه ایران با Leaflet
- ✅ پنل ادمین برای مدیریت نقشه‌ها
- ✅ سیستم تاریخچه آپلودها
- ✅ اتصال به شبکه محلات (Tootapp.ir)
- ✅ حذف نقشه‌ها توسط ادمین

## نصب و راه‌اندازی

### پیش‌نیازها

- Python 3.10 یا بالاتر
- pip

### نصب

```bash
# Clone repository
git clone https://github.com/aghahri/Regions-map-app.git
cd Regions-map-app

# ایجاد virtual environment
python -m venv venv
source venv/bin/activate  # در Windows: venv\Scripts\activate

# نصب پکیج‌ها
pip install -r requirements.txt
```

### اجرا

```bash
python app.py
```

برنامه روی `http://localhost:5003` اجرا می‌شود.

## استفاده

### برای کاربران عادی

1. به صفحه اصلی بروید
2. لیست نقشه‌های آپلود شده را ببینید
3. روی هر نقشه کلیک کنید تا نمایش داده شود
4. روی محلات کلیک کنید تا اطلاعات و لینک توت‌اپ را ببینید

### برای ادمین

1. به `/admin/login` بروید
2. با رمز عبور ادمین وارد شوید (پیش‌فرض: `admin123`)
3. نقشه‌های جدید آپلود کنید
4. نقشه‌های قدیمی را حذف کنید

## تنظیمات

### Environment Variables

برای Production، این متغیرها را تنظیم کنید:

```bash
SECRET_KEY=یک-رشته-تصادفی-قوی
ADMIN_PASSWORD=رمز-عبور-قوی-برای-ادمین
PORT=5003
```

برای تولید SECRET_KEY:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## Deploy

برای deploy روی Render.com یا Railway.app، به فایل `DEPLOY.md` مراجعه کنید.

## ساختار پروژه

```
regions-map-app/
├── app.py                 # فایل اصلی برنامه
├── requirements.txt      # پکیج‌های Python
├── Procfile              # تنظیمات برای deploy
├── README.md             # این فایل
└── uploads/              # پوشه آپلودها (خودکار ایجاد می‌شود)
    ├── regions/
    └── storage/
```

## تکنولوژی‌ها

- **Flask**: Framework وب
- **GeoPandas**: پردازش فایل‌های GIS
- **Leaflet**: نمایش نقشه
- **Gunicorn**: سرور WSGI برای Production

## مجوز

این پروژه برای استفاده شخصی و تجاری آزاد است.

## پشتیبانی

برای مشکلات و سوالات، Issue در GitHub ایجاد کنید.


