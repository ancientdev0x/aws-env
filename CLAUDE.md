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
- [ ] Fri GO/NO-GO: flood mask visually matches NRSC 5-Sep 2024 map in AOI
- [ ] Sat: Lambda API, DynamoDB, frontend, road edit + hub add
- [ ] Sun 12:00 IST feature freeze → video → AWS Builder Center blog → submit (exact deadline time TO VERIFY)

## Ownership
Handed over on Fri Oct 9 to a teammate who now owns the build end-to-end. Next task: PLAN.md Task 2.1
(fetch S1 AOI scenes) → Task 2.2 (flood mask) → Friday GO/NO-GO. Commit small, push often,
and keep the Status section above current.
