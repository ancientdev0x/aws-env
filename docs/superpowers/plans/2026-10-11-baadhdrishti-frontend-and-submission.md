# BaadhDrishti Frontend, Share/CSV, Polish & Submission — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the officer-facing web app (map + ranked queue + road/hub edits + WhatsApp/CSV) on S3 + CloudFront against the already-deployed Lambda API, and produce README, architecture diagram, video script, blog draft and submission checklist — all today (Sun Oct 11).

**Architecture:** Offline scripts already produced `data/processed/*` and a deployed SAM stack (`baadhdrishti`, ap-south-1: HTTP API → Lambda (NetworkX engine) ↔ DynamoDB; data bundle in S3). This plan (1) trims the Lambda POST path and adds `destinations` to the response, (2) exports SAR/mask PNG overlays into `frontend/data/`, (3) writes a single-file `frontend/index.html` (vanilla JS + Leaflet 1.9.4 CDN), (4) adds a private S3 bucket + CloudFront (OAC) to the same SAM stack with a deploy script, (5) writes docs.

**Tech Stack:** Python 3.12 (`.venv`, uv), NetworkX 3.7, rasterio/Pillow/matplotlib (offline only), AWS SAM CLI 1.168, AWS CLI v2, Leaflet 1.9.4, Playwright (via `uv run --with playwright`, test-only).

Spec: `docs/superpowers/specs/2026-10-10-baadhdrishti-frontend-and-submission-design.md`. Read `CLAUDE.md` first.

## Global Constraints

- **AWS profile:** every AWS/SAM command runs with `AWS_PROFILE=baadh` (account 872376836713, region `ap-south-1`). The shell default `AWS_PROFILE=medmitra-bedrock` is a different project — never deploy or delete with it. `samconfig.toml` already pins `profile = "baadh"`.
- **No made-up numbers:** the UI shows only API values; docs/video/blog use only script/API output or cited figures. Unverified items stay marked **TO VERIFY**.
- **Stack only:** S3 + CloudFront, single `index.html` + Leaflet, API Gateway + one Lambda, DynamoDB, SAM. Do NOT add Next.js, React, build tools, Cognito, OpenSearch, SQS, SNS, Step Functions, LocalStack, ML models.
- **Wording:** "field-verification triage queue". Never "rescue dispatch", "navigation", "forecast", "official damage assessment".
- **Fixed copy:** disclaimer text exactly `Preliminary screening triage queue based on mapped roads. NOT official rescue orders.`; urban tooltip exactly `Urban core excluded due to radar double-bounce ambiguity (NRSC 6-Sep map also excludes urban areas)`.
- **Status order** INUNDATED > NO_MAPPED_ROAD_PATH > PATH_EXISTS, then population descending (the API already returns this order — do not re-sort by default).
- **Bridges:** CHECK edges are shown orange and described as "not auto-disrupted, verify".
- **Secrets:** never commit `aws.json`, `frontend/config.json` or any key. **Commits:** small, no `Co-Authored-By` / Claude attribution lines. Push to `origin main` after each task.
- **Python:** run project Python as `.venv/bin/python` from the repo root `aws-env/`. The interactive shell is zsh: in loops use `${=VAR}` to word-split.
- **Live API (current):** `https://f3m0jdk4wi.execute-api.ap-south-1.amazonaws.com`. Current computed output: 7 habitations NO_MAPPED_ROAD_PATH (Tadepalle, Paidurupadu, Elaprolu, Vemavaram, Jakkampudi, Kotturu, Shabada), population proxy 9,314.
- **Demo state:** after any test that writes, run `AWS_PROFILE=baadh scripts/reset_demo_state.sh` (must print `0 items` for both tables).

## Prerequisites (check once, 2 minutes)

```bash
cd aws-env
ls data/interim/20240820_vv_db.tif data/interim/20240901_vv_db.tif data/processed/flood_mask_20240901.tif
.venv/bin/python tests/test_reachability_engine.py | tail -1
AWS_PROFILE=baadh aws sts get-caller-identity --query Arn --output text
sam --version
```
Expected: three files listed; `✓ All Reachability Engine assertions passed successfully!`; `arn:aws:iam::872376836713:user/baadh-dev`; `SAM CLI, version 1.168.0` (or newer).
If the `data/interim` files are missing, regenerate them (≈2 min): `.venv/bin/python scripts/fetch_s1_aoi.py && .venv/bin/python scripts/generate_flood_mask.py`.

## File Structure

| File | Status | Responsibility |
|---|---|---|
| `backend/app.py` | modify | drop server-side "before" compute + `diff`; add `destinations` to triage response |
| `tests/test_lambda_local.py` | modify | assert new response shape |
| `template.yaml` | modify | Lambda 1769 MB; FrontendBucket + CloudFront OAC + Distribution + bucket policy; outputs |
| `scripts/export_overlays.py` | create | SAR pre/post + mask PNGs, `overlays.json`, urban core → `frontend/data/` |
| `tests/test_export_overlays.py` | create | checks overlay outputs |
| `frontend/index.html` | create | the whole web app (map, queue, actions, share, CSV) |
| `frontend/data/*` | generated, committed | overlays served next to the page |
| `frontend/config.json` | generated, gitignored | `{"apiUrl": ...}` written by deploy/local step |
| `tests/frontend_smoke.py` | create | Playwright headless check (+ optional write flow) |
| `scripts/deploy_frontend.sh` | create | write config, sync to S3, invalidate CloudFront |
| `scripts/pick_demo_hub.py` | create | data-backed choice of a real school for the "add hub" demo |
| `scripts/draw_architecture.py` | create | `docs/architecture.png` |
| `README.md` → `docs/HACKATHON.md` | move | keep hackathon rules |
| `README.md` | create | project README |
| `docs/VIDEO.md`, `docs/BLOG.md`, `docs/SUBMISSION.md` | create | video script + checklist, blog draft, submission checklist |
| `CLAUDE.md`, `PLAN.md` | modify | status + task ticks |

---

### Task 1: Faster POSTs and `destinations` in the API response

**Files:**
- Modify: `backend/app.py` (functions `compute`, `road_status`, `add_hub`; delete `status_diff`)
- Modify: `template.yaml` (Globals `MemorySize`)
- Test: `tests/test_lambda_local.py`

**Interfaces:**
- Consumes: existing `compute()` in `backend/app.py`; bundle field `b["destinations"]` (list of dicts with `id, name, type, lat, lon, node, snap_distance_m, source`).
- Produces (used by Task 3 frontend): `GET /api/triage`, `POST /api/road-status` (200) and `POST /api/hubs` (201) all return the same body:
  `{event, aoi, total_habitations, in_scope_habitations, cut_off_count, cut_off_population_proxy, compute_ms, habitations[], out_of_scope[], active_staging_hubs[], road_overrides[], disrupted_edges (GeoJSON FeatureCollection; feature.properties = {edge_id, status ∈ AUTO_SUSPECTED|CHECK|FORCE_CLEARED|FORCE_BLOCKED, blocked, highway, name}), destinations[{id,name,type,lat,lon}], caveats[]}`; `/api/hubs` additionally has `hub`. No `diff` key anywhere.
  Habitation record fields: `id, name, place, lat, lon, snap_distance_m, population_proxy, population_source, in_urban_core, uncertainty_flags[], status, nearest_destination ({id,name,type,distance_km} | null), blocking_edges[], blocking_roads[{edge_id, highway, name}], is_inundated, baseline_distance_km`; out-of-scope records also have `excluded_reason`.

- [ ] **Step 1: Write the failing test** — in `tests/test_lambda_local.py`, inside `test_api_lifecycle()`, replace the block

```python
    code, t = call("GET", "/api/triage")
    assert code == 200
    assert t["cut_off_count"] == offline["cut_off_count"], "Lambda must reproduce the offline triage"
```
with
```python
    code, t = call("GET", "/api/triage")
    assert code == 200
    assert t["cut_off_count"] == offline["cut_off_count"], "Lambda must reproduce the offline triage"
    assert t["destinations"] and set(t["destinations"][0]) == {"id", "name", "type", "lat", "lon"}
    assert "diff" not in t
```
and replace
```python
    rec = next(h for h in r["habitations"] if h["id"] == first["id"])
    assert rec["status"] == "PATH_EXISTS" or rec["blocking_edges"] != first["blocking_edges"]
```
with
```python
    assert "diff" not in r, "diff is computed client-side now"
    rec = next(h for h in r["habitations"] if h["id"] == first["id"])
    assert rec["status"] == "PATH_EXISTS" or rec["blocking_edges"] != first["blocking_edges"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python tests/test_lambda_local.py`
Expected: `AssertionError` on the `t["destinations"]` line (KeyError/assert).

- [ ] **Step 3: Implement** — edit `backend/app.py`:

(a) In `compute()`, in the returned dict, add after `"disrupted_edges": ...,`:
```python
        "destinations": [{k: d[k] for k in ("id", "name", "type", "lat", "lon")} for d in b["destinations"]],
```
(b) Delete the whole `def status_diff(before, after): ...` function.
(c) Replace the body of `road_status` after the validation `if` with:
```python
    if st == "AUTO_SUSPECTED":
        _overrides.delete_item(Key={"edge_id": eid})
    else:
        _overrides.put_item(Item={"edge_id": eid, "override_status": st, "notes": str(body.get("notes", ""))[:500],
                                  "officer_id": str(body.get("officer_name", ""))[:100], "updated_at": int(time.time())})
    return respond(200, compute())
```
(d) In `add_hub`, delete the line `before = compute()` and replace the last three lines with:
```python
    _hubs.put_item(Item=hub)
    return respond(201, {**compute(), "hub": hub})
```
(e) Update the module docstring line `POST /api/road-status  -> ...` to end with `then recompute (client computes the diff)`.

In `template.yaml` change under `Globals: Function:` the line `MemorySize: 1024` to `MemorySize: 1769` and add a comment on the same line: `# 1769 MB = one full vCPU`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python tests/test_lambda_local.py && .venv/bin/python tests/test_reachability_engine.py | tail -1`
Expected: five `✓` lines from the Lambda test (GET, road-status, AUTO_SUSPECTED, hubs, validation) and `✓ All Reachability Engine assertions passed successfully!`.

- [ ] **Step 5: Deploy and smoke-test live**

```bash
AWS_PROFILE=baadh sam build && AWS_PROFILE=baadh sam deploy --no-progressbar | tail -3
API=https://f3m0jdk4wi.execute-api.ap-south-1.amazonaws.com
curl -s $API/api/triage | .venv/bin/python -c "import json,sys;t=json.load(sys.stdin);print(t['cut_off_count'],len(t['destinations']),'diff' in t,t['compute_ms'])"
```
Expected: `Successfully created/updated stack - baadhdrishti in ap-south-1`; then `7 301 False <ms>` — note the `compute_ms` value (expected lower than the previous ≈940 ms; record the actual number in CLAUDE.md, do not guess).

- [ ] **Step 6: Update CLAUDE.md and commit**

In `CLAUDE.md` Status, in the Task 2.5/2.6 bullet, replace `Lambda `compute_ms` ≈ 940–960` … `(GET ≈ 1.6 s warm, POST ≈ 2.4 s since it computes before+after)` with `Lambda 1769 MB, compute_ms ≈ <value from Step 5>; POST computes once (client diffs)`.
```bash
git add backend/app.py template.yaml tests/test_lambda_local.py CLAUDE.md
git commit -m "perf(api): single recompute per POST, add destinations to triage response"
git push origin main
```

### Task 2: Export SAR and flood-mask overlays for the web map

**Files:**
- Create: `scripts/export_overlays.py`
- Create: `tests/test_export_overlays.py`
- Generated (commit): `frontend/data/pre_vv.png`, `frontend/data/post_vv.png`, `frontend/data/flood_mask.png`, `frontend/data/overlays.json`, `frontend/data/urban_core.geojson`

**Interfaces:**
- Consumes: `data/interim/20240820_vv_db.tif`, `data/interim/20240901_vv_db.tif` (float32 dB, EPSG:32644, 20 m), `data/processed/flood_mask_20240901.tif` (uint8, 1 = flood, nodata 0), `data/processed/urban_core.geojson`.
- Produces (used by Task 3): `frontend/data/overlays.json` =
  `{"bounds": [[16.5, 80.5], [16.65, 80.7]], "pre": "pre_vv.png", "post": "post_vv.png", "mask": "flood_mask.png", "pre_date": "2024-08-20", "post_date": "2024-09-01"}`;
  PNGs are RGBA 1600×1200 in EPSG:4326 over the AOI (row 0 = north); `frontend/data/urban_core.geojson` (FeatureCollection, WGS84).

- [ ] **Step 1: Write the failing test** — create `tests/test_export_overlays.py`:

```python
"""
tests/test_export_overlays.py - checks the web overlays written by scripts/export_overlays.py.
Run: .venv/bin/python tests/test_export_overlays.py
"""
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "frontend" / "data"


def test_overlays():
    subprocess.run([sys.executable, str(ROOT / "scripts" / "export_overlays.py")], check=True)
    meta = json.loads((WEB / "overlays.json").read_text())
    assert meta["bounds"] == [[16.5, 80.5], [16.65, 80.7]]
    assert (meta["pre_date"], meta["post_date"]) == ("2024-08-20", "2024-09-01")
    for key in ("pre", "post", "mask"):
        img = Image.open(WEB / meta[key])
        assert img.mode == "RGBA" and img.size == (1600, 1200), (key, img.mode, img.size)
    mask_alpha = Image.open(WEB / meta["mask"]).getchannel("A")
    opaque = sum(1 for a in mask_alpha.getdata() if a > 0) / (1600 * 1200)
    # flood_mask_20240901.geojson metadata reports frac_candidate_final 0.126 of the UTM grid
    assert 0.05 < opaque < 0.25, f"mask opaque fraction {opaque:.3f}"
    urban = json.loads((WEB / "urban_core.geojson").read_text())
    assert urban["type"] == "FeatureCollection" and urban["features"]
    print(f"✓ overlays ok (mask opaque fraction {opaque:.3f})")


if __name__ == "__main__":
    test_overlays()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python tests/test_export_overlays.py`
Expected: FAIL — `python: can't open file '.../scripts/export_overlays.py'` (CalledProcessError).

- [ ] **Step 3: Implement** — create `scripts/export_overlays.py`:

```python
"""
scripts/export_overlays.py - web overlays for the Leaflet map (offline)

Reprojects the pre/post VV dB rasters and the candidate flood mask to an EPSG:4326 grid over the AOI and writes
RGBA PNGs plus overlays.json for L.imageOverlay. Also copies the urban-core polygon next to them.

Inputs: data/interim/{20240820,20240901}_vv_db.tif, data/processed/flood_mask_20240901.tif, urban_core.geojson
Output: frontend/data/{pre_vv,post_vv,flood_mask}.png, overlays.json, urban_core.geojson
"""

import json
import shutil
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image
from rasterio.transform import from_bounds
from rasterio.warp import Resampling, reproject

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "frontend" / "data"
AOI = [80.50, 16.50, 80.70, 16.65]  # lon_min, lat_min, lon_max, lat_max
W, H = 1600, 1200
DB_MIN, DB_MAX = -22.0, 0.0  # same stretch as scripts/quicklook_flood.py
MASK_RGBA = (30, 110, 255, 170)


def to_ll(path, resampling):
    dst = np.full((H, W), np.nan, np.float32)
    with rasterio.open(path) as src:
        reproject(rasterio.band(src, 1), dst, dst_transform=from_bounds(*AOI, W, H), dst_crs="EPSG:4326",
                  dst_nodata=np.nan, resampling=resampling)
    return dst


def gray_png(db, path):
    v = (np.clip((db - DB_MIN) / (DB_MAX - DB_MIN), 0, 1) * 255).astype(np.uint8)
    alpha = np.where(np.isnan(db), 0, 255).astype(np.uint8)
    Image.fromarray(np.dstack([v, v, v, alpha]), "RGBA").save(path, optimize=True)


def mask_png(mask, path):
    rgba = np.zeros((H, W, 4), np.uint8)
    rgba[mask] = MASK_RGBA
    Image.fromarray(rgba, "RGBA").save(path, optimize=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    gray_png(to_ll(ROOT / "data/interim/20240820_vv_db.tif", Resampling.bilinear), OUT / "pre_vv.png")
    gray_png(to_ll(ROOT / "data/interim/20240901_vv_db.tif", Resampling.bilinear), OUT / "post_vv.png")
    mask_png(to_ll(ROOT / "data/processed/flood_mask_20240901.tif", Resampling.nearest) == 1, OUT / "flood_mask.png")
    shutil.copy(ROOT / "data/processed/urban_core.geojson", OUT / "urban_core.geojson")
    meta = {"bounds": [[AOI[1], AOI[0]], [AOI[3], AOI[2]]], "pre": "pre_vv.png", "post": "post_vv.png",
            "mask": "flood_mask.png", "pre_date": "2024-08-20", "post_date": "2024-09-01"}
    (OUT / "overlays.json").write_text(json.dumps(meta, indent=1))
    for f in sorted(OUT.iterdir()):
        print(f"{f.relative_to(ROOT)}  {f.stat().st_size / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python tests/test_export_overlays.py`
Expected: five file lines (`frontend/data/...  X.XX MB`) then `✓ overlays ok (mask opaque fraction 0.1xx)`.
If the fraction is outside 0.05–0.25, do NOT widen the bounds — inspect `frontend/data/flood_mask.png` (open it with the Read tool) and compare with `docs/gonogo_flood_mask_quicklook.png`; they must show the same red/blue pattern.

- [ ] **Step 5: Visual check** — open `frontend/data/post_vv.png` and `frontend/data/flood_mask.png` with the Read tool. The Krishna river must be dark, running from the left edge down to the bottom-centre; the mask must show the large block north-west of centre (Elaprolu–Rayanapadu–Jakkampudi). If the image looks upside-down, the transform is wrong — stop and fix before continuing.

- [ ] **Step 6: Commit**

```bash
git add scripts/export_overlays.py tests/test_export_overlays.py frontend/data/
git commit -m "feat(web): export SAR pre/post and flood-mask overlays for Leaflet"
git push origin main
```

### Task 3: Frontend web app (`frontend/index.html`) — map, queue, officer actions, WhatsApp, CSV

**Files:**
- Create: `tests/frontend_smoke.py`
- Create: `frontend/index.html`
- Modify: `.gitignore` (add `frontend/config.json`)
- Generated, not committed: `frontend/config.json`, `docs/screenshot.png` (commit the screenshot in Task 4)

**Interfaces:**
- Consumes: API body from Task 1 (exact field names listed there); `frontend/data/overlays.json` + PNGs + `urban_core.geojson` from Task 2; `frontend/config.json` = `{"apiUrl": "https://...amazonaws.com"}` (no trailing slash needed).
- Produces (used by Task 4 smoke test and the video): DOM ids `#s-scope #s-cut #s-pop #s-ms` (stats), `#queue .row[data-id]` (queue rows, `data-id` = habitation id), row buttons `button[data-act=zoom|clear|verify]`, `#dlg` (`<dialog>`, inputs by `name`, confirm button `button[value=ok]`), `#toast`, `#banner`, `#caveats li`, `#b-hub #b-wa #b-csv`, map overlays rendered as `.leaflet-image-layer` (3 of them).

- [ ] **Step 1: Write the failing smoke test** — create `tests/frontend_smoke.py`:

```python
"""
tests/frontend_smoke.py - headless-browser check of the frontend (local or CloudFront).

Usage (from aws-env/):
  uv run --with playwright python -m playwright install chromium     # once
  uv run --with playwright python tests/frontend_smoke.py <url>          # read-only + docs/screenshot.png
  uv run --with playwright python tests/frontend_smoke.py <url> --write  # also clears the top row's blocking roads
After --write run: AWS_PROFILE=baadh scripts/reset_demo_state.sh
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent


def main(url, write):
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.on("console", lambda m: m.type == "error" and "tile.openstreetmap.org" not in m.text and errors.append(m.text))
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(url)
        page.wait_for_selector("#queue .row[data-id]", timeout=30000)

        cut = page.inner_text("#s-cut").strip()
        assert cut.isdigit() and int(cut) > 0, f"stats not loaded: {cut!r}"
        rows = page.locator("#queue .row[data-id]").count()
        assert rows == int(cut), f"'Only cut-off' filter should list {cut} rows, got {rows}"
        assert page.locator("#caveats li").count() >= 3, "caveats from API missing"
        assert page.locator(".leaflet-image-layer").count() == 3, "pre/post/mask overlays missing"
        assert "NOT official rescue orders" in page.inner_text("footer")

        page.uncheck("#f-cut")
        assert page.locator("#queue .row[data-id]").count() > rows, "unchecking filter should show PATH_EXISTS rows"
        page.check("#f-cut")

        with page.expect_download() as dl:
            page.click("#b-csv")
        csv_text = Path(dl.value.path()).read_text()
        assert csv_text.splitlines()[0].startswith("rank,id,name,status"), csv_text[:80]

        page.wait_for_timeout(2500)  # let basemap tiles draw
        page.screenshot(path=str(ROOT / "docs" / "screenshot.png"))

        if write:
            first = page.locator("#queue .row[data-id]").first
            name = first.locator(".nm").inner_text()
            first.locator("button[data-act=clear]").click()
            page.fill("#dlg input[name=officer_name]", "smoke-test")
            page.click("#dlg button[value=ok]")
            page.wait_for_function("document.getElementById('toast').textContent.includes('Restored')", timeout=90000)
            print(f"cleared {name}: {page.inner_text('#toast')}")
        browser.close()

    assert not errors, f"console errors: {errors}"
    print("✓ frontend smoke passed" + (" (write flow)" if write else ""))


if __name__ == "__main__":
    main(sys.argv[1], "--write" in sys.argv)
```

- [ ] **Step 2: Prepare local serving and run the test to verify it fails**

```bash
echo 'frontend/config.json' >> .gitignore
API=$(AWS_PROFILE=baadh aws cloudformation describe-stacks --region ap-south-1 --stack-name baadhdrishti \
      --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" --output text)
printf '{"apiUrl": "%s"}\n' "$API" > frontend/config.json
cat frontend/config.json
.venv/bin/python -m http.server 8080 -d frontend >/tmp/bd_http.log 2>&1 &
uv run --with playwright python -m playwright install chromium
uv run --with playwright python tests/frontend_smoke.py http://localhost:8080/
```
Expected: config shows the `https://f3m0jdk4wi...` URL; the smoke test FAILS with a timeout waiting for `#queue .row[data-id]` (no `index.html` yet → 404 directory listing).

- [ ] **Step 3: Implement** — create `frontend/index.html` with exactly the content in the next section ("index.html — full file").

- [ ] **Step 4: Run the smoke test (read-only) and look at the screenshot**

Run: `uv run --with playwright python tests/frontend_smoke.py http://localhost:8080/`
Expected: `✓ frontend smoke passed`. Then open `docs/screenshot.png` with the Read tool and check: stats bar shows 4 numbers; map shows grey SAR image, blue water mask, red/orange road segments, amber dashed urban core, coloured habitation dots; right panel lists the cut-off habitations with "Blocking: …" lines; footer shows the disclaimer and three caveats.

- [ ] **Step 5: Run the write flow, then reset**

```bash
uv run --with playwright python tests/frontend_smoke.py http://localhost:8080/ --write
AWS_PROFILE=baadh scripts/reset_demo_state.sh
```
Expected: `cleared Tadepalle: Restored (5): Tadepalle, Vemavaram, Jakkampudi, Kotturu, Shabada — recomputed in <n> ms` (names/count come from the live API — if they differ, report the actual output; do not edit the test to match a guess), `✓ frontend smoke passed (write flow)`, then both tables `0 items`.

- [ ] **Step 6: Manual checks in a real browser (5 minutes)** — open `http://localhost:8080/`:
  1. Drag the 20 Aug ↔ 1 Sep slider: the grey image fades between the two dates.
  2. Click a red road: popup shows name, status and *Mark cleared / Mark blocked*; *Mark blocked* on an orange (CHECK) bridge → it turns purple, queue/stats update, toast lists changes.
  3. *+ Add staging hub* → click the map → dialog → confirm: a ★ appears and the toast lists restored habitations. Clicking outside the AOI shows a red banner with the API error.
  4. *Share on WhatsApp* opens `wa.me` with the queue text. *Download CSV* saves a file.
  Then run `AWS_PROFILE=baadh scripts/reset_demo_state.sh` and stop the server: `kill %1` (or `pkill -f "http.server 8080"`).

- [ ] **Step 7: Commit**

```bash
git add .gitignore frontend/index.html tests/frontend_smoke.py
git commit -m "feat(web): single-file Leaflet frontend with triage queue, officer edits, WhatsApp and CSV"
git push origin main
```

#### index.html — full file

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>BaadhDrishti — post-flood road-access triage</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
      integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin="">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
        integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>
<style>
  :root { --bg:#0f172a; --panel:#111827; --line:#1f2937; --text:#e5e7eb; --muted:#9ca3af; }
  * { box-sizing: border-box; }
  html, body { margin: 0; height: 100%; background: var(--bg); color: var(--text);
               font: 14px/1.4 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
  body { display: grid; grid-template-rows: auto auto 1fr auto; height: 100vh; }
  header { display: flex; align-items: center; gap: 12px; padding: 10px 16px; border-bottom: 1px solid var(--line); }
  header h1 { font-size: 18px; margin: 0; }
  .sub { color: var(--muted); }
  .badge { margin-left: auto; border: 1px solid var(--line); border-radius: 999px; padding: 2px 10px; color: var(--muted); font-size: 12px; }
  #stats { display: flex; gap: 28px; padding: 8px 16px; border-bottom: 1px solid var(--line); font-variant-numeric: tabular-nums; }
  #stats b { font-size: 18px; display: block; }
  #stats span { color: var(--muted); font-size: 12px; }
  main { display: grid; grid-template-columns: 1fr 430px; min-height: 0; }
  #mapwrap { position: relative; min-height: 0; }
  #map { position: absolute; inset: 0; background: #0b1220; }
  #map.adding { cursor: crosshair; }
  .panel { position: absolute; z-index: 1000; background: rgba(17, 24, 39, .92); border: 1px solid var(--line);
           border-radius: 8px; padding: 8px 10px; font-size: 12px; display: grid; gap: 4px; }
  #controls { left: 56px; top: 10px; }
  #controls label { display: flex; gap: 6px; align-items: center; }
  #legend { left: 10px; bottom: 24px; }
  .sw { display: inline-block; width: 16px; height: 4px; margin-right: 6px; vertical-align: middle; }
  .dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 6px; vertical-align: middle; }
  aside { border-left: 1px solid var(--line); display: grid; grid-template-rows: auto 1fr auto; min-height: 0; }
  #qhead { padding: 10px 12px; border-bottom: 1px solid var(--line); display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
  #qhead h2 { font-size: 12px; letter-spacing: .06em; text-transform: uppercase; margin: 0 auto 0 0; color: var(--muted); }
  #queue { overflow: auto; }
  .row { padding: 10px 12px; border-bottom: 1px solid var(--line); }
  .row.sel { background: #1e293b; }
  .row.verified { opacity: .55; }
  .row .t { display: flex; gap: 8px; align-items: baseline; }
  .rk { color: var(--muted); width: 2.2em; }
  .nm { font-weight: 600; }
  .meta { color: var(--muted); font-size: 12px; margin: 4px 0 6px 2.2em; }
  .st { font-size: 11px; padding: 1px 6px; border-radius: 4px; margin-left: auto; white-space: nowrap; }
  .st.NO_MAPPED_ROAD_PATH { background: #ef4444; color: #fff; }
  .st.INUNDATED { background: #991b1b; color: #fff; }
  .st.PATH_EXISTS { background: #14532d; color: #bbf7d0; }
  .acts { margin-left: 2.2em; display: flex; gap: 6px; flex-wrap: wrap; }
  button, select { background: #1f2937; color: var(--text); border: 1px solid #374151; border-radius: 6px;
                   padding: 4px 10px; font: inherit; font-size: 12px; cursor: pointer; }
  button:hover { background: #374151; }
  button.primary { background: #2563eb; border-color: #2563eb; }
  #qfoot { padding: 10px 12px; border-top: 1px solid var(--line); display: flex; gap: 8px; flex-wrap: wrap; }
  footer { padding: 6px 16px 8px; border-top: 1px solid var(--line); color: var(--muted); font-size: 11px; }
  footer ul { margin: 2px 0; padding-left: 18px; }
  footer a { color: #93c5fd; }
  .disc { color: #fca5a5; font-weight: 600; }
  #banner { display: none; position: fixed; top: 10px; left: 50%; transform: translateX(-50%); z-index: 3000;
            background: #7f1d1d; color: #fff; padding: 8px 14px; border-radius: 8px; cursor: pointer; }
  #toast { display: none; position: fixed; bottom: 80px; left: 50%; transform: translateX(-50%); z-index: 3000;
           background: #064e3b; color: #ecfdf5; padding: 10px 16px; border-radius: 8px; max-width: 680px;
           box-shadow: 0 6px 24px rgba(0, 0, 0, .4); }
  dialog { background: var(--panel); color: var(--text); border: 1px solid #374151; border-radius: 10px; min-width: 360px; }
  dialog::backdrop { background: rgba(0, 0, 0, .5); }
  dialog h3 { margin: 0 0 6px; font-size: 15px; }
  dialog label { display: grid; gap: 4px; margin: 8px 0; font-size: 12px; color: var(--muted); }
  dialog input, dialog textarea, dialog select { background: #0b1220; color: var(--text); border: 1px solid #374151;
                                                 border-radius: 6px; padding: 6px; font: inherit; }
  dialog menu { display: flex; gap: 8px; justify-content: flex-end; padding: 0; margin: 10px 0 0; }
  .leaflet-popup-content { font-size: 12px; }
  .leaflet-popup-content button { color: #111; background: #f3f4f6; border-color: #d1d5db; margin: 4px 2px 0 0; }
  .hubicon { color: #facc15; font-size: 22px; line-height: 22px; text-shadow: 0 0 3px #000; }
</style>
</head>
<body>
<header>
  <h1>BaadhDrishti <span class="sub">(बाढ़-दृष्टि)</span></h1>
  <span class="sub">Vijayawada Budameru flood · 1 Sep 2024 replay · field-verification triage queue</span>
  <span class="badge">Sentinel-1 via AWS Open Data · AWS Lambda · Amazon DynamoDB</span>
</header>
<section id="stats">
  <div><b id="s-scope">–</b><span>habitations in scope</span></div>
  <div><b id="s-cut">–</b><span>no mapped road path</span></div>
  <div><b id="s-pop">–</b><span>cut-off population proxy (GHSL 2020)</span></div>
  <div><b id="s-ms">–</b><span>last recompute on Lambda (ms)</span></div>
</section>
<main>
  <div id="mapwrap">
    <div id="map"></div>
    <div id="controls" class="panel">
      <label><input type="checkbox" id="t-sar" checked> Sentinel-1 VV backscatter</label>
      <label><span id="d-pre">20 Aug</span> <input type="range" id="t-slider" min="0" max="100" value="100"> <span id="d-post">1 Sep</span></label>
      <label><input type="checkbox" id="t-mask" checked> Candidate water mask</label>
      <label><input type="checkbox" id="t-roads" checked> Disrupted roads</label>
      <label><input type="checkbox" id="t-urban" checked> Urban core (excluded)</label>
      <label><input type="checkbox" id="t-dest"> Hospitals / health centres</label>
    </div>
    <div id="legend" class="panel">
      <div><span class="sw" style="background:#ef4444"></span>Road suspected flooded (blocked)</div>
      <div><span class="sw" style="background:#f59e0b"></span>Bridge in flood: CHECK (kept open)</div>
      <div><span class="sw" style="background:#10b981"></span>Officer: cleared</div>
      <div><span class="sw" style="background:#a855f7"></span>Officer: blocked</div>
      <div><span class="dot" style="background:#ef4444"></span>No mapped road path</div>
      <div><span class="dot" style="background:#22c55e"></span>Path exists</div>
      <div><span class="dot" style="background:#6b7280"></span>Out of scope (urban core)</div>
      <div><span class="hubicon" style="font-size:14px">★</span> Staging hub</div>
    </div>
  </div>
  <aside>
    <div id="qhead">
      <h2>Field-verification priority queue</h2>
      <label><input type="checkbox" id="f-cut" checked> Only cut-off</label>
      <select id="f-sort"><option value="status">Sort: status</option><option value="pop">Sort: population</option></select>
    </div>
    <div id="queue"><div class="row">Loading…</div></div>
    <div id="qfoot">
      <button id="b-hub">+ Add staging hub</button>
      <button id="b-wa">Share on WhatsApp</button>
      <button id="b-csv">Download CSV</button>
    </div>
  </aside>
</main>
<footer>
  <div class="disc">Preliminary screening triage queue based on mapped roads. NOT official rescue orders.</div>
  <ul id="caveats"></ul>
  <div>Data: Copernicus Sentinel-1 (ESA) via AWS Open Data / Earth Search · JRC Global Surface Water · Copernicus DEM GLO-30 ·
    GHSL GHS-POP &amp; GHS-SMOD R2023A (CC BY 4.0) · © OpenStreetMap contributors (ODbL) · Reference:
    <a href="https://apsac.ap.gov.in/wp-content/uploads/2024/09/AP_TERRASARX_6_sep_2024_sat_map.pdf" target="_blank" rel="noopener">NRSC/APSAC 6-Sep-2024 flood map</a></div>
</footer>
<div id="banner"></div>
<div id="toast"></div>
<dialog id="dlg">
  <form method="dialog" id="dlg-form">
    <h3 id="dlg-title"></h3>
    <div id="dlg-fields"></div>
    <menu><button value="cancel" formnovalidate>Cancel</button><button value="ok" class="primary">Confirm</button></menu>
  </form>
</dialog>
<script>
const AOI_BOUNDS = [[16.50, 80.50], [16.65, 80.70]];
const ROAD_COLOR = { AUTO_SUSPECTED: '#ef4444', CHECK: '#f59e0b', FORCE_CLEARED: '#10b981', FORCE_BLOCKED: '#a855f7' };
const HAB_COLOR = { NO_MAPPED_ROAD_PATH: '#ef4444', INUNDATED: '#991b1b', PATH_EXISTS: '#22c55e' };
const URBAN_TIP = 'Urban core excluded due to radar double-bounce ambiguity (NRSC 6-Sep map also excludes urban areas)';
const S = { api: null, data: null, prev: null, sel: null, onlyCut: true, sort: 'status', verified: new Set(), addHub: false };
const $ = id => document.getElementById(id);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const fmt = n => Number(n).toLocaleString('en-IN');
const statusText = s => s.replaceAll('_', ' ');

// ---------- map + static layers ----------
const map = L.map('map', { preferCanvas: true }).fitBounds(AOI_BOUNDS);
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 19, attribution: '&copy; OpenStreetMap contributors' }).addTo(map);
for (const [pane, z] of [['sar', 350], ['mask', 360], ['urban', 370], ['roads', 410], ['habs', 450]]) {
  map.createPane(pane).style.zIndex = z;
}
const LY = { pre: null, post: null, mask: null, urban: null,
  roads: L.layerGroup().addTo(map), habs: L.layerGroup().addTo(map), dest: L.layerGroup(), hubs: L.layerGroup().addTo(map) };

function toggle(id, layer) { $(id).checked ? map.addLayer(layer) : map.removeLayer(layer); }
function banner(msg) { $('banner').textContent = msg; $('banner').style.display = msg ? 'block' : 'none'; }
let toastTimer;
function toast(msg, ms = 9000) {
  $('toast').textContent = msg; $('toast').style.display = 'block';
  clearTimeout(toastTimer); toastTimer = setTimeout(() => { $('toast').style.display = 'none'; }, ms);
}
async function getJSON(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${url}: HTTP ${r.status}`);
  return r.json();
}
async function postJSON(path, body) {
  const r = await fetch(S.api + path, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.error || `HTTP ${r.status}`);
  return j;
}

async function loadStatic() {
  const ov = await getJSON('data/overlays.json');
  LY.pre = L.imageOverlay('data/' + ov.pre, ov.bounds, { pane: 'sar', opacity: 0 }).addTo(map);
  LY.post = L.imageOverlay('data/' + ov.post, ov.bounds, { pane: 'sar', opacity: 0 }).addTo(map);
  LY.mask = L.imageOverlay('data/' + ov.mask, ov.bounds, { pane: 'mask', opacity: 0.8 }).addTo(map);
  const day = d => new Date(d + 'T00:00:00Z').toLocaleDateString('en-IN', { day: 'numeric', month: 'short', timeZone: 'UTC' });
  $('d-pre').textContent = day(ov.pre_date); $('d-post').textContent = day(ov.post_date);
  LY.urban = L.geoJSON(await getJSON('data/urban_core.geojson'), {
    pane: 'urban', interactive: true,
    style: { color: '#f59e0b', weight: 2, dashArray: '6 4', fillColor: '#f59e0b', fillOpacity: 0.12 },
  }).bindTooltip(URBAN_TIP, { sticky: true }).addTo(map);
  applySar();
}
function applySar() {
  const on = $('t-sar').checked, v = Number($('t-slider').value) / 100;
  LY.pre.setOpacity(on ? (1 - v) * 0.85 : 0);
  LY.post.setOpacity(on ? v * 0.85 : 0);
}

// ---------- dynamic layers + queue ----------
function roadNames(r) { return [...new Set((r.blocking_roads || []).map(b => b.name || `unnamed ${b.highway || 'road'}`))]; }

function renderStats() {
  const d = S.data;
  $('s-scope').textContent = fmt(d.in_scope_habitations);
  $('s-cut').textContent = fmt(d.cut_off_count);
  $('s-pop').textContent = fmt(d.cut_off_population_proxy);
  $('s-ms').textContent = fmt(Math.round(d.compute_ms));
}
function renderRoads() {
  LY.roads.clearLayers();
  L.geoJSON(S.data.disrupted_edges, {
    pane: 'roads',
    style: f => ({ color: ROAD_COLOR[f.properties.status], weight: f.properties.status === 'AUTO_SUSPECTED' ? 3 : 5, opacity: 0.95 }),
    onEachFeature: (f, layer) => layer.on('click', e => { if (!S.addHub) roadPopup(f.properties, e.latlng); }),
  }).addTo(LY.roads);
  toggle('t-roads', LY.roads);
}
function renderHabs() {
  LY.habs.clearLayers();
  const add = (r, oos) => {
    const cut = !oos && r.status !== 'PATH_EXISTS';
    L.circleMarker([r.lat, r.lon], { pane: 'habs', radius: cut ? 8 : 5, color: '#111827', weight: 1,
        fillColor: oos ? '#6b7280' : HAB_COLOR[r.status], fillOpacity: 0.95 })
      .bindTooltip(`${esc(r.name)} · ${esc(oos ? r.excluded_reason : statusText(r.status))}`)
      .on('click', () => { if (!S.addHub && !oos) select(r.id, true); })
      .addTo(LY.habs);
  };
  S.data.out_of_scope.forEach(r => add(r, true));
  S.data.habitations.forEach(r => add(r, false));
}
function renderDest() {
  LY.dest.clearLayers();
  for (const d of S.data.destinations || []) {
    L.circleMarker([d.lat, d.lon], { pane: 'habs', radius: 3, color: '#1d4ed8', weight: 1, fillColor: '#3b82f6', fillOpacity: 1 })
      .bindTooltip(esc(d.name)).addTo(LY.dest);
  }
  toggle('t-dest', LY.dest);
}
function renderHubs() {
  LY.hubs.clearLayers();
  const icon = L.divIcon({ className: 'hubicon', html: '★', iconSize: [22, 22], iconAnchor: [11, 11] });
  for (const h of S.data.active_staging_hubs) {
    L.marker([h.lat, h.lon], { icon }).bindTooltip('Staging hub: ' + esc(h.name)).addTo(LY.hubs);
  }
}
function renderQueue() {
  const all = S.data.habitations; // API order: status, then population
  const rank = new Map(all.map((r, i) => [r.id, i + 1]));
  let rows = S.onlyCut ? all.filter(r => r.status !== 'PATH_EXISTS') : all.slice();
  if (S.sort === 'pop') rows.sort((a, b) => b.population_proxy - a.population_proxy);
  $('queue').innerHTML = rows.length ? rows.map(r => {
    const nd = r.nearest_destination, roads = roadNames(r);
    const meta = r.status === 'PATH_EXISTS'
      ? `Route open to ${esc(nd.name)} (${nd.distance_km} km; dry baseline ${r.baseline_distance_km} km)`
      : `Blocking: ${roads.length ? roads.map(esc).join('; ') : 'not identified'} · dry-baseline route was ${r.baseline_distance_km} km`;
    const flags = r.uncertainty_flags.length ? ` · flags: ${r.uncertainty_flags.map(esc).join(', ')}` : '';
    return `<div class="row${S.sel === r.id ? ' sel' : ''}${S.verified.has(r.id) ? ' verified' : ''}" data-id="${esc(r.id)}">
      <div class="t"><span class="rk">#${rank.get(r.id)}</span><span class="nm">${esc(r.name)}</span>
        <span class="st ${esc(r.status)}">${esc(statusText(r.status))}</span></div>
      <div class="meta">Population proxy ${fmt(r.population_proxy)} · ${meta}${flags}</div>
      <div class="acts"><button data-act="zoom">Zoom</button>
        ${r.blocking_edges.length ? '<button data-act="clear">Clear blocking roads</button>' : ''}
        <button data-act="verify">${S.verified.has(r.id) ? 'Unmark verified' : 'Mark verified'}</button></div>
    </div>`;
  }).join('') : '<div class="row">No habitations match the filter.</div>';
}
function renderCaveats() { $('caveats').innerHTML = S.data.caveats.map(c => `<li>${esc(c)}</li>`).join(''); }
function renderAll() { renderStats(); renderRoads(); renderHabs(); renderDest(); renderHubs(); renderQueue(); renderCaveats(); }

function select(id, scroll) {
  S.sel = id; renderQueue();
  if (scroll) document.querySelector(`.row[data-id="${CSS.escape(id)}"]`)?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
}
function applyUpdate(data) { S.prev = S.data; S.data = data; renderAll(); }
async function refresh() {
  try { applyUpdate(await getJSON(S.api + '/api/triage')); banner(''); }
  catch (e) { banner('Could not load triage queue: ' + e.message); }
}
function showDiff() {
  const before = new Map((S.prev?.habitations || []).map(r => [r.id, r.status]));
  const restored = [], cut = [];
  for (const r of S.data.habitations) {
    const old = before.get(r.id);
    if (!old || old === r.status) continue;
    (r.status === 'PATH_EXISTS' ? restored : cut).push(r.name);
  }
  const parts = [];
  if (restored.length) parts.push(`Restored (${restored.length}): ${restored.join(', ')}`);
  if (cut.length) parts.push(`Newly cut off (${cut.length}): ${cut.join(', ')}`);
  toast(`${parts.join(' · ') || 'No habitation changed status'} — recomputed in ${fmt(Math.round(S.data.compute_ms))} ms`);
}

// ---------- officer actions ----------
function ask(title, fields) {
  return new Promise(resolve => {
    $('dlg-title').textContent = title;
    $('dlg-fields').innerHTML = fields.map(f => {
      const input = f.type === 'select'
        ? `<select name="${f.name}">${f.options.map(o => `<option${o === f.value ? ' selected' : ''}>${esc(o)}</option>`).join('')}</select>`
        : f.type === 'textarea'
          ? `<textarea name="${f.name}" rows="2">${esc(f.value || '')}</textarea>`
          : `<input name="${f.name}" value="${esc(f.value || '')}"${f.required ? ' required' : ''}>`;
      return `<label>${esc(f.label)}${input}</label>`;
    }).join('');
    const dlg = $('dlg');
    dlg.returnValue = '';
    dlg.onclose = () => resolve(dlg.returnValue === 'ok' ? Object.fromEntries(new FormData($('dlg-form'))) : null);
    dlg.showModal();
  });
}
const officerFields = () => [
  { name: 'officer_name', label: 'Officer name', value: localStorage.getItem('bd_officer') || '', required: true },
  { name: 'notes', label: 'Notes (source of field report)', type: 'textarea' },
];
async function setRoadStatus(edgeIds, status, title) {
  const v = await ask(title, officerFields());
  if (!v) return;
  localStorage.setItem('bd_officer', v.officer_name);
  toast('Recomputing reachability on AWS Lambda…', 60000);
  try {
    let last;
    for (const id of edgeIds) {
      last = await postJSON('/api/road-status', { edge_id: id, status, officer_name: v.officer_name, notes: v.notes });
    }
    applyUpdate(last); showDiff();
  } catch (e) { banner('Update failed: ' + e.message); refresh(); }
}
function roadPopup(p, latlng) {
  const el = document.createElement('div');
  const label = p.name || `Unnamed ${p.highway || 'road'}`;
  el.innerHTML = `<b>${esc(label)}</b><br>${esc(p.highway || '')} · ${esc(statusText(p.status))}`
    + (p.status === 'CHECK' ? '<br>Bridge in flood: not auto-disrupted, verify' : '')
    + '<br><button data-s="FORCE_CLEARED">Mark cleared</button><button data-s="FORCE_BLOCKED">Mark blocked</button>'
    + (['FORCE_CLEARED', 'FORCE_BLOCKED'].includes(p.status) ? '<button data-s="AUTO_SUSPECTED">Reset to satellite</button>' : '');
  const pop = L.popup().setLatLng(latlng).setContent(el).openOn(map);
  el.addEventListener('click', e => {
    const s = e.target.dataset && e.target.dataset.s;
    if (!s) return;
    map.closePopup(pop);
    setRoadStatus([p.edge_id], s, `${statusText(s).toLowerCase()}: ${label}`);
  });
}
function setAddHub(on) {
  S.addHub = on;
  $('map').classList.toggle('adding', on);
  $('b-hub').textContent = on ? 'Click the map to place the hub (cancel)' : '+ Add staging hub';
}
map.on('click', async e => {
  if (!S.addHub) return;
  setAddHub(false);
  const v = await ask(`New staging hub at ${e.latlng.lat.toFixed(5)}, ${e.latlng.lng.toFixed(5)}`, [
    { name: 'name', label: 'Hub name (school / camp)', required: true },
    { name: 'hub_kind', label: 'Kind', type: 'select', value: 'SCHOOL', options: ['SCHOOL', 'RELIEF_CAMP', 'NDRF_BASE', 'DISTRICT_COLLECTORATE'] },
  ]);
  if (!v) return;
  toast('Recomputing reachability on AWS Lambda…', 60000);
  try {
    applyUpdate(await postJSON('/api/hubs', { name: v.name, hub_kind: v.hub_kind, lat: e.latlng.lat, lon: e.latlng.lng }));
    showDiff();
  } catch (err) { $('toast').style.display = 'none'; banner('Hub not added: ' + err.message); }
});

// ---------- share + CSV ----------
function shareText() {
  const rows = S.data.habitations.filter(r => r.status !== 'PATH_EXISTS').slice(0, 10);
  return [
    'BaadhDrishti field-verification queue — Vijayawada Budameru flood (1 Sep 2024 replay)',
    `Generated ${new Date().toLocaleString('en-IN')}`,
    `No mapped road path to a hospital/hub: ${S.data.cut_off_count} habitations, population proxy ${fmt(S.data.cut_off_population_proxy)} (GHSL 2020)`,
    ...rows.map((r, i) => `${i + 1}. ${r.name} — ${statusText(r.status)} — pop. proxy ${fmt(r.population_proxy)} — blocked: ${roadNames(r).join('; ') || 'not identified'}`),
    'Preliminary screening from Sentinel-1 + mapped roads. NOT official rescue orders — verify on ground.',
    location.href,
  ].join('\n');
}
function downloadCsv() {
  const cols = ['rank', 'id', 'name', 'status', 'population_proxy', 'baseline_distance_km', 'nearest_destination',
    'distance_km', 'blocking_roads', 'blocking_edge_ids', 'uncertainty_flags'];
  const q = v => `"${String(v ?? '').replaceAll('"', '""')}"`;
  const lines = [cols.join(',')].concat(S.data.habitations.map((r, i) => [i + 1, r.id, r.name, r.status, r.population_proxy,
    r.baseline_distance_km, r.nearest_destination?.name, r.nearest_destination?.distance_km, roadNames(r).join('; '),
    r.blocking_edges.join(' '), r.uncertainty_flags.join(' ')].map(q).join(',')));
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([lines.join('\n')], { type: 'text/csv' }));
  a.download = `baadhdrishti_queue_${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

// ---------- wiring ----------
$('t-sar').onchange = applySar;
$('t-slider').oninput = applySar;
$('t-mask').onchange = () => toggle('t-mask', LY.mask);
$('t-urban').onchange = () => toggle('t-urban', LY.urban);
$('t-roads').onchange = () => toggle('t-roads', LY.roads);
$('t-dest').onchange = () => toggle('t-dest', LY.dest);
$('f-cut').onchange = e => { S.onlyCut = e.target.checked; renderQueue(); };
$('f-sort').onchange = e => { S.sort = e.target.value; renderQueue(); };
$('banner').onclick = () => banner('');
$('b-hub').onclick = () => setAddHub(!S.addHub);
$('b-wa').onclick = () => S.data && window.open('https://wa.me/?text=' + encodeURIComponent(shareText()), '_blank', 'noopener');
$('b-csv').onclick = () => S.data && downloadCsv();
$('queue').addEventListener('click', e => {
  const row = e.target.closest('.row[data-id]');
  if (!row) return;
  const r = S.data.habitations.find(h => h.id === row.dataset.id);
  const act = e.target.closest('button')?.dataset.act;
  if (!act) return select(r.id, false);
  if (act === 'zoom') { select(r.id, false); map.flyTo([r.lat, r.lon], 15); }
  if (act === 'verify') { S.verified.has(r.id) ? S.verified.delete(r.id) : S.verified.add(r.id); renderQueue(); }
  if (act === 'clear') setRoadStatus(r.blocking_edges, 'FORCE_CLEARED', `Clear ${roadNames(r).join('; ') || 'blocking roads'} for ${r.name}`);
});

(async () => {
  try {
    S.api = (await getJSON('config.json')).apiUrl.replace(/\/$/, '');
    await loadStatic();
  } catch (e) { banner('Startup failed: ' + e.message); return; }
  await refresh();
})();
</script>
</body>
</html>
```

(This exact file was verified on 2026-10-11 against the live API with `tests/frontend_smoke.py`, read-only and `--write`: "Restored (5): Tadepalle, Vemavaram, Jakkampudi, Kotturu, Shabada — recomputed in 940 ms".)

### Task 4: S3 + CloudFront hosting in the SAM stack, deploy script, live smoke test

**Files:**
- Modify: `template.yaml` (insert resources before `  ApiFunction:`; append outputs at the end)
- Create: `scripts/deploy_frontend.sh`
- Generated: `frontend/config.json` (gitignored), `docs/screenshot.png` (commit)

**Interfaces:**
- Consumes: `frontend/` from Tasks 2–3; stack outputs `ApiUrl` (existing).
- Produces: stack outputs `FrontendUrl` (https://<id>.cloudfront.net), `FrontendBucketName`, `DistributionId`; `scripts/deploy_frontend.sh` (idempotent; prints the URL as its last line).

- [ ] **Step 1: Add the resources** — in `template.yaml`, insert this block (2-space indented, under `Resources:`) immediately **before** the line `  ApiFunction:`:

```yaml
  FrontendBucket:
    Type: AWS::S3::Bucket
    Properties:
      PublicAccessBlockConfiguration:
        BlockPublicAcls: true
        BlockPublicPolicy: true
        IgnorePublicAcls: true
        RestrictPublicBuckets: true

  FrontendOAC:
    Type: AWS::CloudFront::OriginAccessControl
    Properties:
      OriginAccessControlConfig:
        Name: !Sub "${AWS::StackName}-frontend-oac"
        OriginAccessControlOriginType: s3
        SigningBehavior: always
        SigningProtocol: sigv4

  FrontendDistribution:
    Type: AWS::CloudFront::Distribution
    Properties:
      DistributionConfig:
        Enabled: true
        Comment: BaadhDrishti frontend
        DefaultRootObject: index.html
        HttpVersion: http2
        PriceClass: PriceClass_200   # includes India edge locations
        Origins:
          - Id: frontend-s3
            DomainName: !GetAtt FrontendBucket.RegionalDomainName
            OriginAccessControlId: !GetAtt FrontendOAC.Id
            S3OriginConfig:
              OriginAccessIdentity: ""
        DefaultCacheBehavior:
          TargetOriginId: frontend-s3
          ViewerProtocolPolicy: redirect-to-https
          AllowedMethods: [GET, HEAD]
          CachedMethods: [GET, HEAD]
          Compress: true
          CachePolicyId: 658327ea-f89d-4fab-a63d-7e88639e58f6   # AWS managed "CachingOptimized"

  FrontendBucketPolicy:
    Type: AWS::S3::BucketPolicy
    Properties:
      Bucket: !Ref FrontendBucket
      PolicyDocument:
        Version: "2012-10-17"
        Statement:
          - Sid: AllowCloudFrontOAC
            Effect: Allow
            Principal: { Service: cloudfront.amazonaws.com }
            Action: s3:GetObject
            Resource: !Sub "${FrontendBucket.Arn}/*"
            Condition:
              StringEquals:
                AWS:SourceArn: !Sub "arn:aws:cloudfront::${AWS::AccountId}:distribution/${FrontendDistribution}"
```

and append at the very end of the file, under the existing `Outputs:` section:

```yaml
  FrontendUrl:
    Value: !Sub "https://${FrontendDistribution.DomainName}"
  FrontendBucketName:
    Value: !Ref FrontendBucket
  DistributionId:
    Value: !Ref FrontendDistribution
```

(Task 1 already changed `MemorySize` to 1769.)

- [ ] **Step 2: Validate**

Run: `AWS_PROFILE=baadh sam validate --lint --region ap-south-1`
Expected: `template.yaml is a valid SAM Template` (this exact block was lint-checked on 2026-10-11).

- [ ] **Step 3: Create `scripts/deploy_frontend.sh`**

```bash
#!/usr/bin/env bash
# Publish frontend/ (index.html + data/ overlays) to the stack's S3 bucket behind CloudFront.
# Usage: scripts/deploy_frontend.sh            (always uses the hackathon profile "baadh", never the shell default)
set -euo pipefail
export AWS_PROFILE=baadh
REGION=ap-south-1
STACK=${STACK:-baadhdrishti}
cd "$(dirname "$0")/.."
out() { aws cloudformation describe-stacks --region "$REGION" --stack-name "$STACK" \
          --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text; }
API=$(out ApiUrl); BUCKET=$(out FrontendBucketName); DIST=$(out DistributionId); URL=$(out FrontendUrl)
printf '{"apiUrl": "%s"}\n' "$API" > frontend/config.json
aws s3 sync frontend/ "s3://$BUCKET/" --region "$REGION" --exclude ".*" --delete --only-show-errors
aws cloudfront create-invalidation --distribution-id "$DIST" --paths "/*" --query Invalidation.Id --output text >/dev/null
echo "API      $API"
echo "Frontend $URL"
```
Then: `chmod +x scripts/deploy_frontend.sh`

- [ ] **Step 4: Deploy the stack** (CloudFront creation takes ~5–10 min)

```bash
AWS_PROFILE=baadh sam build && AWS_PROFILE=baadh sam deploy --no-progressbar | tail -20
```
Expected: `Successfully created/updated stack - baadhdrishti in ap-south-1`, outputs include `FrontendUrl`.

**If it fails** with `Your account must be verified before you can add new CloudFront resources` (common on brand-new AWS accounts): CloudFormation rolls back automatically (existing API keeps working). Then (a) open an AWS Support case "CloudFront account verification" from the console of account 872376836713 and continue with Task 5 while waiting; (b) if not resolved by 14:00 IST, use the fallback: replace the four Frontend* resources above with
```yaml
  FrontendBucket:
    Type: AWS::S3::Bucket
    Properties:
      WebsiteConfiguration: { IndexDocument: index.html }
      PublicAccessBlockConfiguration:
        BlockPublicAcls: true
        BlockPublicPolicy: false
        IgnorePublicAcls: true
        RestrictPublicBuckets: false

  FrontendBucketPolicy:
    Type: AWS::S3::BucketPolicy
    Properties:
      Bucket: !Ref FrontendBucket
      PolicyDocument:
        Version: "2012-10-17"
        Statement:
          - Effect: Allow
            Principal: "*"
            Action: s3:GetObject
            Resource: !Sub "${FrontendBucket.Arn}/*"
```
and the outputs with `FrontendUrl: { Value: !GetAtt FrontendBucket.WebsiteURL }`, `FrontendBucketName: { Value: !Ref FrontendBucket }`; in `deploy_frontend.sh` delete the `DIST=` lookup and the `create-invalidation` line. Record the switch in CLAUDE.md (S3 website is HTTP-only; the README/video then say "Amazon S3 static website").

- [ ] **Step 5: Publish the frontend and smoke-test the live URL**

```bash
scripts/deploy_frontend.sh
URL=$(AWS_PROFILE=baadh aws cloudformation describe-stacks --region ap-south-1 --stack-name baadhdrishti --query "Stacks[0].Outputs[?OutputKey=='FrontendUrl'].OutputValue" --output text)
curl -s -o /dev/null -w "%{http_code}\n" "$URL/" ; curl -s "$URL/config.json"
uv run --with playwright python tests/frontend_smoke.py "$URL/"
uv run --with playwright python tests/frontend_smoke.py "$URL/" --write
AWS_PROFILE=baadh scripts/reset_demo_state.sh
```
Expected: `200`; config JSON with the API URL; `✓ frontend smoke passed`; `cleared Tadepalle: Restored (5): …` + `✓ frontend smoke passed (write flow)`; both tables `0 items`. (If the first curl returns 403, wait 2 minutes for the invalidation/distribution to finish and retry.)

- [ ] **Step 6: Update docs and commit**

In `CLAUDE.md` Status replace `- [ ] Task 2.7: index.html + Leaflet frontend (S3 + CloudFront), road edit + hub add UI` with:
```text
- [x] Task 2.7/2.8: `frontend/index.html` (Leaflet, queue, road edit, hub add, WhatsApp, CSV) on S3 + CloudFront: <FrontendUrl>. Deploy: `scripts/deploy_frontend.sh`. Smoke: `tests/frontend_smoke.py <url> [--write]`.
```
(write the real URL). In `PLAN.md` §6 tick `Task 2.7` and `Task 2.8` (`- [ ]` → `- [x]`).

```bash
git add template.yaml scripts/deploy_frontend.sh docs/screenshot.png CLAUDE.md PLAN.md
git commit -m "feat(infra): S3 + CloudFront frontend hosting and deploy script (Tasks 2.7, 2.8)"
git push origin main
```

### Task 5: Data-backed demo staging hub (for the video)

**Files:**
- Create: `scripts/pick_demo_hub.py`
- Generated (gitignored under data/raw): `data/raw/osm/hub_candidates_aoi.json`

**Interfaces:**
- Consumes: `data/processed/lambda_bundle.json`, `urban_core.geojson`, `flood_mask_20240901.tif`, `engine.reachability.evaluate_reachability`.
- Produces: printed ranking lines `"<n> restored | <name> [<kind>] | <lat>, <lon> | snap <m> m | <source> | <names>"`, used verbatim in `docs/VIDEO.md` (Task 7).

Why: OSM maps very few public buildings in the cut-off cluster (checked 2026-10-11: 48 schools in the AOI, only 4 named
schools outside the urban core, none within 2 km of a cut-off habitation), so the demo must not claim "a dry school".
The script ranks real named OSM amenities **and** cut-off habitation points ("officer-nominated village-centre camp")
that are dry in our mask, by how many cut-off habitations a hub there restores.

- [ ] **Step 1: Create `scripts/pick_demo_hub.py`** with exactly:

```python
"""
scripts/pick_demo_hub.py - pick a real OSM public building for the video's "add staging hub" step (offline, read-only).

OSM maps few rural schools here (2026-10-11: 48 schools in the AOI, only 4 named ones outside the urban core), so
candidates are (1) named OSM amenities typically used as relief sites (HUB_AMENITIES) and (2) the points of currently
cut-off habitations ("<name> village centre", i.e. an officer-nominated camp). A candidate must: have a name, lie outside the GHSL urban core, have no candidate-flood pixel within ~60 m
(3 px of 20 m), snap to a road node within 1 km, and be within 3 km of a currently cut-off habitation.
For each candidate the engine is re-run with the school as an extra STAGING_HUB; we count restored habitations.
Prints the top 5. Caches the Overpass response in data/raw/osm/hub_candidates_aoi.json.
"""

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import rasterio
import shapely
from pyproj import Transformer
from rasterio.transform import rowcol
from scipy.spatial import cKDTree
from shapely.geometry import shape

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from engine.reachability import evaluate_reachability  # noqa: E402

PROC = ROOT / "data" / "processed"
CACHE = ROOT / "data" / "raw" / "osm" / "hub_candidates_aoi.json"
AOI = [80.50, 16.50, 80.70, 16.65]
FLOOD_CLEAR_PX = 3
MAX_SNAP_M = 1000.0
MAX_TO_CUTOFF_M = 3000.0
HUB_AMENITIES = "school|college|community_centre|townhall|place_of_worship|marketplace"
to_utm = Transformer.from_crs("EPSG:4326", "EPSG:32644", always_xy=True).transform


def fetch_candidates():
    q = f'[out:json][timeout:120];nwr["amenity"~"^({HUB_AMENITIES})$"]({AOI[1]},{AOI[0]},{AOI[3]},{AOI[2]});out center tags;'
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["curl", "-sf", "--max-time", "200", "-A", "BaadhDrishti/1.0", "https://overpass-api.de/api/interpreter",
                    "--data-urlencode", f"data={q}", "-o", str(CACHE)], check=True)


def main():
    if not CACHE.exists():
        fetch_candidates()
    b = json.loads((PROC / "lambda_bundle.json").read_text())
    edges = [{"edge_id": e[0], "u": e[1], "v": e[2], "weight": e[3], "is_bridge": e[4]} for e in b["edges"]]
    suspected = set(b["auto_suspected"])
    node_ids = [int(n) for n in b["nodes"]]
    nxs, nys = to_utm([c[0] for c in b["nodes"].values()], [c[1] for c in b["nodes"].values()])
    tree = cKDTree(np.column_stack([nxs, nys]))
    core = shapely.union_all([shape(f["geometry"]) for f in json.loads((PROC / "urban_core.geojson").read_text())["features"]])
    with rasterio.open(PROC / "flood_mask_20240901.tif") as src:
        flood, ft = src.read(1) == 1, src.transform

    base = evaluate_reachability([dict(e) for e in edges], b["habitations"], b["destinations"], suspected)
    cut = [r for r in base if not r["in_urban_core"] and r["status"] != "PATH_EXISTS"]
    cut_ids = {r["id"] for r in cut}
    cut_xy = np.column_stack(to_utm([r["lon"] for r in cut], [r["lat"] for r in cut]))
    print(f"currently cut off (in scope): {len(cut)}")

    candidates = []
    for el in json.loads(CACHE.read_text())["elements"]:
        lat, lon = (el["lat"], el["lon"]) if "lat" in el else (el["center"]["lat"], el["center"]["lon"])
        if el.get("tags", {}).get("name"):
            candidates.append((el["tags"]["name"], el["tags"]["amenity"], lat, lon, f"OSM {el['type']}/{el['id']}"))
    candidates += [(f"{r['name']} village centre", "officer-nominated camp", r["lat"], r["lon"], r["id"]) for r in cut]

    results = []
    for name, kind, lat, lon, source in candidates:
        if core.contains(shapely.Point(lon, lat)):
            continue
        x, y = to_utm(lon, lat)
        if np.min(np.hypot(cut_xy[:, 0] - x, cut_xy[:, 1] - y)) > MAX_TO_CUTOFF_M:
            continue
        r, c = rowcol(ft, x, y)
        win = flood[max(r - FLOOD_CLEAR_PX, 0):r + FLOOD_CLEAR_PX + 1, max(c - FLOOD_CLEAR_PX, 0):c + FLOOD_CLEAR_PX + 1]
        if win.size == 0 or win.any():
            continue
        snap_m, i = tree.query([x, y])
        if snap_m > MAX_SNAP_M:
            continue
        hub = {"id": "demo_hub", "name": name, "type": "STAGING_HUB", "node": node_ids[i]}
        res = evaluate_reachability([dict(e) for e in edges], b["habitations"], b["destinations"] + [hub], suspected)
        restored = [h["name"] for h in res if h["id"] in cut_ids and h["status"] == "PATH_EXISTS"]
        results.append((len(restored), f"{name} [{kind}]", lat, lon, round(float(snap_m)), source, restored))

    print(f"candidates checked: {len(results)}")
    for n, name, lat, lon, snap_m, source, restored in sorted(results, key=lambda t: (-t[0], t[4]))[:5]:
        print(f"{n} restored | {name} | {lat:.6f}, {lon:.6f} | snap {snap_m} m | {source} | {', '.join(restored)}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it**

Run: `.venv/bin/python scripts/pick_demo_hub.py`
Expected (verified 2026-10-11; first run fetches Overpass with curl ~10 s):
```text
currently cut off (in scope): 7
candidates checked: 8
5 restored | Jakkampudi village centre [officer-nominated camp] | 16.584085, 80.614908 | snap 16 m | hab_node_5645738551 | Tadepalle, Vemavaram, Jakkampudi, Kotturu, Shabada
5 restored | Kotturu village centre [officer-nominated camp] | 16.620465, 80.622135 | snap 28 m | hab_node_5645738552 | Tadepalle, Vemavaram, Jakkampudi, Kotturu, Shabada
...
```
If the output differs (e.g. OSM changed), use the actual first line in Task 7 — never the numbers above.

- [ ] **Step 3: Commit**

```bash
git add scripts/pick_demo_hub.py
git commit -m "feat(demo): data-backed staging-hub candidate ranking for the video"
git push origin main
```

### Task 6: Project README, hackathon rules moved, architecture diagram

**Files:**
- Move: `README.md` → `docs/HACKATHON.md` (content unchanged)
- Create: `README.md`, `scripts/draw_architecture.py`, `docs/architecture.png`
- Modify: `CLAUDE.md` (first line reference to rules)

**Interfaces:**
- Consumes: `FrontendUrl` and `ApiUrl` stack outputs (Task 4), `docs/screenshot.png` (Task 3/4).
- Produces: `docs/architecture.png` (used in README, VIDEO, BLOG).

- [ ] **Step 1: Move the rules file and fix references**

```bash
git mv README.md docs/HACKATHON.md
grep -rn "README.md" CLAUDE.md PLAN.md
```
In `CLAUDE.md` line 3 change ``Rules + judging: `README.md`.`` to ``Rules + judging: `docs/HACKATHON.md`.`` and in the "Read these" section, if any line names `README.md` as the rules file, change it the same way. Any `README.md` mention in `PLAN.md` that refers to the rules → `docs/HACKATHON.md`.

- [ ] **Step 2: Create `scripts/draw_architecture.py`** with exactly:

```python
"""scripts/draw_architecture.py - render docs/architecture.png (README + video slide). Uses matplotlib only."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "docs" / "architecture.png"
# key: (x, y, w, h, label, fill)
BOXES = {
    "s1": (0.2, 4.3, 3.5, 1.0, "AWS Open Data (S3)\nSentinel-1 GRD 20 Aug / 1 Sep 2024", "#fbd38d"),
    "aux": (0.2, 2.9, 3.5, 1.0, "JRC water · Copernicus DEM\nGHSL population · OpenStreetMap", "#e2e8f0"),
    "pipe": (4.5, 3.6, 3.2, 1.3, "Offline Python pipeline (run once)\ncalibrate → flood mask →\nroad graph → triage bundle", "#bee3f8"),
    "data": (8.4, 3.6, 2.6, 1.3, "Amazon S3\nprecomputed bundle", "#c6f6d5"),
    "lambda": (8.4, 1.2, 2.6, 1.3, "AWS Lambda (Python)\nNetworkX reachability\nper officer action", "#fbd38d"),
    "ddb": (11.8, 1.2, 2.6, 1.3, "Amazon DynamoDB\nroad overrides\nstaging hubs", "#c3dafe"),
    "apigw": (4.5, 1.2, 3.2, 1.3, "Amazon API Gateway (HTTP)\nGET /api/triage\nPOST /api/road-status · /api/hubs", "#e9d8fd"),
    "officer": (0.2, 1.35, 3.5, 1.0, "District officer\n(browser)", "#ffffff"),
    "cf": (0.2, -0.3, 3.5, 1.1, "Amazon CloudFront + S3\nindex.html + Leaflet", "#e9d8fd"),
}
ARROWS = [("s1", "pipe"), ("aux", "pipe"), ("pipe", "data"), ("data", "lambda"), ("lambda", "ddb"),
          ("officer", "apigw"), ("apigw", "lambda"), ("cf", "officer")]


def center(k):
    x, y, w, h = BOXES[k][:4]
    return x + w / 2, y + h / 2


def edge_point(k, toward):
    """Point where the line from box k's centre toward `toward` leaves the box."""
    x, y, w, h = BOXES[k][:4]
    cx, cy = x + w / 2, y + h / 2
    dx, dy = toward[0] - cx, toward[1] - cy
    s = min((w / 2) / abs(dx) if dx else float("inf"), (h / 2) / abs(dy) if dy else float("inf"))
    return cx + dx * s, cy + dy * s


def main():
    fig, ax = plt.subplots(figsize=(14, 6.6))
    ax.set_xlim(0, 14.6)
    ax.set_ylim(-0.5, 5.8)
    ax.axis("off")
    for x, y, w, h, label, fill in BOXES.values():
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.04,rounding_size=0.12", fc=fill, ec="#1a202c", lw=1.2))
        ax.text(x + w / 2, y + h / 2, label, ha="center", va="center", fontsize=9.5, color="#1a202c")
    for a, b in ARROWS:
        ax.annotate("", xy=edge_point(b, center(a)), xytext=edge_point(a, center(b)),
                    arrowprops=dict(arrowstyle="-|>", lw=1.5, color="#1a202c"))
    ax.text(7.3, 5.55, "Offline: heavy SAR/GIS processing, once", ha="center", fontsize=10, style="italic", color="#4a5568")
    ax.text(7.3, 0.25, "Online: officer edits → recompute in Lambda", ha="center", fontsize=10, style="italic", color="#4a5568")
    ax.set_title("BaadhDrishti on AWS", fontsize=15, weight="bold")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=150, bbox_inches="tight", facecolor="white")
    print(OUT)


if __name__ == "__main__":
    main()
```
Run: `.venv/bin/python scripts/draw_architecture.py`
Expected: prints `.../docs/architecture.png`. Open it with the Read tool: 9 boxes, arrows Sentinel-1/aux → pipeline → S3 bundle → Lambda → DynamoDB; officer → API Gateway → Lambda; CloudFront → officer; no text overflowing a box (verified 2026-10-11).

- [ ] **Step 3: Create `README.md`** — get the URLs first:
```bash
for k in FrontendUrl ApiUrl; do AWS_PROFILE=baadh aws cloudformation describe-stacks --region ap-south-1 --stack-name baadhdrishti --query "Stacks[0].Outputs[?OutputKey=='$k'].OutputValue" --output text; done
```
Then write `README.md` with exactly this content, replacing `FRONTEND_URL` and `API_URL` with the two printed values:

````markdown
# BaadhDrishti (बाढ़-दृष्टि) — which villages lost every mapped road to a hospital?

**Live demo:** FRONTEND_URL · **API:** API_URL/api/triage
Bharat Builds Tour — Environmental Hacks, Track 02 Heat & Water. Hackathon rules: [`docs/HACKATHON.md`](docs/HACKATHON.md).

![BaadhDrishti screenshot](docs/screenshot.png)

After a flood, satellites tell a control room **where the water is**. They do not tell it **which habitations have no
mapped road left to a hospital or relief hub** — the question that decides where field teams verify first.
BaadhDrishti replays the 31 Aug – 2 Sep 2024 Budameru / Krishna flood around Vijayawada: Sentinel-1 radar change
detection → candidate flood mask → OpenStreetMap road graph → ranked **field-verification triage queue**. An officer can
mark a road cleared/blocked or add a staging hub, and the queue is recomputed on AWS Lambda.

It is **not** a rescue-dispatch system, navigation, a forecast, or an official damage assessment.

## What the replay finds (script output, not ground truth)
- 7 peri-urban habitations with **no mapped road path** to any hospital/health centre — Tadepalle, Paidurupadu,
  Elaprolu, Vemavaram, Jakkampudi, Kotturu, Shabada — population proxy 9,314 (GHSL 2020 estimate).
- Clearing the 4 reported blocking segments of Tadepalle's route (Vijayawada–Vissannapeta Road) restores 5 of them.
- Candidate flood area 44.93 km² (432 polygons, 20 m grid) before excluding the 70.4 km² urban core from the road analysis.

## Architecture
![Architecture](docs/architecture.png)

| Layer | AWS | What it does |
|---|---|---|
| Data | AWS Open Data (`s3://sentinel-s1-l1c`, Earth Search STAC) | Sentinel-1A GRD, 20 Aug & 1 Sep 2024, relative orbit 92 descending |
| Offline pipeline | — (Python, run once) | σ⁰ calibration + noise removal, geocoding, ΔVV < −3 dB change detection, masks, OSM graph, triage |
| Storage | Amazon S3 | precomputed graph/triage bundle; static frontend |
| API | Amazon API Gateway (HTTP) + AWS Lambda (Python, NetworkX) | multi-source Dijkstra reachability per request |
| State | Amazon DynamoDB | officer road overrides, staging hubs |
| Frontend | Amazon CloudFront + S3 | single `index.html` + Leaflet |
| Deploy | AWS SAM | `template.yaml` |

## Method (short)
1. Same-geometry Sentinel-1 pair (S1A, orbit 92, descending) from AWS Open Data; only the AOI window is read.
2. Radiometric calibration with the product LUTs (σ⁰), thermal-noise removal, GCP geocoding to 20 m UTM, and a 250 m
   near-range geolocation correction estimated against JRC permanent water (GCP heights ≠ terrain).
3. 5×5 median, ΔVV < −3 dB **and** post-event VV darker than reference open water; slope > 5° (Copernicus DEM) and
   permanent water (JRC) excluded. Visually checked against the NRSC/APSAC 6-Sep-2024 flood map.
4. OSM drivable roads → graph; a road within 25 m of candidate water is suspected blocked; bridges are never
   auto-disrupted (flagged CHECK). Habitations = OSM villages/hamlets/suburbs/neighbourhoods; destinations = OSM
   hospitals/health centres + officer hubs; population = GHSL GHS-POP 2020 per Voronoi cell.
5. Status order INUNDATED > NO_MAPPED_ROAD_PATH > PATH_EXISTS, then population.

## Honest limits
- Candidate observed inundation, not ground verified; dense urban core excluded (radar double-bounce), as in the NRSC map.
- Road network and facilities are current OpenStreetMap, not a 2024 snapshot.
- Population is a GHSL 2020 estimate, not a census count. No auth on the demo API (throttled).

## Run it
```bash
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r scripts/requirements-offline.txt
# offline pipeline: see PLAN.md §6 (fetch → flood mask → road graph → reachability → bundle → overlays)
.venv/bin/python tests/test_reachability_engine.py && .venv/bin/python tests/test_lambda_local.py
AWS_PROFILE=<your-profile> sam build && sam deploy        # samconfig.toml: stack baadhdrishti, ap-south-1
aws s3 cp data/processed/lambda_bundle.json s3://<DataBucketName>/lambda_bundle.json
scripts/deploy_frontend.sh
```

## Data & credits
Copernicus Sentinel-1 data (ESA) via AWS Open Data / Element 84 Earth Search · JRC Global Surface Water ·
Copernicus DEM GLO-30 · GHSL GHS-POP and GHS-SMOD R2023A (European Commission JRC, CC BY 4.0) ·
© OpenStreetMap contributors (ODbL) · Validation reference: NRSC/APSAC flood map of 6 Sep 2024.
````

- [ ] **Step 4: Commit**

```bash
git add README.md docs/HACKATHON.md scripts/draw_architecture.py docs/architecture.png CLAUDE.md PLAN.md
git commit -m "docs: project README with architecture diagram; move hackathon rules to docs/HACKATHON.md"
git push origin main
```

### Task 7: Video script and recording checklist (`docs/VIDEO.md`)

**Files:**
- Create: `docs/VIDEO.md`
- Modify: `PLAN.md` §7 (one line pointing to `docs/VIDEO.md`)

**Interfaces:**
- Consumes: live `FrontendUrl` (Task 4), first ranking line of `scripts/pick_demo_hub.py` (Task 5), `docs/architecture.png` (Task 6).
- Produces: the script the owner records from.

- [ ] **Step 1: Re-check the numbers the narration uses** (they must come from the live API at recording time):

```bash
curl -s https://f3m0jdk4wi.execute-api.ap-south-1.amazonaws.com/api/triage | .venv/bin/python -c "
import json,sys; t=json.load(sys.stdin); cut=[r for r in t['habitations'] if r['status']!='PATH_EXISTS']
print('cut_off', t['cut_off_count'], 'pop', t['cut_off_population_proxy'], 'compute_ms', t['compute_ms'])
print('top', cut[0]['name'], cut[0]['population_proxy'], sorted({b['name'] for b in cut[0]['blocking_roads'] if b['name']}))"
```
Expected today: `cut_off 7 pop 9314 compute_ms <n>` and `top Tadepalle 2404 ['Vijayawada - Vissannapeta Road']`.
If any value differs, use the printed value in Step 2 instead of the ones written there.

- [ ] **Step 2: Create `docs/VIDEO.md`** with exactly this content (edit only values that Step 1 printed differently; replace `HUB_LINE` with the first ranking line printed by `scripts/pick_demo_hub.py`):

````markdown
# BaadhDrishti — 3-minute demo video

Rules: every number on screen or in the voiceover comes from the live UI/API or this repo's script output.
APSDMA / cusecs figures are **TO VERIFY** — they are left out below; add them only with a citation on screen.

## Before recording (checklist)
- [ ] `AWS_PROFILE=baadh scripts/reset_demo_state.sh` → both tables `0 items`.
- [ ] Open the FrontendUrl in a fresh browser window (1440×900 or 1920×1080), reload once to warm the Lambda.
- [ ] Stats bar reads: 40 in scope · 7 no mapped road path · 9,314 population proxy · compute ms (note the value: ____ ms).
- [ ] Demo hub location: HUB_LINE
- [ ] Have `docs/architecture.png` open in another tab.
- [ ] After recording: run the reset script again.

## Shot list

| Time | Screen | Voiceover |
|---|---|---|
| 0:00–0:25 | Title card → NRSC/APSAC 6-Sep-2024 map PDF (cite on screen) | "In early September 2024 the Budameru flood cut villages around Vijayawada off from care. Flood maps show where the water is. A control room also needs to know: which villages have no mapped road left to a hospital, and where should field teams verify first?" |
| 0:25–1:05 | BaadhDrishti opens. Drag the slider 20 Aug → 1 Sep, toggle the blue water mask, hover the amber urban core | "BaadhDrishti uses Sentinel-1 radar from AWS Open Data — it sees through cloud. We calibrate the 20 August and 1 September images, detect where the radar return dropped like open water, and mask permanent water and slopes. The dense urban core is excluded and labelled, because radar double-bounce makes city flooding ambiguous — the official NRSC map excludes it too." |
| 1:05–1:45 | Red road segments; queue on the right; click row #1 Tadepalle → Zoom | "The difference is the road network. We turn OpenStreetMap roads into a graph, mark segments next to candidate water as suspected blocked — bridges are never auto-closed, they are flagged for checking — and ask, for every habitation, is any mapped road path left to a hospital? Seven peri-urban habitations have none. Tadepalle, population estimate 2,404, tops the verification queue; its route is blocked on the Vijayawada–Vissannapeta Road." |
| 1:45–2:25 | Click "Clear blocking roads" on Tadepalle → dialog (officer name, note "tractor passable per police outpost") → toast "Restored (5)…"; then click an orange bridge → Mark blocked; then "+ Add staging hub" at the demo hub location | "Disaster response is human-in-the-loop. A field report says that stretch is passable — the officer marks it cleared, and AWS Lambda recomputes reachability for the whole district in about the time shown here: five habitations get a path back. A bridge can be marked blocked, or the officer can nominate a dry staging point — and the queue updates again. Share it to WhatsApp or download a CSV for the field teams." |
| 2:25–3:00 | `docs/architecture.png`, then back to the app footer with the disclaimer | "Under the hood: Sentinel-1 from AWS Open Data, a one-time offline pipeline into Amazon S3, an API Gateway and Lambda engine, officer edits in DynamoDB, and a single Leaflet page on CloudFront, deployed with AWS SAM. BaadhDrishti is not a rescue order or a forecast — it is an uncertainty-aware verification queue that helps officers decide where to look first." |
````

- [ ] **Step 3: Point PLAN.md to it** — in `PLAN.md`, directly under the heading `## 7. 3-Minute Demo Video Script (Shot-by-Shot)`, add the line:
`> Recording version with live values and checklist: docs/VIDEO.md (supersedes the table below).`

- [ ] **Step 4: Commit**

```bash
git add docs/VIDEO.md PLAN.md
git commit -m "docs: recording-ready video script and checklist"
git push origin main
```

### Task 8: AWS Builder Center blog draft (`docs/BLOG.md`)

**Files:**
- Create: `docs/BLOG.md`

- [ ] **Step 1: Create `docs/BLOG.md`** with exactly this content (replace `FRONTEND_URL` with the live URL):

````markdown
# Which villages lost every road to a hospital? Building BaadhDrishti on AWS

*Bharat Builds Tour — Environmental Hacks · Track 02 Heat & Water · live demo: FRONTEND_URL · code: https://github.com/ancientdev0x/aws-env*

## The problem
When the Budameru rivulet flooded Vijayawada in early September 2024, rapid flood maps (NRSC/APSAC, Copernicus) showed
where the water was. What a district control room also needs is a short list: which habitations have **no mapped road
left** to a hospital or relief hub, ranked so field teams know where to verify first. BaadhDrishti replays that event and
produces exactly that — a field-verification triage queue an officer can correct.

## What it does
- Sentinel-1 radar (pre 20 Aug, post 1 Sep 2024) → candidate flood mask.
- OpenStreetMap roads → graph; segments next to candidate water are suspected blocked (bridges only flagged).
- For every habitation: is any mapped road path left to a hospital/health centre or officer hub? Ranked by status, then
  GHSL population estimate.
- The officer marks a road cleared/blocked or adds a staging hub; AWS Lambda recomputes the queue; share via WhatsApp/CSV.

In the replay, 7 peri-urban habitations had no mapped road path (population proxy 9,314); clearing four reported segments
of one route restored five of them.

## The stack
- **AWS Open Data**: Sentinel-1 GRD from `s3://sentinel-s1-l1c`, found via the Earth Search STAC API — read as AOI windows only.
- **Offline Python** (run once): rasterio, NumPy/SciPy, OSMnx, Shapely → a 3.6 MB bundle in **Amazon S3**.
- **Amazon API Gateway + AWS Lambda** (Python, NetworkX): multi-source Dijkstra from all destinations per request.
- **Amazon DynamoDB**: officer road overrides and staging hubs.
- **Amazon CloudFront + S3**: one `index.html` with Leaflet. **AWS SAM** deploys all of it.

![Architecture](architecture.png)

## What fought back
1. **Raw radar is not decibels.** The Earth Search GRD TIFFs are uint16 digital numbers. We applied the product's
   calibration and thermal-noise LUTs to get σ⁰ before any thresholding.
2. **A 250 m geolocation error.** GRD comes with ground-control points whose heights don't match the terrain, so the
   geocoded image sat about 250 m toward far range. We estimated the shift against JRC permanent water (IoU 0.418 → 0.535)
   and checked it independently against OSM water polygons (residual ≤ 20 m) — essential when roads are buffered by 25 m.
3. **Crop fields look like floods.** ΔVV < −3 dB alone flagged farmland south of the Krishna that the NRSC map shows dry.
   Requiring the post-event pixel to be as dark as reference open water (threshold derived from JRC water, −14.01 dB)
   removed most of it.
4. **One bridge hid every cut-off.** OSMnx graph simplification merged short bridge segments into multi-kilometre road
   edges; since bridges are never auto-closed, whole flooded roads stayed open. Splitting edges where the bridge tag
   changes took the result from 1 to 7 cut-off habitations.
5. **Small things:** Overpass hung from Python over IPv4 on our network (curl over IPv6 worked); OSM has few mapped rural
   public buildings, so the demo hub is an officer-nominated village-centre point checked dry in our mask, not a "school".

## Honest limits
Candidate inundation, not ground truth; dense urban core excluded (radar double-bounce), as NRSC also does; OSM is
today's network, not September 2024's; population is a GHSL 2020 estimate. It is a screening queue, not rescue orders.

## Try it
Live: FRONTEND_URL · Code and reproduce steps: https://github.com/ancientdev0x/aws-env
````

- [ ] **Step 2: Commit**

```bash
git add docs/BLOG.md
git commit -m "docs: AWS Builder Center blog draft"
git push origin main
```

### Task 9: Submission checklist and final status

**Files:**
- Create: `docs/SUBMISSION.md`
- Modify: `CLAUDE.md` (Status, Ownership)

- [ ] **Step 1: Create `docs/SUBMISSION.md`** with exactly:

```markdown
# Submission checklist (Sun Oct 11)

- [ ] Repo https://github.com/ancientdev0x/aws-env is public; README shows live URL, screenshot, architecture.
- [ ] `AWS_PROFILE=baadh scripts/reset_demo_state.sh` run after the last test; live URL loads and shows 7 cut-off.
- [ ] Video (≤ 3 min) uploaded (YouTube unlisted / Drive with view access) — link: ____
- [ ] Blog published on AWS Builder Center from docs/BLOG.md (attach docs/architecture.png, docs/screenshot.png) — link: ____
- [ ] AWS Builder Center student profile verified.
- [ ] Submission form: project name BaadhDrishti, Track 02 Heat & Water, repo link, live link, video link, blog link,
      AWS services: S3, CloudFront, API Gateway, Lambda, DynamoDB, SAM, AWS Open Data (Sentinel-1).
- [ ] After judging: deactivate the `baadh-dev` access key in IAM; `sam delete --stack-name baadhdrishti` when no longer needed.
```

- [ ] **Step 2: Final CLAUDE.md update** — in Status, add after the Task 2.7/2.8 line:
```text
- [x] Docs (Sun): README (rules moved to docs/HACKATHON.md), docs/architecture.png, docs/VIDEO.md, docs/BLOG.md, docs/SUBMISSION.md.
  Demo hub: officer-nominated village-centre point from scripts/pick_demo_hub.py (OSM has too few rural public buildings).
```
and replace the Ownership "Next:" line with `Next: record video (docs/VIDEO.md), publish blog (docs/BLOG.md), submit (docs/SUBMISSION.md).`

- [ ] **Step 3: Final verification**

```bash
.venv/bin/python tests/test_reachability_engine.py | tail -1
.venv/bin/python tests/test_lambda_local.py | tail -1
.venv/bin/python tests/test_export_overlays.py | tail -1
URL=$(AWS_PROFILE=baadh aws cloudformation describe-stacks --region ap-south-1 --stack-name baadhdrishti --query "Stacks[0].Outputs[?OutputKey=='FrontendUrl'].OutputValue" --output text)
uv run --with playwright python tests/frontend_smoke.py "$URL/" | tail -1
AWS_PROFILE=baadh scripts/reset_demo_state.sh
git status --short
```
Expected: four `✓` lines, both tables `0 items`, and `git status` shows only `docs/screenshot.png` (re-rendered) or nothing. Commit the screenshot if changed.

- [ ] **Step 4: Commit**

```bash
git add docs/SUBMISSION.md CLAUDE.md docs/screenshot.png
git commit -m "docs: submission checklist and final status"
git push origin main
```

---

## Self-review (done while writing this plan)

- **Spec coverage:** overlays (Task 2) · frontend map/slider/toggles/urban/roads/habitations/hospitals/hubs/queue/filter/sort/
  modal/add-hub/diff toast/footer/config (Task 3) · WhatsApp + CSV (Task 3) · Lambda single compute, `destinations`,
  1769 MB (Task 1) · CloudFront + OAC + bucket policy + outputs + deploy script (Task 4) · README swap + architecture
  (Task 6) · VIDEO with checklist (Task 7) · BLOG (Task 8) · SUBMISSION (Task 9) · tests: engine, Lambda local,
  overlays, Playwright (Tasks 1–4, 9). Spec deviation, recorded in Task 5: the demo hub is an officer-nominated
  village-centre point, because OSM has no suitable rural public building near the cut-off cluster.
- **Verified before writing:** `scripts/export_overlays.py` (mask opaque fraction 0.126), the full `index.html` with
  `tests/frontend_smoke.py` read-only and `--write` against the live API, the template additions with
  `sam validate --lint`, `scripts/pick_demo_hub.py` output, `scripts/draw_architecture.py` render.
- **Names used across tasks:** `compute()`, `destinations[{id,name,type,lat,lon}]`, `frontend/data/overlays.json`
  keys `bounds/pre/post/mask/pre_date/post_date`, stack outputs `ApiUrl/FrontendUrl/FrontendBucketName/DistributionId`,
  DOM ids listed in Task 3 Interfaces.

## Execution handoff

Plan complete. Execute task by task in order 1 → 9 (Tasks 7–9 can run in parallel after Task 6). Recommended:
superpowers:subagent-driven-development (fresh subagent per task, review between tasks), or superpowers:executing-plans
inline with a checkpoint after Tasks 1, 3, 4 and 9.
