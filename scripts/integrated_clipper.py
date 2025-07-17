#!/usr/bin/env python3
"""
Integrated YouTube Clipper Pipeline
Processes videos directly in new-yt and uploads clips to IG folder
"""

import os
import sys
import json
import shutil
import logging
import requests
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

# Add clipper_core to path
sys.path.insert(0, str(Path(__file__).parent.parent / "clipper_core"))

from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/opt/new-yt/logs/integrated_clipper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DROPBOX_ACCESS_TOKEN = os.getenv("DROPBOX_ACCESS_TOKEN")
DROPBOX_REFRESH_TOKEN = os.getenv("DROPBOX_REFRESH_TOKEN")
DROPBOX_APP_KEY = os.getenv("DROPBOX_APP_KEY")
DROPBOX_APP_SECRET = os.getenv("DROPBOX_APP_SECRET")
SELECT_USER = os.getenv("SELECT_USER")
ROOT_NAMESPACE_ID = os.getenv("ROOT_NAMESPACE_ID")

# Output folder for IG clips
DROPBOX_OUTPUT_FOLDER = "/Video Content/Final Cuts/Repurposed YT Clips For IG"

# Slack webhook URL
SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/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"

# Directories
BASE_DIR = Path(__file__).parent.parent
TEMP_DIR = BASE_DIR / "data" / "temp_clips"
DOWNLOADS_DIR = BASE_DIR / "data" / "downloads"

# Ensure directories exist
TEMP_DIR.mkdir(parents=True, exist_ok=True)
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

class IntegratedClipper:
    def __init__(self):
        self.openai_client = OpenAI(api_key=OPENAI_API_KEY)
        self.dropbox_client = self._get_dropbox_client()
        
    def _get_dropbox_client(self):
        """Get Dropbox client using team refresh token"""
        try:
            from dropbox import DropboxTeam, common
            
            team = DropboxTeam(
                oauth2_refresh_token=DROPBOX_REFRESH_TOKEN,
                app_key=DROPBOX_APP_KEY,
                app_secret=DROPBOX_APP_SECRET,
            )
            dbx = team.as_user(SELECT_USER)
            dbx = dbx.with_path_root(common.PathRoot.namespace_id(ROOT_NAMESPACE_ID))
            
            logger.info("Successfully connected to Dropbox")
            return dbx
            
        except Exception as e:
            logger.error(f"Failed to connect to Dropbox: {e}")
            raise
    
    def transcribe_video(self, video_path: Path) -> str:
        """Extract audio and transcribe using OpenAI Whisper with chunking"""
        logger.info(f"Transcribing video: {video_path}")
        
        # Convert to audio
        audio_path = video_path.with_suffix('.mp3')
        
        import subprocess
        result = subprocess.run([
            'ffmpeg', '-i', str(video_path), '-vn', '-acodec', 'mp3',
            '-ab', '192k', '-ar', '44100', '-ac', '2', str(audio_path), '-y'
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"Audio conversion failed: {result.stderr}")
        
        # Transcribe with Whisper (handle chunking for large files)
        try:
            MAX_BYTES = 25 * 1024 * 1024  # 25 MiB
            SEGMENT_SECONDS = 5 * 60  # 5-minute chunks
            
            if audio_path.stat().st_size > MAX_BYTES:
                logger.info(f"Audio file is large ({audio_path.stat().st_size} bytes), splitting into chunks")
                transcript = self._transcribe_large_file(audio_path, SEGMENT_SECONDS)
            else:
                with open(audio_path, 'rb') as audio_file:
                    transcript = self.openai_client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        response_format="text"
                    )
            
            # Clean up audio file
            audio_path.unlink()
            
            logger.info("Transcription completed successfully")
            return transcript
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise
    
    def _transcribe_large_file(self, audio_path: Path, segment_seconds: int) -> str:
        """Transcribe large audio file by chunking it"""
        import subprocess
        import shutil
        
        # Create temp directory for chunks
        chunk_dir = TEMP_DIR / "chunks"
        chunk_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Split audio into chunks
            pattern = str(chunk_dir / f"{audio_path.stem}_%03d.mp3")
            subprocess.run([
                "ffmpeg", "-hide_banner", "-loglevel", "error",
                "-i", str(audio_path),
                "-f", "segment",
                "-segment_time", str(segment_seconds),
                "-c", "copy",
                pattern
            ], check=True)
            
            # Get chunks
            chunks = sorted(chunk_dir.glob(f"{audio_path.stem}_*.mp3"))
            
            # Transcribe each chunk
            transcript_parts = []
            for chunk in chunks:
                with open(chunk, 'rb') as chunk_file:
                    chunk_transcript = self.openai_client.audio.transcriptions.create(
                        model="whisper-1",
                        file=chunk_file,
                        response_format="text"
                    )
                    transcript_parts.append(chunk_transcript)
            
            # Combine transcripts
            full_transcript = " ".join(transcript_parts)
            
            # Cleanup chunks
            shutil.rmtree(chunk_dir)
            
            return full_transcript
            
        except Exception as e:
            # Cleanup on error
            if chunk_dir.exists():
                shutil.rmtree(chunk_dir)
            raise
    
    def get_clip_suggestions(self, transcript: str, video_name: str) -> List[Dict]:
        """Get clip suggestions from OpenAI"""
        logger.info("Getting clip suggestions from AI")
        
        prompt = f"""
        You are a social media expert analyzing a video transcript to identify the best clips for Instagram/TikTok.
        
        Based on the transcript below, identify 2-4 engaging segments (30-90 seconds each) that would perform well on social media.
        
        Video: {video_name}
        Transcript: {transcript[:3000]}...
        
        For each segment, estimate reasonable start and end times based on the content flow.
        
        Respond with valid JSON only:
        
        {{
            "clips": [
                {{
                    "title": "Engaging Title Here",
                    "start_time": "2:30",
                    "end_time": "3:45",
                    "description": "Why this segment is engaging"
                }}
            ]
        }}
        """
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            
            response_content = response.choices[0].message.content.strip()
            logger.info(f"Raw AI response: {response_content}")
            
            # Try to parse JSON, handle potential formatting issues
            try:
                clips_data = json.loads(response_content)
            except json.JSONDecodeError as e:
                # Try to extract JSON from response if it's wrapped in other text
                import re
                json_match = re.search(r'\{.*\}', response_content, re.DOTALL)
                if json_match:
                    clips_data = json.loads(json_match.group())
                else:
                    raise e
            
            logger.info(f"Generated {len(clips_data['clips'])} clip suggestions")
            return clips_data['clips']
            
        except Exception as e:
            logger.error(f"Failed to get clip suggestions: {e}")
            raise
    
    def extract_clips(self, video_path: Path, clips_data: List[Dict]) -> List[Path]:
        """Extract clips from video using ffmpeg"""
        logger.info(f"Extracting {len(clips_data)} clips from video")
        
        extracted_clips = []
        video_stem = video_path.stem
        
        for i, clip in enumerate(clips_data):
            # Convert MM:SS to seconds
            start_seconds = self._time_to_seconds(clip['start_time'])
            end_seconds = self._time_to_seconds(clip['end_time'])
            duration = end_seconds - start_seconds
            
            # Create safe filename
            safe_title = "".join(c for c in clip['title'] if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_title = safe_title.replace(' ', '-')
            
            clip_filename = f"{video_stem}_{i:02d}_{safe_title}.mp4"
            clip_path = TEMP_DIR / clip_filename
            
            # Extract clip with ffmpeg
            import subprocess
            result = subprocess.run([
                'ffmpeg', '-i', str(video_path), '-ss', str(start_seconds),
                '-t', str(duration), '-c:v', 'libx264', '-c:a', 'aac',
                '-avoid_negative_ts', 'make_zero', str(clip_path), '-y'
            ], capture_output=True, text=True)
            
            if result.returncode == 0 and clip_path.exists():
                extracted_clips.append(clip_path)
                logger.info(f"Extracted clip: {clip_filename}")
            else:
                logger.error(f"Failed to extract clip {i}: {result.stderr}")
        
        return extracted_clips
    
    def upload_clips_to_dropbox(self, clips: List[Path], original_name: str) -> List[Dict[str, str]]:
        """Upload clips to Dropbox IG folder and create shareable links"""
        logger.info(f"Uploading {len(clips)} clips to Dropbox")
        
        uploaded_files = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder_name = f"{original_name}_{timestamp}_clips"
        
        for clip_path in clips:
            try:
                dropbox_path = f"{DROPBOX_OUTPUT_FOLDER}/{folder_name}/{clip_path.name}"
                
                # Upload file
                with open(clip_path, 'rb') as f:
                    import dropbox
                    self.dropbox_client.files_upload(
                        f.read(),
                        dropbox_path,
                        mode=dropbox.files.WriteMode.overwrite
                    )
                
                # Create shareable link
                try:
                    shared_link = self.dropbox_client.sharing_create_shared_link_with_settings(
                        dropbox_path,
                        settings=dropbox.sharing.SharedLinkSettings(
                            requested_visibility=dropbox.sharing.RequestedVisibility.public
                        )
                    )
                    
                    uploaded_files.append({
                        'name': clip_path.name,
                        'path': dropbox_path,
                        'url': shared_link.url
                    })
                    
                except Exception as link_error:
                    logger.warning(f"Failed to create shareable link for {clip_path.name}: {link_error}")
                    uploaded_files.append({
                        'name': clip_path.name,
                        'path': dropbox_path,
                        'url': None
                    })
                
                logger.info(f"Uploaded: {clip_path.name}")
                
            except Exception as e:
                logger.error(f"Failed to upload {clip_path.name}: {e}")
        
        return uploaded_files
    
    def send_slack_notification(self, video_name: str, clips: List[Dict[str, str]]):
        """Send notification to Slack webhook with shareable links"""
        logger.info("Sending Slack notification")
        
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
                logger.info("Slack notification sent successfully")
            else:
                logger.error(f"Slack notification failed: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
    
    def _time_to_seconds(self, time_str: str) -> float:
        """Convert MM:SS to seconds"""
        parts = time_str.split(':')
        if len(parts) == 2:
            minutes, seconds = parts
            return int(minutes) * 60 + int(seconds)
        elif len(parts) == 3:
            hours, minutes, seconds = parts
            return int(hours) * 3600 + int(minutes) * 60 + int(seconds)
        else:
            return float(time_str)
    
    def process_video(self, video_path: Path) -> bool:
        """Process a single video through the complete pipeline"""
        logger.info(f"Starting integrated clipping pipeline for: {video_path}")
        
        try:
            # Step 1: Transcribe video
            transcript = self.transcribe_video(video_path)
            
            # Step 2: Get clip suggestions
            clips_data = self.get_clip_suggestions(transcript, video_path.name)
            
            # Step 3: Extract clips
            extracted_clips = self.extract_clips(video_path, clips_data)
            
            if not extracted_clips:
                logger.warning("No clips were successfully extracted")
                return False
            
            # Step 4: Upload to Dropbox
            uploaded_files = self.upload_clips_to_dropbox(extracted_clips, video_path.stem)
            
            # Step 5: Send Slack notification
            self.send_slack_notification(video_path.name, uploaded_files)
            
            # Step 6: Cleanup temp files
            for clip in extracted_clips:
                try:
                    clip.unlink()
                except Exception as e:
                    logger.warning(f"Failed to cleanup {clip}: {e}")
            
            logger.info(f"Successfully processed {video_path.name}")
            return True
            
        except Exception as e:
            logger.error(f"Pipeline failed for {video_path.name}: {e}")
            return False

def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python integrated_clipper.py <video_path>")
        sys.exit(1)
    
    video_path = Path(sys.argv[1])
    if not video_path.exists():
        print(f"Error: Video file not found: {video_path}")
        sys.exit(1)
    
    clipper = IntegratedClipper()
    success = clipper.process_video(video_path)
    
    if success:
        print(f"✅ Successfully processed {video_path.name}")
    else:
        print(f"❌ Failed to process {video_path.name}")
        sys.exit(1)

if __name__ == "__main__":
    main()