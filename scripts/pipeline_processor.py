#!/usr/bin/env python3
"""
Pipeline Processor
Downloads Dropbox videos and triggers the clipper pipeline
"""

import os
import sys
import json
import logging
import subprocess
import shutil
from datetime import datetime
from typing import Dict, Optional

import dropbox
from dropbox.exceptions import ApiError
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/opt/new-yt/logs/pipeline_processor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PipelineProcessor:
    """Process Dropbox videos through the clipper pipeline"""
    
    def __init__(self, config: Config):
        self.config = config
        self.slack_client = WebClient(token=config.SLACK_BOT_TOKEN)
        self.download_dir = '/opt/new-yt/data/downloads'
        self.clipper_input_dir = config.CLIPPER_INPUT_DIR
        self._initialize_dropbox()
        
    def _initialize_dropbox(self):
        """Initialize Dropbox client"""
        try:
            # Use refresh token if available, otherwise use access token
            if self.config.DROPBOX_REFRESH_TOKEN:
                self.dbx = dropbox.Dropbox(
                    app_key=self.config.DROPBOX_APP_KEY,
                    app_secret=self.config.DROPBOX_APP_SECRET,
                    oauth2_refresh_token=self.config.DROPBOX_REFRESH_TOKEN
                )
            else:
                self.dbx = dropbox.Dropbox(self.config.DROPBOX_ACCESS_TOKEN)
            
            # Set select user for team accounts
            if hasattr(self.config, 'SELECT_USER') and self.config.SELECT_USER:
                self.dbx = self.dbx.with_path_root(dropbox.common.PathRoot.namespace_id(self.config.ROOT_NAMESPACE_ID))
                self.dbx._session.headers['Dropbox-API-Select-User'] = self.config.SELECT_USER
            
            logger.info("Successfully connected to Dropbox")
            
        except Exception as e:
            logger.error(f"Error initializing Dropbox: {e}")
            raise
    
    def download_file(self, file_path: str, file_id: str) -> Optional[str]:
        """Download file from Dropbox"""
        logger.info(f"Downloading file: {file_path}")
        
        os.makedirs(self.download_dir, exist_ok=True)
        
        # Extract filename from path
        filename = os.path.basename(file_path)
        output_path = os.path.join(self.download_dir, filename)
        
        try:
            # Download file from Dropbox
            metadata, response = self.dbx.files_download(file_path)
            
            # Save to local file
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"File downloaded successfully: {output_path}")
            return output_path
            
        except ApiError as e:
            logger.error(f"Dropbox API error: {e}")
            return None
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            return None
    
    def copy_to_clipper(self, video_path: str, file_metadata: Dict) -> bool:
        """Copy video to clipper input directory"""
        try:
            # Use original filename from Dropbox
            filename = os.path.basename(file_metadata['path'])
            dest_path = os.path.join(self.clipper_input_dir, filename)
            
            # Copy file
            shutil.copy2(video_path, dest_path)
            logger.info(f"Video copied to clipper: {dest_path}")
            
            # Create metadata file for clipper
            metadata_file = os.path.join(self.clipper_input_dir, f"{filename}.metadata.json")
            with open(metadata_file, 'w') as f:
                json.dump(file_metadata, f, indent=2)
            
            return True
            
        except Exception as e:
            logger.error(f"Error copying to clipper: {e}")
            return False
    
    def trigger_clipper_pipeline(self) -> bool:
        """Trigger the clipper pipeline"""
        try:
            logger.info("Triggering clipper pipeline...")
            
            # Run clipper main.py
            result = subprocess.run(
                [sys.executable, "/opt/clipper/scripts/main.py"],
                capture_output=True,
                text=True,
                cwd="/opt/clipper"
            )
            
            if result.returncode == 0:
                logger.info("Clipper pipeline completed successfully")
                return True
            else:
                logger.error(f"Clipper pipeline failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error triggering clipper: {e}")
            return False
    
    def send_slack_notification(self, file_metadata: Dict, success: bool):
        """Send notification to Slack"""
        try:
            if success:
                # Get Dropbox folder link from config
                dropbox_folder_url = self.config.DROPBOX_OUTPUT_FOLDER_URL
                
                message = f"✅ New video file processed successfully!\n\n" \
                         f"*File:* {file_metadata['filename']}\n" \
                         f"*Source:* Dropbox - {file_metadata['path']}\n" \
                         f"*Size:* {file_metadata['size'] / (1024*1024):.1f} MB\n\n" \
                         f"📁 *Clips uploaded to Dropbox:*\n{dropbox_folder_url}"
            else:
                message = f"❌ Failed to process video file\n\n" \
                         f"*File:* {file_metadata['filename']}\n" \
                         f"*Path:* {file_metadata['path']}\n" \
                         f"Check logs for details."
            
            response = self.slack_client.chat_postMessage(
                channel=self.config.SLACK_CHANNEL,
                text=message
            )
            logger.info("Slack notification sent successfully")
            
        except SlackApiError as e:
            logger.error(f"Error sending Slack notification: {e}")
    
    def cleanup_downloads(self, video_path: str):
        """Clean up downloaded files"""
        try:
            if os.path.exists(video_path):
                os.remove(video_path)
                logger.info(f"Cleaned up: {video_path}")
        except Exception as e:
            logger.error(f"Error cleaning up: {e}")
    
    def process_file(self, trigger_data: Dict):
        """Process a single file through the entire pipeline"""
        logger.info(f"Processing file: {trigger_data['filename']}")
        
        file_path = None
        success = False
        
        try:
            # Download file from Dropbox
            file_path = self.download_file(trigger_data['path'], trigger_data['file_id'])
            if not file_path:
                raise Exception("Failed to download file")
            
            # Copy to clipper input
            if not self.copy_to_clipper(file_path, trigger_data):
                raise Exception("Failed to copy file to clipper")
            
            # Trigger clipper pipeline
            if not self.trigger_clipper_pipeline():
                raise Exception("Clipper pipeline failed")
            
            success = True
            logger.info(f"Successfully processed file: {trigger_data['file_id']}")
            
        except Exception as e:
            logger.error(f"Error processing file: {e}")
            success = False
        
        finally:
            # Send Slack notification
            self.send_slack_notification(trigger_data, success)
            
            # Cleanup downloads
            if file_path:
                self.cleanup_downloads(file_path)
    
    def process_pending_triggers(self):
        """Process any pending trigger files"""
        trigger_dir = "/opt/new-yt/data/triggers"
        if not os.path.exists(trigger_dir):
            return
        
        for filename in os.listdir(trigger_dir):
            if filename.endswith('.json'):
                trigger_file = os.path.join(trigger_dir, filename)
                try:
                    with open(trigger_file, 'r') as f:
                        trigger_data = json.load(f)
                    
                    self.process_file(trigger_data)
                    
                    # Archive processed trigger
                    archive_dir = os.path.join(trigger_dir, 'processed')
                    os.makedirs(archive_dir, exist_ok=True)
                    shutil.move(trigger_file, os.path.join(archive_dir, filename))
                    
                except Exception as e:
                    logger.error(f"Error processing trigger {filename}: {e}")

def main():
    """Main entry point for standalone execution"""
    from dotenv import load_dotenv
    load_dotenv()
    
    config = Config()
    processor = PipelineProcessor(config)
    
    # Process any pending triggers
    processor.process_pending_triggers()

if __name__ == "__main__":
    main()