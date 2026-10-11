"""
video/timeline.py - single source of scene timing for the recorder (record_app.py) and the assembler (assemble.py).

Scene clock: t = 0 at the first video frame. Narration starts at LEAD[scene]. GAPS insert silence into the narration
just before a word, so a live-API action (network latency varies) has landed on screen before the voice describes it.
"""

import json
from pathlib import Path

AUDIO = Path(__file__).resolve().parent / "audio"
SCENES = [1, 2, 3, 4, 5, 6]
LEAD = {1: 0.3, 2: 0.5, 3: 0.3, 4: 0.3, 5: 0.3, 6: 0.3}
TAIL = {1: 0.8, 2: 1.0, 3: 1.0, 4: 1.5, 5: 0.8, 6: 6.5}   # 6: end card with the live URL
# (word it precedes, only words starting at/after this narration time, seconds of silence)
GAPS = {1: [("This", 28.0, 1.5)],                          # hold the 9,314 card before the wordmark
        4: [("and", 20.0, 2.0), ("But", 22.0, 2.0)]}


def words(scene):
    """Spoken words with start/end (s, relative to the scene's audio clip); pause tokens dropped, '--' -> '—'."""
    out = []
    for w in json.loads((AUDIO / f"scene{scene}.json").read_text())["words"]:
        if w["text"] == ".":
            continue
        out.append({**w, "text": "—" if w["text"] == "--" else w["text"]})
    return out


def audio_duration(scene):
    return json.loads((AUDIO / "manifest.json").read_text())["scenes"][str(scene)]["duration_s"]


def gaps(scene):
    """[(audio_time_where_silence_is_inserted, seconds)] resolved against the word timings."""
    out = []
    for token, not_before, secs in GAPS.get(scene, []):
        w = next(w for w in words(scene) if w["start"] >= not_before and w["text"].lower().startswith(token.lower()))
        out.append((w["start"] - 0.05, secs))
    return out


def shift(scene, t_audio):
    """Audio-clip time -> narration time after inserted gaps."""
    return t_audio + sum(s for at, s in gaps(scene) if t_audio >= at)


def cue(scene, token, nth=1):
    """Scene-clock time (incl. LEAD and gaps) of the nth spoken word starting with `token`."""
    hits = [w["start"] for w in words(scene) if w["text"].lower().startswith(token.lower())]
    if len(hits) < nth:
        raise KeyError(f"scene {scene}: no word {token!r} #{nth}")
    return LEAD[scene] + shift(scene, hits[nth - 1])


def duration(scene):
    return LEAD[scene] + audio_duration(scene) + sum(s for _, s in gaps(scene)) + TAIL[scene]


if __name__ == "__main__":
    total = 0.0
    for s in SCENES:
        total += duration(s)
        print(f"scene {s}: {duration(s):6.2f} s  gaps {gaps(s)}")
    print(f"total {total:.2f} s ({int(total // 60)}:{total % 60:04.1f})")
