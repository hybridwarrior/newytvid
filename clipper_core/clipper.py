#!/usr/bin/env python3
"""
Extract clips from source MP4s based on refined JSON definitions.
Uses downloaded_clips.json manifest to locate videos, waits for JSON, and extracts clips.
"""
import sys
import json
import subprocess
import time
from pathlib import Path
import logging

from config import UPLOADS_DIR

# ─── Configuration ────────────────────────────────────────────────────────────
JSON_TIMEOUT = 30  # seconds to wait for JSON file
_SUFFIXES = [
    '.segments.summary.refined.clips.json',
    '.segments.clips.json',
    '.refined.clips.json',
    '.clips.json',
]

# ─── Logging setup ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)


def find_clips_file(category_dir: Path) -> Path | None:
    """Return the first matching clips JSON at top level of category_dir."""
    for suffix in _SUFFIXES:
        for f in category_dir.glob(f'*{suffix}'):
            return f
    return None


def extract_clips(video_path: Path, clips: list[dict], out_dir: Path) -> None:
    """Run ffmpeg to extract each clip into out_dir."""
    out_dir.mkdir(parents=True, exist_ok=True)
    base = video_path.stem

    for idx, clip in enumerate(clips, start=1):
        try:
            start = float(clip['start'])
            end = float(clip['end'])
        except (KeyError, ValueError) as e:
            logger.warning(f"Invalid timestamps in clip {idx}: {clip} ({e})")
            continue

        label = clip.get('label', f'clip{idx}')
        safe = ''.join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in label)
        safe = safe.strip().replace(' ', '_')
        filename = f"{base}_{idx:02d}_{safe}.mp4"
        dest = out_dir / filename
        duration = end - start

        logger.info(f"Clip {idx}: start={start}, duration={duration}, label={label}")
        cmd = [
            'ffmpeg', '-y', '-i', str(video_path),
            '-ss', str(start), '-t', str(duration),
            '-c', 'copy', str(dest)
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            logger.error(f"ffmpeg error for clip {idx}: {result.stderr.decode().strip()}")
        else:
            logger.info(f"Saved clip: {dest}")


def main():
    manifest_file = UPLOADS_DIR / 'downloaded_clips.json'
    if not UPLOADS_DIR.exists():
        logger.critical(f"Uploads directory not found: {UPLOADS_DIR}")
        sys.exit(1)

    try:
        manifest = json.loads(manifest_file.read_text(encoding='utf-8'))
    except Exception as e:
        logger.critical(f"Failed to load manifest {manifest_file}: {e}")
        sys.exit(1)

    for category, videos in manifest.items():
        try:
            if not videos:
                logger.info(f"No new downloads for {category}, skipping.")
                continue

            video_name = videos[0]
            category_dir = UPLOADS_DIR / category

            clips_file = find_clips_file(category_dir)
            if not clips_file:
                logger.info(f"No clips JSON for {category}, skipping.")
                continue

            # Wait for JSON availability
            start_time = time.time()
            while not clips_file.exists():
                if time.time() - start_time > JSON_TIMEOUT:
                    logger.error(f"Timeout waiting for JSON {clips_file.name} in {category}")
                    break
                time.sleep(1)
            if not clips_file.exists():
                continue

            logger.info(f"Processing '{category}' using JSON '{clips_file.name}' and video '{video_name}'")
            clips = json.loads(clips_file.read_text(encoding='utf-8'))
            if not isinstance(clips, list):
                logger.error(f"Expected list in {clips_file}, got {type(clips).__name__}")
                continue

            video_path = category_dir / video_name
            if not video_path.exists():
                base = Path(video_name).stem
                for ext in ('.mp4', '.MP4'):
                    alt = category_dir / f"{base}{ext}"
                    if alt.exists():
                        video_path = alt
                        break
            if not video_path.exists():
                logger.error(f"Source video not found: {video_name} in {category_dir}")
                continue

            extract_clips(video_path, clips, category_dir / 'clipped')
        except Exception as e:
            logger.exception(f"Unexpected error processing category '{category}': {e}")

    logger.info("🎥 All clips processed.")

if __name__ == '__main__':
    main()