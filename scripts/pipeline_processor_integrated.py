#!/usr/bin/env python3
"""
Pipeline Processor with Integrated Clipper
Downloads Dropbox videos and processes them with integrated YouTube clipper
"""

import os
import sys
import json
import logging
import shutil
from datetime import datetime
from typing import Dict, Optional
from pathlib import Path

import dropbox
from dropbox.exceptions import ApiError

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

class PipelineProcessorIntegrated:
    """Process Dropbox videos through the integrated clipper pipeline"""
    
    def __init__(self, config: Config):
        self.config = config
        self.download_dir = '/opt/new-yt/data/downloads'
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
    
    def process_with_integrated_clipper(self, video_path: str) -> bool:
        """Process video using integrated clipper"""
        try:
            logger.info("Processing video with integrated clipper...")
            
            # Import and run the integrated clipper
            clipper_script = Path(__file__).parent / "integrated_clipper.py"
            
            import subprocess
            result = subprocess.run(
                [sys.executable, str(clipper_script), video_path],
                capture_output=True,
                text=True,
                cwd="/opt/new-yt"
            )
            
            if result.returncode == 0:
                logger.info("Integrated clipper completed successfully")
                return True
            else:
                logger.error(f"Integrated clipper failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error running integrated clipper: {e}")
            return False
    
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
            
            # Process with integrated clipper
            if not self.process_with_integrated_clipper(file_path):
                raise Exception("Integrated clipper failed")
            
            success = True
            logger.info(f"Successfully processed file: {trigger_data['file_id']}")
            
        except Exception as e:
            logger.error(f"Error processing file: {e}")
            success = False
        
        finally:
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
    processor = PipelineProcessorIntegrated(config)
    
    # Process any pending triggers
    processor.process_pending_triggers()

if __name__ == "__main__":
    main()