# Workflow به‌روزرسانی

## من (AI) چه کار می‌کنم:
✅ هر بار که کد را تغییر می‌دهم، خودم commit و push می‌کنم به GitHub

## شما چه کار می‌کنید:

### روش 1: استفاده از اسکریپت (ساده‌تر)

```bash
# روی سرور
cd /var/www/regions-map-app
chmod +x regions-map-app/update.sh
./regions-map-app/update.sh
```

یا:

```bash
bash /var/www/regions-map-app/regions-map-app/update.sh
```

---

### روش 2: دستورات دستی (سریع)

```bash
cd /var/www/regions-map-app && git pull origin main && cd regions-map-app && source /var/www/regions-map-app/venv/bin/activate && pip install -r requirements.txt && sudo systemctl restart regions-map-app && sudo systemctl restart nginx
```

---

### روش 3: مرحله به مرحله

```bash
# 1. Pull
cd /var/www/regions-map-app
git pull origin main

# 2. Update dependencies (اگر نیاز باشد)
cd regions-map-app
source /var/www/regions-map-app/venv/bin/activate
pip install -r requirements.txt

# 3. Restart
sudo systemctl restart regions-map-app
sudo systemctl restart nginx

# 4. بررسی
sudo systemctl status regions-map-app
```

---

## نکات:

1. ✅ من همیشه commit و push می‌کنم - شما فقط pull کنید
2. ✅ بعد از pull، حتماً restart کنید
3. ✅ اگر مشکلی بود، logs را بررسی کنید

---

## بررسی اینکه آخرین نسخه است:

```bash
# دیدن آخرین commit
cd /var/www/regions-map-app
git log --oneline -1

# یا دیدن تغییرات
git log --oneline -5
```

---

## اگر conflict دارید:

```bash
# ذخیره تغییرات محلی
git stash

# Pull
git pull origin main

# برگرداندن تغییرات (اگر نیاز دارید)
git stash pop
```

یا اگر می‌خواهید remote را قبول کنید:

```bash
git fetch origin
git reset --hard origin/main
```

---

## خلاصه:

**من:** تغییر → Commit → Push  
**شما:** `git pull` → Restart

ساده! 🎉

