# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Dropbox folder monitoring system that watches for new video uploads and processes them through the clipper pipeline at `/opt/clipper/`. It supports both real-time webhook notifications (recommended) and polling-based monitoring for different deployment scenarios.

## Key Commands

### Running the Webhook Server (Recommended)
```bash
cd /opt/new-yt
source venv/bin/activate
python scripts/webhook_server.py

# Production mode with gunicorn:
gunicorn -w 4 -b 0.0.0.0:8080 scripts.webhook_server:app
```

### Running the Polling Monitor (Fallback)
```bash
cd /opt/new-yt
source venv/bin/activate
python scripts/dropbox_monitor.py
```

### Webhook Setup Helper
```bash
python scripts/setup_webhook.py  # Shows webhook configuration instructions
```

### Manual Pipeline Processing
```bash
# Process any pending video triggers manually
cd /opt/new-yt
source venv/bin/activate
python scripts/pipeline_processor.py
```

### First-Time Setup
```bash
cd /opt/new-yt
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# Then configure .env with Dropbox credentials
# Run dropbox_monitor.py to start monitoring
```

## Architecture Overview

The system supports two monitoring modes:

### Webhook Mode (Recommended)
1. **Webhook Server** (`scripts/webhook_server.py`)
   - Flask web server that receives real-time notifications from Dropbox
   - Verifies webhook signatures for security
   - Processes file creation events immediately
   - Runs on configurable port (default: 8080)
   - Provides health check endpoint for monitoring

2. **Pipeline Processor** (`scripts/pipeline_processor.py`)
   - Downloads files from Dropbox using the Dropbox API
   - Copies videos to `/opt/clipper/data/input/` with metadata
   - Executes the clipper pipeline as a subprocess
   - Sends Slack notifications upon completion

### Polling Mode (Fallback)
1. **Dropbox Monitor** (`scripts/dropbox_monitor.py`)
   - Runs continuously, checking Dropbox folder every 30 minutes (configurable)
   - Uses Dropbox API with either access token or refresh token authentication
   - Creates trigger files in `data/triggers/` when new video files are found
   - Maintains processed file state in `data/processed_files.json` using Dropbox file IDs
   - Supports multiple video formats: mp4, mov, avi, mkv, webm, flv, m4v

## Integration Points

- **Dropbox API**: Uses either access token or refresh token authentication
- **Clipper Pipeline**: Executes `/opt/clipper/scripts/main.py` for video processing
- **Slack**: Sends notifications via bot token
- **Dropbox Output**: Provides shareable links to processed clips

## Data Flow

1. Monitor checks Dropbox folder → Creates trigger file with file metadata
2. Processor reads trigger → Downloads file from Dropbox → Copies to clipper input
3. Clipper processes video → Uploads clips to Dropbox
4. System sends Slack notification with Dropbox folder link

## Important Files and Directories

- `config.py`: Centralized configuration loading from environment
- `data/processed_files.json`: Tracks already processed Dropbox file IDs
- `data/triggers/`: New video trigger files (JSON format)
- `data/downloads/`: Temporary video storage before clipper processing
- `logs/`: Application logs for both monitor and processor

## Environment Variables

Required in `.env` file:
- Dropbox Authentication (one of):
  - `DROPBOX_ACCESS_TOKEN`: Direct access token
  - OR `DROPBOX_REFRESH_TOKEN` + `DROPBOX_APP_KEY` + `DROPBOX_APP_SECRET`: OAuth refresh token
- `SLACK_BOT_TOKEN`: For notifications
- `DROPBOX_OUTPUT_FOLDER_URL`: Shareable link for processed clips

Optional:
- `DROPBOX_WATCH_FOLDER`: Folder to monitor (default: /All files/Video Content/Final Cuts)
- `CHECK_INTERVAL_MINUTES`: Monitoring frequency for polling mode (default: 30)
- `SLACK_CHANNEL`: Notification channel (default: #video-notifications)
- `WEBHOOK_PORT`: Port for webhook server (default: 8080)
- `DROPBOX_WEBHOOK_APP_SECRET`: For webhook signature verification

## Development Notes

- No test suite or linting configuration currently exists
- Logging is comprehensive - check `logs/` directory for debugging
- State persistence allows safe restarts without reprocessing
- Error handling allows continued operation after individual failures
- The system integrates tightly with `/opt/clipper/` - ensure that pipeline is functional
- Dropbox file IDs are used for tracking to handle file renames/moves