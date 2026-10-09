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
   - Intersect road edges with buffered candidate water polygon ($25\text{m}$ buffer).
   - Flag intersecting edges as `SUSPECTED_DISRUPTED`.
   - Multi-source reachability: Check if each habitation has an active path in remaining graph to any mapped Hospital/PHC or designated Staging Hub (Collectorate, NDRF Camp).
5. **Product Claim Boundary**:
   - **What it is**: *"Post-acquisition field-verification triage queue"* for disaster response officers.
   - **What it is NOT**: NOT a live flood forecast, NOT a rescue dispatch engine, NOT a vehicle turn-by-turn navigation system, NOT a damage valuation tool.

---

## 1. Day 2 (Friday) GO/NO-GO Gate (Target: 21:00 IST)

The hard gate for Friday night: **A working Jupyter notebook / standalone Python script rendering candidate flood polygons overlaid on the road network, showing at least 3 disconnected habitations in Vijayawada.**

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
- Build NetworkX `MultiDiGraph`.
- Spatial intersect edges with `flood_mask_20240901.geojson` buffered by 25m.
- Run baseline connectivity vs remaining connectivity.
- *Pass Criteria*: Output `data/processed/triage_summary.json` with habitations clearly flagged `NO_MAPPED_ROAD_PATH`.

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
        "area_sqm": 45200,
        "delta_db_mean": -4.2
      },
      "geometry": { "type": "Polygon", "coordinates": [[[80.582, 16.541], "..."]] }
    }
  ]
}
```

### 2.2 Habitation & Triage Record (`triage_summary.json`)
```json
[
  {
    "id": "hab_rayanapadu_01",
    "name": "Rayanapadu Village",
    "lat": 16.5624,
    "lon": 80.5512,
    "population_proxy": 4200,
    "population_source": "GHSL_2020_100m",
    "status": "NO_MAPPED_ROAD_PATH",
    "baseline_distance_km": 6.4,
    "nearest_destination": {
      "id": "hosp_gollapudi_phc",
      "name": "Gollapudi Primary Health Centre",
      "type": "HOSPITAL",
      "baseline_dist_km": 3.8,
      "current_dist_km": null
    },
    "blocking_edges": [
      {
        "edge_id": "osm_way_9841203",
        "name": "Rayanapadu Access Road",
        "water_intersection_m": 140,
        "coords": [[80.556, 16.558], [80.558, 16.559]]
      }
    ],
    "uncertainty_flags": ["peri_urban_edge", "single_culvert_dependence"],
    "action_required": "Dispatch boat/drone verification team"
  }
]
```

### 2.3 Road Status Override (`road_overrides` DynamoDB Table)
*Partition Key*: `edge_id` (String)  
*Attributes*:
- `override_status`: `"FORCE_CLEARED"` | `"FORCE_BLOCKED"` | `"AUTO_SUSPECTED"`
- `notes`: `"Local police confirms flyover ramp is elevated & motorable"`
- `officer_id`: `"officer_ntr_04"`
- `updated_at`: `1728471200`

### 2.4 Staging Hubs Config (`staging_hubs` DynamoDB Table)
*Partition Key*: `hub_id` (String)  
*Attributes*:
- `name`: `"Indira Gandhi Municipal Stadium Relief Camp"`
- `lat`: 16.5075
- `lon`: 80.6486
- `type`: `"RELIEF_CAMP"` | `"NDRF_BASE"` | `"DISTRICT_COLLECTORATE"`
- `is_active`: `true`

---

## 3. Reachability Algorithm & Executable Assertion Test

### 3.1 Algorithm Pseudo-code
```text
Algorithm EvaluateHabitationReachability:
Input:
  Graph G = (V, E) [Nodes: road junctions; Edges: road segments with length]
  Habitations H = { (id, node_v, pop) }
  Destinations D = { (id, node_d, type) } [Hospitals + Active Staging Hubs]
  SuspectedEdges S_auto [Edges overlapping flood buffer]
  Overrides O [Manual FORCE_CLEARED or FORCE_BLOCKED from DynamoDB]

1. Construct Active Graph G_active:
   E_active = (E \ S_auto)
   For each (edge_e, status) in O:
     if status == FORCE_CLEARED: E_active = E_active U {edge_e}
     if status == FORCE_BLOCKED: E_active = E_active \ {edge_e}
   G_active = (V, E_active)

2. Multi-Target Shortest Path:
   Add auxiliary super-sink node TARGET_SINK
   For each node_d in D:
     Add directed edge (node_d -> TARGET_SINK, weight=0)

3. For each habitation h in H:
   path_exists = nx.has_path(G_active, h.node_v, TARGET_SINK)
   if path_exists:
     h.status = "PATH_EXISTS"
     h.nearest_dest = nx.shortest_path(G_active, h.node_v, TARGET_SINK)[-2]
   else:
     h.status = "NO_MAPPED_ROAD_PATH"
     h.nearest_dest = None

4. Sort H by:
   Primary: status == "NO_MAPPED_ROAD_PATH" (descending)
   Secondary: population_proxy (descending)
```

### 3.2 Standalone Python Test (`tests/test_reachability_engine.py`)
```python
import networkx as nx

def evaluate_reachability(nodes, edges, habitations, destinations, blocked_edges):
    G = nx.Graph()
    for u, v, w, eid in edges:
        if eid not in blocked_edges:
            G.add_edge(u, v, weight=w, edge_id=eid)
    
    results = {}
    for hab_id, hab_node in habitations.items():
        connected_dest = None
        min_dist = float('inf')
        for dest_id, dest_node in destinations.items():
            if dest_node in G and nx.has_path(G, hab_node, dest_node):
                d = nx.shortest_path_length(G, hab_node, dest_node, weight='weight')
                if d < min_dist:
                    min_dist = d
                    connected_dest = dest_id
        
        results[hab_id] = {
            "status": "PATH_EXISTS" if connected_dest else "NO_MAPPED_ROAD_PATH",
            "nearest": connected_dest,
            "dist": min_dist if connected_dest else None
        }
    return results

def test_reachability_lifecycle():
    # Toy graph: Habitation A connected via Edge 1 to Junction J, Junction J connected via Edge 2 to Hospital H
    # Alternative path: Junction J connected via Edge 3 to North Hub N
    nodes = ["A", "J", "H", "N"]
    edges = [
        ("A", "J", 2.0, "e1"), # Road from Village A to Junction J
        ("J", "H", 3.0, "e2"), # Road from Junction J to Hospital H
        ("J", "N", 5.0, "e3"), # Rural road from Junction J to North Hub N
    ]
    habitations = {"Village_A": "A"}
    destinations = {"Hospital_H": "H"}

    # 1. Baseline: All roads open
    r1 = evaluate_reachability(nodes, edges, habitations, destinations, blocked_edges=set())
    assert r1["Village_A"]["status"] == "PATH_EXISTS"
    assert r1["Village_A"]["nearest"] == "Hospital_H"

    # 2. Flood cuts Edge 2 (J -> H)
    r2 = evaluate_reachability(nodes, edges, habitations, destinations, blocked_edges={"e2"})
    assert r2["Village_A"]["status"] == "NO_MAPPED_ROAD_PATH"
    assert r2["Village_A"]["nearest"] is None

    # 3. Officer adds North Hub N as an active Staging Base
    destinations_with_hub = {"Hospital_H": "H", "Relief_Hub_N": "N"}
    r3 = evaluate_reachability(nodes, edges, habitations, destinations_with_hub, blocked_edges={"e2"})
    assert r3["Village_A"]["status"] == "PATH_EXISTS"
    assert r3["Village_A"]["nearest"] == "Relief_Hub_N"

    # 4. Officer confirms Edge 2 is actually an elevated bridge (Force Clear e2)
    r4 = evaluate_reachability(nodes, edges, habitations, destinations, blocked_edges=set())
    assert r4["Village_A"]["status"] == "PATH_EXISTS"
    assert r4["Village_A"]["nearest"] == "Hospital_H"

    print("✓ All Reachability Lifecycle assertions passed!")

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
  "total_habitations": 48,
  "cut_off_count": 14,
  "cut_off_population_proxy": 58400,
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
  "officer_name": "R. Sharma (Sub-Collector)"
}
```
- **Response `200 OK`**: Recomputes graph in memory (<50ms) and returns updated stats and diff.

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

Single responsive web interface built with Next.js/Tailwind (or vanilla React + Leaflet) deployed on AWS Amplify / S3 + CloudFront.

```
+---------------------------------------------------------------------------------------------------+
|  BAADHDRISHTI (बाढ़-दृष्टि)  |  Vijayawada Budameru Floods (1 Sep 2024 Replay)   |  [AWS Open Data] |
+---------------------------------------------------------------------------------------------------+
|  [ STATS BAR ]                                                                                    |
|  Total Habitations: 48  |  Cut-off (No Mapped Road): 14  |  Est. Isolated Pop: 58,400  [Export CSV] |
+---------------------------------------------------+-----------------------------------------------+
|  MAP VIEW (Leaflet / MapLibre)                    |  FIELD-VERIFICATION PRIORITY QUEUE            |
|                                                   |                                               |
|  [ Layer Toggle: Before / After / Water Mask ]    |  Filter: [X] Show Only Cut-Off  Sort: [Pop v] |
|  +---------------------------------------------+  |  -------------------------------------------  |
|  |                 [Velagaleru Regulator]      |  |  #1. RAYANAPADU (Pop: 4,200)   [NO ROAD PATH] |
|  |                     \                       |  |      Blocking: Rayanapadu Link Rd (140m wet)  |
|  |       [Rayanapadu]   \===[Water Mask===]    |  |      Nearest Hosp: Gollapudi PHC (Unreachable)|
|  |         (RED PIN)     \   (A-Tier)          |  |      Action: [Verify Boat] [Clear Road]       |
|  |                        \                    |  |  -------------------------------------------  |
|  |  ============[Disrupted Road (RED)]======== |  |  #2. JAKKAMPUDI COLONY (3,800) [NO ROAD PATH] |
|  |           |                                 |  |      Blocking: Inner Ring Rd Culvert          |
|  |      [Gollapudi PHC]                        |  |      Action: [Verify Boat] [Clear Road]       |
|  |         (GREEN)                             |  |  -------------------------------------------  |
|  |                                             |  |  #3. AMBAPURAM (Pop: 2,100)    [PATH EXISTS]  |
|  |  [AMBER ZONE: Urban Core Excluded - Radar]   |  |      Route open to Gollapudi PHC (4.2 km)     |
|  +---------------------------------------------+  |  -------------------------------------------  |
|  [SLIDER: 20 Aug Baseline <==========> 1 Sep]     |  [+ Add Staging Hub]  [Share WhatsApp Report] |
+---------------------------------------------------+-----------------------------------------------+
|  CAVEATS & PROVENANCE: Sentinel-1A GRD (12-day revisit) | GHSL 2020 Pop | OpenStreetMap Network   |
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
  *Done Criteria*: Run `pytest tests/test_reachability_engine.py` passes; `triage_summary.json` generated.

### Saturday, Oct 10 (AWS Backend, Frontend & Interactivity)
- [ ] **Task 2.5**: Set up DynamoDB tables (`road_overrides`, `staging_hubs`) and SAM template.  
  *Done Criteria*: `sam build && sam deploy` creates stack with live API Gateway URL.
- [ ] **Task 2.6**: Lambda implementation of reachability engine reading from S3 graph + DynamoDB overrides.  
  *Done Criteria*: `curl $API_URL/api/triage` returns JSON with status code 200.
- [ ] **Task 2.7**: Build Next.js / Leaflet frontend with side-by-side / overlay slider, triage table, road override modal, and hub addition.  
  *Done Criteria*: Frontend deployed to Amplify / S3 website with live public HTTPS URL.
- [ ] **Task 2.8**: WhatsApp share generator button (`wa.me/?text=...`) + CSV download verification.  
  *Done Criteria*: WhatsApp link formats top 5 cut-off habitations cleanly into clipboard/URL.

### Sunday, Oct 11 (Feature Freeze, Video & Submission)
- [ ] **12:00 IST**: **Strict Feature Freeze** (Zero new features, only bug fixes).
- [ ] **12:00 – 15:00 IST**: Record 3-minute demo video following exact script.
- [ ] **15:00 – 17:00 IST**: Draft & publish technical blog post on AWS Builder Center (eligible for AirPods 5 prize!).
- [ ] **17:00 – 19:00 IST**: Submit project on hackathon portal (Luma/WeMakeDevs) with demo video URL, GitHub repo, and live deployment link.

---

## 7. 3-Minute Demo Video Script (Shot-by-Shot)

| Timestamp | Screen Visual | Spoken Voiceover (High Energy, Confident) |
|---|---|---|
| **0:00 – 0:30** (Problem) | News headlines of Vijayawada 2024 Budameru flood; APSDMA statistics (12.8L affected, 4,300 km roads submerged). | *"In September 2024, the Budameru rivulet breached carrying 35,000 cusecs into Vijayawada, severing entire rural clusters from emergency care. Disaster control rooms faced a critical question: Which villages have lost 100% of their road access right now, and where must boats be dispatched first?"* |
| **0:30 – 1:15** (Data & SAR) | BaadhDrishti UI opens. Slider moves from 20-Aug dry baseline to 1-Sep flood radar mask. Urban amber hatching visible. | *"Meet BaadhDrishti. Powered by AWS Open Data, we ingest Copernicus Sentinel-1 Synthetic Aperture Radar. Because radar penetrates clouds, we run automated change detection. We deliberately exclude the dense urban core to avoid false positives from radar double-bounce, isolating real open-water inundation across peri-urban corridors."* |
| **1:15 – 2:00** (Reachability & Triage) | Zoom into road network: intersecting roads turn red. Triage table populates on right. | *"Instead of just showing a blue flood map, BaadhDrishti converts OpenStreetMap and PMGSY road networks into a dynamic topology graph. 14 habitations immediately trigger 'NO MAPPED ROAD PATH'. Rayanapadu, home to 4,200 residents, has its only motorable access road submerged. It jumps to Rank #1 on our verification queue."* |
| **2:00 – 2:30** (Interactivity & Action) | Officer clicks 'Clear Road' on an elevated culvert, then adds 'Kavuluru High School' as a staging hub. Table updates instantly. | *"Disaster response is human-in-the-loop. A field scout calls in: tractor traffic can pass via an elevated embankment. The officer marks the segment 'Cleared'—or designates a new dry high school as a staging hub. Our AWS Lambda engine recomputes reachability in 40 milliseconds, restoring connectivity and updating the relief dispatch queue instantly."* |
| **2:30 – 3:00** (Architecture & AWS Fit) | Clean AWS Architecture slide (S3 + Lambda + DynamoDB + Amplify + AWS Open Data) + honest disclaimer footer. | *"Architected on AWS: Sentinel-1 data directly from AWS Open Data S3, real-time graph routing on serverless AWS Lambda, and persistent state in DynamoDB. BaadhDrishti doesn't replace official warnings—it arms relief officers with actionable, uncertainty-aware triage within hours of satellite acquisition."* |

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
3. **AWS Deployment Stack**: Confirming serverless stack: **AWS S3 + CloudFront (Frontend) + API Gateway/Lambda (Python/NetworkX) + DynamoDB**. No OpenSearch, no heavy VPC.
