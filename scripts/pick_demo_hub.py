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
    urls = ["https://lz4.overpass-api.de/api/interpreter", "https://overpass-api.de/api/interpreter"]
    for url in urls:
        try:
            subprocess.run(["curl", "-sf", "--max-time", "200", "-A", "BaadhDrishti/1.0", url,
                            "--data-urlencode", f"data={q}", "-o", str(CACHE)], check=True)
            if '"elements":' in CACHE.read_text():
                return
        except subprocess.CalledProcessError:
            continue
    raise RuntimeError("Failed to fetch Overpass amenities from all mirrors")


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
