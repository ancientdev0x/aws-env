"""
video/record_app.py - screen-record the LIVE BaadhDrishti app for scenes 2-4, synced to the narration timings.

Every action (slider, toggles, clicks, dialogs) runs against the deployed site and API; numbers on screen are
whatever the live API returns. A visible cursor + click ripple is injected because headless Chrome draws none.
Frames come from the Chrome DevTools screencast (JPEG q90, 1920x1080) and are re-timed to constant 30 fps.

Usage (from aws-env/):  uv run --with playwright python video/record_app.py [--scenes 2 3 4]
Output: video/build/scene<N>_app.mp4 (silent), video/build/scene<N>_events.json (click/type times, seconds)
Resets officer state (DynamoDB) before and after recording via scripts/reset_demo_state.sh (profile baadh).
"""

import argparse
import base64
import json
import subprocess
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

from timeline import cue, duration

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "video" / "build"
URL = "http://baadhdrishti-frontendbucket-e1tfhveh47sy.s3-website.ap-south-1.amazonaws.com/"
API = "https://f3m0jdk4wi.execute-api.ap-south-1.amazonaws.com"
W, H, FPS = 1920, 1080, 30          # output frame size
VW, VH, DSF = 1536, 864, 1.25        # CSS viewport x device scale = 1920x1080; UI text 25% larger on video
AOI = [[16.50, 80.50], [16.65, 80.70]]
BRIDGE = [16.62909, 80.61715]      # Vijayawada-Vissannapeta Road bridge (CHECK edge), docs/VIDEO.md
HUB = [16.605902, 80.580402]       # dry staging point that restores Paidurupadu, docs/VIDEO.md

CURSOR_JS = """
(() => {
  if (window.__cur) return;
  const c = document.createElement('div');
  c.innerHTML = '<svg width="30" height="30" viewBox="0 0 30 30"><path d="M5 3 L5 24 L10.5 18.6 L14.2 27 L18 25.3 L14.4 17.2 L22 17.2 Z" fill="#fff" stroke="#111" stroke-width="1.6" stroke-linejoin="round"/></svg>';
  Object.assign(c.style, {position: 'fixed', left: '0', top: '0', zIndex: 2147483647, pointerEvents: 'none',
    filter: 'drop-shadow(0 2px 3px rgba(0,0,0,.55))', willChange: 'transform'});
  let x = 920, y = 520;
  const place = () => { c.style.transform = `translate(${x - 5}px, ${y - 3}px)`; };
  const host = () => document.querySelector('dialog[open]') || document.body;
  const ease = t => (t === 1 ? 1 : 1 - Math.pow(2, -10 * t));   // expo-out, same curve as cubic-bezier(0.22,1,0.36,1) feel
  window.__cur = {
    pos: () => [x, y],
    move(nx, ny, ms) {
      host().appendChild(c);
      return new Promise(res => {
        const sx = x, sy = y, t0 = performance.now();
        const step = now => { const k = Math.min(1, (now - t0) / ms), e = ease(k);
          x = sx + (nx - sx) * e; y = sy + (ny - sy) * e; place(); k < 1 ? requestAnimationFrame(step) : res(); };
        requestAnimationFrame(step);
      });
    },
    ripple() {
      const r = document.createElement('div');
      Object.assign(r.style, {position: 'fixed', left: (x - 20) + 'px', top: (y - 20) + 'px', width: '40px', height: '40px',
        borderRadius: '50%', border: '2px solid rgba(255,255,255,.95)', zIndex: 2147483646, pointerEvents: 'none',
        transition: 'transform .5s cubic-bezier(0.22,1,0.36,1), opacity .5s cubic-bezier(0.22,1,0.36,1)'});
      host().appendChild(r);
      requestAnimationFrame(() => { r.style.transform = 'scale(1.9)'; r.style.opacity = '0'; });
      setTimeout(() => r.remove(), 700);
    },
  };
  place(); document.body.appendChild(c);
})();
"""


class Recorder:
    def __init__(self, page, scene):
        self.page, self.scene, self.frames, self.events = page, scene, [], []
        self.dir = BUILD / f"scene{scene}_frames"
        self.dir.mkdir(parents=True, exist_ok=True)
        for f in self.dir.glob("*.jpg"):
            f.unlink()
        self.cdp = page.context.new_cdp_session(page)
        self.cdp.on("Page.screencastFrame", self._frame)

    def _frame(self, f):
        i = len(self.frames)
        (self.dir / f"{i:05d}.jpg").write_bytes(base64.b64decode(f["data"]))
        self.frames.append(f["metadata"]["timestamp"])
        self.cdp.send("Page.screencastFrameAck", {"sessionId": f["sessionId"]})

    def start(self):
        self.t0 = time.time()
        self.cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 90, "maxWidth": W, "maxHeight": H})
        self.page.evaluate("window.scrollTo(0, 0)")

    def now(self):
        return time.time() - self.t0

    def until(self, t, label):
        """Block until scene-clock time t (s, from timeline.cue), then log the action."""
        while self.now() < t:
            self.page.wait_for_timeout(min(50, max(1, (t - self.now()) * 1000)))
        print(f"  scene {self.scene} {label:<34} planned {t:6.2f}s  actual {self.now():6.2f}s")

    def log(self, kind):
        self.events.append({"t": round(self.now(), 3), "kind": kind})

    def stop(self, total):
        while self.now() < total:
            self.page.wait_for_timeout(50)
        self.cdp.send("Page.stopScreencast")
        self.page.wait_for_timeout(300)
        return self._encode(total)

    def _encode(self, total):
        ts = [t - self.t0 for t in self.frames]
        lines = []
        for i, t in enumerate(ts):
            nxt = ts[i + 1] if i + 1 < len(ts) else total
            lines += [f"file '{self.dir / f'{i:05d}.jpg'}'", f"duration {max(nxt - t, 0.001):.4f}"]
        lines.append(f"file '{self.dir / f'{len(ts) - 1:05d}.jpg'}'")
        # first frame also covers [0, ts0)
        lines = [f"file '{self.dir / '00000.jpg'}'", f"duration {max(ts[0], 0.001):.4f}"] + lines
        concat = BUILD / f"scene{self.scene}_frames.txt"
        concat.write_text("\n".join(lines) + "\n")
        out = BUILD / f"scene{self.scene}_app.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
                        "-vf", f"fps={FPS},scale={W}:{H}:flags=lanczos,format=yuv420p", "-t", f"{total:.3f}",
                        "-c:v", "libx264", "-preset", "slow", "-crf", "16", str(out)], check=True)
        (BUILD / f"scene{self.scene}_events.json").write_text(json.dumps(self.events, indent=1))
        print(f"  -> {out.name}: {len(ts)} frames captured, {total:.2f}s, {len(self.events)} events")
        return out


# ---------- page helpers ----------
def center(page, selector):
    b = page.locator(selector).first.bounding_box()
    return b["x"] + b["width"] / 2, b["y"] + b["height"] / 2


def latlng_xy(page, lat, lon):
    return page.evaluate("([la, lo]) => { const p = map.latLngToContainerPoint([la, lo]); const r = document.getElementById('map').getBoundingClientRect(); return [r.left + p.x, r.top + p.y]; }", [lat, lon])


def move(page, x, y, ms=700):
    page.evaluate("([x, y, ms]) => window.__cur.move(x, y, ms)", [x, y, ms])
    page.mouse.move(x, y)


def click_xy(rec, x, y, ms=700):
    move(rec.page, x, y, ms)
    rec.page.evaluate("window.__cur.ripple()")
    rec.log("click")
    rec.page.mouse.click(x, y)


def click(rec, selector, ms=700):
    click_xy(rec, *center(rec.page, selector), ms=ms)


def type_into(rec, selector, text):
    click(rec, selector, ms=450)
    rec.log("type_start")
    rec.page.keyboard.type(text, delay=32)
    rec.log("type_end")


def fly(page, latlng, zoom, secs):
    page.evaluate("([ll, z, s]) => void map.flyTo(ll, z, {duration: s})", [latlng, zoom, secs])


def fly_wait(page, latlng, zoom, secs):
    """flyTo and block until the map has stopped (needed before clicking a map feature)."""
    page.evaluate("([ll, z, s]) => new Promise(r => { map.once('moveend', () => setTimeout(r, 150)); map.flyTo(ll, z, {duration: s}); })",
                  [latlng, zoom, secs])


def fit_aoi(page, secs=None):
    if secs:
        page.evaluate("([b, s]) => void map.flyToBounds(b, {duration: s})", [AOI, secs])
    else:
        page.evaluate("(b) => void map.fitBounds(b)", AOI)


def set_check(page, selector, on):
    if page.is_checked(selector) != on:
        page.click(selector)


def settle(page, ms=2500):
    page.wait_for_timeout(ms)


# ---------- scenes ----------
def scene2(page):
    s = 2
    set_check(page, "#t-sar", True); set_check(page, "#t-mask", False); set_check(page, "#t-roads", False)
    set_check(page, "#t-urban", False); set_check(page, "#t-dest", False); set_check(page, "#f-cut", True)
    page.evaluate("() => { const r = document.getElementById('t-slider'); r.value = 0; r.dispatchEvent(new Event('input')); }")
    fit_aoi(page); settle(page, 3500)
    page.evaluate("window.__cur.move(920, 520, 1)")
    rec = Recorder(page, s); rec.start()
    rec.until(cue(s, "AWS"), "cursor to layer controls")
    move(page, *center(page, "#controls"), 900)
    rec.until(cue(s, "twentieth") - 0.3, "cursor to slider (20 Aug)")
    sx, sy = center(page, "#t-slider"); bw = page.locator("#t-slider").bounding_box()["width"]
    move(page, sx - bw / 2 + 6, sy, 600)
    rec.until(cue(s, "one"), "drag slider to 1 Sep")
    page.evaluate("window.__cur.ripple()"); rec.log("click")
    page.mouse.move(sx - bw / 2 + 6, sy); page.mouse.down()
    for i in range(1, 16):
        x = sx - bw / 2 + 6 + (bw - 12) * i / 15
        page.evaluate("([x, y]) => window.__cur.move(x, y, 30)", [x, sy]); page.mouse.move(x, sy)
    page.mouse.up()
    rec.until(cue(s, "mark"), "water mask on")
    click(rec, "label:has(#t-mask)")
    rec.until(cue(s, "Permanent"), "fly into flood block")
    fly(page, [16.592, 80.588], 13.4, 2.6)
    rec.until(cue(s, "dense"), "urban core on + fly out")
    click(rec, "label:has(#t-urban)")
    fit_aoi(page, 2.0)
    rec.until(cue(s, "bounces"), "hover urban core")
    ux, uy = latlng_xy(page, 16.522, 80.640)
    move(page, ux, uy, 900)
    rec.until(cue(s, "NRSC"), "hover NRSC reference link")
    move(page, *center(page, "footer a"), 1000)
    return rec, duration(s)


def scene3(page):
    s = 3
    # SAR off when zoomed in: 20 m radar pixels hide the roads; OSM basemap + water mask read better
    set_check(page, "#t-sar", False); set_check(page, "#t-mask", True); set_check(page, "#t-urban", True); set_check(page, "#t-roads", False)
    page.mouse.move(920, 520); page.evaluate("window.__cur.move(920, 520, 1)")
    fit_aoi(page); settle(page, 3000)
    rec = Recorder(page, s); rec.start()
    rec.until(cue(s, "We"), "roads layer on")
    click(rec, "label:has(#t-roads)")
    rec.until(cue(s, "Any"), "fly into flood block")
    fly(page, [16.598, 80.602], 14, 2.4)
    rec.until(cue(s, "except"), "fly to CHECK bridge")
    fly(page, BRIDGE, 16, 1.6)
    rec.until(cue(s, "never"), "hover bridge")
    page.wait_for_timeout(300)
    move(page, *latlng_xy(page, *BRIDGE), 900)
    rec.until(cue(s, "Then"), "back to overview")
    fit_aoi(page, 2.2)
    rec.until(cue(s, "Seven"), "point at cut-off count")
    move(page, *center(page, "#s-cut"), 900)
    rec.until(cue(s, "peri-urban"), "point at queue")
    move(page, *center(page, "#queue .row[data-id] .nm"), 900)
    rec.until(cue(s, "Tadepalle"), "zoom to Tadepalle")
    click(rec, "#queue .row[data-id] button[data-act=zoom]")
    rec.until(cue(s, "cut", 1), "point at blocking road")
    move(page, *center(page, "#queue .row[data-id] .meta"), 900)
    return rec, duration(s)


def scene4(page):
    s = 4
    set_check(page, "#t-sar", False); set_check(page, "#t-mask", True); set_check(page, "#t-urban", True); set_check(page, "#t-roads", True)
    warm(page)
    rec = Recorder(page, s); rec.start()
    rec.until(0.2, "cursor to Clear blocking roads")
    move(page, *center(page, "#queue .row[data-id] button[data-act=clear]"), 1000)
    rec.until(cue(s, "field"), "open officer dialog")
    click(rec, "#queue .row[data-id] button[data-act=clear]", ms=300)
    page.wait_for_selector("#dlg[open]")
    type_into(rec, "#dlg input[name=officer_name]", "District control room")
    rec.page.keyboard.press("Tab"); rec.log("type_start")
    rec.page.keyboard.type("Police outpost: tractor passable", delay=22); rec.log("type_end")
    rec.until(cue(s, "cleared") - 0.4, "confirm clear")
    click(rec, "#dlg button[value=ok]", ms=400)
    page.wait_for_function("document.getElementById('toast').textContent.includes('Restored')", timeout=20000)
    print(f"    toast @ {rec.now():.2f}s: {page.inner_text('#toast')}")
    rec.until(cue(s, "For"), "add-hub mode + fly to hub point")
    click(rec, "#b-hub", ms=600)
    fly(page, HUB, 15, 1.5)
    rec.until(cue(s, "staging") - 0.2, "click hub location")
    page.wait_for_timeout(100)
    click_xy(rec, *latlng_xy(page, *HUB), ms=700)
    page.wait_for_selector("#dlg[open]")
    click(rec, "#dlg input[name=name]", ms=350)
    rec.log("type_start"); page.keyboard.type("Paidurupadu dry staging point", delay=18); rec.log("type_end")
    page.select_option("#dlg select[name=hub_kind]", "RELIEF_CAMP")
    click(rec, "#dlg button[value=ok]", ms=400)
    page.wait_for_function("document.getElementById('toast').textContent.includes('Paidurupadu')", timeout=20000)
    print(f"    toast @ {rec.now():.2f}s: {page.inner_text('#toast')}")
    rec.until(cue(s, "too") + 1.0, "fly to bridge (wait until stopped)")  # keep the new hub star on screen ~1.5 s
    fly_wait(page, BRIDGE, 16, 1.0)
    rec.until(cue(s, "bridge"), "click bridge")
    click_xy(rec, *latlng_xy(page, *BRIDGE), ms=600)
    page.wait_for_selector(".leaflet-popup-content button[data-s=FORCE_BLOCKED]")
    click(rec, ".leaflet-popup-content button[data-s=FORCE_BLOCKED]", ms=400)
    page.wait_for_selector("#dlg[open]")
    click(rec, "#dlg button[value=ok]", ms=450)
    page.wait_for_function("document.getElementById('toast').textContent.includes('Newly cut off')", timeout=20000)
    print(f"    toast @ {rec.now():.2f}s: {page.inner_text('#toast')}")
    rec.until(cue(s, "queue"), "point at WhatsApp")
    move(page, *center(page, "#b-wa"), 900)
    rec.until(cue(s, "spreadsheet") - 0.2, "point at CSV")
    move(page, *center(page, "#b-csv"), 600)
    return rec, duration(s)


def warm(page):
    """Keep the Lambda and the browser's TLS connection warm so live API latency stays ~0.7 s during the take.
    AUTO_SUSPECTED on an edge without an override only deletes nothing."""
    page.evaluate("""async (api) => {
        for (let i = 0; i < 3; i++) await fetch(api + '/api/triage');
        await fetch(api + '/api/road-status', {method: 'POST', headers: {'content-type': 'application/json'},
            body: JSON.stringify({edge_id: S.data.disrupted_edges.features[0].properties.edge_id, status: 'AUTO_SUSPECTED'})});
    }""", API)


def reset():
    subprocess.run(["bash", str(ROOT / "scripts" / "reset_demo_state.sh")], check=True,
                   env={**__import__("os").environ, "AWS_PROFILE": "baadh"})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenes", type=int, nargs="+", default=[2, 3, 4])
    a = ap.parse_args()
    BUILD.mkdir(parents=True, exist_ok=True)
    reset()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": VW, "height": VH}, device_scale_factor=DSF)
        page.goto(URL)
        page.wait_for_selector("#queue .row[data-id]", timeout=30000)
        page.evaluate("fetch('%s/api/triage')" % API)  # warm the Lambda
        page.evaluate(CURSOR_JS)
        settle(page, 3000)
        for s in a.scenes:
            print(f"scene {s}")
            if s == 4 and 3 not in a.scenes:      # scene 4 starts where scene 3 ends
                page.click("#queue .row[data-id] button[data-act=zoom]")
                settle(page, 2500)
            rec, total = {2: scene2, 3: scene3, 4: scene4}[s](page)
            rec.stop(total)
        browser.close()
    reset()


if __name__ == "__main__":
    main()
