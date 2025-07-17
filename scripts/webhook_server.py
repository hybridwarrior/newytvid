#!/usr/bin/env python3
"""
Dropbox Webhook Server
Receives webhook notifications from Dropbox when files are added to the monitored folder
"""

import os
import sys
import json
import hmac
import hashlib
import threading
import logging
from datetime import datetime
from typing import Dict, Optional

from flask import Flask, request, jsonify
import dropbox
from dropbox.files import FileMetadata

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/opt/new-yt/logs/webhook_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
config = Config()

# Initialize Dropbox client
if config.DROPBOX_REFRESH_TOKEN:
    dbx = dropbox.Dropbox(
        app_key=config.DROPBOX_APP_KEY,
        app_secret=config.DROPBOX_APP_SECRET,
        oauth2_refresh_token=config.DROPBOX_REFRESH_TOKEN
    )
else:
    dbx = dropbox.Dropbox(config.DROPBOX_ACCESS_TOKEN)

# Set select user for team accounts
if hasattr(config, 'SELECT_USER') and config.SELECT_USER:
    dbx = dbx.with_path_root(dropbox.common.PathRoot.namespace_id(config.ROOT_NAMESPACE_ID))
    dbx._session.headers['Dropbox-API-Select-User'] = config.SELECT_USER

# Video extensions to process
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.m4v'}

# Store processed file IDs to avoid duplicates
processed_files_file = '/opt/new-yt/data/processed_files.json'
processed_files = set()

def load_processed_files():
    """Load processed file IDs from disk"""
    global processed_files
    if os.path.exists(processed_files_file):
        try:
            with open(processed_files_file, 'r') as f:
                processed_files = set(json.load(f))
        except Exception as e:
            logger.error(f"Error loading processed files: {e}")

def save_processed_files():
    """Save processed file IDs to disk"""
    os.makedirs(os.path.dirname(processed_files_file), exist_ok=True)
    with open(processed_files_file, 'w') as f:
        json.dump(list(processed_files), f, indent=2)

def is_video_file(filename: str) -> bool:
    """Check if file is a video based on extension"""
    return any(filename.lower().endswith(ext) for ext in VIDEO_EXTENSIONS)

def verify_signature(data: bytes, signature: str) -> bool:
    """Verify the webhook signature from Dropbox"""
    if not config.DROPBOX_WEBHOOK_APP_SECRET:
        logger.warning("No webhook app secret configured, skipping verification")
        return True
    
    expected = hmac.new(
        config.DROPBOX_WEBHOOK_APP_SECRET.encode('utf-8'),
        data,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected, signature)

def process_file_async(file_metadata: Dict):
    """Process a file asynchronously using integrated clipper"""
    try:
        # Import the integrated processor
        from pipeline_processor_integrated import PipelineProcessorIntegrated
        
        # Create trigger data
        trigger_data = {
            'file_id': file_metadata['id'],
            'filename': file_metadata['name'],
            'path': file_metadata['path_display'],
            'size': file_metadata.get('size', 0),
            'modified': file_metadata.get('client_modified'),
            'triggered_at': datetime.now().isoformat(),
            'source': 'dropbox_webhook'
        }
        
        trigger_file = f"/opt/new-yt/data/triggers/file_{file_metadata['id']}.json"
        os.makedirs(os.path.dirname(trigger_file), exist_ok=True)
        
        with open(trigger_file, 'w') as f:
            json.dump(trigger_data, f, indent=2)
        
        logger.info(f"Created trigger file: {trigger_file}")
        
        # Mark as processed
        processed_files.add(file_metadata['id'])
        save_processed_files()
        
        # Trigger the integrated pipeline processor
        processor = PipelineProcessorIntegrated(config)
        processor.process_file(trigger_data)
        
    except Exception as e:
        logger.error(f"Error processing file {file_metadata['id']}: {e}")

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    """Handle Dropbox webhook notifications"""
    
    # Verification request
    if request.method == 'GET':
        challenge = request.args.get('challenge')
        logger.info("Received webhook verification request")
        return challenge
    
    # Notification request
    if request.method == 'POST':
        # Verify signature
        signature = request.headers.get('X-Dropbox-Signature')
        if signature and not verify_signature(request.data, signature):
            logger.warning("Invalid webhook signature")
            return '', 403
        
        try:
            # Log the raw webhook data for debugging
            logger.info(f"Received webhook notification")
            
            # For Dropbox webhooks, we need to manually check for changes
            # The webhook just tells us "something changed"
            try:
                # List folder to find new files
                result = dbx.files_list_folder(
                    config.DROPBOX_WATCH_FOLDER,
                    recursive=False,
                    include_deleted=False
                )
                
                # Process entries
                for entry in result.entries:
                    if isinstance(entry, FileMetadata):
                        # Check if it's a video file we haven't processed
                        if (is_video_file(entry.name) and 
                            entry.id not in processed_files):
                            
                            logger.info(f"New video file detected: {entry.name}")
                            
                            # Process in background thread
                            file_data = {
                                'id': entry.id,
                                'name': entry.name,
                                'path_display': entry.path_display,
                                'size': entry.size,
                                'client_modified': entry.client_modified.isoformat() if entry.client_modified else None
                            }
                            
                            thread = threading.Thread(
                                target=process_file_async,
                                args=(file_data,)
                            )
                            thread.start()
                
            except Exception as e:
                logger.error(f"Error listing folder changes: {e}")
            
            return '', 200
            
        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            return '', 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'processed_files': len(processed_files),
        'watch_folder': config.DROPBOX_WATCH_FOLDER
    })

def main():
    """Main entry point"""
    from dotenv import load_dotenv
    load_dotenv()
    
    # Load processed files
    load_processed_files()
    
    # Start Flask server
    port = config.WEBHOOK_PORT
    host = config.WEBHOOK_HOST
    logger.info(f"Starting webhook server on {host}:{port}")
    if host == '127.0.0.1':
        logger.info("Running in production mode - configure nginx to proxy to this server")
        logger.info(f"Webhook URL should be: https://your-domain.com/dropbox-webhook")
    else:
        logger.info(f"Webhook URL will be: http://{host}:{port}/webhook")
    logger.info(f"Monitoring folder: {config.DROPBOX_WATCH_FOLDER}")
    
    app.run(
        host=host,
        port=port,
        debug=False
    )

if __name__ == "__main__":
    main()