"""
scripts/export_lambda_bundle.py - pack data/processed/* into one compact JSON for the Lambda (offline)

Lambda loads this from S3 at cold start, so it carries only what the engine and API need:
edges as [edge_id, u, v, weight_km, is_bridge, highway, name], node coords, habitations, destinations,
auto-suspected / bridge-CHECK edge ids, and geometry only for those edges (map display).

Output: data/processed/lambda_bundle.json
"""

import json
from pathlib import Path

PROC = Path(__file__).resolve().parent.parent / "data" / "processed"


def main():
    edges = json.loads((PROC / "road_edges.geojson").read_text())["features"]
    suspected = json.loads((PROC / "suspected_edges.json").read_text())
    summary = json.loads((PROC / "triage_summary.json").read_text())
    show = set(suspected["auto_suspected"]) | set(suspected["bridge_check"])

    bundle = {
        "event": summary["event"],
        "aoi": summary["aoi"],
        "caveats": summary["caveats"],
        "edges": [[p["edge_id"], p["u"], p["v"], p["weight"], p["is_bridge"], p["highway"], p["name"]]
                  for p in (f["properties"] for f in edges)],
        "edge_geometry": {f["properties"]["edge_id"]: f["geometry"]["coordinates"]
                          for f in edges if f["properties"]["edge_id"] in show},
        "nodes": json.loads((PROC / "road_nodes.json").read_text()),
        "habitations": json.loads((PROC / "habitations.json").read_text()),
        "destinations": json.loads((PROC / "destinations.json").read_text()),
        "auto_suspected": suspected["auto_suspected"],
    }
    out = PROC / "lambda_bundle.json"
    out.write_text(json.dumps(bundle, separators=(",", ":")))
    print(f"{out} {out.stat().st_size / 1e6:.2f} MB, {len(bundle['edges'])} edges, {len(bundle['edge_geometry'])} with geometry")


if __name__ == "__main__":
    main()
