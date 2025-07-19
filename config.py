"""
Configuration for Dropbox Video Monitor
"""

import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configuration settings"""
    
    # Dropbox API Configuration
    DROPBOX_ACCESS_TOKEN = os.getenv('DROPBOX_ACCESS_TOKEN')
    DROPBOX_REFRESH_TOKEN = os.getenv('DROPBOX_REFRESH_TOKEN')
    DROPBOX_APP_KEY = os.getenv('DROPBOX_APP_KEY')
    DROPBOX_APP_SECRET = os.getenv('DROPBOX_APP_SECRET')
    
    # Dropbox Folder Configuration
    DROPBOX_WATCH_FOLDER = os.getenv('DROPBOX_WATCH_FOLDER', '/All files/Video Content/Final Cuts')
    
    # Dropbox Team Configuration
    SELECT_USER = os.getenv('SELECT_USER')
    ROOT_NAMESPACE_ID = os.getenv('ROOT_NAMESPACE_ID')
    
    # Monitoring Configuration
    CHECK_INTERVAL_MINUTES = int(os.getenv('CHECK_INTERVAL_MINUTES', '30'))  # How often to check for new files
    
    # Clipper Integration
    CLIPPER_INPUT_DIR = os.getenv('CLIPPER_INPUT_DIR', '/opt/clipper/data/input')
    
    # Slack Configuration
    SLACK_BOT_TOKEN = os.getenv('SLACK_BOT_TOKEN')
    SLACK_CHANNEL = os.getenv('SLACK_CHANNEL', '#video-notifications')
    
    # Dropbox Output Configuration
    DROPBOX_OUTPUT_FOLDER_URL = os.getenv('DROPBOX_OUTPUT_FOLDER_URL')  # Shareable link to Dropbox output folder
    
    # Storage Box Configuration
    STORAGE_HOST = os.getenv('STORAGE_HOST')
    STORAGE_USER = os.getenv('STORAGE_USER')
    STORAGE_PASSWORD = os.getenv('STORAGE_PASSWORD')
    STORAGE_BASE_PATH = os.getenv('STORAGE_BASE_PATH', '/BoxingDB/youtube')
    
    # Webhook Configuration
    WEBHOOK_PORT = int(os.getenv('WEBHOOK_PORT', '8080'))
    WEBHOOK_HOST = os.getenv('WEBHOOK_HOST', '127.0.0.1')  # Use 127.0.0.1 for production with nginx
    DROPBOX_WEBHOOK_APP_SECRET = os.getenv('DROPBOX_WEBHOOK_APP_SECRET')  # For verifying webhook signatures
    
    def __init__(self):
        """Validate required configuration"""
        # At least one Dropbox auth method is required
        if not self.DROPBOX_ACCESS_TOKEN and not (self.DROPBOX_REFRESH_TOKEN and self.DROPBOX_APP_KEY and self.DROPBOX_APP_SECRET):
            raise ValueError("Either DROPBOX_ACCESS_TOKEN or (DROPBOX_REFRESH_TOKEN, DROPBOX_APP_KEY, DROPBOX_APP_SECRET) must be provided")
        
        # Other required variables
        required_vars = [
            'SLACK_BOT_TOKEN',
            'DROPBOX_OUTPUT_FOLDER_URL'
        ]
        
        missing = [var for var in required_vars if not getattr(self, var)]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")