"""
tests/test_lambda_local.py - local smoke test of backend/app.py against the real data bundle.
DynamoDB and S3 are replaced by in-memory fakes; no AWS calls.
Run: .venv/bin/python tests/test_lambda_local.py  (needs data/processed/lambda_bundle.json)
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "backend")]
os.environ.setdefault("AWS_DEFAULT_REGION", "ap-south-1")
os.environ["DATA_BUCKET"] = "local"

import app  # noqa: E402


class FakeTable:
    def __init__(self, key):
        self.key, self.items = key, {}

    def scan(self, **_):
        return {"Items": list(self.items.values())}

    def put_item(self, Item):
        self.items[Item[self.key]] = Item

    def delete_item(self, Key):
        self.items.pop(Key[self.key], None)


class FakeS3:
    def get_object(self, Bucket, Key):
        return {"Body": open(ROOT / "data" / "processed" / Key, "rb")}


def call(method, path, body=None):
    res = app.handler({"requestContext": {"http": {"method": method}}, "rawPath": path,
                       "body": json.dumps(body) if body else None}, None)
    return res["statusCode"], json.loads(res["body"])


def test_api_lifecycle():
    app._overrides, app._hubs = FakeTable("edge_id"), FakeTable("hub_id")
    app.boto3.client = lambda name: FakeS3()
    offline = json.loads((ROOT / "data" / "processed" / "triage_summary.json").read_text())

    code, t = call("GET", "/api/triage")
    assert code == 200
    assert t["cut_off_count"] == offline["cut_off_count"], "Lambda must reproduce the offline triage"
    first = next(r for r in t["habitations"] if r["status"] == "NO_MAPPED_ROAD_PATH")
    assert first["blocking_roads"], "cut-off habitation must name its blocking roads"
    print(f"✓ GET /api/triage: {t['cut_off_count']} cut off, compute {t['compute_ms']} ms")

    # Clearing every reported blocking edge must change something (status or next blocking edges)
    for e in first["blocking_edges"]:
        code, r = call("POST", "/api/road-status", {"edge_id": e, "status": "FORCE_CLEARED", "officer_name": "test"})
        assert code == 200
    rec = next(h for h in r["habitations"] if h["id"] == first["id"])
    assert rec["status"] == "PATH_EXISTS" or rec["blocking_edges"] != first["blocking_edges"]
    print(f"✓ POST /api/road-status: {first['name']} -> {rec['status']}")

    # Undo -> back to offline result
    for e in first["blocking_edges"]:
        call("POST", "/api/road-status", {"edge_id": e, "status": "AUTO_SUSPECTED"})
    code, t2 = call("GET", "/api/triage")
    assert t2["cut_off_count"] == offline["cut_off_count"]
    print("✓ AUTO_SUSPECTED removes override")

    # Hub at the cut-off habitation itself -> it becomes PATH_EXISTS to that hub
    code, h = call("POST", "/api/hubs", {"name": "Test hub", "lat": first["lat"], "lon": first["lon"]})
    assert code == 201, h
    rec = next(x for x in h["habitations"] if x["id"] == first["id"])
    assert rec["status"] == "PATH_EXISTS" and rec["nearest_destination"]["type"] == "STAGING_HUB"
    print(f"✓ POST /api/hubs: {first['name']} -> PATH_EXISTS via hub")

    assert call("POST", "/api/road-status", {"edge_id": "nope", "status": "FORCE_CLEARED"})[0] == 400
    assert call("POST", "/api/hubs", {"name": "x", "lat": 10, "lon": 10})[0] == 400
    assert call("GET", "/api/nothing")[0] == 404
    print("✓ validation errors")


if __name__ == "__main__":
    test_api_lifecycle()
