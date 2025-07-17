#!/usr/bin/env python3
"""
Test script to check Dropbox folder structure
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import Config
import dropbox

def main():
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
    
    print("=== Dropbox Folder Structure ===")
    print(f"Configured watch folder: {config.DROPBOX_WATCH_FOLDER}")
    print()
    
    # List root folder
    print("Root folder contents:")
    try:
        result = dbx.files_list_folder("", recursive=False)
        for entry in result.entries:
            if hasattr(entry, 'name'):
                print(f"  {entry.name} ({'folder' if hasattr(entry, 'id') and entry.id else 'file'})")
    except Exception as e:
        print(f"Error listing root: {e}")
    
    print()
    
    # Try to list the configured folder
    print(f"Trying to list configured folder: {config.DROPBOX_WATCH_FOLDER}")
    try:
        result = dbx.files_list_folder(config.DROPBOX_WATCH_FOLDER, recursive=False)
        print(f"Success! Found {len(result.entries)} items:")
        for entry in result.entries:
            if hasattr(entry, 'name'):
                print(f"  {entry.name}")
    except Exception as e:
        print(f"Error: {e}")
    
    print()
    
    # Try some common variations
    variations = [
        "/Video Content/Final Cuts",
        "/All files/Video Content/Final Cuts",
        "/Video Content",
        "/All files/Video Content",
        "/All files",
        "/HWT Ltd/All files/Video Content/Final Cuts",
        "/HWT Ltd/Video Content/Final Cuts"
    ]
    
    print("Trying common path variations:")
    for path in variations:
        try:
            result = dbx.files_list_folder(path, recursive=False)
            print(f"  ✅ {path} - Found {len(result.entries)} items")
        except Exception as e:
            print(f"  ❌ {path} - {str(e)[:100]}...")

if __name__ == "__main__":
    main()