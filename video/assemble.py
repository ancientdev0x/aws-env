"""
video/assemble.py - final cut: 6 scene clips + narration (with timeline gaps) + SFX + music bed + burned captions.

Inputs: video/build/scene{1,5,6}_html.mp4 (render_html.py), scene{2,3,4}_app.mp4 + scene{N}_events.json (record_app.py),
        video/audio/scene<N>.mp3 + word timings (scripts/video_tts.py), timing from timeline.py.
Output: video/out/baadhdrishti_demo.mp4 (1920x1080, 30 fps, H.264 + AAC), video/build/captions.ass, mix.wav

Audio is built in NumPy so the mix is deterministic: clicks/typing come from the recorder's event log, the music bed
is a soft synthesized pad ducked under the voice, and the result is loudness-normalised to -16 LUFS by ffmpeg.
"""

import json
import subprocess
import wave
from pathlib import Path

import numpy as np

from timeline import LEAD, SCENES, duration, gaps, shift, words

ROOT = Path(__file__).resolve().parent.parent
BUILD, OUT, AUDIO = ROOT / "video" / "build", ROOT / "video" / "out", ROOT / "video" / "audio"
SR = 48000
CLIP = {1: "scene1_html.mp4", 2: "scene2_app.mp4", 3: "scene3_app.mp4", 4: "scene4_app.mp4", 5: "scene5_html.mp4", 6: "scene6_html.mp4"}
NO_FADE_BETWEEN = {(3, 4)}          # scene 3 -> 4 is one continuous app session
CHAPTER_WHOOSH = [2, 5]             # a single whoosh where the film changes chapter
rng = np.random.default_rng(7)


def decode(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "s16le", "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0


def scene_starts():
    t, out = 0.0, {}
    for s in SCENES:
        out[s] = t
        t += duration(s)
    return out, t


def narration(starts, total):
    buf = np.zeros(int(total * SR) + SR, np.float32)
    for s in SCENES:
        a = decode(AUDIO / f"scene{s}.mp3")
        cuts = [0.0] + [g for g, _ in gaps(s)] + [len(a) / SR]
        pad = [0.0] + [sec for _, sec in gaps(s)]
        pos = starts[s] + LEAD[s]
        for i in range(len(cuts) - 1):
            pos += pad[i]
            seg = a[int(cuts[i] * SR):int(cuts[i + 1] * SR)]
            j = int(pos * SR)
            buf[j:j + len(seg)] += seg
            pos += len(seg) / SR
    return buf / max(1e-6, np.abs(buf).max()) * 0.9


def click():
    n = int(0.012 * SR); t = np.arange(n) / SR
    noise = np.diff(rng.standard_normal(n + 1)).astype(np.float32) * np.exp(-t / 0.0022)
    ping = np.sin(2 * np.pi * 2600 * t) * np.exp(-t / 0.004)
    return (0.22 * noise / np.abs(noise).max() + 0.08 * ping).astype(np.float32)


def key():
    n = int(0.006 * SR); t = np.arange(n) / SR
    k = np.diff(rng.standard_normal(n + 1)).astype(np.float32) * np.exp(-t / 0.0012)
    return (0.07 * k / np.abs(k).max()).astype(np.float32)


def whoosh():
    n = int(0.7 * SR); t = np.arange(n) / SR
    noise = rng.standard_normal(n).astype(np.float32)
    out, y = np.zeros(n, np.float32), 0.0
    for i in range(n):                                   # one-pole low-pass sweeping up then down
        a = 0.02 + 0.25 * np.sin(np.pi * i / n) ** 2
        y += a * (noise[i] - y); out[i] = y
    return (0.12 * out / np.abs(out).max() * np.sin(np.pi * t / t[-1]) ** 1.5).astype(np.float32)


def place(buf, sig, t):
    j = int(t * SR)
    if 0 <= j < len(buf):
        m = min(len(sig), len(buf) - j)
        buf[j:j + m] += sig[:m]


def sfx(starts, total):
    buf = np.zeros(int(total * SR) + SR, np.float32)
    for s in (2, 3, 4):
        ev = json.loads((BUILD / f"scene{s}_events.json").read_text())
        for e in ev:
            if e["kind"] == "click":
                place(buf, click(), starts[s] + e["t"])
        for a, b in zip([e["t"] for e in ev if e["kind"] == "type_start"], [e["t"] for e in ev if e["kind"] == "type_end"]):
            t = a
            while t < b:
                place(buf, key(), starts[s] + t); t += 0.045 + 0.04 * rng.random()
    # scene 1: question typing + "Run triage" click, same cue maths as scenes.html
    w1 = {w["text"].lower(): LEAD[1] + shift(1, w["start"]) for w in reversed(words(1))}
    q0, q1 = w1["which"], w1["first?"] + 0.3
    t = q0
    while t < q1:
        place(buf, key(), starts[1] + t); t += 0.055 + 0.05 * rng.random()
    place(buf, click(), starts[1] + q1 + 0.35)
    for s in CHAPTER_WHOOSH:
        place(buf, whoosh(), starts[s] - 0.35)
    return buf


def moving_avg(x, k):
    c = np.cumsum(np.concatenate([[0.0], x]))
    m = (c[k:] - c[:-k]) / k
    return np.concatenate([np.full(k // 2, m[0]), m, np.full(len(x) - len(m) - k // 2, m[-1])])


def music(total, voice):
    n = int(total * SR) + SR; t = np.arange(n) / SR
    notes = [110.0, 164.81, 220.0, 246.94, 261.63]       # A minor add9, very low and slow
    pad = sum((0.6 + 0.4 * np.sin(2 * np.pi * (0.05 + 0.017 * i) * t + i)) * np.sin(2 * np.pi * f * (1 + 0.0015 * i) * t)
              for i, f in enumerate(notes)).astype(np.float32)
    pad = np.convolve(pad, np.ones(64) / 64, mode="same")      # soften
    pad = pad / np.abs(pad).max()
    env = moving_avg(np.abs(voice), int(0.25 * SR))
    duck = 1.0 - 0.55 * np.clip(env / (env.max() * 0.25 + 1e-6), 0, 1)
    fade = np.clip(t / 2.0, 0, 1) * np.clip((total - t) / 3.0, 0, 1)
    return (0.045 * pad * duck * fade).astype(np.float32)


def write_wav(path, x):
    x = np.clip(x, -1, 1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


def ass_time(t):
    h, rem = divmod(max(t, 0), 3600); m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def captions(starts):
    cues = []
    for s in SCENES:
        ws = [{"text": w["text"], "start": starts[s] + LEAD[s] + shift(s, w["start"]),
               "end": starts[s] + LEAD[s] + shift(s, w["end"])} for w in words(s)]
        cur = []
        for i, w in enumerate(ws):
            cur.append(w)
            text = " ".join(x["text"] for x in cur)
            nxt = ws[i + 1] if i + 1 < len(ws) else None
            pause = nxt is None or nxt["start"] - w["end"] > 0.3
            if pause or w["text"][-1] in ".?!;:" or len(text) > 44 or (nxt and len(text) + len(nxt["text"]) > 52):
                cues.append([cur[0]["start"], w["end"] + 0.25, text]); cur = []
    for a, b in zip(cues, cues[1:]):
        a[1] = min(a[1], b[0] - 0.04)
    head = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Noto Sans,46,&H00F2F2F2,&H00F2F2F2,&H8C000000,&H00000000,0,0,0,0,100,100,0,0,3,12,0,2,80,80,44,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [f"Dialogue: 0,{ass_time(a)},{ass_time(b)},Cap,,0,0,0,,{t}" for a, b, t in cues]
    (BUILD / "captions.ass").write_text(head + "\n".join(lines) + "\n")
    return len(cues)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    starts, total = scene_starts()
    voice = narration(starts, total)
    mix = voice + sfx(starts, total) + music(total, voice)
    write_wav(BUILD / "mix.wav", mix[: int(total * SR)])
    n_caps = captions(starts)

    inputs, chains = [], []
    for k, s in enumerate(SCENES):
        d = duration(s)
        inputs += ["-i", str(BUILD / CLIP[s])]
        fi = 0.0 if (SCENES[k - 1], s) in NO_FADE_BETWEEN or k == 0 else 0.2
        fo = 0.0 if k + 1 < len(SCENES) and (s, SCENES[k + 1]) in NO_FADE_BETWEEN else 0.2
        if k == 0: fi = 0.5
        if k == len(SCENES) - 1: fo = 0.8
        f = f"[{k}:v]trim=0:{d:.3f},setpts=PTS-STARTPTS,fps=30,scale=1920:1080,setsar=1,tpad=stop_mode=clone:stop_duration=1,trim=0:{d:.3f}"
        if fi: f += f",fade=t=in:st=0:d={fi}"
        if fo: f += f",fade=t=out:st={d - fo:.3f}:d={fo}"
        chains.append(f + f"[v{k}]")
    graph = ";".join(chains) + ";" + "".join(f"[v{k}]" for k in range(len(SCENES))) + \
        f"concat=n={len(SCENES)}:v=1:a=0[cat];[cat]subtitles={BUILD / 'captions.ass'}[vout];" \
        f"[{len(SCENES)}:a]loudnorm=I=-16:TP=-1.5:LRA=11[aout]"
    out = OUT / "baadhdrishti_demo.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-i", str(BUILD / "mix.wav"), "-filter_complex", graph,
                    "-map", "[vout]", "-map", "[aout]", "-c:v", "libx264", "-preset", "slow", "-crf", "18",
                    "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                    "-movflags", "+faststart", "-t", f"{total:.3f}", str(out)], check=True)
    print(f"{out}  {total:.2f} s  captions {n_caps}  scenes {[round(duration(s), 2) for s in SCENES]}")


if __name__ == "__main__":
    main()
