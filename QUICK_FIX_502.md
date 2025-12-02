# راهنمای سریع رفع 502

## روی سرور این دستورات را اجرا کنید:

### 1. دانلود اسکریپت تشخیص:
```bash
cd /path/to/Regions-map-app/regions-map-app
wget https://raw.githubusercontent.com/aghahri/Regions-map-app/main/regions-map-app/diagnose_502.sh
chmod +x diagnose_502.sh
./diagnose_502.sh
```

### 2. یا دستورات دستی:

```bash
# بررسی وضعیت
sudo systemctl status regions-map-app
sudo systemctl status nginx

# اگر stopped هستند:
sudo systemctl start regions-map-app
sudo systemctl start nginx

# بررسی logs
sudo journalctl -u regions-map-app -n 50
sudo tail -20 /var/log/nginx/error.log

# Restart
sudo systemctl restart regions-map-app
sudo systemctl restart nginx
```

### 3. اگر مشکل از Socket است:

```bash
# پیدا کردن socket path
grep -r "app.sock" /etc/nginx/sites-enabled/

# بررسی وجود socket
ls -la /path/to/app.sock

# اگر وجود ندارد، permissions را درست کنید
sudo chown www-data:www-data /path/to/app.sock
sudo chmod 666 /path/to/app.sock
```

### 4. اگر مشکل از Dependencies است:

```bash
cd /path/to/Regions-map-app/regions-map-app
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart regions-map-app
```

---

## خروجی اسکریپت را برای من بفرستید تا مشکل را پیدا کنم!

