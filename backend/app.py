"""
backend/app.py - BaadhDrishti API Lambda (PLAN.md §4)

GET  /api/triage       -> ranked queue with current officer overrides + hubs
POST /api/road-status  -> FORCE_CLEARED | FORCE_BLOCKED | AUTO_SUSPECTED (= remove override), then recompute
POST /api/hubs         -> add officer staging hub (snapped to nearest road node), then recompute

Precomputed graph/habitations come from s3://$DATA_BUCKET/$BUNDLE_KEY (scripts/export_lambda_bundle.py).
No SAR/GIS work here - only NetworkX via engine.reachability.
"""

import json
import math
import os
import time
import uuid
from decimal import Decimal

import boto3

from engine.reachability import evaluate_reachability

ROAD_STATUSES = {"FORCE_CLEARED", "FORCE_BLOCKED", "AUTO_SUSPECTED"}
HUB_KINDS = {"RELIEF_CAMP", "NDRF_BASE", "DISTRICT_COLLECTORATE", "SCHOOL"}
MAX_HUB_SNAP_M = 1000.0

_ddb = boto3.resource("dynamodb")
_overrides = _ddb.Table(os.environ.get("ROAD_OVERRIDES_TABLE", "road_overrides"))
_hubs = _ddb.Table(os.environ.get("STAGING_HUBS_TABLE", "staging_hubs"))
_bundle = None


def load_bundle():
    """Cold-start cache of the precomputed bundle plus the dry-baseline result (scope rules)."""
    global _bundle
    if _bundle is None:
        obj = boto3.client("s3").get_object(Bucket=os.environ["DATA_BUCKET"], Key=os.environ.get("BUNDLE_KEY", "lambda_bundle.json"))
        b = json.loads(obj["Body"].read())
        b["graph_edges"] = [{"edge_id": e[0], "u": e[1], "v": e[2], "weight": e[3], "is_bridge": e[4]} for e in b["edges"]]
        b["edge_meta"] = {e[0]: {"highway": e[5], "name": e[6]} for e in b["edges"]}
        b["auto_suspected"] = set(b["auto_suspected"])
        b["bridge_ids"] = {e["edge_id"] for e in b["graph_edges"] if e["is_bridge"]}
        base = evaluate_reachability([dict(e) for e in b["graph_edges"]], b["habitations"], b["destinations"], set())
        b["baseline"] = {r["id"]: r for r in base}
        _bundle = b
    return _bundle


def nearest_node(nodes, lon, lat):
    """Brute-force equirectangular nearest road node (~19k nodes; only on hub add)."""
    k = math.cos(math.radians(lat))
    best, best_d = None, float("inf")
    for nid, (x, y) in nodes.items():
        d = ((x - lon) * k) ** 2 + (y - lat) ** 2
        if d < best_d:
            best, best_d = nid, d
    return int(best), math.sqrt(best_d) * 111320.0


def scan(table):
    items, kwargs = [], {}
    while True:
        page = table.scan(**kwargs)
        items += page["Items"]
        if "LastEvaluatedKey" not in page:
            return items
        kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]


def plain(o):
    if isinstance(o, Decimal):
        return int(o) if o == o.to_integral_value() else float(o)
    if isinstance(o, (set, frozenset)):
        return sorted(o)
    raise TypeError(type(o))


def compute():
    b = load_bundle()
    t0 = time.perf_counter()
    overrides = scan(_overrides)
    cleared = {o["edge_id"] for o in overrides if o["override_status"] == "FORCE_CLEARED"}
    blocked = {o["edge_id"] for o in overrides if o["override_status"] == "FORCE_BLOCKED"}
    hubs = [h for h in scan(_hubs) if h.get("is_active", True)]
    destinations = b["destinations"] + [
        {"id": h["hub_id"], "name": h["name"], "type": "STAGING_HUB", "node": int(h["node"])} for h in hubs]

    graph_edges = [dict(e) for e in b["graph_edges"]]
    records = evaluate_reachability(graph_edges, b["habitations"], destinations, b["auto_suspected"],
                                    force_cleared_edges=cleared, force_blocked_edges=blocked)
    compute_ms = round((time.perf_counter() - t0) * 1000, 1)

    queue, out_of_scope = [], []
    for r in records:
        base = b["baseline"][r["id"]]
        r["baseline_distance_km"] = base["nearest_destination"]["distance_km"] if base["nearest_destination"] else None
        r["blocking_roads"] = [{"edge_id": e, **b["edge_meta"][e]} for e in r["blocking_edges"]]
        r.pop("node", None)
        if r["in_urban_core"]:
            out_of_scope.append({**r, "excluded_reason": "URBAN_CORE_EXCLUDED"})
        elif base["status"] != "PATH_EXISTS":
            out_of_scope.append({**r, "excluded_reason": "NO_BASELINE_PATH"})
        else:
            queue.append(r)

    effective = ((b["auto_suspected"] - b["bridge_ids"]) - cleared) | blocked
    disrupted = []
    for eid in (b["auto_suspected"] | blocked | cleared):
        if eid not in b["edge_geometry"]:
            continue
        if eid in blocked:
            st = "FORCE_BLOCKED"
        elif eid in cleared:
            st = "FORCE_CLEARED"
        elif eid in b["bridge_ids"]:
            st = "CHECK"
        else:
            st = "AUTO_SUSPECTED"
        disrupted.append({"type": "Feature", "geometry": {"type": "LineString", "coordinates": b["edge_geometry"][eid]},
                          "properties": {"edge_id": eid, "status": st, "blocked": eid in effective, **b["edge_meta"][eid]}})

    cut = [r for r in queue if r["status"] != "PATH_EXISTS"]
    return {
        "event": b["event"],
        "aoi": b["aoi"],
        "total_habitations": len(records),
        "in_scope_habitations": len(queue),
        "cut_off_count": len(cut),
        "cut_off_population_proxy": sum(r["population_proxy"] for r in cut),
        "compute_ms": compute_ms,
        "habitations": queue,
        "out_of_scope": out_of_scope,
        "active_staging_hubs": hubs,
        "road_overrides": overrides,
        "disrupted_edges": {"type": "FeatureCollection", "features": disrupted},
        "caveats": b["caveats"],
    }


def respond(code, body):
    return {"statusCode": code, "headers": {"Content-Type": "application/json"}, "body": json.dumps(body, default=plain)}


def status_diff(before, after):
    old = {r["id"]: r["status"] for r in before["habitations"]}
    return [{"id": r["id"], "name": r["name"], "from": old.get(r["id"]), "to": r["status"]}
            for r in after["habitations"] if old.get(r["id"]) != r["status"]]


def road_status(body):
    b = load_bundle()
    eid, st = body.get("edge_id"), body.get("status")
    if eid not in b["edge_meta"] or st not in ROAD_STATUSES:
        return respond(400, {"error": f"edge_id must be a known edge and status one of {sorted(ROAD_STATUSES)}"})
    before = compute()
    if st == "AUTO_SUSPECTED":
        _overrides.delete_item(Key={"edge_id": eid})
    else:
        _overrides.put_item(Item={"edge_id": eid, "override_status": st, "notes": str(body.get("notes", ""))[:500],
                                  "officer_id": str(body.get("officer_name", ""))[:100], "updated_at": int(time.time())})
    after = compute()
    return respond(200, {**after, "diff": status_diff(before, after)})


def add_hub(body):
    b = load_bundle()
    try:
        lat, lon = float(body["lat"]), float(body["lon"])
        name = str(body["name"]).strip()[:120]
    except (KeyError, TypeError, ValueError):
        return respond(400, {"error": "name, lat, lon required"})
    lon0, lat0, lon1, lat1 = b["aoi"]
    if not name or not (lon0 <= lon <= lon1 and lat0 <= lat <= lat1):
        return respond(400, {"error": "hub must have a name and lie inside the AOI"})
    node, snap_m = nearest_node(b["nodes"], lon, lat)
    if snap_m > MAX_HUB_SNAP_M:
        return respond(400, {"error": f"nearest mapped road is {snap_m:.0f} m away"})
    before = compute()
    hub = {"hub_id": f"hub_{uuid.uuid4().hex[:10]}", "name": name, "lat": Decimal(str(lat)), "lon": Decimal(str(lon)),
           "type": "STAGING_HUB", "hub_kind": body.get("hub_kind") if body.get("hub_kind") in HUB_KINDS else "SCHOOL",
           "node": node, "snap_distance_m": Decimal(str(round(snap_m, 1))), "is_active": True}
    _hubs.put_item(Item=hub)
    after = compute()
    return respond(201, {**after, "hub": hub, "diff": status_diff(before, after)})


def handler(event, context):
    method = event.get("requestContext", {}).get("http", {}).get("method", "GET")
    path = event.get("rawPath", "")
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return respond(400, {"error": "invalid JSON"})
    if method == "GET" and path == "/api/triage":
        return respond(200, compute())
    if method == "POST" and path == "/api/road-status":
        return road_status(body)
    if method == "POST" and path == "/api/hubs":
        return add_hub(body)
    return respond(404, {"error": "not found"})
