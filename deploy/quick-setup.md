# Quick Setup for dropbox.oracleboxing.com

Now that you have the DNS pointing to your server, here's the quick setup:

## 1. Set up SSL Certificate (if not already done)

```bash
sudo /opt/new-yt/deploy/setup-ssl.sh
```

This will:
- Install certbot if needed
- Get SSL certificate for dropbox.oracleboxing.com
- Configure nginx automatically

## 2. Install and Start the Webhook Service

```bash
# Install Python dependencies
cd /opt/new-yt
source venv/bin/activate
pip install -r requirements.txt

# Install the systemd service
sudo cp /opt/new-yt/deploy/dropbox-webhook.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable dropbox-webhook
sudo systemctl start dropbox-webhook

# Check if it's running
sudo systemctl status dropbox-webhook
```

## 3. Configure Dropbox Webhook

1. Go to [Dropbox App Console](https://www.dropbox.com/developers/apps)
2. Select your app
3. Go to "Webhooks" section
4. Add webhook URI: `https://dropbox.oracleboxing.com/webhook`
5. Click "Add" - Dropbox will verify automatically

## 4. Test Everything

```bash
# Test the health endpoint
curl https://dropbox.oracleboxing.com/health

# Watch the logs
sudo journalctl -u dropbox-webhook -f
```

## Your Webhook URLs:

- **Webhook endpoint**: https://dropbox.oracleboxing.com/webhook
- **Health check**: https://dropbox.oracleboxing.com/health

## That's it! 

When you upload a video to `/All files/Video Content/Final Cuts` in Dropbox, it will:
1. Trigger the webhook
2. Download the video
3. Process it through the clipper pipeline
4. Send you a Slack notification