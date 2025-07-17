#!/usr/bin/env python3
"""
Polling Monitor with Integrated Clipper
Periodically checks Dropbox for new files and processes them
"""

import os
import sys
import json
import time
import logging
from datetime import datetime
from pathlib import Path

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
        logging.FileHandler('/opt/new-yt/logs/polling_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PollingMonitorIntegrated:
    """Monitor Dropbox folder and process new videos with integrated clipper"""
    
    def __init__(self, config: Config):
        self.config = config
        self.watch_folder = config.DROPBOX_WATCH_FOLDER
        self.processed_files_file = '/opt/new-yt/data/processed_files.json'
        self.processed_files = set()
        self.video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.m4v'}
        
        self._load_processed_files()
        self._initialize_dropbox()
        
    def _initialize_dropbox(self):
        """Initialize Dropbox client with team settings"""
        try:
            from dropbox import DropboxTeam, common
            
            # Use team refresh token
            team = DropboxTeam(
                oauth2_refresh_token=self.config.DROPBOX_REFRESH_TOKEN,
                app_key=self.config.DROPBOX_APP_KEY,
                app_secret=self.config.DROPBOX_APP_SECRET,
            )
            self.dbx = team.as_user(self.config.SELECT_USER)
            self.dbx = self.dbx.with_path_root(common.PathRoot.namespace_id(self.config.ROOT_NAMESPACE_ID))
            
            logger.info("Successfully connected to Dropbox")
            
        except Exception as e:
            logger.error(f"Error initializing Dropbox: {e}")
            raise
    
    def _load_processed_files(self):
        """Load processed file IDs from disk"""
        if os.path.exists(self.processed_files_file):
            try:
                with open(self.processed_files_file, 'r') as f:
                    self.processed_files = set(json.load(f))
                logger.info(f"Loaded {len(self.processed_files)} processed files")
            except Exception as e:
                logger.error(f"Error loading processed files: {e}")
    
    def _save_processed_files(self):
        """Save processed file IDs to disk"""
        os.makedirs(os.path.dirname(self.processed_files_file), exist_ok=True)
        with open(self.processed_files_file, 'w') as f:
            json.dump(list(self.processed_files), f, indent=2)
    
    def _is_video_file(self, filename: str) -> bool:
        """Check if file is a video based on extension"""
        return any(filename.lower().endswith(ext) for ext in self.video_extensions)
    
    def _process_file(self, file_metadata: FileMetadata):
        """Process a new video file"""
        try:
            # Create trigger data
            trigger_data = {
                'file_id': file_metadata.id,
                'filename': file_metadata.name,
                'path': file_metadata.path_display,
                'size': file_metadata.size,
                'modified': file_metadata.client_modified.isoformat() if file_metadata.client_modified else None,
                'triggered_at': datetime.now().isoformat(),
                'source': 'polling_monitor'
            }
            
            logger.info(f"Processing new video: {file_metadata.name}")
            
            # Import and use the integrated processor
            from scripts.pipeline_processor_integrated import PipelineProcessorIntegrated
            processor = PipelineProcessorIntegrated(self.config)
            processor.process_file(trigger_data)
            
            # Mark as processed
            self.processed_files.add(file_metadata.id)
            self._save_processed_files()
            
        except Exception as e:
            logger.error(f"Error processing file {file_metadata.name}: {e}")
    
    def check_for_new_files(self):
        """Check Dropbox folder for new video files"""
        try:
            logger.info(f"Checking folder: {self.watch_folder}")
            
            # List files in the watched folder
            result = self.dbx.files_list_folder(self.watch_folder)
            
            new_files_count = 0
            for entry in result.entries:
                if isinstance(entry, FileMetadata):
                    # Check if it's a video file and not already processed
                    if (self._is_video_file(entry.name) and 
                        entry.id not in self.processed_files):
                        
                        logger.info(f"Found new video: {entry.name}")
                        self._process_file(entry)
                        new_files_count += 1
            
            # Handle pagination
            while result.has_more:
                result = self.dbx.files_list_folder_continue(result.cursor)
                for entry in result.entries:
                    if isinstance(entry, FileMetadata):
                        if (self._is_video_file(entry.name) and 
                            entry.id not in self.processed_files):
                            
                            logger.info(f"Found new video: {entry.name}")
                            self._process_file(entry)
                            new_files_count += 1
            
            if new_files_count > 0:
                logger.info(f"Processed {new_files_count} new video files")
            else:
                logger.info("No new video files found")
                
        except Exception as e:
            logger.error(f"Error checking for new files: {e}")
    
    def run(self):
        """Run the polling monitor"""
        logger.info("Starting polling monitor with integrated clipper")
        logger.info(f"Monitoring folder: {self.watch_folder}")
        logger.info(f"Check interval: {self.config.CHECK_INTERVAL_MINUTES} minutes")
        
        try:
            while True:
                self.check_for_new_files()
                
                # Sleep for the configured interval
                sleep_seconds = self.config.CHECK_INTERVAL_MINUTES * 60
                logger.info(f"Sleeping for {self.config.CHECK_INTERVAL_MINUTES} minutes...")
                time.sleep(sleep_seconds)
                
        except KeyboardInterrupt:
            logger.info("Polling monitor stopped by user")
        except Exception as e:
            logger.error(f"Polling monitor crashed: {e}")
            raise

def main():
    """Main entry point"""
    from dotenv import load_dotenv
    load_dotenv()
    
    config = Config()
    monitor = PollingMonitorIntegrated(config)
    monitor.run()

if __name__ == "__main__":
    main()