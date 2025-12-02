# رفع مشکل Divergent Branches

## مشکل: "fatal: Need to specify how to reconcile divergent branches"

این خطا یعنی branch محلی و remote از هم جدا شده‌اند.

---

## راه حل 1: Merge (پیشنهادی)

```bash
# Pull با merge
git pull origin main --no-rebase

# یا
git config pull.rebase false
git pull origin main
```

---

## راه حل 2: Rebase (اگر می‌خواهید تاریخچه تمیز باشد)

```bash
# Pull با rebase
git pull origin main --rebase

# یا
git config pull.rebase true
git pull origin main
```

---

## راه حل 3: Force Pull (اگر می‌خواهید remote را قبول کنید)

⚠️ **هشدار**: این کار تغییرات محلی را از بین می‌برد!

```bash
# ذخیره تغییرات محلی (اگر نیاز دارید)
git stash

# Reset به remote
git fetch origin
git reset --hard origin/main

# برگرداندن تغییرات (اگر stash کردید)
git stash pop
```

---

## راه حل 4: بررسی و حل Conflict

```bash
# 1. Pull
git pull origin main

# 2. اگر conflict داشت، فایل‌های conflict را باز کنید
# 3. Conflict را حل کنید
# 4. Add کنید
git add .

# 5. Commit کنید
git commit -m "Merge remote changes"
```

---

## راه حل سریع (اگر می‌خواهید remote را قبول کنید):

```bash
git fetch origin
git reset --hard origin/main
```

⚠️ این کار همه تغییرات محلی را از بین می‌برد!

---

## راه حل امن (ذخیره تغییرات محلی):

```bash
# 1. ذخیره تغییرات محلی
git stash

# 2. Pull
git pull origin main

# 3. برگرداندن تغییرات
git stash pop

# 4. اگر conflict داشت، حل کنید و commit کنید
```

---

## بررسی وضعیت:

```bash
# دیدن تفاوت‌ها
git log HEAD..origin/main --oneline
git log origin/main..HEAD --oneline

# دیدن وضعیت
git status
```

---

## تنظیمات پیش‌فرض (برای جلوگیری از این مشکل):

```bash
# تنظیم merge به عنوان پیش‌فرض
git config pull.rebase false

# یا rebase به عنوان پیش‌فرض
git config pull.rebase true
```

