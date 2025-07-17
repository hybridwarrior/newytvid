#!/usr/bin/env python3
"""
Dropbox Folder Monitor
Monitors a Dropbox folder for new video uploads and triggers the clipper pipeline
"""

import os
import sys
import time
import json
import logging
from datetime import datetime
from typing import Optional, Dict, List, Set

import dropbox
from dropbox.files import FileMetadata
from dropbox.exceptions import AuthError, ApiError
import schedule

# Add parent directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/opt/new-yt/logs/dropbox_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DropboxMonitor:
    """Monitor Dropbox folder for new video uploads"""
    
    VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.m4v'}
    
    def __init__(self, config: Config):
        self.config = config
        self.dbx = None
        self.watch_folder = config.DROPBOX_WATCH_FOLDER
        self.check_interval = config.CHECK_INTERVAL_MINUTES
        self.processed_files_file = '/opt/new-yt/data/processed_files.json'
        self.processed_files = self._load_processed_files()
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
            
            # Test the connection
            self.dbx.users_get_current_account()
            logger.info("Successfully connected to Dropbox")
            
        except AuthError as e:
            logger.error(f"Dropbox authentication failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Error initializing Dropbox: {e}")
            raise
    
    def _load_processed_files(self) -> Set[str]:
        """Load set of already processed file IDs"""
        if os.path.exists(self.processed_files_file):
            try:
                with open(self.processed_files_file, 'r') as f:
                    return set(json.load(f))
            except Exception as e:
                logger.error(f"Error loading processed files: {e}")
        return set()
    
    def _save_processed_files(self):
        """Save set of processed file IDs"""
        os.makedirs(os.path.dirname(self.processed_files_file), exist_ok=True)
        with open(self.processed_files_file, 'w') as f:
            json.dump(list(self.processed_files), f, indent=2)
    
    def _is_video_file(self, filename: str) -> bool:
        """Check if file is a video based on extension"""
        return any(filename.lower().endswith(ext) for ext in self.VIDEO_EXTENSIONS)
    
    def get_folder_files(self) -> List[FileMetadata]:
        """Get all video files in the watch folder"""
        try:
            files = []
            has_more = True
            cursor = None
            
            while has_more:
                if cursor is None:
                    result = self.dbx.files_list_folder(self.watch_folder, recursive=False)
                else:
                    result = self.dbx.files_list_folder_continue(cursor)
                
                for entry in result.entries:
                    if isinstance(entry, FileMetadata) and self._is_video_file(entry.name):
                        files.append(entry)
                
                cursor = result.cursor
                has_more = result.has_more
            
            return files
            
        except ApiError as e:
            if e.error.is_path() and e.error.get_path().is_not_found():
                logger.error(f"Folder not found: {self.watch_folder}")
            else:
                logger.error(f"API error: {e}")
            return []
        except Exception as e:
            logger.error(f"Error listing folder: {e}")
            return []
    
    def check_for_new_files(self):
        """Check for new video files and process them"""
        logger.info("Checking for new video files...")
        
        try:
            files = self.get_folder_files()
            new_files = [f for f in files if f.id not in self.processed_files]
            
            if new_files:
                logger.info(f"Found {len(new_files)} new video file(s)")
                for file in new_files:
                    self.process_new_file(file)
            else:
                logger.info("No new video files found")
                
        except Exception as e:
            logger.error(f"Error checking for new files: {e}")
    
    def process_new_file(self, file: FileMetadata):
        """Process a new video file by triggering the pipeline"""
        logger.info(f"Processing new file: {file.name} (ID: {file.id})")
        
        try:
            # Create a trigger file for the pipeline
            trigger_data = {
                'file_id': file.id,
                'filename': file.name,
                'path': file.path_display,
                'size': file.size,
                'modified': file.client_modified.isoformat() if file.client_modified else None,
                'triggered_at': datetime.now().isoformat(),
                'source': 'dropbox'
            }
            
            trigger_file = f"/opt/new-yt/data/triggers/file_{file.id}.json"
            os.makedirs(os.path.dirname(trigger_file), exist_ok=True)
            
            with open(trigger_file, 'w') as f:
                json.dump(trigger_data, f, indent=2)
            
            # Mark file as processed
            self.processed_files.add(file.id)
            self._save_processed_files()
            
            logger.info(f"Created trigger file: {trigger_file}")
            
            # Trigger the pipeline processor
            from pipeline_processor import PipelineProcessor
            processor = PipelineProcessor(self.config)
            processor.process_file(trigger_data)
            
        except Exception as e:
            logger.error(f"Error processing file {file.id}: {e}")
    
    def run(self):
        """Run the monitor continuously"""
        logger.info(f"Starting Dropbox monitor for folder: {self.watch_folder}")
        logger.info(f"Checking every {self.check_interval} minutes")
        
        # Initial check
        self.check_for_new_files()
        
        # Schedule periodic checks
        schedule.every(self.check_interval).minutes.do(self.check_for_new_files)
        
        # Run scheduler
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute for due tasks

def main():
    """Main entry point"""
    from dotenv import load_dotenv
    load_dotenv()
    
    config = Config()
    monitor = DropboxMonitor(config)
    
    try:
        monitor.run()
    except KeyboardInterrupt:
        logger.info("Monitor stopped by user")
    except Exception as e:
        logger.error(f"Monitor failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()