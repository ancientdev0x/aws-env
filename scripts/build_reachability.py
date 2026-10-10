"""
scripts/build_reachability.py - Task 2.4: flood/road intersection + reachability triage (offline)

Inputs (all produced by earlier scripts / fetches):
  data/processed/flood_mask_20240901.tif, road_edges.geojson, road_nodes.json
  data/raw/osm/places_aoi.json, health_aoi.json        (Overpass, current OSM)
  data/raw/ghsl/pop_R7_C26.zip, smod_R7_C26.zip        (GHSL R2023A E2020: POP 100 m, SMOD 1 km)

Rules (CLAUDE.md / PLAN.md):
  - Urban core = GHSL SMOD class 30 "urban centre". Flood pixels there are ignored (radar double-bounce) and
    habitations there are reported as out of scope. Urban roads are therefore NOT auto-suspected (unknown, kept open).
  - No morphological closing: tested 3/5/7 px; 5+ only added Amaravati-side villages where NRSC 6-Sep shows no flooding.
  - Edge auto-suspected if within EDGE_BUFFER_M of a candidate flood pixel; bridge=yes edges handled by the engine (CHECK).
  - Habitation INUNDATED if its point falls in a candidate flood pixel.
  - Habitations with no path even in the dry baseline are flagged NO_BASELINE_PATH (graph artefact), not counted as cut off.
  - Population proxy = GHSL POP summed over each habitation's Voronoi cell (nearest-seed assignment), clipped to AOI.

Outputs:
  data/processed/triage_summary.json, habitations.json, destinations.json, suspected_edges.json, urban_core.geojson
"""

import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import rasterio
import shapely
from pyproj import Transformer
from rasterio.features import geometry_mask, shapes
from rasterio.transform import rowcol
from rasterio.windows import from_bounds
from scipy.spatial import cKDTree
from shapely.geometry import box, mapping, shape

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from engine.reachability import evaluate_reachability  # noqa: E402

PROC, RAW = ROOT / "data" / "processed", ROOT / "data" / "raw"
AOI = [80.50, 16.50, 80.70, 16.65]
UTM, MOLL = "EPSG:32644", "ESRI:54009"
HAB_PLACES = {"village", "hamlet", "suburb", "neighbourhood"}
SMOD_URBAN_CENTRE = 30
EDGE_BUFFER_M = 25.0      # PLAN.md Step 1.4
NOT_HUMAN_HEALTH = ("pet clinic", "veterinary", "animal hospital")
FAR_SNAP_M = 500.0        # habitation/destination farther than this from a road node gets FAR_FROM_ROAD
POP_SOURCE = "GHSL GHS-POP R2023A E2020 100m (Voronoi cell of habitation, clipped to AOI)"

to_utm = Transformer.from_crs("EPSG:4326", UTM, always_xy=True).transform
to_wgs = Transformer.from_crs(UTM, "EPSG:4326", always_xy=True).transform


def zipped_tif(path):
    name = next(n for n in zipfile.ZipFile(path).namelist() if n.endswith(".tif"))
    return f"/vsizip/{path}/{name}"


def project(geom, fn):
    return shapely.transform(geom, lambda xy: np.column_stack(fn(xy[:, 0], xy[:, 1])))


def urban_core_utm():
    """Union of SMOD urban-centre 1 km cells intersecting the AOI, in UTM."""
    to_moll = Transformer.from_crs("EPSG:4326", MOLL, always_xy=True).transform
    aoi_moll = project(box(*AOI), to_moll)
    with rasterio.open(zipped_tif(RAW / "ghsl" / "smod_R7_C26.zip")) as src:
        win = from_bounds(*aoi_moll.buffer(2000).bounds, src.transform).round_offsets().round_lengths()
        smod = src.read(1, window=win)
        cells = [shape(g) for g, v in shapes((smod == SMOD_URBAN_CENTRE).astype(np.uint8),
                                             transform=src.window_transform(win)) if v == 1]
    moll_to_utm = Transformer.from_crs(MOLL, UTM, always_xy=True).transform
    core = shapely.union_all([c.intersection(aoi_moll) for c in cells])
    return project(core, moll_to_utm)


def load_points(path, keep):
    out = []
    for e in json.loads(path.read_text())["elements"]:
        lat, lon = (e["lat"], e["lon"]) if "lat" in e else (e["center"]["lat"], e["center"]["lon"])
        if keep(e["tags"]):
            out.append({"osm": f"{e['type']}/{e['id']}", "tags": e["tags"], "lat": lat, "lon": lon})
    return out


def snap(points, node_ids, tree):
    xs, ys = to_utm([p["lon"] for p in points], [p["lat"] for p in points])
    dist, idx = tree.query(np.column_stack([xs, ys]))
    for p, d, i, x, y in zip(points, dist, idx, xs, ys):
        p["node"], p["snap_m"], p["xy"] = node_ids[i], round(float(d), 1), (x, y)


def voronoi_population(habs):
    """Sum GHSL POP 100 m pixels (centres inside AOI) into nearest-habitation cells."""
    with rasterio.open(zipped_tif(RAW / "ghsl" / "pop_R7_C26.zip")) as src:
        to_moll = Transformer.from_crs("EPSG:4326", MOLL, always_xy=True).transform
        aoi_moll = project(box(*AOI), to_moll)
        win = from_bounds(*aoi_moll.bounds, src.transform).round_offsets().round_lengths()
        pop = src.read(1, window=win)
        t = src.window_transform(win)
    rows, cols = np.nonzero(pop > 0)
    mx, my = t * (cols + 0.5, rows + 0.5)
    lon, lat = Transformer.from_crs(MOLL, "EPSG:4326", always_xy=True).transform(mx, my)
    inside = (lon >= AOI[0]) & (lon <= AOI[2]) & (lat >= AOI[1]) & (lat <= AOI[3])
    ux, uy = to_utm(lon[inside], lat[inside])
    _, owner = cKDTree(np.array([h["xy"] for h in habs])).query(np.column_stack([ux, uy]))
    sums = np.bincount(owner, weights=pop[rows, cols][inside], minlength=len(habs))
    for h, s in zip(habs, sums):
        h["population_proxy"] = int(round(s))
    return float(pop[rows, cols][inside].sum())


def main():
    edges_fc = json.loads((PROC / "road_edges.geojson").read_text())["features"]
    nodes = json.loads((PROC / "road_nodes.json").read_text())
    node_ids = [int(n) for n in nodes]
    nx_, ny_ = to_utm([c[0] for c in nodes.values()], [c[1] for c in nodes.values()])
    tree = cKDTree(np.column_stack([nx_, ny_]))

    core = urban_core_utm()
    shapely.prepare(core)

    # Flood mask (UTM 20 m) with urban core removed
    with rasterio.open(PROC / "flood_mask_20240901.tif") as src:
        flood = src.read(1) == 1
        ft = src.transform
    core_mask = geometry_mask([core], flood.shape, ft, invert=True) if not core.is_empty else np.zeros_like(flood)
    flood_eff = flood & ~core_mask
    flood_polys = [shape(g) for g, v in shapes(flood_eff.astype(np.uint8), mask=flood_eff, transform=ft) if v == 1]
    ftree = shapely.STRtree(flood_polys)

    edge_geoms = [project(shape(f["geometry"]), to_utm) for f in edges_fc]
    hit = ftree.query(edge_geoms, predicate="dwithin", distance=EDGE_BUFFER_M)
    suspected = {edges_fc[i]["properties"]["edge_id"] for i in np.unique(hit[0])}
    graph_edges = [{k: f["properties"][k] for k in ("u", "v", "weight", "edge_id", "is_bridge")} for f in edges_fc]

    # Habitations and destinations
    habs = load_points(RAW / "osm" / "places_aoi.json", lambda t: t.get("place") in HAB_PLACES and t.get("name"))
    dests = load_points(RAW / "osm" / "health_aoi.json",
                        lambda t: not any(k in t.get("name", "").lower() for k in NOT_HUMAN_HEALTH))
    snap(habs, node_ids, tree)
    snap(dests, node_ids, tree)
    aoi_pop = voronoi_population(habs)

    habitations, destinations, inundated = [], [], set()
    for h in habs:
        x, y = h["xy"]
        in_core = core.contains(shapely.Point(x, y))
        r, c = rowcol(ft, x, y)
        if 0 <= r < flood.shape[0] and 0 <= c < flood.shape[1] and flood_eff[r, c]:
            inundated.add(f"hab_{h['osm'].replace('/', '_')}")
        flags = (["URBAN_CORE_EXCLUDED"] if in_core else []) + (["FAR_FROM_ROAD"] if h["snap_m"] > FAR_SNAP_M else [])
        habitations.append({
            "id": f"hab_{h['osm'].replace('/', '_')}", "name": h["tags"]["name"], "place": h["tags"]["place"],
            "lat": h["lat"], "lon": h["lon"], "node": h["node"], "snap_distance_m": h["snap_m"],
            "population_proxy": h["population_proxy"], "population_source": POP_SOURCE,
            "in_urban_core": in_core, "uncertainty_flags": flags,
        })
    for d in dests:
        t = d["tags"]
        destinations.append({
            "id": f"dest_{d['osm'].replace('/', '_')}", "name": t.get("name", "Unnamed health facility"),
            "type": "HOSPITAL" if "hospital" in (t.get("amenity"), t.get("healthcare")) else "HEALTH_CENTRE",
            "lat": d["lat"], "lon": d["lon"], "node": d["node"], "snap_distance_m": d["snap_m"],
            "source": "OSM " + d["osm"],
        })

    baseline = {r["id"]: r for r in evaluate_reachability([dict(e) for e in graph_edges], habitations, destinations, set())}
    flooded = evaluate_reachability(graph_edges, habitations, destinations, suspected, inundated_habitations=inundated)

    queue, out_of_scope = [], []
    for r in flooded:
        b = baseline[r["id"]]
        r["baseline_distance_km"] = b["nearest_destination"]["distance_km"] if b["nearest_destination"] else None
        r.pop("node")
        if r["in_urban_core"]:
            out_of_scope.append({**r, "excluded_reason": "URBAN_CORE_EXCLUDED"})
        elif b["status"] != "PATH_EXISTS":
            r["uncertainty_flags"].append("NO_BASELINE_PATH")
            out_of_scope.append({**r, "excluded_reason": "NO_BASELINE_PATH"})
        else:
            queue.append(r)

    cut = [r for r in queue if r["status"] != "PATH_EXISTS"]
    check_edges = sorted(e["edge_id"] for e in graph_edges if e.get("uncertainty_flag") == "CHECK")
    summary = {
        "event": "Vijayawada Budameru Flood (2024-09-01 Replay)",
        "aoi": AOI,
        "total_habitations": len(habitations),
        "in_scope_habitations": len(queue),
        "out_of_scope_habitations": len(out_of_scope),
        "inundated_count": sum(r["status"] == "INUNDATED" for r in queue),
        "no_mapped_road_path_count": sum(r["status"] == "NO_MAPPED_ROAD_PATH" for r in queue),
        "cut_off_count": len(cut),
        "cut_off_population_proxy": sum(r["population_proxy"] for r in cut),
        "aoi_population_ghsl_e2020": int(round(aoi_pop)),
        "destinations": len(destinations),
        "road_edges": len(graph_edges),
        "auto_suspected_edges": len(suspected),
        "bridge_check_edges": len(check_edges),
        "urban_core_area_sqkm": round(core.area / 1e6, 2),
        "caveats": [
            "Candidate observed inundation from Sentinel-1 change detection; not ground verified.",
            "Urban core (GHSL SMOD urban centre) excluded: radar double-bounce; its roads are treated as open/unknown.",
            "Road network and facilities are current OpenStreetMap, not a 2024 snapshot.",
            "Population is a GHSL 2020 estimate apportioned by Voronoi cell, not a census count.",
        ],
        "habitations": queue,
        "out_of_scope": out_of_scope,
    }
    (PROC / "triage_summary.json").write_text(json.dumps(summary, indent=1))
    (PROC / "habitations.json").write_text(json.dumps(habitations))
    (PROC / "destinations.json").write_text(json.dumps(destinations))
    (PROC / "suspected_edges.json").write_text(json.dumps({"auto_suspected": sorted(suspected), "bridge_check": check_edges}))
    (PROC / "urban_core.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"label": "Urban core excluded due to radar double-bounce ambiguity",
                                           "source": "GHSL GHS-SMOD R2023A E2020 class 30"},
         "geometry": mapping(project(core, to_wgs))}]}))
    print(json.dumps({k: v for k, v in summary.items() if k not in ("habitations", "out_of_scope", "caveats")}, indent=1))


if __name__ == "__main__":
    main()
