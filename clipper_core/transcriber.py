#!/usr/bin/env python3
import os
import sys
import shutil
import subprocess
import json
from pathlib import Path

from dotenv import load_dotenv, find_dotenv
from openai import OpenAI
from config import UPLOADS_DIR

# ─── Load .env ───────────────────────────────────────────────────────────────
dotenv_path = find_dotenv(usecwd=True)
if not dotenv_path:
    print("❌ .env not found", file=sys.stderr)
    sys.exit(1)
load_dotenv(dotenv_path, override=True)

API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    print("❌ Missing OPENAI_API_KEY", file=sys.stderr)
    sys.exit(1)

# build the Whisper client
client = OpenAI(api_key=API_KEY).audio

# ─── Configuration ───────────────────────────────────────────────────────────
WHISPER_MODEL   = "whisper-1"
MAX_BYTES       = 25 * 1024 * 1024     # 25 MiB
SEGMENT_SECONDS = 5 * 60               # split into 5-minute chunks
TEMP_DIR        = Path(__file__).parent / ".transcriber_chunks"


def split_into_chunks(mp3_path: Path) -> list[tuple[Path,int]]:
    """Chop `mp3_path` into ~SEGMENT_SECONDS pieces with ffmpeg."""
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)
    TEMP_DIR.mkdir()
    pattern = str(TEMP_DIR / f"{mp3_path.stem}_%03d.mp3")
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-i", str(mp3_path),
        "-f", "segment",
        "-segment_time", str(SEGMENT_SECONDS),
        "-c", "copy",
        pattern
    ], check=True)
    chunks = sorted(TEMP_DIR.glob(f"{mp3_path.stem}_*.mp3"))
    return [(chunk, idx * SEGMENT_SECONDS) for idx, chunk in enumerate(chunks)]


def transcribe_file(mp3_path: Path):
    """Transcribe `mp3_path` → verbose JSON with start/end/text."""
    # decide splitting
    if mp3_path.stat().st_size > MAX_BYTES:
        print(f"🔪 {mp3_path.name} is >25 MiB, splitting…")
        pieces = split_into_chunks(mp3_path)
    else:
        pieces = [(mp3_path, 0)]

    transcripts = []
    for idx, (piece, offset) in enumerate(pieces, 1):
        print(f"▶️ Transcribing chunk {idx}/{len(pieces)}: {piece.name}")
        with piece.open("rb") as rf:
            resp = client.transcriptions.create(
                model=WHISPER_MODEL,
                file=rf,
                response_format="verbose_json",
                language="en"
            )
        # now `resp` is a TranscriptionVerbose object with a .segments list
        for seg in resp.segments:
            transcripts.append({
                "start": seg.start + offset,
                "end":   seg.end   + offset,
                "text":  seg.text.strip()
            })

    # write out to JSON alongside the mp3
    out_json = mp3_path.with_suffix(".json")
    out_json.write_text(json.dumps(transcripts, indent=2), encoding="utf-8")
    print(f"💾 Saved transcript JSON: {out_json}")

    # cleanup
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)


def main():
    if not UPLOADS_DIR.exists():
        print(f"❌ Uploads directory not found: {UPLOADS_DIR}", file=sys.stderr)
        sys.exit(1)

    # walk each category dir for .mp3 files
    for category_dir in UPLOADS_DIR.iterdir():
        if not category_dir.is_dir():
            continue
        for mp3_path in category_dir.glob("*.mp3"):
            try:
                transcribe_file(mp3_path)
            except Exception as e:
                print(f"‼️ Failed to transcribe {mp3_path.name}: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()