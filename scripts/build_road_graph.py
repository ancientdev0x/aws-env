"""
scripts/build_road_graph.py - Task 2.3: OSM drivable road graph for the AOI (offline, run once)

Raw OSM is fetched with curl into data/raw/osm/roads_aoi.osm (Python requests hung on overpass-api.de over IPv4
from our machine; curl falls back to IPv6). This is CURRENT OSM (see <meta osm_base>), not a 2024 snapshot.

Outputs:
  data/processed/road_graph.graphml   - OSMnx graph (highway/bridge/name tags, length in meters)
  data/processed/road_edges.geojson   - one undirected feature per edge in engine format:
                                        edge_id, u, v, weight (km), is_bridge, highway, name
  data/processed/road_nodes.json      - {node_id: [lon, lat]} for snapping habitations / hospitals / officer hubs
"""

import json
import subprocess
from pathlib import Path

import osmnx as ox
from shapely.geometry import LineString, mapping

AOI = [80.50, 16.50, 80.70, 16.65]  # lon_min, lat_min, lon_max, lat_max
HIGHWAYS = ["motorway", "trunk", "primary", "secondary", "tertiary", "unclassified", "residential"]
# PLAN.md Step 1.4 classes plus their *_link ramps (same road, OSM splits the ramp tag)
FILTER = '["highway"~"^(' + "|".join(HIGHWAYS + [h + "_link" for h in HIGHWAYS[:5]]) + ')$"]'
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
ROOT = Path(__file__).resolve().parent.parent
RAW_OSM = ROOT / "data" / "raw" / "osm" / "roads_aoi.osm"
OUT = ROOT / "data" / "processed"


def first(v):
    return v[0] if isinstance(v, list) else v


def fetch_osm():
    lon0, lat0, lon1, lat1 = AOI
    query = f'[out:xml][timeout:180];(way{FILTER}({lat0},{lon0},{lat1},{lon1}););(._;>;);out body;'
    RAW_OSM.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["curl", "-sf", "--max-time", "300", "-A", "BaadhDrishti/1.0", OVERPASS_URL,
                    "--data-urlencode", f"data={query}", "-o", str(RAW_OSM)], check=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    if not RAW_OSM.exists():
        fetch_osm()
    # Split simplified edges wherever the bridge tag changes; otherwise a short bridge is merged into a long road edge
    # and the whole edge would be exempt from auto-disruption (bridge rule).
    G = ox.graph_from_xml(RAW_OSM, simplify=False, retain_all=True)
    G = ox.simplify_graph(G, edge_attrs_differ=["bridge"])
    ox.save_graphml(G, OUT / "road_graph.graphml")

    features = []
    # to_undirected merges reciprocal one-way pairs; remaining parallel edges are distinguished by key k
    for u, v, k, data in ox.convert.to_undirected(G).edges(keys=True, data=True):
        a, b = min(u, v), max(u, v)
        geom = data.get("geometry") or LineString([(G.nodes[u]["x"], G.nodes[u]["y"]),
                                                   (G.nodes[v]["x"], G.nodes[v]["y"])])
        bridge = data.get("bridge")
        features.append({
            "type": "Feature",
            "properties": {
                "edge_id": f"osm_way_{first(data['osmid'])}_{a}_{b}" + (f"_{k}" if k else ""),
                "u": int(u), "v": int(v),
                "weight": round(data["length"] / 1000.0, 4),  # OSMnx meters -> engine km
                "is_bridge": any(b in ("yes", "viaduct", "aqueduct") for b in (bridge if isinstance(bridge, list) else [bridge])),
                "highway": first(data["highway"]),
                "name": first(data.get("name")),
                "osm_way_ids": data["osmid"] if isinstance(data["osmid"], list) else [data["osmid"]],
            },
            "geometry": mapping(geom),
        })

    (OUT / "road_nodes.json").write_text(json.dumps({str(n): [round(d["x"], 7), round(d["y"], 7)] for n, d in G.nodes(data=True)}))
    (OUT / "road_edges.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": features}))
    n_bridge = sum(f["properties"]["is_bridge"] for f in features)
    km = sum(f["properties"]["weight"] for f in features)
    print(f"nodes {G.number_of_nodes()}  undirected edges {len(features)}  bridges {n_bridge}  total {km:.1f} km")


if __name__ == "__main__":
    main()
