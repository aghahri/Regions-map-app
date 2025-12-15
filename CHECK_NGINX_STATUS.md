# راهنمای بررسی وضعیت nginx

## بررسی وضعیت nginx:

### 1. بررسی status nginx:

```bash
sudo systemctl status nginx
```

**باید ببینید:**
- `Active: active (running)`

### 2. تست nginx:

```bash
# تست از طریق localhost
curl -I http://127.0.0.1

# تست از طریق IP سرور
curl -I http://171.22.27.42
```

**باید 200 OK بدهد (نه 502)**

### 3. بررسی config nginx:

```bash
# تست config
sudo nginx -t

# بررسی config فعال
sudo cat /etc/nginx/sites-enabled/regions-map-app
```

### 4. بررسی لاگ‌های nginx:

```bash
# error log
sudo tail -f /var/log/nginx/error.log

# access log
sudo tail -f /var/log/nginx/access.log
```

### 5. بررسی Flask (که nginx به آن proxy می‌کند):

```bash
# بررسی status Flask
sudo systemctl status regions-map-app

# تست Flask
curl -I http://127.0.0.1:8000
```

---

## اگر nginx کار نمی‌کند:

### 1. Restart nginx:

```bash
sudo systemctl restart nginx
sudo systemctl status nginx
```

### 2. بررسی config:

```bash
sudo nginx -t
```

**اگر خطا دارد، باید اصلاح شود**

### 3. بررسی اینکه Flask کار می‌کند:

```bash
curl -I http://127.0.0.1:8000
```

**اگر Flask کار نمی‌کند، nginx هم 502 می‌دهد**

---

## خلاصه دستورات:

```bash
# 1. بررسی status
sudo systemctl status nginx

# 2. تست nginx
curl -I http://171.22.27.42

# 3. تست config
sudo nginx -t

# 4. بررسی Flask
sudo systemctl status regions-map-app
curl -I http://127.0.0.1:8000
```

---

**موفق باشید! 🚀**

