"""
scripts/video_tts.py - narration audio for the demo video via ElevenLabs (with character timestamps)

Reads the scenes from docs/NARRATION.md, sends each scene to ElevenLabs `/with-timestamps`, and writes
  video/audio/scene<N>.mp3        - one clip per scene
  video/audio/scene<N>.json       - word timings {text, start, end} (seconds, relative to the clip)
  video/audio/manifest.json       - scene list with title, duration_s and file names (drives the video timeline)

The API key is read from $ELEVENLABS_API_KEY or from aws-env/.env (gitignored). It is never printed.

Usage:
  .venv/bin/python scripts/video_tts.py --list-voices            # pick a voice id
  .venv/bin/python scripts/video_tts.py --dry-run                # show parsed scenes, no API call
  .venv/bin/python scripts/video_tts.py --voice <voice_id> [--only 3]
"""

import argparse
import base64
import json
import os
import re
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NARRATION = ROOT / "docs" / "NARRATION.md"
OUT = ROOT / "video" / "audio"
API = "https://api.elevenlabs.io/v1"
MODEL = "eleven_multilingual_v2"
PAUSE = '<break time="0.45s" />'  # stands in for "//" in the script
VOICE_SETTINGS = {"stability": 0.55, "similarity_boost": 0.75, "style": 0.15, "use_speaker_boost": True, "speed": 1.1}


def api_key():
    key = os.environ.get("ELEVENLABS_API_KEY")
    env = ROOT / ".env"
    if not key and env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("ELEVENLABS_API_KEY="):
                key = line.split("=", 1)[1].strip().strip("'\"")
    if not key:
        raise SystemExit("ELEVENLABS_API_KEY not set (env var or aws-env/.env)")
    return key


def call(path, body=None):
    req = urllib.request.Request(API + path, data=json.dumps(body).encode() if body else None,
                                 headers={"xi-api-key": api_key(), "content-type": "application/json"},
                                 method="POST" if body else "GET")
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"ElevenLabs HTTP {e.code}: {e.read()[:300].decode(errors='replace')}")


def scenes():
    """[(n, title, spoken_text)] from '## Scene N — Title (...)' sections of docs/NARRATION.md."""
    out, cur = [], None
    for line in NARRATION.read_text().splitlines():
        m = re.match(r"^## Scene (\d+) — ([^(·]+)", line)
        if m:
            cur = [int(m.group(1)), m.group(2).strip(), []]
            out.append(cur)
        elif line.startswith("## ") or line.startswith("---"):
            cur = None
        elif cur is not None and line.strip():
            cur[2].append(line.strip())
    return [(n, title, " ".join(lines)) for n, title, lines in out]


def to_tts_text(text):
    text = re.sub(r"\s*//\s*$", "", text)
    return re.sub(r"\s*//\s*", f" {PAUSE} ", text)


def words_from_alignment(al):
    """Group character timings into words (break tags are not in the alignment)."""
    words, cur, start, end = [], "", None, None
    for ch, s, e in zip(al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]):
        if ch.isspace():
            if cur:
                words.append({"text": cur, "start": round(start, 3), "end": round(end, 3)})
            cur, start = "", None
            continue
        if start is None:
            start = s
        cur, end = cur + ch, e
    if cur:
        words.append({"text": cur, "start": round(start, 3), "end": round(end, 3)})
    return words


def duration(path):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                                capture_output=True, text=True, check=True).stdout)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list-voices", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--voice")
    ap.add_argument("--only", type=int, help="regenerate one scene number")
    a = ap.parse_args()

    if a.list_voices:
        for v in call("/voices")["voices"]:
            lab = v.get("labels", {})
            print(f"{v['voice_id']}  {v['name']:<22} {lab.get('gender', ''):<7} {lab.get('accent', ''):<14} {lab.get('description', '')} {lab.get('use_case', '')}")
        return

    sc = scenes()
    if a.dry_run:
        for n, title, text in sc:
            print(f"--- scene {n}: {title} ({len(text)} chars)\n{to_tts_text(text)}\n")
        print("total chars:", sum(len(t) for _, _, t in sc))
        return
    if not a.voice:
        raise SystemExit("--voice <voice_id> required (see --list-voices)")

    OUT.mkdir(parents=True, exist_ok=True)
    manifest_path = OUT / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {"scenes": {}}
    manifest.update({"voice_id": a.voice, "model_id": MODEL})
    for n, title, text in sc:
        if a.only and n != a.only:
            continue
        res = call(f"/text-to-speech/{a.voice}/with-timestamps?output_format=mp3_44100_128",
                   {"text": to_tts_text(text), "model_id": MODEL, "voice_settings": VOICE_SETTINGS})
        mp3 = OUT / f"scene{n}.mp3"
        mp3.write_bytes(base64.b64decode(res["audio_base64"]))
        words = words_from_alignment(res.get("normalized_alignment") or res["alignment"])
        (OUT / f"scene{n}.json").write_text(json.dumps({"scene": n, "title": title, "words": words}, indent=1))
        manifest["scenes"][str(n)] = {"title": title, "audio": mp3.name, "timings": f"scene{n}.json",
                                      "duration_s": round(duration(mp3), 3), "chars": len(text)}
        print(f"scene {n}: {manifest['scenes'][str(n)]['duration_s']:.1f} s, {len(words)} words  ({title})")
    manifest_path.write_text(json.dumps(manifest, indent=1))
    total = sum(s["duration_s"] for s in manifest["scenes"].values())
    print(f"total narration {total:.1f} s")


if __name__ == "__main__":
    main()
