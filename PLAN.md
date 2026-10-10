# BaadhDrishti — Implementation Plan & Engineering Blueprint

**Project Name**: BaadhDrishti (Flood Reachability & Habitation Isolation Triage)  
**Hackathon**: Bharat Builds Tour — Event 02: Environmental Hacks (Oct 8–11, 2026)  
**Track**: Track 02 — Heat & Water  
**Working Directory**: repo root (all paths below are repo-relative)  
**GitHub Repo**: `https://github.com/ancientdev0x/aws-env`  
**Date**: Friday, Oct 9, 2026 (Day 2 of 4) — updated Sat Oct 10 after Tasks 2.1–2.4 (see CLAUDE.md Status)

---

## 0. Frozen Decisions & Scope Contract

1. **Case Study & Event**:
   - 31 August – 2 September 2024 Budameru / Krishna flood around Vijayawada, Andhra Pradesh.
   - Pre-event scene: `2024-08-20` (Sentinel-1A GRD)
   - Post-event scene: `2024-09-01` (Sentinel-1A GRD)
   - Source: AWS Open Data Element84 Earth Search (`sentinel-1-grd`, `s3://sentinel-s1-l1c/`, public no-sign-request).
2. **Area of Interest (AOI)**:
   - Peri-urban / rural flood corridors: Gollapudi (falls inside the GHSL urban core), Rayanapadu, Jakkampudi Colony, Ambapuram, Elaprolu, Velagaleru regulator downstream.
   - **Urban core explicitly excluded**: defined as **GHSL GHS-SMOD R2023A E2020 class 30 (urban centre)**, 70.4 km² inside the AOI (`data/processed/urban_core.geojson`). Displayed with an amber hatching overlay labeled: *"Urban core excluded due to radar double-bounce ambiguity (NRSC 6-Sep map also excludes urban areas)"*. Flood pixels inside it are ignored, its roads are treated as open/unknown, and its habitations are listed as out of scope.
3. **SAR Processing Strategy (Offline, Once)**:
   - **Plan A (implemented, GO)**: Same relative orbit check → windowed AOI read of raw DN via GCPs → **σ⁰ calibration + thermal-noise removal** from the annotation LUTs (not raw DN²) → GCP thin-plate-spline geocode to a 20 m UTM 44N grid → **250 m near-range geolocation shift** estimated against JRC permanent water (GCP heights ≠ terrain; no DEM terrain correction) → dB → $5 \times 5$ median → $\Delta \text{VV} < -3\text{dB}$ **and post VV < −14.01 dB** (p90 of post VV over JRC ≥ 90 % water) → exclude Copernicus DEM GLO-30 slope $> 5^\circ$ and JRC occurrence ≥ 50 % → drop components < 10 px → GeoJSON/GeoTIFF.
   - **Plan B (Fallback, not used)**: Microsoft Planetary Computer `sentinel-1-rtc` for the exact AOI bbox (coverage still TO VERIFY).
4. **Graph & Reachability Engine**:
   - Base graph: **current** OpenStreetMap via Overpass (osm_base 2026-10-10, not a 2024 snapshot). PMGSY not used.
   - Simplification splits edges wherever the `bridge` tag changes, so only the bridge segment itself is exempt from auto-disruption.
   - **Habitations source**: OpenStreetMap `place=village|hamlet|suburb|neighbourhood` nodes.
   - **Destinations**: OSM `amenity=hospital` / `healthcare=hospital|centre` / named PHC-CHC clinics (veterinary excluded) + officer staging hubs.
   - **Population source**: Voronoi cell of each habitation (clipped to AOI) intersected with GHSL GHS-POP R2023A (100m).
   - **Bridge handling rule**: OSM `bridge=yes` edges must NOT be auto-disrupted. Tag them with uncertainty flag `CHECK`.
   - **Reachability logic**: `effective_blocked = (auto_suspected - force_cleared) | force_blocked`. Single `nx.multi_source_dijkstra` call finds nearest destinations and distances for all reachable nodes.
   - **Blocking edges**: blocked edges on the habitation's dry-baseline shortest route to its nearest destination (one extra multi-source Dijkstra on the unblocked graph).
   - **Baseline guard**: habitations with no path even with zero flooding are flagged `NO_BASELINE_PATH` and not counted as cut off.
   - **Status & Ranking hierarchy**:
     - `INUNDATED`: Habitation point itself falls inside candidate flood mask.
     - `NO_MAPPED_ROAD_PATH`: Habitation is not inundated, but all mapped road routes to destinations are disrupted.
     - `PATH_EXISTS`: Active mapped road route exists to at least one hospital or staging hub.
     - **Ranking hierarchy**: `INUNDATED` > `NO_MAPPED_ROAD_PATH` > `PATH_EXISTS`, sorted within each status group by population descending.
5. **Product Claim Boundary**:
   - **What it is**: *"Post-acquisition field-verification triage queue"* for disaster response officers.
   - **What it is NOT**: NOT a live flood forecast, NOT a rescue dispatch engine, NOT a vehicle turn-by-turn navigation system, NOT a damage valuation tool.
6. **Strict Truthfulness / No Hallucinated Metrics Rule**:
   - **Video/UI me sirf script-computed ya cited numbers aayenge.**
   - All wireframes, mock data schemas, documentation, and video scripts must use `<computed>` or `<officer_name>` placeholders. Never invent arbitrary counts (e.g. population numbers, habitation totals, or synthetic latency benchmarks). Cited numbers must come from official reports (e.g., "4,388 km R&B roads damaged (APSDMA)").

---

## 1. Day 2 (Friday) GO/NO-GO Gate (Target: 21:00 IST)

The hard gate for Friday night: **AOI me hamara flood mask NRSC map se visually match kare. Uske baad jitne bhi habitations cut-off niklen, wahi honestly report karo.**

> **Result (Fri night): GO.** No "5-Sep" NRSC map was found; the reference used is APSAC/NRSC **6-Sep 2024** *Flood Inundation Areas Surrounding Vijayawada* (pre: Sentinel-1A 20-Aug, post: TerraSAR-X 6-Sep, urban areas not analysed): https://apsac.ap.gov.in/wp-content/uploads/2024/09/AP_TERRASARX_6_sep_2024_sat_map.pdf . The Elaprolu–Kavuluru–Rayanapadu–Jakkampudi–Ambapuram block and the eastward band north of the city match; our 1-Sep mask is somewhat larger (expected recession by 6-Sep). Comparison image: `docs/gonogo_flood_mask_quicklook.png`.

### Exact Verification Commands & Steps:

#### Step 1.1: Verify S1 Scene Pair in Earth Search STAC
```bash
python3 -c "
import urllib.request, json
url = 'https://earth-search.aws.element84.com/v1/collections/sentinel-1-grd/items?bbox=80.45,16.45,80.75,16.65&datetime=2024-08-19T00:00:00Z/2024-09-02T23:59:59Z'
req = urllib.request.Request(url, headers={'User-Agent': 'BaadhDrishti/1.0'})
res = urllib.request.urlopen(req)
items = json.loads(res.read())['features']
print(f'Found {len(items)} scenes')
for it in items:
    props = it['properties']
    print(it['id'], props.get('datetime'), 'Orbit:', props.get('sat:relative_orbit'), 'Pass:', props.get('sat:orbit_state'))
"
```
*Pass Criteria*: Both `2024-08-20` and `2024-09-01` scenes must share the same `sat:orbit_state` (e.g. Descending) and relative orbit number for valid change detection.

#### Step 1.2: Download AOI Sub-window or Calibrated Slices
Download bounding box `[80.50, 16.50, 80.70, 16.65]` using GDAL/rasterio vsis3 or Planetary Computer fallback.

#### Step 1.3: Generate Candidate Flood Mask (`scripts/generate_flood_mask.py`)
- Apply dB difference threshold $\Delta \text{dB} = \text{dB}_{\text{post}} - \text{dB}_{\text{pre}} < -3.0$.
- Mask out slope $> 5^\circ$ using Copernicus DEM GLO-30.
- Mask out permanent water bodies.
- Vectorize to `data/processed/flood_mask_20240901.geojson`.

#### Step 1.4: Build Road Graph & Reachability Check (`scripts/build_reachability.py`)
- Extract OSM drivable highways (`motorway`, `trunk`, `primary`, `secondary`, `tertiary`, `unclassified`, `residential`).
- Build NetworkX `Graph` (or `MultiDiGraph`).
- Spatial intersect edges with `flood_mask_20240901.geojson` buffered by 25m (excluding `bridge=yes` edges, which get tagged `CHECK`).
- Run baseline connectivity vs remaining connectivity using `evaluate_reachability`.
- *Pass Criteria*: AOI me hamara flood mask NRSC 6-Sep 2024 map se visually match kare. Uske baad jitne bhi habitations cut-off niklen, wahi honestly report karo (output in `data/processed/triage_summary.json`).

---

## 2. Data Contracts & Schemas

### 2.1 Candidate Flood Mask (`data/processed/flood_mask_20240901.geojson`, WGS84 lon/lat)
Produced by `scripts/generate_flood_mask.py`. Also written as a 20 m GeoTIFF (`flood_mask_20240901.tif`, EPSG:32644).
```json
{
  "type": "FeatureCollection",
  "metadata": {
    "event": "Vijayawada Budameru Flood",
    "pre_scene": "S1A_IW_GRDH_1SDV_20240820T003107_20240820T003132_055289_06BD9B",
    "post_scene": "S1A_IW_GRDH_1SDV_20240901T003107_20240901T003132_055464_06C415",
    "detection_method": "Calibrated sigma0 VV, 5x5 median, delta dB < -3.0 and post VV < <computed> dB ...",
    "geolocation": "GCP TPS geocode + <computed> m near-range shift estimated vs JRC GSW ...",
    "resolution_m": 20.0,
    "status": "candidate observed inundation - not ground verified",
    "stats": { "candidate_area_sqkm": "<computed>", "polygons": "<computed>", "...": "exclusion fractions" }
  },
  "features": [
    {
      "type": "Feature",
      "properties": {
        "area_sqm": "<computed>",
        "delta_db_mean": "<computed>",
        "vh_agree_frac": "<computed>"
      },
      "geometry": { "type": "Polygon", "coordinates": ["..."] }
    }
  ]
}
```
`vh_agree_frac` = share of polygon pixels where VH also drops below −3 dB (QA signal; replaces the earlier undefined `confidence` tier).

### 2.2 Habitation & Triage Record (`data/processed/triage_summary.json`)
Produced by `scripts/build_reachability.py`.
- **Habitation Definition**: OpenStreetMap `place=village|hamlet|suburb|neighbourhood` nodes within AOI, snapped to the nearest road node (`snap_distance_m`; > 500 m adds `FAR_FROM_ROAD`).
- **Population Source**: GHSL GHS-POP R2023A E2020 100 m pixels assigned to the nearest habitation (= Voronoi cell), clipped to AOI.
- **Status Hierarchy**:
  - `INUNDATED`: Habitation point itself falls inside candidate flood mask. (Current output: none — village points sit on built-up pixels, which are bright in SAR.)
  - `NO_MAPPED_ROAD_PATH`: Habitation point not inundated, but all mapped road routes to destinations are disrupted.
  - `PATH_EXISTS`: Active mapped road route exists to at least one hospital or staging hub.
- **Ranking Hierarchy**: `INUNDATED` > `NO_MAPPED_ROAD_PATH` > `PATH_EXISTS`, sorted within each status group by population descending.
- **Out of scope** (listed under `out_of_scope` with `excluded_reason`): `URBAN_CORE_EXCLUDED`, `NO_BASELINE_PATH`.
- **Bridge Handling Rule**: OSM `bridge=yes` edges must NOT be auto-disrupted. Tag them with uncertainty flag `CHECK`.

Top level: `event, aoi, total_habitations, in_scope_habitations, out_of_scope_habitations, inundated_count,
no_mapped_road_path_count, cut_off_count, cut_off_population_proxy, aoi_population_ghsl_e2020, destinations, road_edges,
auto_suspected_edges, bridge_check_edges, urban_core_area_sqkm, caveats[], habitations[], out_of_scope[]`.

```json
{
  "id": "hab_node_<osm_id>",
  "name": "<habitation name>",
  "place": "village",
  "lat": "<computed>",
  "lon": "<computed>",
  "snap_distance_m": "<computed>",
  "population_proxy": "<computed>",
  "population_source": "GHSL GHS-POP R2023A E2020 100m (Voronoi cell of habitation, clipped to AOI)",
  "in_urban_core": false,
  "status": "NO_MAPPED_ROAD_PATH",
  "baseline_distance_km": "<computed>",
  "nearest_destination": null,
  "blocking_edges": ["osm_way_<way>_<u>_<v>"],
  "is_inundated": false,
  "uncertainty_flags": []
}
```
When `PATH_EXISTS`, `nearest_destination` = `{ "id", "name", "type": "HOSPITAL" | "HEALTH_CENTRE" | "STAGING_HUB", "distance_km" }`.
The UI derives the action text from `status` (e.g. "Field-verify road access"); it is not stored.

Supporting files for Lambda/frontend: `road_edges.geojson` (edge_id, u, v, weight km, is_bridge, highway, name),
`road_nodes.json` ({node: [lon, lat]}), `habitations.json`, `destinations.json`, `suspected_edges.json`
(`auto_suspected`, `bridge_check`), `urban_core.geojson`.

### 2.3 Road Status Override (`road_overrides` DynamoDB Table)
*Partition Key*: `edge_id` (String)  
*Attributes*:
- `override_status`: `"FORCE_CLEARED"` | `"FORCE_BLOCKED"` | `"AUTO_SUSPECTED"`
- `notes`: `"Local police confirms flyover ramp is elevated & motorable"`
- `officer_id`: `"<officer_name>"`
- `updated_at`: 1728471200

### 2.4 Staging Hubs Config (`staging_hubs` DynamoDB Table)
*Partition Key*: `hub_id` (String)  
*Attributes*:
- `name`: `"Indira Gandhi Municipal Stadium Relief Camp"`
- `lat`: 16.5075
- `lon`: 80.6486
- `type`: `"STAGING_HUB"` (engine destination type; same value as the engine test)
- `hub_kind`: `"RELIEF_CAMP"` | `"NDRF_BASE"` | `"DISTRICT_COLLECTORATE"` | `"SCHOOL"` (display only)
- `is_active`: true

---

## 3. Reachability Algorithm & Executable Assertion Test

### 3.1 Algorithm Pseudo-code
```text
Algorithm EvaluateHabitationReachability:
Input:
  GraphEdges E = [ {u, v, weight, edge_id, is_bridge} ]
  Habitations H = [ {id, name, node, population_proxy, ...} ]
  Destinations D = [ {id, name, node, type, ...} ]
  SuspectedEdges S_auto [Edges overlapping candidate flood buffer]
  Overrides O: ForceCleared F_clear, ForceBlocked F_block
  InundatedHabitations H_inundated [Habitations whose points fall inside flood mask]

1. Bridge Handling & Effective Blocked Calculation:
   BridgeEdges = { edge_id for edge in E if edge.is_bridge == True or edge.bridge == "yes" }
   For each edge in E where edge_id in BridgeEdges and edge_id in S_auto:
     edge.uncertainty_flag = "CHECK"
   AutoBlocked = S_auto \ BridgeEdges  // OSM bridge=yes edges must NOT be auto-disrupted
   EffectiveBlocked = (AutoBlocked \ F_clear) U F_block

2. Construct Active Graph G_active:
   G_active = Graph()
   For edge in E:
     If edge.edge_id not in EffectiveBlocked:
       G_active.add_edge(edge.u, edge.v, weight=edge.weight)

3. Multi-Source Dijkstra (Single Call):
   ValidDestNodes = { d.node for d in D if d.node in G_active }
   If ValidDestNodes is not empty:
     (Distances, Paths) = nx.multi_source_dijkstra(G_active, ValidDestNodes, target=None, weight="weight")
   Else:
     Distances = {}, Paths = {}

4. Habitation Classification:
   For hab in H:
     If hab.id in H_inundated:
       hab.status = "INUNDATED"
     Else if hab.node in Distances:
       hab.status = "PATH_EXISTS"
       hab.nearest_destination = { id, name, type, distance_km: Distances[hab.node] }
     Else:
       hab.status = "NO_MAPPED_ROAD_PATH"
       hab.nearest_destination = None
     If hab.status != "PATH_EXISTS":
       // BaselinePaths = multi_source_dijkstra on the full (unblocked) graph
       hab.blocking_edges = [e on BaselinePaths[hab.node] if every parallel edge of that segment is in EffectiveBlocked]

5. Sorting Hierarchy:
   Sort H by:
     Primary: Status order (INUNDATED: 0, NO_MAPPED_ROAD_PATH: 1, PATH_EXISTS: 2)
     Secondary: population_proxy descending
```

### 3.2 Standalone Python Test (abridged — full version in `tests/test_reachability_engine.py`)
```python
from engine.reachability import evaluate_reachability

def test_reachability_lifecycle():
    graph_edges = [
        {"u": "A", "v": "J", "weight": 2.0, "edge_id": "e1"},
        {"u": "J", "v": "H", "weight": 3.0, "edge_id": "e2"},
        {"u": "J", "v": "N", "weight": 5.0, "edge_id": "e3"},
        {"u": "B", "v": "J", "weight": 1.0, "edge_id": "e4"},
    ]
    hab_a = {"id": "Village_A", "name": "Village A", "node": "A", "population_proxy": 2000}
    hab_b = {"id": "Village_B", "name": "Village B", "node": "B", "population_proxy": 5000}
    dest_hospital = [{"id": "Hospital_H", "name": "Hospital H", "node": "H", "type": "HOSPITAL"}]

    # 1. Baseline open -> PATH_EXISTS to nearest hospital
    r1 = evaluate_reachability(graph_edges, [hab_a], dest_hospital, auto_suspected_edges=set())
    assert r1[0]["status"] == "PATH_EXISTS"
    assert r1[0]["nearest_destination"]["id"] == "Hospital_H"

    # 2. Auto-suspected flood blocks edge -> NO_MAPPED_ROAD_PATH
    r2 = evaluate_reachability(graph_edges, [hab_a], dest_hospital, auto_suspected_edges={"e2"})
    assert r2[0]["status"] == "NO_MAPPED_ROAD_PATH"
    assert r2[0]["blocking_edges"] == ["e2"]  # blocked edge on the dry-baseline route A-J-H

    # 3. Officer adds new Staging Hub -> PATH_EXISTS to new hub
    dest_with_hub = dest_hospital + [{"id": "Relief_Hub_N", "name": "Relief Hub N", "node": "N", "type": "STAGING_HUB"}]
    r3 = evaluate_reachability(graph_edges, [hab_a], dest_with_hub, auto_suspected_edges={"e2"})
    assert r3[0]["status"] == "PATH_EXISTS"
    assert r3[0]["nearest_destination"]["id"] == "Relief_Hub_N"

    # 4. Real FORCE_CLEARED override restores PATH_EXISTS
    r4 = evaluate_reachability(graph_edges, [hab_a], dest_hospital, auto_suspected_edges={"e2"}, force_cleared_edges={"e2"})
    assert r4[0]["status"] == "PATH_EXISTS"

    # 5. Real FORCE_BLOCKED override triggers NO_MAPPED_ROAD_PATH
    r5 = evaluate_reachability(graph_edges, [hab_a], dest_hospital, auto_suspected_edges=set(), force_blocked_edges={"e2"})
    assert r5[0]["status"] == "NO_MAPPED_ROAD_PATH"

    # 6. INUNDATED status ranks #1 above other cut-off habitations
    r6 = evaluate_reachability(graph_edges, [hab_a, hab_b], dest_hospital, auto_suspected_edges={"e2"}, inundated_habitations={"Village_A"})
    assert r6[0]["id"] == "Village_A" and r6[0]["status"] == "INUNDATED"
    assert r6[1]["id"] == "Village_B" and r6[1]["status"] == "NO_MAPPED_ROAD_PATH"

    # 7. Bridge handling: bridge=yes edges NOT auto-disrupted; tagged CHECK
    bridge_edges = [
        {"u": "A", "v": "J", "weight": 2.0, "edge_id": "e1"},
        {"u": "J", "v": "H", "weight": 3.0, "edge_id": "e_bridge", "is_bridge": True},
    ]
    r7 = evaluate_reachability(bridge_edges, [hab_a], dest_hospital, auto_suspected_edges={"e_bridge"})
    assert r7[0]["status"] == "PATH_EXISTS"
    assert any(e.get("uncertainty_flag") == "CHECK" for e in bridge_edges if e["edge_id"] == "e_bridge")

    print("✓ All Reachability Engine assertions passed!")

if __name__ == "__main__":
    test_reachability_lifecycle()
```

---

## 4. API Specification

Deployed via API Gateway + single AWS Lambda (`lambda_function.py`) with bundled NetworkX.

### 4.1 `GET /api/triage`
- **Description**: Returns full triage queue sorted by isolation status and population, along with active overrides and hubs.
- **Response `200 OK`**:
```json
{
  "event": "Vijayawada Budameru Flood (2024-09-01 Replay)",
  "total_habitations": "<computed>",
  "cut_off_count": "<computed>",
  "cut_off_population_proxy": "<computed>",
  "habitations": [ /* array of habitation records */ ],
  "active_staging_hubs": [ /* array of active hubs */ ],
  "disrupted_edges": [ /* geojson features for map display */ ]
}
```

### 4.2 `POST /api/road-status`
- **Description**: Officer marks a road edge as `FORCE_CLEARED` (e.g., boat ferry or elevated culvert verified) or `FORCE_BLOCKED`.
- **Request Body**:
```json
{
  "edge_id": "osm_way_<way>_<u>_<v>",
  "status": "FORCE_CLEARED",
  "notes": "Police outpost reports single-lane tractor traffic passable",
  "officer_name": "<officer_name>"
}
```
- **Response `200 OK`**: Recomputes graph in memory (<computed> ms) and returns updated stats and diff.
- Note: clearing the reported `blocking_edges` may expose further blocked edges on the next-best route; the recompute reports them.

### 4.3 `POST /api/hubs`
- **Description**: Officer designates a new school/stadium as an active staging hub.
- **Request Body**:
```json
{
  "name": "<school name> Relief Base",
  "lat": "<lat of an actual dry school, TO VERIFY>",
  "lon": "<lon>",
  "type": "STAGING_HUB",
  "hub_kind": "SCHOOL"
}
```
- **Response `201 Created`**: Snaps to nearest road node, re-evaluates reachability, returns updated queue.

---

## 5. UI Architecture & ASCII Wireframe

Single responsive web interface built with a clean single `index.html` + Leaflet.js (hosted on S3 / CloudFront or local web server). Pre/post SAR PNG overlays will be generated offline and rendered via Leaflet `imageOverlay`.

> [!IMPORTANT]
> **Video/UI me sirf script-computed ya cited numbers aayenge.** No placeholder numbers are hardcoded.

```
+---------------------------------------------------------------------------------------------------+
|  BAADHDRISHTI (बाढ़-दृष्टि)  |  Vijayawada Budameru Floods (1 Sep 2024 Replay)   |  [AWS Open Data] |
+---------------------------------------------------------------------------------------------------+
|  [ STATS BAR ]                                                                                    |
|  Total Habitations: <computed>  |  Cut-off (No Road): <computed>  |  Isolated Pop: <computed>     |
+---------------------------------------------------+-----------------------------------------------+
|  MAP VIEW (Leaflet)                               |  FIELD-VERIFICATION PRIORITY QUEUE            |
|                                                   |                                               |
|  [ Layer Toggle: Before / After / Water Mask ]    |  Filter: [X] Show Only Cut-Off  Sort: [Pop v] |
|  +---------------------------------------------+  |  -------------------------------------------  |
|  |                 [Velagaleru Regulator]      |  |  #1. <HAB> (Pop: <computed>) [NO ROAD PATH]   |
|  |                     \                       |  |      Blocking: <road name> (<computed> segs)  |
|  |      [<habitation>]  \===[Water Mask===]    |  |      Nearest Hosp: <facility> (Unreachable)   |
|  |         (RED PIN)     \   (candidate)       |  |      Action: [Mark Verified] [Clear Road]     |
|  |                        \                    |  |  -------------------------------------------  |
|  |  ============[Disrupted Road (RED)]======== |  |  #2. <HAB> (Pop: <computed>) [NO ROAD PATH]   |
|  |           |                                 |  |      Blocking: <road name>                    |
|  |      [<facility>]                           |  |      Action: [Mark Verified] [Clear Road]     |
|  |         (GREEN)                             |  |  -------------------------------------------  |
|  |                                             |  |  #3. <HAB> (Pop: <computed>) [PATH EXISTS]    |
|  |  [AMBER ZONE: Urban Core Excluded - Radar]   |  |      Route open to <facility> (<computed> km) |
|  +---------------------------------------------+  |  -------------------------------------------  |
|  [SLIDER: 20 Aug Baseline <==========> 1 Sep]     |  [+ Add Staging Hub]  [Share WhatsApp Report] |
+---------------------------------------------------+-----------------------------------------------+
|  CAVEATS & PROVENANCE: Sentinel-1A GRD | GHSL GHS-POP R2023A (100m) | OpenStreetMap (current)     |
|  DISCLAIMER: Preliminary screening triage queue based on mapped roads. NOT official rescue orders. |
+---------------------------------------------------------------------------------------------------+
```

---

## 6. Execution Timeline & Task Manifest

### Friday, Oct 9 – Saturday morning (Data Pipeline & Graph Core) — DONE
- [x] **Task 2.1**: `scripts/fetch_s1_aoi.py` → `data/raw/{20240820,20240901}/{vv,vh}_dn.tif` + calibration/noise XMLs. Both scenes S1A, relative orbit 92, descending (STAC-verified).
- [x] **Task 2.2**: `scripts/generate_flood_mask.py` → `data/processed/flood_mask_20240901.{geojson,tif}` (method in §0.3); `scripts/quicklook_flood.py` → GO/NO-GO image.
- [x] **Task 2.3**: `scripts/build_road_graph.py` → `data/processed/road_edges.geojson`, `road_nodes.json`, `road_graph.graphml` (gitignored).
- [x] **Task 2.4**: `scripts/build_reachability.py` → `data/processed/triage_summary.json` (+ Lambda/frontend inputs); engine tests pass.

**Reproduce the offline pipeline** (Python 3.12, from repo root):
```bash
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r scripts/requirements-offline.txt
.venv/bin/python scripts/fetch_s1_aoi.py          # ~40 s, S1 AOI windows (AWS Open Data, no-sign-request)
.venv/bin/python scripts/generate_flood_mask.py   # ~40 s, needs JRC GSW + COP-DEM (read remotely)
.venv/bin/python scripts/build_road_graph.py      # fetches Overpass with curl if data/raw/osm/roads_aoi.osm missing
# places/health/GHSL inputs are fetched manually today: data/raw/osm/{places_aoi,health_aoi}.json,
# data/raw/ghsl/{pop,smod}_R7_C26.zip (GHSL R2023A E2020 tiles) — see CLAUDE.md
.venv/bin/python scripts/build_reachability.py
.venv/bin/python tests/test_reachability_engine.py
```

### Saturday, Oct 10 (AWS Backend, Frontend & Interactivity)
- [x] **Task 2.5**: Set up DynamoDB tables (`road_overrides`, `staging_hubs`) and SAM template.  
  *Done Criteria*: `sam build && sam deploy` creates stack with live API Gateway URL.
- [x] **Task 2.6**: Lambda implementation of reachability engine reading from S3 graph + DynamoDB overrides.  
  *Done Criteria*: `curl $API_URL/api/triage` returns JSON with status code 200.
- [ ] **Task 2.7**: Build clean single `index.html` + Leaflet.js frontend with offline pre/post SAR PNG overlays (Leaflet `imageOverlay`), triage queue table, road override modal, and hub addition.  
  *Done Criteria*: Frontend deployed to S3 website / CloudFront or local host with responsive UI.
- [ ] **Task 2.8**: WhatsApp share generator button (`wa.me/?text=...`) + CSV download verification.  
  *Done Criteria*: WhatsApp link formats top cut-off habitations cleanly into clipboard/URL.

### Sunday, Oct 11 (Feature Freeze, Video & Submission)
> [!IMPORTANT]
> **Submission deadline ka exact time verify karna hai (TO VERIFY).**

- [ ] **12:00 IST**: **Strict Feature Freeze** (Zero new features, only bug fixes).
- [ ] **12:00 – 15:00 IST**: Record 3-minute demo video following exact script.
- [ ] **15:00 – 17:00 IST**: Draft & publish technical blog post on AWS Builder Center (eligible for AirPods 5 prize!).
- [ ] **17:00 – 19:00 IST**: Submit project on hackathon portal (Luma/WeMakeDevs) with demo video URL, GitHub repo, and live deployment link.

---

## 7. 3-Minute Demo Video Script (Shot-by-Shot)

| Timestamp | Screen Visual | Spoken Voiceover (High Energy, Confident) |
|---|---|---|
| **0:00 – 0:30** (Problem) | News headlines of Vijayawada 2024 Budameru flood; APSDMA statistics (12.8L affected, 4,388 km R&B roads damaged — **citations TO VERIFY before recording**). | *"In September 2024, the Budameru rivulet breached into Vijayawada [35,000 cusecs — TO VERIFY], cutting rural clusters off from emergency care. Control rooms faced a question: which villages have lost every mapped road to a hospital, and where should field teams verify first?"* |
| **0:30 – 1:15** (Data & SAR) | BaadhDrishti UI opens. Slider moves from 20-Aug dry baseline to 1-Sep flood radar mask. Urban amber hatching visible. | *"Meet BaadhDrishti. Powered by AWS Open Data, we ingest Copernicus Sentinel-1 Synthetic Aperture Radar. Because radar penetrates clouds, we run automated change detection. We deliberately exclude the dense urban core to avoid false positives from radar double-bounce, isolating real open-water inundation across peri-urban corridors."* |
| **1:15 – 2:00** (Reachability & Triage) | Zoom into road network: intersecting roads turn red. Triage table populates on right. | *"Instead of just showing a blue flood map, BaadhDrishti converts the OpenStreetMap road network into a graph. <computed> peri-urban habitations have no mapped road path left to any hospital. <top-ranked habitation>, with a GHSL population estimate of <computed>, tops the verification queue."* (Use values from `triage_summary.json` at feature freeze. Current script output: 7 habitations, top-ranked Tadepalle. Do NOT say Rayanapadu — it is PATH_EXISTS in our output.) |
| **2:00 – 2:30** (Interactivity & Action) | Officer clicks 'Clear Road' on a reported blocking edge, then adds a dry school (real OSM location, TO VERIFY) as a staging hub. Table updates instantly. | *"Disaster response is human-in-the-loop. A field scout calls in: tractor traffic can pass via an elevated embankment. The officer marks the segment 'Cleared'—or designates a new dry high school as a staging hub. Our AWS Lambda engine recomputes reachability in <computed> ms, restoring connectivity and updating the relief dispatch queue instantly."* |
| **2:30 – 3:00** (Architecture & AWS Fit) | Clean AWS Architecture slide (S3 + Lambda + DynamoDB + CloudFront + AWS Open Data) + honest disclaimer footer. | *"Architected on AWS: Sentinel-1 data directly from AWS Open Data S3, reachability analysis on serverless AWS Lambda, and persistent state in DynamoDB. BaadhDrishti doesn't replace official warnings or ground checks—it gives relief officers an uncertainty-aware verification queue from each Sentinel-1 acquisition."* |

---

## 8. Risks, Traps & Fallbacks

| Risk | Probability | Impact | Mitigation / Fallback |
|---|---|---|---|
| **S1 raw DN calibration too complex in 24h** | ~~Medium~~ Resolved | High | Calibration + noise removal implemented from annotation LUTs; Plan B not needed. |
| **SAR geolocation offset (no terrain correction)** | Happened | High | ~250 m range offset found; corrected with a JRC-estimated near-range shift; independent OSM-water check residual ≤ 20 m. |
| **Bridge segments merged into long road edges** | Happened | High | Fixed with `edge_attrs_differ=["bridge"]`; without it every cut-off was hidden. |
| **Current OSM ≠ 2024 network** (e.g. Vijayawada West Bypass) | Medium | Medium | Caveat in UI; West Bypass Sep-2024 status TO VERIFY. |
| **Overpass unreachable from Python (IPv4)** | Happened | Low | Fetch with curl (IPv6) and cache raw OSM under `data/raw/osm/`. |
| **PMGSY GeoSadak portal API slow/down** | n/a | — | PMGSY dropped; OSM only. |
| **Lambda deployment package size exceeds 250MB (GDAL/NetworkX)** | Low | High | Pre-compute flood mask vectors offline; Lambda only loads NetworkX graph + GeoJSON metadata. NetworkX is pure Python, minimal footprint (<15MB). |
| **Time Crunch on Saturday Night** | Medium | Medium | **Feature Cut List**: Drop manual road editing modal; keep read-only interactive map + triage table + precomputed CSV export. The video story remains 100% intact. |

---

## 9. Decisions Log

1. **SAR source**: Plan A (raw GRD on AWS Open Data, calibrated) — GO. Plan B kept as fallback only.
2. **Road network**: current OpenStreetMap via Overpass; PMGSY not used.
3. **AWS stack**: S3 + CloudFront (single index.html + Leaflet) + API Gateway HTTP API/Lambda (Python/NetworkX) + DynamoDB, SAM deploy, region ap-south-1 (deployed Sat Oct 10).
4. **Urban core**: GHSL SMOD class 30 urban centre (owner approved Sat Oct 10).
5. **GO/NO-GO reference**: APSAC/NRSC 6-Sep 2024 TerraSAR-X map (no 5-Sep map found).
