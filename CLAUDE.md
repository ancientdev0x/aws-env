# BaadhDrishti — team context for Claude

Hackathon: Bharat Builds Tour Event 02 — Environmental Hacks (Oct 8–11, 2026). Rules + judging: `README.md`.
Judges only see a 3-min recorded video. "One feature that works beats five that almost do."

## What we are building (FROZEN — do not re-debate)
Post-flood **field-verification triage queue** (Heat & Water track). Replay of the Vijayawada Budameru flood:
Sentinel-1 pre (2024-08-20) / post (2024-09-01) change detection → candidate flood mask → OSM road graph →
which habitations have NO MAPPED ROAD PATH to a hospital / officer-nominated staging hub → ranked table.
Officer can mark a road cleared/blocked or add a hub, and the queue recomputes.

It is NOT: a rescue dispatch system, navigation, a live forecast, or an official damage assessment.

## Read these
- `PLAN.md` — the implementation plan, schemas, API, timeline, video script. Source of truth.
- `RESEARCH_BAADH.md` — data sources, method, competitors (Copernicus GFM, NRSC/Bhuvan, UNOSAT).
- `engine/reachability.py` + `tests/test_reachability_engine.py` — core engine; run `python3 tests/test_reachability_engine.py`.
- `RESEARCH_IDEAS.md`, `RESEARCH_V2.md` — older idea rounds; background only.

## Hard rules
- **No made-up numbers.** UI, video and blog use only script-computed values or cited figures. Use `<computed>` placeholders until real output exists.
- Heavy SAR/GIS processing is **offline** (scripts → files in S3). Lambda only loads the precomputed graph and runs NetworkX.
- Stack: S3 + CloudFront/Amplify (single `index.html` + Leaflet), API Gateway + one Python Lambda, DynamoDB (`road_overrides`, `staging_hubs`). SAM for deploy.
- Do NOT add: OpenSearch, Cedar, Cognito, LocalStack, SQS, Step Functions, SNS, Next.js, ML models, live ingestion.
- Dense urban core is excluded (radar double-bounce) and labelled so in the UI.
- OSM `bridge=yes` edges are never auto-disrupted; they get a `CHECK` flag.
- Status order: `INUNDATED` > `NO_MAPPED_ROAD_PATH` > `PATH_EXISTS`, then population descending.
- Population: GHSL GHS-POP R2023A E2020 100m (not WorldPop — URL 404). Destinations: OSM hospitals/PHCs + officer hubs; OSM `amenity=shelter` is NOT a relief camp.
- Never commit API keys / AWS credentials.

## Data facts already verified
- `s3://sentinel-s1-l1c` works with `--no-sign-request`; measurement TIFFs are raw DN with calibration XMLs alongside.
- Scene search: Earth Search STAC `https://earth-search.aws.element84.com/v1`, collection `sentinel-1-grd`.
- Fallback if raw DN pipeline fails: Microsoft Planetary Computer `sentinel-1-rtc` (coverage still TO VERIFY).
- OSMnx edge lengths are meters; engine reports `distance_km` — convert when building the graph.

## Status (update this section as you go)
- [x] Research, plan, reachability engine + tests
- [x] Task 2.1 (Fri): `scripts/fetch_s1_aoi.py` → `data/raw/{20240820,20240901}/` (VV+VH raw DN AOI windows, ~2400×2800 px,
  210 GCPs each, calibration + noise XMLs). STAC-verified: both S1A, relative orbit 92, descending, VV/VH.
  (2024-09-08 S1A is orbit 27 ascending — not comparable.) Setup: `uv venv --python 3.12 .venv` + `scripts/requirements-offline.txt`.
- [x] Task 2.2 (Fri): `scripts/generate_flood_mask.py` → `data/processed/flood_mask_20240901.{geojson,tif}`.
  Method: sigma0 calibration + thermal-noise removal → GCP TPS geocode (20 m, EPSG:32644) → 5×5 median →
  ΔVV < −3 dB **AND post VV < −14.01 dB** (added rule: p90 of post VV over JRC ≥90% water; removes most crop/wet-soil
  false positives south of Krishna) → exclude slope > 5° (COP-DEM GLO-30) and JRC occurrence ≥ 50% → min 10 px.
  Script output: 44.93 km² candidate, 432 polygons (pre-urban-exclusion).
  **Geolocation fix:** GCP heights (~90–150 m) ≠ terrain, so geocoded SAR was offset ~250 m toward far range.
  Script estimates a near-range shift against JRC water (best 250 m, IoU 0.418 → 0.535) and applies it to both dates
  (pre↔post phase correlation = 0,0 px). No DEM terrain correction — residual error TO VERIFY against OSM roads.
- [~] Fri GO/NO-GO: compared `docs/gonogo_flood_mask_quicklook.png` with APSAC/NRSC **6-Sep** TerraSAR-X map
  (`AP_TERRASARX_6_sep_2024_sat_map.pdf`; no "5-Sep" NRSC map found). Main Elaprolu–Kavuluru–Rayanapadu–Jakkampudi–
  Ambapuram block and eastward band north of the city match. Mask is somewhat larger (1-Sep vs 6-Sep recession expected).
  Assessment: **GO** (pending owner confirmation). Plan B not needed so far.
- [x] Task 2.3 (Sat): `scripts/build_road_graph.py` → `data/processed/road_edges.geojson` (engine format: edge_id, u, v,
  weight in **km**, is_bridge, highway, name) + `road_graph.graphml` (gitignored, 18 MB, reproducible).
  Script output: 19,287 nodes, 26,343 undirected edges (unique IDs `osm_way_<way>_<u>_<v>[_k]`), 266 bridge edges, 2,276.5 km.
  Simplification splits edges where `bridge` changes (`edge_attrs_differ`) — otherwise a short bridge merged into a 4 km
  road made the whole road exempt from flooding (this bug hid every cut-off). Long bridges left are real flyovers / the
  Vijayawada West Bypass Krishna bridge — **whether West Bypass was open in Sep 2024 is TO VERIFY** (current OSM).
  Also writes `road_nodes.json` ({node: [lon, lat]}) for snapping.
  Classes: PLAN list + `*_link`. Raw OSM via curl → `data/raw/osm/roads_aoi.osm` (Python requests hangs on overpass-api.de
  over IPv4 here; curl uses IPv6). **OSM is current (osm_base 2026-10-10), not a 2024 snapshot** — caveat for UI.
  Independent geolocation check vs OSM water polygons: residual best fit ≤ 1 px (20 m) east of current alignment.
- [x] Task 2.4 (Sat): `scripts/build_reachability.py` → `data/processed/triage_summary.json` (+ habitations.json,
  destinations.json, suspected_edges.json, urban_core.geojson). Script output (computed, OK to quote with caveats):
  130 OSM habitations; 90 inside urban core (out of scope), 40 in scope; **7 NO_MAPPED_ROAD_PATH** — Tadepalle,
  Paidurupadu, Elaprolu, Vemavaram, Jakkampudi, Kotturu, Shabada — population proxy 9,314; 0 INUNDATED (village points
  are built-up = bright in SAR, so the point test never fires; known SAR limitation). 689 auto-suspected edges,
  29 bridge CHECK edges, 301 health destinations ("pet clinic" excluded), urban core 70.4 km².
  Morphological closing was tested (3/5/7 px) and rejected: 5+ only added Amaravati-side villages where NRSC shows no flood.
  Engine fix: `blocking_edges` now = blocked edges on the habitation's dry-baseline route (was incident-only → empty).
  Clearing them can expose further blocked edges on the next-best route (recompute handles it).
- [x] Urban core = GHSL SMOD R2023A E2020 class 30 (owner OK'd option (a), Sat). Its roads are treated as open/unknown.
- [ ] Sat: Lambda API, DynamoDB, frontend, road edit + hub add
- [ ] Sun 12:00 IST feature freeze → video → AWS Builder Center blog → submit (exact deadline time TO VERIFY)

## Ownership
Handed over on Fri Oct 9 to a teammate who now owns the build end-to-end. Next task: PLAN.md Task 2.1
(fetch S1 AOI scenes) → Task 2.2 (flood mask) → Friday GO/NO-GO. Commit small, push often,
and keep the Status section above current.
