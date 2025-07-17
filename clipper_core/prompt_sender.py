#!/usr/bin/env python3
"""
Send transcripts to OpenAI GPT to generate clip summaries per category instructions.
Refactored to use centralized UPLOADS_DIR from config.py and environment for API key.
"""
import os
import sys
import json
from pathlib import Path

from config import UPLOADS_DIR
from openai import OpenAI

# ─── Load API key ─────────────────────────────────────────────────────────────
API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    print("❌ Missing OPENAI_API_KEY environment variable", file=sys.stderr)
    sys.exit(1)
client = OpenAI(api_key=API_KEY)

# ─── Configuration ────────────────────────────────────────────────────────────
PROMPT_INSTRUCTIONS = {
    "Oracle_Chronicles": (
        """You’re editing a premium boxing education series called Oracle Chronicles.
The video features padwork, sparring, and bagwork sessions with real-time coach commentary.
From the following timestamped transcript, **condense** to just the single most valuable moments—
each on its own line in the format `start-end: spoken text`.
Aim for ~52 s per moment, adjust boundaries as needed to capture full combo + reaction.
Do NOT output any JSON or extra formatting—just lines like:
275.0-327.0: Nice and sharp combination, keep it tight and quick."""
    ),
    "Training": (
        """You’re editing boxing training footage (bag work, pad work, sparring) without commentary.
If the transcript explicitly says \"clip the last three minutes,\" do exactly that.
Otherwise:
 • If there’s any spoken dialogue, clip the entire spoken section plus ~5–10 s before and after for context.
 • If there’s no dialogue, estimate the most action-packed moments based on typical 3-minute rounds.
 • Whenever you see audible cues (grunts, bag thuds, crowd noise), include ~10–20 s around them.
Aim for generous clips of ~30–45 s each, free of repetition.
Output each on its own line in the format `start-end: text or description of action`.
Do NOT output JSON or any extra formatting."""
    ),
    "YouTube_Clipper": (
        """You’re editing a YouTube boxing tutorial into ~60 s social clips.
From the timestamped transcript, choose only the clearest standalone lessons.
If a lesson exceeds 60 s, split into “Part 1: Label,” “Part 2: Label,” etc., but avoid repeats.
Output each on its own line `start-end: text`—no JSON, no extra formatting."""
    ),
    "YouTube_Editor": (
        """You’re editing uncut boxing instruction for final YouTube.
Extract only polished segments (hooks, intros, demos, CTAs), omit filler/mistakes, obey any “do not include…” directions.
Aim for 30–60 s per clip.
Output each on its own line `start-end: text`—no JSON, no extra formatting."""
    ),
    "Non-Boxing": (
        """You’re editing a non-boxing video (business talks, casual banter, interviews, sketches, etc.).  
From the timestamped transcript, identify the single most compelling moments—insightful insights, punchlines, key takeaways, or standout reactions.  
 • For spoken sections, clip the heart of each idea or joke, including ~3–5 s of lead-in and follow-through for context.  
 • For purely visual moments (pauses, reactions, actions), use the transcript cues to estimate ~5–10 s highlights.  
 • Aim for clips of ~45–60 s each.  
Output each clip on its own line in the format `start-end: description or spoken text`.  
Do NOT output JSON or any extra formatting—just plain lines like:  
275.0-325.0: “When you pitch, focus on the problem before the solution—here’s why…”"""
    ),
}

# ─── Helper: chunk the transcript to avoid token limits ─────────────────────────
def chunks(lines, max_chars=12000):
    chunk, count = [], 0
    for line in lines:
        count += len(line)
        chunk.append(line)
        if count > max_chars:
            yield chunk
            chunk, count = [], 0
    if chunk:
        yield chunk


def main():
    if not UPLOADS_DIR.exists():
        print(f"❌ Uploads directory not found: {UPLOADS_DIR}", file=sys.stderr)
        sys.exit(1)

    # Iterate categories
    for category_dir in UPLOADS_DIR.iterdir():
        if not category_dir.is_dir():
            continue
        instr = PROMPT_INSTRUCTIONS.get(category_dir.name)
        if not instr:
            continue

        # Process each transcript JSON file
        for json_file in sorted(category_dir.glob('*.json')):
            # load segments
            data = json.loads(json_file.read_text(encoding='utf-8'))
            if not data:
                continue

            # build lines: "start-end: text"
            lines = [f"{seg['start']}-{seg['end']}: {seg['text']}" for seg in data]
            summary_lines = []
            header = instr + "\n\nTimestamped transcript:\n"

            # Send in manageable chunks
            for chunk in chunks(lines):
                payload = header + "\n".join(chunk)
                print(f"🤖 Sending {len(chunk)} lines to GPT for '{json_file.name}'...")
                resp = client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": payload}]
                )
                content = resp.choices[0].message.content.strip().splitlines()
                summary_lines.extend(content)

            # Dedupe & sort by start time
            seen, unique = set(), []
            def parse_start(line):
                try:
                    return float(line.split(':',1)[0].split('-',1)[0])
                except:
                    return 0.0

            for line in summary_lines:
                if line and line not in seen:
                    seen.add(line)
                    unique.append(line)
            unique.sort(key=parse_start)

            # Save results
            out_file = json_file.with_suffix('.summary.txt')
            out_file.write_text("\n".join(unique), encoding='utf-8')
            print(f"💾 Saved condensed summary to {out_file}")

if __name__ == '__main__':
    main()
