#!/usr/bin/env python3
"""
Test script to demonstrate Slack notification with shareable links
"""

import requests
import json

SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/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"
DROPBOX_OUTPUT_FOLDER = "/Video Content/Final Cuts/Repurposed YT Clips For IG"

def test_slack_notification():
    """Test the Slack notification with mock data"""
    
    # Mock clips data with shareable links
    clips = [
        {
            'name': 'test_clip_01_Amazing-Boxing-Combo.mp4',
            'path': '/Video Content/Final Cuts/Repurposed YT Clips For IG/test_20250717_clips/test_clip_01_Amazing-Boxing-Combo.mp4',
            'url': 'https://www.dropbox.com/s/abc123/test_clip_01_Amazing-Boxing-Combo.mp4?dl=0'
        },
        {
            'name': 'test_clip_02_Training-Session-Highlights.mp4',
            'path': '/Video Content/Final Cuts/Repurposed YT Clips For IG/test_20250717_clips/test_clip_02_Training-Session-Highlights.mp4',
            'url': 'https://www.dropbox.com/s/def456/test_clip_02_Training-Session-Highlights.mp4?dl=0'
        },
        {
            'name': 'test_clip_03_Sparring-Technique-Tips.mp4',
            'path': '/Video Content/Final Cuts/Repurposed YT Clips For IG/test_20250717_clips/test_clip_03_Sparring-Technique-Tips.mp4',
            'url': 'https://www.dropbox.com/s/ghi789/test_clip_03_Sparring-Technique-Tips.mp4?dl=0'
        }
    ]
    
    video_name = "Test Video (Demo).mov"
    
    # Build clips list with links
    clips_text = ""
    for clip in clips:
        if clip.get('url'):
            clips_text += f"• <{clip['url']}|{clip['name']}>\n"
        else:
            clips_text += f"• {clip['name']} (link failed)\n"
    
    message = {
        "text": f"🎬 New IG clips ready from: {video_name}",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*🎬 New IG Clips Ready!*\n\n*Source Video:* {video_name}\n*Clips Generated:* {len(clips)}\n*Location:* {DROPBOX_OUTPUT_FOLDER}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Clips:*\n{clips_text}"
                }
            }
        ]
    }
    
    try:
        response = requests.post(SLACK_WEBHOOK_URL, json=message)
        if response.status_code == 200:
            print("✅ Slack notification sent successfully")
            print(f"Message preview:\n{json.dumps(message, indent=2)}")
        else:
            print(f"❌ Slack notification failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Failed to send Slack notification: {e}")

if __name__ == "__main__":
    test_slack_notification()