"""
scripts/export_overlays.py - web overlays for the Leaflet map (offline)

Reprojects the pre/post VV dB rasters and the candidate flood mask to an EPSG:4326 grid over the AOI and writes
RGBA PNGs plus overlays.json for L.imageOverlay. Also copies the urban-core polygon next to them.

Inputs: data/interim/{20240820,20240901}_vv_db.tif, data/processed/flood_mask_20240901.tif, urban_core.geojson
Output: frontend/data/{pre_vv,post_vv,flood_mask}.png, overlays.json, urban_core.geojson
"""

import json
import shutil
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image
from rasterio.transform import from_bounds
from rasterio.warp import Resampling, reproject

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "frontend" / "data"
AOI = [80.50, 16.50, 80.70, 16.65]  # lon_min, lat_min, lon_max, lat_max
W, H = 1600, 1200
DB_MIN, DB_MAX = -22.0, 0.0  # same stretch as scripts/quicklook_flood.py
MASK_RGBA = (30, 110, 255, 170)


def to_ll(path, resampling):
    dst = np.full((H, W), np.nan, np.float32)
    with rasterio.open(path) as src:
        reproject(rasterio.band(src, 1), dst, dst_transform=from_bounds(*AOI, W, H), dst_crs="EPSG:4326",
                  dst_nodata=np.nan, resampling=resampling)
    return dst


def gray_png(db, path):
    v = (np.clip((db - DB_MIN) / (DB_MAX - DB_MIN), 0, 1) * 255).astype(np.uint8)
    alpha = np.where(np.isnan(db), 0, 255).astype(np.uint8)
    Image.fromarray(np.dstack([v, v, v, alpha]), "RGBA").save(path, optimize=True)


def mask_png(mask, path):
    rgba = np.zeros((H, W, 4), np.uint8)
    rgba[mask] = MASK_RGBA
    Image.fromarray(rgba, "RGBA").save(path, optimize=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    gray_png(to_ll(ROOT / "data/interim/20240820_vv_db.tif", Resampling.bilinear), OUT / "pre_vv.png")
    gray_png(to_ll(ROOT / "data/interim/20240901_vv_db.tif", Resampling.bilinear), OUT / "post_vv.png")
    mask_png(to_ll(ROOT / "data/processed/flood_mask_20240901.tif", Resampling.nearest) == 1, OUT / "flood_mask.png")
    shutil.copy(ROOT / "data/processed/urban_core.geojson", OUT / "urban_core.geojson")
    meta = {"bounds": [[AOI[1], AOI[0]], [AOI[3], AOI[2]]], "pre": "pre_vv.png", "post": "post_vv.png",
            "mask": "flood_mask.png", "pre_date": "2024-08-20", "post_date": "2024-09-01"}
    (OUT / "overlays.json").write_text(json.dumps(meta, indent=1))
    for f in sorted(OUT.iterdir()):
        print(f"{f.relative_to(ROOT)}  {f.stat().st_size / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
