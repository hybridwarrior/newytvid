#!/bin/bash
# Complete production setup script

set -e  # Exit on error

echo "=== Setting up Dropbox Webhook Production Server ==="

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root: sudo $0"
    exit 1
fi

# Step 1: Install Python dependencies
echo "1. Installing Python dependencies..."
cd /opt/new-yt
source venv/bin/activate
pip install -r requirements.txt

# Step 2: Install systemd service
echo "2. Installing systemd service..."
cp /opt/new-yt/deploy/dropbox-webhook.service /etc/systemd/system/
systemctl daemon-reload

# Step 3: Set up SSL certificate (if needed)
echo "3. Checking SSL certificate..."
if [ ! -d "/etc/letsencrypt/live/dropbox.oracleboxing.com" ]; then
    echo "Getting SSL certificate from Let's Encrypt..."
    if ! command -v certbot &> /dev/null; then
        apt-get update
        apt-get install -y certbot python3-certbot-nginx
    fi
    certbot certonly --standalone -d dropbox.oracleboxing.com \
        --non-interactive \
        --agree-tos \
        --email admin@oracleboxing.com \
        --pre-hook "systemctl stop nginx" \
        --post-hook "systemctl start nginx"
else
    echo "SSL certificate already exists"
fi

# Step 4: Configure nginx
echo "4. Configuring nginx..."
cp /opt/new-yt/deploy/nginx-dropbox.conf /etc/nginx/sites-available/dropbox.oracleboxing.com
ln -sf /etc/nginx/sites-available/dropbox.oracleboxing.com /etc/nginx/sites-enabled/

# Test nginx configuration
nginx -t
if [ $? -ne 0 ]; then
    echo "❌ Nginx configuration test failed!"
    exit 1
fi

# Step 5: Start services
echo "5. Starting services..."
systemctl reload nginx
systemctl enable dropbox-webhook
systemctl start dropbox-webhook

# Wait a moment for service to start
sleep 2

# Step 6: Verify everything is working
echo "6. Verifying setup..."
echo ""

# Check service status
if systemctl is-active --quiet dropbox-webhook; then
    echo "✅ Webhook service is running"
else
    echo "❌ Webhook service failed to start"
    echo "Check logs with: journalctl -u dropbox-webhook -n 50"
    exit 1
fi

# Test local endpoint
if curl -s http://localhost:8080/health > /dev/null; then
    echo "✅ Local webhook server is responding"
else
    echo "❌ Local webhook server is not responding"
    exit 1
fi

# Test public endpoint
if curl -s https://dropbox.oracleboxing.com/health > /dev/null; then
    echo "✅ Public webhook endpoint is working"
else
    echo "❌ Public webhook endpoint is not working"
    echo "Check nginx logs: tail -f /var/log/nginx/error.log"
    exit 1
fi

echo ""
echo "=== Setup Complete! ==="
echo ""
echo "Webhook URL: https://dropbox.oracleboxing.com/webhook"
echo "Health check: https://dropbox.oracleboxing.com/health"
echo ""
echo "Next steps:"
echo "1. Go to Dropbox App Console"
echo "2. Add webhook URL: https://dropbox.oracleboxing.com/webhook"
echo "3. Upload a test video to verify it works"
echo ""
echo "Useful commands:"
echo "- View logs: sudo journalctl -u dropbox-webhook -f"
echo "- Restart service: sudo systemctl restart dropbox-webhook"
echo "- Check status: sudo systemctl status dropbox-webhook"