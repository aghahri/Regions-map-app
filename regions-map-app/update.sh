#!/bin/bash
# اسکریپت ساده برای update کردن از GitHub

echo "🔄 Pulling latest changes from GitHub..."
cd /var/www/regions-map-app
git pull origin main

echo "📦 Updating dependencies (if needed)..."
cd regions-map-app
source /var/www/regions-map-app/venv/bin/activate
pip install -r requirements.txt --quiet

echo "🔄 Restarting services..."
sudo systemctl restart regions-map-app
sudo systemctl restart nginx

echo "✅ Update completed!"
echo ""
echo "Checking status..."
sudo systemctl status regions-map-app --no-pager -l | head -10


