#!/usr/bin/env python3
"""
Setup Dropbox Webhook
Helps configure the Dropbox app to send webhooks to your server
"""

import os
import sys
import requests
from urllib.parse import urljoin

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config

def main():
    """Display webhook setup instructions"""
    from dotenv import load_dotenv
    load_dotenv()
    
    config = Config()
    
    print("=== Dropbox Webhook Setup ===\n")
    
    print("To set up Dropbox webhooks, follow these steps:\n")
    
    print("1. First, ensure your webhook server is accessible from the internet:")
    print(f"   - Your server should be running on port {config.WEBHOOK_PORT}")
    print("   - You'll need a public URL (e.g., https://your-server.com)")
    print("   - Consider using ngrok for testing: ngrok http 8080\n")
    
    print("2. Start the webhook server:")
    print("   cd /opt/new-yt")
    print("   source venv/bin/activate")
    print("   python scripts/webhook_server.py\n")
    
    print("3. Configure the webhook in Dropbox App Console:")
    print("   a. Go to: https://www.dropbox.com/developers/apps")
    print("   b. Select your app")
    print("   c. Go to the 'Webhooks' section")
    print("   d. Add a webhook URI:")
    print(f"      https://your-server.com:{config.WEBHOOK_PORT}/webhook")
    print("   e. Dropbox will send a verification request\n")
    
    print("4. Webhook Configuration Details:")
    print(f"   - Webhook endpoint: /webhook")
    print(f"   - Port: {config.WEBHOOK_PORT}")
    print(f"   - Watch folder: {config.DROPBOX_WATCH_FOLDER}")
    
    if config.DROPBOX_WEBHOOK_APP_SECRET:
        print(f"   - Signature verification: ENABLED")
    else:
        print(f"   - Signature verification: DISABLED (set DROPBOX_WEBHOOK_APP_SECRET to enable)")
    
    print("\n5. Testing the webhook:")
    print("   - Upload a video file to the watched Dropbox folder")
    print("   - Check the logs at /opt/new-yt/logs/webhook_server.log")
    print("   - The file should be automatically processed through the clipper pipeline")
    
    print("\n6. Running in production:")
    print("   Use gunicorn for better performance:")
    print("   gunicorn -w 4 -b 0.0.0.0:8080 scripts.webhook_server:app")
    
    print("\n=== Current Configuration ===")
    print(f"Dropbox App Key: {config.DROPBOX_APP_KEY}")
    print(f"Watch Folder: {config.DROPBOX_WATCH_FOLDER}")
    print(f"Webhook Port: {config.WEBHOOK_PORT}")
    print(f"Webhook Secret: {'Set' if config.DROPBOX_WEBHOOK_APP_SECRET else 'Not set'}")

if __name__ == "__main__":
    main()