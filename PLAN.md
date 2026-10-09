# BaadhDrishti — Implementation Plan & Engineering Blueprint

**Project Name**: BaadhDrishti (Flood Reachability & Habitation Isolation Triage)  
**Hackathon**: Bharat Builds Tour — Event 02: Environmental Hacks (Oct 8–11, 2026)  
**Track**: Track 02 — Heat & Water  
**Working Directory**: `/home/ancientai/Projects/serious/aws-env`  
**GitHub Repo**: `https://github.com/ancientdev0x/aws-env`  
**Date**: Friday, Oct 9, 2026 (Day 2 of 4)

---

## 0. Frozen Decisions & Scope Contract

1. **Case Study & Event**:
   - 31 August – 2 September 2024 Budameru / Krishna flood around Vijayawada, Andhra Pradesh.
   - Pre-event scene: `2024-08-20` (Sentinel-1A GRD)
   - Post-event scene: `2024-09-01` (Sentinel-1A GRD)
   - Source: AWS Open Data Element84 Earth Search (`sentinel-1-grd`, `s3://sentinel-s1-l1c/`, public no-sign-request).
2. **Area of Interest (AOI)**:
   - Peri-urban / rural flood corridors: Gollapudi, Rayanapadu, Jakkampudi Colony, Ambapuram, Elaprolu, Velagaleru regulator downstream.
   - **Urban core explicitly excluded**: Displayed with an amber hatching overlay on map labeled: *"Urban core excluded due to radar double-bounce ambiguity (NRSC 5-Sep reference standard)"*.
3. **SAR Processing Strategy (Offline, Once)**:
   - **Plan A**: Same relative orbit check → windowed AOI read → $10 \log_{10}(\text{DN}^2)$ → $5 \times 5$ median speckle filter → $\Delta \text{dB} < -3\text{dB}$ → JRC permanent water mask + Copernicus DEM 30m slope $> 5^\circ$ mask → rasterio/gdalwarp geocode → candidate water mask GeoJSON/COG.
   - **Plan B (Fallback)**: If Plan A noisy/misaligned by Friday 21:00, use Microsoft Planetary Computer `sentinel-1-rtc` pre-processed calibrated backscatter for the exact AOI bbox.
4. **Graph & Reachability Engine**:
   - Base graph: OpenStreetMap (Geofabrik AP extract) + PMGSY GeoSadak rural habitation connectors.
   - **Habitations source**: OpenStreetMap `place=village|hamlet|suburb|neighbourhood` nodes.
   - **Population source**: Voronoi cell of each habitation (clipped to AOI) intersected with GHSL GHS-POP R2023A (100m).
   - **Bridge handling rule**: OSM `bridge=yes` edges must NOT be auto-disrupted. Tag them with uncertainty flag `CHECK`.
   - **Reachability logic**: `effective_blocked = (auto_suspected - force_cleared) | force_blocked`. Single `nx.multi_source_dijkstra` call finds nearest destinations and distances for all reachable nodes.
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

The hard gate for Friday night: **AOI me hamara flood mask NRSC 5-Sep 2024 map se visually match kare. Uske baad jitne bhi habitations cut-off niklen, wahi honestly report karo.**

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
- *Pass Criteria*: AOI me hamara flood mask NRSC 5-Sep 2024 map se visually match kare. Uske baad jitne bhi habitations cut-off niklen, wahi honestly report karo (output in `data/processed/triage_summary.json`).

---

## 2. Data Contracts & Schemas

### 2.1 Candidate Flood Mask (`flood_mask.geojson`)
```json
{
  "type": "FeatureCollection",
  "crs": { "type": "name", "properties": { "name": "urn:ogc:def:crs:OGC:1.3:CRS84" } },
  "metadata": {
    "event": "Vijayawada Budameru Flood",
    "pre_scene": "S1A_IW_GRDH_..._20240820",
    "post_scene": "S1A_IW_GRDH_..._20240901",
    "detection_method": "Dual-pol dB difference < -3.0 with slope exclusion",
    "resolution_m": 20
  },
  "features": [
    {
      "type": "Feature",
      "properties": {
        "confidence": "A_HIGH",
        "area_sqm": "<computed>",
        "delta_db_mean": -4.2
      },
      "geometry": { "type": "Polygon", "coordinates": [[[80.582, 16.541], "..."]] }
    }
  ]
}
```

### 2.2 Habitation & Triage Record (`triage_summary.json`)
- **Habitation Definition**: OpenStreetMap `place=village|hamlet|suburb|neighbourhood` nodes within AOI.
- **Population Source**: Voronoi cell of each habitation (clipped to AOI) intersected with GHSL GHS-POP R2023A (100m).
- **Status Hierarchy**:
  - `INUNDATED`: Habitation point itself falls inside candidate flood mask.
  - `NO_MAPPED_ROAD_PATH`: Habitation point not inundated, but all mapped road routes to destinations are disrupted.
  - `PATH_EXISTS`: Active mapped road route exists to at least one hospital or staging hub.
- **Ranking Hierarchy**: `INUNDATED` > `NO_MAPPED_ROAD_PATH` > `PATH_EXISTS`, sorted within each status group by population descending.
- **Bridge Handling Rule**: OSM `bridge=yes` edges must NOT be auto-disrupted. Tag them with uncertainty flag `CHECK`.

```json
[
  {
    "id": "hab_rayanapadu_01",
    "name": "Rayanapadu Village",
    "lat": 16.5624,
    "lon": 80.5512,
    "population_proxy": "<computed>",
    "population_source": "GHSL GHS-POP R2023A (100m Voronoi cell clipped to AOI)",
    "status": "INUNDATED",
    "baseline_distance_km": "<computed>",
    "nearest_destination": {
      "id": "hosp_gollapudi_phc",
      "name": "Gollapudi Primary Health Centre",
      "type": "HOSPITAL",
      "distance_km": "<computed>"
    },
    "blocking_edges": [
      "osm_way_9841203"
    ],
    "uncertainty_flags": ["CHECK", "peri_urban_edge"],
    "action_required": "Dispatch boat/drone verification team"
  }
]
```

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
- `type`: `"RELIEF_CAMP"` | `"NDRF_BASE"` | `"DISTRICT_COLLECTORATE"`
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

5. Sorting Hierarchy:
   Sort H by:
     Primary: Status order (INUNDATED: 0, NO_MAPPED_ROAD_PATH: 1, PATH_EXISTS: 2)
     Secondary: population_proxy descending
```

### 3.2 Standalone Python Test (`tests/test_reachability_engine.py`)
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
  "edge_id": "osm_way_9841203",
  "status": "FORCE_CLEARED",
  "notes": "Police outpost reports single-lane tractor traffic passable",
  "officer_name": "<officer_name>"
}
```
- **Response `200 OK`**: Recomputes graph in memory (<computed> ms) and returns updated stats and diff.

### 4.3 `POST /api/hubs`
- **Description**: Officer designates a new school/stadium as an active staging hub.
- **Request Body**:
```json
{
  "name": "Kavuluru ZP High School Relief Base",
  "lat": 16.5812,
  "lon": 80.5290,
  "type": "STAGING_BASE"
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
|  |                 [Velagaleru Regulator]      |  |  #1. RAYANAPADU (Pop: <computed>) [INUNDATED] |
|  |                     \                       |  |      Blocking: Link Rd (<computed> m wet)     |
|  |       [Rayanapadu]   \===[Water Mask===]    |  |      Nearest Hosp: Gollapudi PHC (Unreachable)|
|  |         (RED PIN)     \   (A-Tier)          |  |      Action: [Verify Boat] [Clear Road]       |
|  |                        \                    |  |  -------------------------------------------  |
|  |  ============[Disrupted Road (RED)]======== |  |  #2. JAKKAMPUDI (<computed>) [NO ROAD PATH]   |
|  |           |                                 |  |      Blocking: Inner Ring Rd Culvert          |
|  |      [Gollapudi PHC]                        |  |      Action: [Verify Boat] [Clear Road]       |
|  |         (GREEN)                             |  |  -------------------------------------------  |
|  |                                             |  |  #3. AMBAPURAM (Pop: <computed>) [PATH EXISTS]|
|  |  [AMBER ZONE: Urban Core Excluded - Radar]   |  |      Route open to Gollapudi PHC (<computed>) |
|  +---------------------------------------------+  |  -------------------------------------------  |
|  [SLIDER: 20 Aug Baseline <==========> 1 Sep]     |  [+ Add Staging Hub]  [Share WhatsApp Report] |
+---------------------------------------------------+-----------------------------------------------+
|  CAVEATS & PROVENANCE: Sentinel-1A GRD | GHSL GHS-POP R2023A (100m) | OpenStreetMap Network       |
|  DISCLAIMER: Preliminary screening triage queue based on mapped roads. NOT official rescue orders. |
+---------------------------------------------------------------------------------------------------+
```

---

## 6. Execution Timeline & Task Manifest

### Friday, Oct 9 (Data Pipeline & Graph Core)
- [ ] **Task 2.1**: Download/Extract S1 GRD bounding box for Vijayawada (20 Aug & 1 Sep) via Element84 / PC.  
  *Done Criteria*: Two `.tif` files in `data/raw/` covering `[80.50, 16.50, 80.70, 16.65]`.
- [ ] **Task 2.2**: Run change detection script (`dB < -3`, slope mask $>5^\circ$).  
  *Done Criteria*: `data/processed/flood_mask.geojson` generated with $>0$ flood polygons.
- [ ] **Task 2.3**: Download OSM road network for Vijayawada AOI via OSMnx / Geofabrik.  
  *Done Criteria*: `data/processed/road_graph.graphml` saved with highway tags.
- [ ] **Task 2.4**: Spatial intersection & reachability test execution.  
  *Done Criteria*: Run `python3 tests/test_reachability_engine.py` passes; `triage_summary.json` generated.

### Saturday, Oct 10 (AWS Backend, Frontend & Interactivity)
- [ ] **Task 2.5**: Set up DynamoDB tables (`road_overrides`, `staging_hubs`) and SAM template.  
  *Done Criteria*: `sam build && sam deploy` creates stack with live API Gateway URL.
- [ ] **Task 2.6**: Lambda implementation of reachability engine reading from S3 graph + DynamoDB overrides.  
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
| **0:00 – 0:30** (Problem) | News headlines of Vijayawada 2024 Budameru flood; APSDMA statistics (12.8L affected, 4,388 km R&B roads damaged (APSDMA)). | *"In September 2024, the Budameru rivulet breached carrying 35,000 cusecs into Vijayawada, severing entire rural clusters from emergency care. Disaster control rooms faced a critical question: Which villages have lost 100% of their road access right now, and where must boats be dispatched first?"* |
| **0:30 – 1:15** (Data & SAR) | BaadhDrishti UI opens. Slider moves from 20-Aug dry baseline to 1-Sep flood radar mask. Urban amber hatching visible. | *"Meet BaadhDrishti. Powered by AWS Open Data, we ingest Copernicus Sentinel-1 Synthetic Aperture Radar. Because radar penetrates clouds, we run automated change detection. We deliberately exclude the dense urban core to avoid false positives from radar double-bounce, isolating real open-water inundation across peri-urban corridors."* |
| **1:15 – 2:00** (Reachability & Triage) | Zoom into road network: intersecting roads turn red. Triage table populates on right. | *"Instead of just showing a blue flood map, BaadhDrishti converts OpenStreetMap and PMGSY road networks into a dynamic topology graph. <computed> habitations immediately trigger triage alerts ('INUNDATED' or 'NO MAPPED ROAD PATH'). Rayanapadu, home to <computed> residents, has its access road submerged. It jumps to Rank #1 on our verification queue."* |
| **2:00 – 2:30** (Interactivity & Action) | Officer clicks 'Clear Road' on an elevated culvert, then adds 'Kavuluru High School' as a staging hub. Table updates instantly. | *"Disaster response is human-in-the-loop. A field scout calls in: tractor traffic can pass via an elevated embankment. The officer marks the segment 'Cleared'—or designates a new dry high school as a staging hub. Our AWS Lambda engine recomputes reachability in <computed> ms, restoring connectivity and updating the relief dispatch queue instantly."* |
| **2:30 – 3:00** (Architecture & AWS Fit) | Clean AWS Architecture slide (S3 + Lambda + DynamoDB + CloudFront + AWS Open Data) + honest disclaimer footer. | *"Architected on AWS: Sentinel-1 data directly from AWS Open Data S3, reachability analysis on serverless AWS Lambda, and persistent state in DynamoDB. BaadhDrishti doesn't replace official warnings—it arms relief officers with actionable, uncertainty-aware triage within hours of satellite acquisition."* |

---

## 8. Risks, Traps & Fallbacks

| Risk | Probability | Impact | Mitigation / Fallback |
|---|---|---|---|
| **S1 raw DN calibration too complex in 24h** | Medium | High | **Plan B activated immediately**: Use Microsoft Planetary Computer `sentinel-1-rtc` or pre-calibrated S1 COG slice for the Vijayawada bbox. |
| **PMGSY GeoSadak portal API slow/down** | High | Medium | Use Geofabrik Andhra Pradesh OSM extract (`.osm.pbf`) filtered for drivable highways (`highway=*`). OSM coverage in Vijayawada peri-urban is dense. |
| **Lambda deployment package size exceeds 250MB (GDAL/NetworkX)** | Low | High | Pre-compute flood mask vectors offline; Lambda only loads NetworkX graph + GeoJSON metadata. NetworkX is pure Python, minimal footprint (<15MB). |
| **Time Crunch on Saturday Night** | Medium | Medium | **Feature Cut List**: Drop manual road editing modal; keep read-only interactive map + triage table + precomputed CSV export. The video story remains 100% intact. |

---

## 9. Top 3 Decisions for User Confirmation

1. **SAR Data Source Approval**: Can we lock **Plan B (Planetary Computer S1-RTC pre-calibrated backscatter)** as our primary backup if raw AWS S3 ESA GRD calibration has projection hiccups by Friday 20:00?
2. **Road Network Source**: Confirming that **OpenStreetMap (Geofabrik AP extract)** will be the primary road layer, supplemented by PMGSY only if trivially downloadable.
3. **AWS Deployment Stack**: Confirming serverless stack: **AWS S3 + CloudFront (Frontend: single index.html + Leaflet.js) + API Gateway/Lambda (Python/NetworkX) + DynamoDB**. No OpenSearch, no heavy VPC.
