"""
video/render_html.py - render the code-drawn scenes (1 hook, 5 architecture, 6 close) frame by frame.

Loads video/scenes/scenes.html, injects T = {scene, words (scene-clock times from timeline.py), data}, then for every
frame calls window.render(t) and screenshots the page (1920x1080 JPEG) into ffmpeg -> video/build/scene<N>_html.mp4.
Numbers shown (cut-off count, population proxy) are read from data/processed/triage_summary.json, never typed in.

Usage (from aws-env/):  uv run --with playwright python video/render_html.py [--scenes 1 5 6] [--preview 3.5 12 ...]
"""

import argparse
import json
import subprocess
from pathlib import Path

from playwright.sync_api import sync_playwright

from record_app import URL
from timeline import LEAD, duration, shift, words

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "video" / "build"
HTML = ROOT / "video" / "scenes" / "scenes.html"
FPS = 30


def payload(scene):
    s = json.loads((ROOT / "data" / "processed" / "triage_summary.json").read_text())
    return {"scene": scene, "dur": duration(scene),
            "words": [{"text": w["text"], "t": round(LEAD[scene] + shift(scene, w["start"]), 3)} for w in words(scene)],
            "data": {"cut_off_count": s["cut_off_count"], "cut_off_population_proxy": s["cut_off_population_proxy"],
                     "frontend_url": URL.rstrip("/")}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenes", type=int, nargs="+", default=[1, 5, 6])
    ap.add_argument("--preview", type=float, nargs="*", help="only write PNG stills at these times")
    a = ap.parse_args()
    BUILD.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
        page.goto(HTML.as_uri())
        # fonts load lazily (scenes start hidden) - force them before the first frame
        page.evaluate("""() => Promise.all(['400 48px Inter', '600 48px Inter', '400 48px "Instrument Serif"',
            'italic 400 48px "Instrument Serif"', '400 20px "JetBrains Mono"'].map(f => document.fonts.load(f))).then(() => 1)""")
        assert page.evaluate("document.fonts.check('48px \"Instrument Serif\"') && document.fonts.check('600 48px Inter')"), "fonts missing"
        for scene in a.scenes:
            page.evaluate("t => { window.T = t; }", payload(scene))
            if a.preview:
                for t in a.preview:
                    page.evaluate("t => window.render(t)", t)
                    page.screenshot(path=str(BUILD / f"preview_s{scene}_{t:05.1f}.png"))
                continue
            total = duration(scene)
            out = BUILD / f"scene{scene}_html.mp4"
            ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "image2pipe", "-framerate", str(FPS), "-i", "-",
                                   "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p", str(out)],
                                  stdin=subprocess.PIPE)
            n = int(round(total * FPS))
            for i in range(n):
                page.evaluate("t => window.render(t)", i / FPS)
                ff.stdin.write(page.screenshot(type="jpeg", quality=92))
            ff.stdin.close(); ff.wait()
            print(f"scene {scene}: {n} frames, {total:.2f} s -> {out.name}")
        browser.close()


if __name__ == "__main__":
    main()
