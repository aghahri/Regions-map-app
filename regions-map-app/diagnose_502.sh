#!/bin/bash
# اسکریپت تشخیص مشکل 502 Bad Gateway

echo "=========================================="
echo "🔍 بررسی مشکل 502 Bad Gateway"
echo "=========================================="
echo ""

# رنگ‌ها
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. بررسی وضعیت Gunicorn
echo "1️⃣ بررسی وضعیت Gunicorn..."
if systemctl is-active --quiet regions-map-app; then
    echo -e "${GREEN}✅ Gunicorn service در حال اجرا است${NC}"
    systemctl status regions-map-app --no-pager -l | head -10
else
    echo -e "${RED}❌ Gunicorn service در حال اجرا نیست!${NC}"
    echo "تلاش برای start..."
    sudo systemctl start regions-map-app
    sleep 2
    if systemctl is-active --quiet regions-map-app; then
        echo -e "${GREEN}✅ Gunicorn start شد${NC}"
    else
        echo -e "${RED}❌ Gunicorn start نشد. بررسی logs:${NC}"
        sudo journalctl -u regions-map-app -n 20 --no-pager
    fi
fi
echo ""

# 2. بررسی وضعیت Nginx
echo "2️⃣ بررسی وضعیت Nginx..."
if systemctl is-active --quiet nginx; then
    echo -e "${GREEN}✅ Nginx در حال اجرا است${NC}"
else
    echo -e "${RED}❌ Nginx در حال اجرا نیست!${NC}"
    sudo systemctl start nginx
fi
echo ""

# 3. بررسی Logs Gunicorn
echo "3️⃣ آخرین خطاهای Gunicorn:"
sudo journalctl -u regions-map-app -n 30 --no-pager | tail -20
echo ""

# 4. بررسی Logs Nginx
echo "4️⃣ آخرین خطاهای Nginx:"
sudo tail -20 /var/log/nginx/error.log 2>/dev/null || echo "فایل log پیدا نشد"
echo ""

# 5. بررسی Socket File
echo "5️⃣ بررسی Socket File..."
SOCKET_PATH=$(grep -r "app.sock" /etc/nginx/sites-enabled/ 2>/dev/null | grep -oP 'unix:[^;]+' | cut -d: -f2 | head -1)
if [ -n "$SOCKET_PATH" ]; then
    echo "Socket path: $SOCKET_PATH"
    if [ -e "$SOCKET_PATH" ]; then
        echo -e "${GREEN}✅ Socket file موجود است${NC}"
        ls -la "$SOCKET_PATH"
    else
        echo -e "${RED}❌ Socket file موجود نیست!${NC}"
        echo "مسیر: $SOCKET_PATH"
    fi
else
    echo "از TCP port استفاده می‌شود"
    PORT=$(grep -r "proxy_pass" /etc/nginx/sites-enabled/ 2>/dev/null | grep -oP ':\K[0-9]+' | head -1)
    if [ -n "$PORT" ]; then
        echo "Port: $PORT"
        if netstat -tlnp 2>/dev/null | grep -q ":$PORT "; then
            echo -e "${GREEN}✅ Port $PORT در حال listening است${NC}"
        else
            echo -e "${RED}❌ Port $PORT در حال listening نیست!${NC}"
        fi
    fi
fi
echo ""

# 6. بررسی Nginx Config
echo "6️⃣ تست Nginx Config:"
sudo nginx -t
echo ""

# 7. بررسی Python و Dependencies
echo "7️⃣ بررسی Python و Dependencies..."
APP_PATH=$(find / -name "app.py" -path "*/regions-map-app/*" 2>/dev/null | head -1)
if [ -n "$APP_PATH" ]; then
    APP_DIR=$(dirname "$APP_PATH")
    echo "مسیر app: $APP_DIR"
    
    if [ -d "$APP_DIR/venv" ]; then
        echo "Virtual environment موجود است"
        source "$APP_DIR/venv/bin/activate"
        
        echo "تست import app..."
        if python -c "import app" 2>&1; then
            echo -e "${GREEN}✅ Import موفق بود${NC}"
        else
            echo -e "${RED}❌ Import خطا دارد!${NC}"
            python -c "import app" 2>&1
        fi
    else
        echo -e "${YELLOW}⚠️ Virtual environment پیدا نشد${NC}"
    fi
else
    echo -e "${RED}❌ app.py پیدا نشد!${NC}"
fi
echo ""

# 8. بررسی Process
echo "8️⃣ Processهای Gunicorn:"
ps aux | grep gunicorn | grep -v grep
echo ""

# 9. خلاصه
echo "=========================================="
echo "📋 خلاصه:"
echo "=========================================="
if systemctl is-active --quiet regions-map-app && systemctl is-active --quiet nginx; then
    echo -e "${GREEN}✅ هر دو service در حال اجرا هستند${NC}"
    echo ""
    echo "اگر هنوز 502 می‌گیرید، احتمالاً:"
    echo "1. Socket file مشکل دارد"
    echo "2. Nginx config اشتباه است"
    echo "3. Import error در app.py"
    echo ""
    echo "Logs را بررسی کنید:"
    echo "  sudo journalctl -u regions-map-app -f"
    echo "  sudo tail -f /var/log/nginx/error.log"
else
    echo -e "${RED}❌ یکی از serviceها در حال اجرا نیست${NC}"
    echo "تلاش برای restart..."
    sudo systemctl restart regions-map-app
    sudo systemctl restart nginx
    sleep 2
    echo ""
    echo "وضعیت جدید:"
    systemctl is-active --quiet regions-map-app && echo "✅ Gunicorn: running" || echo "❌ Gunicorn: stopped"
    systemctl is-active --quiet nginx && echo "✅ Nginx: running" || echo "❌ Nginx: stopped"
fi

