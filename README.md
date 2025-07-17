# Dropbox Video Monitor

Monitors a Dropbox folder for new video uploads and automatically processes them through the clipper pipeline. Supports both webhook-based (recommended) and polling-based monitoring.

## Features

- Real-time webhook notifications from Dropbox (recommended)
- Fallback polling mode for environments without public URLs
- Supports multiple video formats (mp4, mov, avi, mkv, webm, flv, m4v)
- Downloads videos from Dropbox to local storage
- Triggers the `/opt/clipper` pipeline for video processing
- Sends Slack notifications with Dropbox folder links
- Maintains state to avoid reprocessing files

## Setup

### 1. Install Dependencies

```bash
cd /opt/new-yt
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Dropbox API

1. Create a Dropbox app at [Dropbox App Console](https://www.dropbox.com/developers/apps)
2. Generate access token or set up OAuth with refresh token
3. Note your app key and secret if using refresh token
4. Enable webhooks in the app settings (for webhook mode)

### 3. Environment Configuration

```bash
cp .env.example .env
# Edit .env with your values:
# - DROPBOX_ACCESS_TOKEN or DROPBOX_REFRESH_TOKEN + app credentials
# - DROPBOX_WATCH_FOLDER: Path to monitor (default: /All files/Video Content/Final Cuts)
# - SLACK_BOT_TOKEN: Your Slack bot token
# - DROPBOX_OUTPUT_FOLDER_URL: Shareable link to Dropbox output folder
# - WEBHOOK_PORT: Port for webhook server (default: 8080)
# - DROPBOX_WEBHOOK_APP_SECRET: App secret for webhook verification (optional)
```

## Running the Monitor

### Option 1: Webhook Mode (Recommended)

This mode provides real-time notifications when files are added to Dropbox.

1. **Ensure your server is publicly accessible:**
   - For production: Use your public server URL
   - For testing: Use ngrok: `ngrok http 8080`

2. **Start the webhook server:**
   ```bash
   cd /opt/new-yt
   source venv/bin/activate
   python scripts/webhook_server.py
   ```

   For production, use gunicorn:
   ```bash
   gunicorn -w 4 -b 0.0.0.0:8080 scripts.webhook_server:app
   ```

3. **Configure webhook in Dropbox:**
   ```bash
   # Run setup script for instructions
   python scripts/setup_webhook.py
   ```
   
   Then in Dropbox App Console:
   - Go to your app's Webhooks section
   - Add webhook URI: `https://your-server.com:8080/webhook`
   - Dropbox will verify the endpoint

### Option 2: Polling Mode (Fallback)

Use this if you can't expose a public webhook endpoint.

```bash
cd /opt/new-yt
source venv/bin/activate
python scripts/dropbox_monitor.py
```

This will check for new files every 30 minutes (configurable).

## How It Works

### Webhook Mode:
1. Dropbox sends notification when files are added to the watched folder
2. Webhook server receives notification and verifies signature
3. Server downloads new video files from Dropbox
4. Files are copied to `/opt/clipper/data/input/`
5. Clipper pipeline processes the video
6. Slack notification sent with Dropbox output link

### Polling Mode:
1. Script checks Dropbox folder every 30 minutes
2. New video files are identified by their file ID
3. Files are downloaded and processed as above

## File Structure

- `scripts/webhook_server.py` - Flask webhook server
- `scripts/dropbox_monitor.py` - Polling-based monitor
- `scripts/pipeline_processor.py` - Handles video processing
- `scripts/setup_webhook.py` - Webhook setup helper
- `config.py` - Configuration management
- `data/processed_files.json` - Tracks processed file IDs
- `data/triggers/` - Trigger files for new videos
- `data/downloads/` - Temporary download directory
- `logs/` - Application logs

## API Endpoints (Webhook Mode)

- `GET /webhook` - Dropbox verification endpoint
- `POST /webhook` - Receives Dropbox notifications
- `GET /health` - Health check endpoint

## Troubleshooting

- Check logs in `/opt/new-yt/logs/`
- Verify Dropbox API authentication is working
- For webhooks: Ensure your server is publicly accessible
- Test webhook verification: `curl http://localhost:8080/webhook?challenge=test`
- Ensure clipper pipeline is properly configured
- Check that the watch folder path exists in Dropbox

## Security Notes

- Webhook signatures are verified if `DROPBOX_WEBHOOK_APP_SECRET` is set
- Use HTTPS in production for webhook endpoints
- Keep your Dropbox tokens secure and never commit them to version control