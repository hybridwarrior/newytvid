# New-YT Integration Updates

## What's New
The new-yt project now includes an integrated YouTube clipper that processes videos directly and uploads clips to the IG folder with shareable Dropbox links.

## Key Features
- **Integrated Clipper**: Processes videos without needing external clipper
- **Shareable Links**: Creates Dropbox shareable links for each clip
- **Slack Notifications**: Sends notifications with clickable links to your webhook
- **Custom Output**: Uploads to `/Video Content/Final Cuts/Repurposed YT Clips For IG`

## How It Works
1. **Video Upload**: New videos in `/Video Content/Final Cuts/YouTube` trigger the webhook
2. **Processing**: The integrated clipper:
   - Transcribes with OpenAI Whisper (handles large files with chunking)
   - Uses GPT-4 to identify engaging clips for IG/TikTok
   - Extracts clips with ffmpeg
   - Uploads to Dropbox IG folder
   - Creates shareable links
3. **Notification**: Sends Slack message with clickable links to each clip

## Updated Files
- `scripts/integrated_clipper.py` - Main clipping pipeline
- `scripts/pipeline_processor_integrated.py` - Integrated processor
- `scripts/webhook_server.py` - Updated to use integrated processor
- `.env` - Updated with correct Slack channel and webhook URL

## Configuration
- **Slack Webhook**: `https://hooks.slack.com/services/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`
- **Slack Channel**: `C092ALGA4MT`
- **Output Folder**: `/Video Content/Final Cuts/Repurposed YT Clips For IG`

## Usage
1. Start the webhook server: `python scripts/webhook_server.py`
2. Upload videos to the monitored Dropbox folder
3. The system will automatically process and notify you with shareable links

## Testing
Use `python scripts/test_notification.py` to test the Slack notification format.