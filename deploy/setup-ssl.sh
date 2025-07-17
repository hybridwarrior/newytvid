#!/bin/bash
# Script to set up SSL certificate for dropbox.oracleboxing.com

echo "=== Setting up SSL for dropbox.oracleboxing.com ==="

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

# Install certbot if not already installed
if ! command -v certbot &> /dev/null; then
    echo "Installing certbot..."
    apt-get update
    apt-get install -y certbot python3-certbot-nginx
fi

# Get SSL certificate
echo "Obtaining SSL certificate from Let's Encrypt..."
certbot certonly --nginx -d dropbox.oracleboxing.com \
    --non-interactive \
    --agree-tos \
    --email admin@oracleboxing.com \
    --redirect

# Copy nginx configuration
echo "Setting up nginx configuration..."
cp /opt/new-yt/deploy/nginx-dropbox.conf /etc/nginx/sites-available/dropbox.oracleboxing.com

# Enable the site
ln -sf /etc/nginx/sites-available/dropbox.oracleboxing.com /etc/nginx/sites-enabled/

# Test nginx configuration
echo "Testing nginx configuration..."
nginx -t

if [ $? -eq 0 ]; then
    echo "Reloading nginx..."
    systemctl reload nginx
    echo "✅ SSL setup complete!"
    echo ""
    echo "Your webhook URL is: https://dropbox.oracleboxing.com/webhook"
else
    echo "❌ Nginx configuration test failed. Please check the configuration."
    exit 1
fi