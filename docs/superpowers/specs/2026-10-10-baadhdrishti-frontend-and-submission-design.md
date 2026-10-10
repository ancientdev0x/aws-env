# BaadhDrishti — Frontend, Share/CSV, Polish & Submission Design

Date: 2026-10-10 (Sat). Target: everything done today. Scope: all remaining PLAN.md features (Tasks 2.7, 2.8) plus the
backend/infra changes they need, project docs, video and blog material, and the submission checklist.

Read first: `CLAUDE.md` (hard rules, status, verified facts), `PLAN.md` §4 (API) and §5 (wireframe).

## Context (already done — do not redo)

- Offline pipeline (Tasks 2.1–2.4) → `data/processed/*` (flood mask, road graph, triage). Reproduce steps: PLAN.md §6.
- SAM stack `baadhdrishti` in **ap-south-1**, AWS CLI profile **`baadh`** (never the default `medmitra-bedrock` profile).
  HTTP API `https://f3m0jdk4wi.execute-api.ap-south-1.amazonaws.com` with `GET /api/triage`, `POST /api/road-status`,
  `POST /api/hubs`; Lambda `backend/app.py`; DynamoDB `baadhdrishti-road_overrides`, `baadhdrishti-staging_hubs`;
  data bundle `s3://<DataBucketName>/lambda_bundle.json`.
- Computed output today: 7 habitations NO_MAPPED_ROAD_PATH (Tadepalle, Paidurupadu, Elaprolu, Vemavaram, Jakkampudi,
  Kotturu, Shabada), population proxy 9,314; clearing Tadepalle's 4 blocking edges restores 5 habitations.

## Hard rules that constrain this design

- No made-up numbers: UI shows only API values; video/blog use only script/API output or cited figures (citations TO VERIFY).
- Stack: S3 + CloudFront, single `index.html` + Leaflet, API Gateway + one Lambda, DynamoDB, SAM. No Next.js, Cognito,
  OpenSearch, SQS, SNS, Step Functions, LocalStack, ML.
- Urban core labelled as excluded; bridges get CHECK, never auto-disrupted; status order INUNDATED > NO_MAPPED_ROAD_PATH >
  PATH_EXISTS then population.
- Product is a field-verification triage queue — wording must never say rescue dispatch / navigation / forecast.
- Never commit credentials (`aws.json` is gitignored). No Claude co-author trailers in commits.

## Approach

Single static `frontend/index.html` (vanilla JS, Leaflet 1.9 from CDN, inline CSS) on a private S3 bucket behind
CloudFront (Origin Access Control), added to the **same SAM stack**. Rejected: Amplify Hosting (extra service, manual
console wiring), serving HTML from Lambda (weak architecture story).

## Components

### 1. Offline overlays — `scripts/export_overlays.py` (new)
- Inputs: `data/interim/20240820_vv_db.tif`, `data/interim/20240901_vv_db.tif`, `data/processed/flood_mask_20240901.tif`.
- Reproject each to EPSG:4326 over the AOI `[80.50, 16.50, 80.70, 16.65]` (same `to_ll` logic as `scripts/quicklook_flood.py`).
- Write `data/processed/web/pre_vv.png`, `post_vv.png` (grayscale, dB stretched −22..0, nodata transparent),
  `flood_mask.png` (blue RGBA, transparent where not flood), and `overlays.json`
  `{ "bounds": [[16.50, 80.50], [16.65, 80.70]], "pre": "pre_vv.png", "post": "post_vv.png", "mask": "flood_mask.png",
  "pre_date": "2024-08-20", "post_date": "2024-09-01" }`.
- Copy `data/processed/urban_core.geojson` into `data/processed/web/`.
- Leaflet `imageOverlay` with lat/lon bounds over Web Mercator: distortion across 0.15° latitude is negligible.

### 2. Frontend — `frontend/index.html` (new, single file)
Layout follows PLAN.md §5:
- **Header**: "BaadhDrishti (बाढ़-दृष्टि) — Vijayawada Budameru Flood, 1 Sep 2024 replay", AWS Open Data badge.
- **Stats bar** (from API): in-scope habitations, cut off, cut-off population proxy, last recompute `compute_ms`.
- **Map** (left, Leaflet):
  - OSM tile basemap (attribution required).
  - SAR before/after: both PNG overlays stacked; a range slider crossfades opacity (0 = 20 Aug, 100 = 1 Sep).
  - Toggles: water mask, urban core, disrupted roads, hospitals.
  - Urban core: amber dashed outline + hatch fill (SVG pattern or `fillOpacity` + dashArray), tooltip
    "Urban core excluded due to radar double-bounce ambiguity".
  - Disrupted roads from `disrupted_edges`: red = AUTO_SUSPECTED & blocked, orange = CHECK (bridge), green = FORCE_CLEARED,
    purple = FORCE_BLOCKED. Click → popup: road name/highway, status, buttons Clear / Block / Reset to auto.
  - Habitation markers (circle): red = NO_MAPPED_ROAD_PATH, dark red = INUNDATED, green = PATH_EXISTS, grey = out of scope.
  - Hospitals (small blue), staging hubs (star). Destinations are not in the triage response today → see §3.
- **Queue** (right): filter "Show only cut-off", sort Status (default, matches engine order) or Population.
  Row = rank, name, population proxy, status badge, blocking road names (deduped `blocking_roads[].name`, "unnamed road"
  if null), nearest destination + distance when PATH_EXISTS, baseline distance, flags. Buttons: Zoom, Clear blocking roads,
  Mark verified (UI-only highlight, not persisted).
- **Officer modal** for every write: officer name (remembered in `localStorage`), notes. Sends `POST /api/road-status`.
  "Clear blocking roads" posts FORCE_CLEARED for each `blocking_edges` id sequentially, then refreshes.
- **Add Hub mode**: button toggles crosshair; map click opens modal (name, kind: SCHOOL | RELIEF_CAMP | NDRF_BASE |
  DISTRICT_COLLECTORATE) → `POST /api/hubs`. Show API 400 messages (outside AOI / too far from road) inline.
- **Diff toast**: frontend keeps the previous response; after each write it lists habitations whose status changed
  ("Restored: Tadepalle, Vemavaram, …" / "Newly cut off: …").
- **Share (Task 2.8)**: WhatsApp button builds `https://wa.me/?text=` + URL-encoded text: title, timestamp, top cut-off
  rows (rank, name, status, population proxy, blocking road), disclaimer line, page URL. CSV button: client-side Blob of
  the in-scope queue (id, name, status, population_proxy, baseline_distance_km, nearest_destination, distance_km,
  blocking roads, flags).
- **Footer**: `caveats[]` from API + fixed disclaimer "Preliminary screening triage queue based on mapped roads. NOT
  official rescue orders." + provenance (Sentinel-1A GRD via AWS Open Data, GHSL GHS-POP R2023A, OpenStreetMap
  contributors, NRSC 6-Sep reference link).
- **Config**: fetch `config.json` (`{ "apiUrl": "..." }`) at load. Loading and error states for every fetch.
- Accessibility basics: buttons are `<button>`, colour is never the only status signal (badge text), readable at 1366×768.

### 3. Backend/infra changes
- `backend/app.py`:
  - Remove the "before" `compute()` in `road_status` and `add_hub`; drop server-side `diff` (frontend diffs). Halves POST latency.
  - Add `"destinations"` (id, name, type, lat, lon of OSM health facilities) to the triage response so the map can draw
    hospitals from a single source (the bundle). Hubs stay in `active_staging_hubs`.
- `template.yaml`:
  - Lambda `MemorySize: 1769` (one full vCPU) to cut `compute_ms`.
  - `FrontendBucket` (private, public access blocked), `AWS::CloudFront::OriginAccessControl`, `AWS::CloudFront::Distribution`
    (default root `index.html`, HTTPS redirect, managed CachingOptimized policy), bucket policy allowing only the distribution.
  - Output `FrontendUrl` and `FrontendBucketName`, `DistributionId`.
- `scripts/deploy_frontend.sh` (new): reads stack outputs with `AWS_PROFILE=baadh`, writes `frontend/config.json`
  (gitignored), `aws s3 sync frontend/` + `data/processed/web/` → `s3://<FrontendBucket>/` (`data/` prefix for web files),
  then `aws cloudfront create-invalidation --paths "/*"`.
- CORS stays `*` (no auth by design; throttling already set).

### 4. Docs & submission
- **README swap (owner decision, default yes)**: move current hackathon-rules `README.md` → `docs/HACKATHON.md`
  (update the reference in `CLAUDE.md`), write a project `README.md`: one-paragraph problem, live URL, screenshot,
  architecture diagram, how it works (pipeline → graph → Lambda), what it is NOT, caveats, reproduce + deploy commands,
  data credits/licences (Copernicus Sentinel data, JRC GSW, Copernicus DEM, GHSL CC BY 4.0, OSM ODbL).
- `docs/architecture.png`: generated by a small matplotlib script `scripts/draw_architecture.py` (boxes: AWS Open Data S3
  Sentinel-1 → offline Python pipeline → S3 data bucket → Lambda (NetworkX) ↔ DynamoDB; CloudFront + S3 index.html →
  API Gateway → Lambda). No new dependencies.
- `docs/VIDEO.md`: 3-minute shot list from PLAN.md §7 with values filled from the live API at feature freeze, plus a
  recording checklist (run `scripts/reset_demo_state.sh`, warm the Lambda, steps to click, which road to clear,
  which school to add as hub — location TO VERIFY from OSM `amenity=school` outside flood mask).
- `docs/BLOG.md`: AWS Builder Center draft — problem, what it does, stack, "what fought back" (raw DN calibration, 250 m
  geolocation shift, bridge-merge bug hiding every cut-off, Overpass IPv4, urban double-bounce), honest limits, links.
- Owner does: record/voice video, publish blog, submit form (owner decision: confirmed by default).
- Submission checklist in `docs/SUBMISSION.md`: repo public, live URL works after reset, video link, blog link,
  Builder Center student profile, AWS services list.

### 5. Testing & verification
- `tests/test_lambda_local.py`: update for removed server diff and new `destinations` field; keep offline-parity assertion.
- `tests/test_reachability_engine.py` unchanged and passing.
- After `sam deploy`: curl smoke (GET 200 and cut_off_count == offline; clear/undo; hub add then delete via CLI;
  `scripts/reset_demo_state.sh`).
- Frontend: open CloudFront URL in a headless browser, screenshot, exercise Clear blocking roads and Add Hub; console
  must be error-free. Reset state afterwards.

## Out of scope (YAGNI)
Auth, hub delete endpoint (reset script covers demo), live ingestion, multiple events, mobile-specific layout, i18n,
persisting "Mark verified".

## Open items (TO VERIFY, do not assert in video/blog until checked)
- Vijayawada West Bypass open in Sep 2024 (current OSM may include a road that did not exist then).
- APSDMA "12.8L affected", "4,388 km R&B roads damaged", Budameru "35,000 cusecs" citations.
- Demo hub school location (real OSM school, outside flood mask, near a cut-off cluster).
