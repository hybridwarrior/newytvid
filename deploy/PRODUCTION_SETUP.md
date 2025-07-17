# Production Deployment Guide

This guide explains how to deploy the Dropbox webhook server in production with HTTPS using your existing domain.

## Prerequisites

- A domain with valid SSL certificate (e.g., Let's Encrypt)
- Nginx installed and configured
- Python virtual environment set up

## Step 1: Install Dependencies

```bash
cd /opt/new-yt
source venv/bin/activate
pip install -r requirements.txt
```

## Step 2: Configure Environment

Edit your `.env` file to ensure `WEBHOOK_HOST` is set for localhost only:

```bash
WEBHOOK_HOST=127.0.0.1  # Important: Only listen on localhost
WEBHOOK_PORT=8080       # Internal port
```

## Step 3: Set Up Nginx Reverse Proxy

1. Copy the nginx configuration:
   ```bash
   sudo cp /opt/new-yt/deploy/nginx.conf /etc/nginx/sites-available/dropbox-webhook
   ```

2. Edit the configuration:
   ```bash
   sudo nano /etc/nginx/sites-available/dropbox-webhook
   ```
   
   Update:
   - `server_name` to your actual domain
   - SSL certificate paths to match your Let's Encrypt setup

3. Enable the site:
   ```bash
   sudo ln -s /etc/nginx/sites-available/dropbox-webhook /etc/nginx/sites-enabled/
   sudo nginx -t  # Test configuration
   sudo systemctl reload nginx
   ```

## Step 4: Install Systemd Service

1. Copy the service file:
   ```bash
   sudo cp /opt/new-yt/deploy/dropbox-webhook.service /etc/systemd/system/
   ```

2. Reload systemd and enable the service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable dropbox-webhook
   sudo systemctl start dropbox-webhook
   ```

3. Check service status:
   ```bash
   sudo systemctl status dropbox-webhook
   sudo journalctl -u dropbox-webhook -f  # View logs
   ```

## Step 5: Configure Dropbox Webhook

1. Go to [Dropbox App Console](https://www.dropbox.com/developers/apps)
2. Select your app
3. Go to the "Webhooks" section
4. Add webhook URI: `https://your-domain.com/dropbox-webhook`
5. Dropbox will automatically verify the endpoint

## Step 6: Verify Everything is Working

1. Check the webhook endpoint:
   ```bash
   curl https://your-domain.com/dropbox-webhook/health
   ```

2. Upload a test video to your Dropbox folder
3. Check the logs:
   ```bash
   sudo journalctl -u dropbox-webhook -f
   tail -f /opt/new-yt/logs/webhook_server.log
   ```

## Security Considerations

- The webhook server only listens on localhost (127.0.0.1)
- Nginx handles SSL termination and acts as reverse proxy
- Webhook signatures are verified if `DROPBOX_WEBHOOK_APP_SECRET` is set
- The systemd service runs with limited privileges

## Maintenance

### View logs:
```bash
sudo journalctl -u dropbox-webhook -f
tail -f /opt/new-yt/logs/webhook_server.log
```

### Restart service:
```bash
sudo systemctl restart dropbox-webhook
```

### Update code:
```bash
cd /opt/new-yt
git pull  # or update your code
sudo systemctl restart dropbox-webhook
```

## Alternative: If You Can't Modify Nginx

If you can't add a new nginx configuration, you can:

1. Add the webhook location block to an existing server block in your main nginx config
2. Use a subdomain with its own SSL certificate
3. Use a different path that fits your existing nginx structure

The key is that Dropbox needs:
- A valid HTTPS endpoint
- The ability to reach your webhook server
- Consistent URL that matches what you configure in Dropbox App Console