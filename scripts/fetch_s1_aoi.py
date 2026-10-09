"""
scripts/fetch_s1_aoi.py - Task 2.1: fetch Sentinel-1 GRD AOI windows (offline, run once)

1. Query Earth Search STAC for the pre/post scenes and assert same relative orbit + pass.
2. Map the AOI bbox to a pixel window via the scene GCPs (GRD is in radar geometry, no CRS).
3. Read only that window of raw uint16 DN (VV, VH) from s3://sentinel-s1-l1c (no-sign-request).
4. Save DN windows with GCPs shifted to window coords, plus calibration/noise XMLs and a sidecar JSON.

Output: data/raw/<YYYYMMDD>/{vv,vh}_dn.tif, calibration-*.xml, noise-*.xml, meta.json
"""

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("AWS_NO_SIGN_REQUEST", "YES")
os.environ.setdefault("AWS_REGION", "eu-central-1")

import boto3
import rasterio
from botocore import UNSIGNED
from botocore.config import Config
from pystac_client import Client
from rasterio.control import GroundControlPoint
from rasterio.transform import GCPTransformer
from rasterio.windows import Window

STAC_URL = "https://earth-search.aws.element84.com/v1"
AOI = [80.50, 16.50, 80.70, 16.65]  # lon_min, lat_min, lon_max, lat_max (PLAN.md Step 1.2)
SCENES = {
    "20240820": "S1A_IW_GRDH_1SDV_20240820T003107_20240820T003132_055289_06BD9B",
    "20240901": "S1A_IW_GRDH_1SDV_20240901T003107_20240901T003132_055464_06C415",
}
PAD_PX = 200
ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"


def s3_split(href):
    bucket, key = href[len("s3://"):].split("/", 1)
    return bucket, key


def aoi_window(gcps, width, height):
    t = GCPTransformer(gcps)
    lon0, lat0, lon1, lat1 = AOI
    xs = [lon0, lon1, lon0, lon1]
    ys = [lat0, lat0, lat1, lat1]
    rows, cols = t.rowcol(xs, ys)
    r0 = max(0, int(min(rows)) - PAD_PX)
    r1 = min(height, int(max(rows)) + PAD_PX)
    c0 = max(0, int(min(cols)) - PAD_PX)
    c1 = min(width, int(max(cols)) + PAD_PX)
    return Window(c0, r0, c1 - c0, r1 - r0)


def main():
    items = {d: Client.open(STAC_URL).get_collection("sentinel-1-grd").get_item(sid) for d, sid in SCENES.items()}
    geom = {d: (it.properties["sat:relative_orbit"], it.properties["sat:orbit_state"]) for d, it in items.items()}
    print("Geometry:", geom)
    if len(set(geom.values())) != 1:
        sys.exit("FAIL: pre/post scenes are not same relative orbit + pass")

    s3 = boto3.client("s3", region_name="eu-central-1", config=Config(signature_version=UNSIGNED))
    for date, it in items.items():
        out = RAW / date
        out.mkdir(parents=True, exist_ok=True)
        meta = {"scene_id": it.id, "datetime": it.properties["datetime"],
                "relative_orbit": geom[date][0], "orbit_state": geom[date][1], "aoi": AOI, "pols": {}}
        for pol in ("vv", "vh"):
            for kind in ("calibration", "noise"):
                bucket, key = s3_split(it.assets[f"schema-{kind}-{pol}"].href)
                s3.download_file(bucket, key, str(out / f"{kind}-{pol}.xml"))

            src_path = "/vsis3/" + it.assets[pol].href[len("s3://"):]
            with rasterio.open(src_path) as src:
                gcps, gcp_crs = src.gcps
                win = aoi_window(gcps, src.width, src.height)
                dn = src.read(1, window=win)
                shifted = [GroundControlPoint(row=g.row - win.row_off, col=g.col - win.col_off,
                                              x=g.x, y=g.y, z=g.z, id=g.id) for g in gcps]
                profile = {"driver": "GTiff", "dtype": "uint16", "count": 1, "nodata": 0,
                           "width": int(win.width), "height": int(win.height),
                           "tiled": True, "compress": "deflate"}
                with rasterio.open(out / f"{pol}_dn.tif", "w", **profile) as dst:
                    dst.write(dn, 1)
                    dst.gcps = (shifted, gcp_crs)
            meta["pols"][pol] = {"source": it.assets[pol].href, "row_off": int(win.row_off),
                                 "col_off": int(win.col_off), "height": int(win.height), "width": int(win.width)}
            print(date, pol, "window", meta["pols"][pol], "nonzero_frac", float((dn > 0).mean()))
        (out / "meta.json").write_text(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
