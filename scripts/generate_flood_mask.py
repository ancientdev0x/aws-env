"""
scripts/generate_flood_mask.py - Task 2.2: candidate flood mask from S1 pre/post change detection (offline)

Pipeline (PLAN.md 0.3 Plan A, with calibration per RESEARCH_BAADH.md):
  raw DN -> sigma0 (calibration + thermal noise removal) -> GCP geocode to 20 m UTM grid
  -> range-direction geolocation shift estimated against JRC permanent water (GCP heights != terrain)
  -> dB -> 5x5 median -> delta_dB(VV) = post - pre < -3 dB
  -> post VV must be water-dark: below the 90th pct of post VV over JRC occurrence >= 90 % (reference open water)
  -> exclude slope > 5 deg (Copernicus DEM GLO-30) and JRC occurrence >= 50 %
  -> drop components < MIN_PIXELS -> vectorize.

Inputs: data/raw/<date>/ from scripts/fetch_s1_aoi.py
Outputs: data/processed/flood_mask_20240901.{tif,geojson}, data/interim/*.tif, data/interim/flood_mask_quicklook.png
"""

import json
from pathlib import Path

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.features import shapes
from scipy import ndimage
from shapely.geometry import mapping, shape
import shapely

from s1_calibrate import (DST_CRS, RES_M, Resampling, aoi_grid, calibrate_window, geocode,
                          warp_to_grid)

ROOT = Path(__file__).resolve().parent.parent
RAW, INTERIM, PROCESSED = ROOT / "data" / "raw", ROOT / "data" / "interim", ROOT / "data" / "processed"
PRE, POST = "20240820", "20240901"

DELTA_DB = -3.0          # PLAN.md: delta dB < -3
SLOPE_MAX_DEG = 5.0      # PLAN.md: slope > 5 deg excluded
JRC_PERMANENT_PCT = 50   # JRC GSW occurrence >= 50 % treated as permanent water
MIN_PIXELS = 10          # 10 px * 400 m2 = 0.4 ha minimum mapping unit
MEDIAN_PX = 5
WATER_REF_PCT, WATER_REF_PCTL = 90, 90  # post-dark threshold derived from reference open water
DARK_DB = -18.0          # VV dark-water level, used only for the shift estimate

JRC_URL = "/vsicurl/https://storage.googleapis.com/global-surface-water/downloads2021/occurrence/occurrence_80E_20Nv1_4_2021.tif"
DEM_URL = "/vsis3/copernicus-dem-30m/Copernicus_DSM_COG_10_N16_00_E080_00_DEM/Copernicus_DSM_COG_10_N16_00_E080_00_DEM.tif"


def platform_heading(scene_dir):
    import xml.etree.ElementTree as ET
    return float(ET.parse(scene_dir / "annotation-vv.xml").getroot().find(".//platformHeading").text)


def estimate_range_shift(sigma0, gcps, gcp_crs, permanent, heading_deg):
    """1-D search along near-range bearing (right-looking SAR) maximizing IoU(dark VV, JRC water)."""
    bearing = np.radians(heading_deg + 270.0)
    best = (-1.0, 0.0, (0.0, 0.0))
    for d in range(0, 501, 10):
        e, n = d * np.sin(bearing), d * np.cos(bearing)
        dark = 10 * np.log10(geocode(sigma0, gcps, gcp_crs, (e, n))) < DARK_DB
        iou = (dark & permanent).sum() / (dark | permanent).sum()
        best = max(best, (float(iou), float(d), (float(e), float(n))))
    return best


def save_tif(path, arr, dtype="float32", nodata=np.nan):
    transform, width, height = aoi_grid()
    with rasterio.open(path, "w", driver="GTiff", width=width, height=height, count=1, dtype=dtype,
                       crs=DST_CRS, transform=transform, nodata=nodata, compress="deflate") as dst:
        dst.write(arr.astype(dtype), 1)


def slope_deg(dem):
    gy, gx = np.gradient(dem, RES_M)
    return np.degrees(np.arctan(np.hypot(gx, gy)))


def main():
    INTERIM.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)

    jrc = warp_to_grid(JRC_URL, Resampling.average)
    dem = warp_to_grid(DEM_URL, Resampling.bilinear, {"AWS_NO_SIGN_REQUEST": "YES"})
    permanent = jrc >= JRC_PERMANENT_PCT
    steep = slope_deg(dem) > SLOPE_MAX_DEG

    # Shift estimated on the pre-event scene; pre/post share orbit geometry (phase correlation 0,0 px).
    s_pre, gcps_pre, crs_pre = calibrate_window(RAW / PRE, "vv")
    iou, shift_d, shift_m = estimate_range_shift(s_pre, gcps_pre, crs_pre, permanent, platform_heading(RAW / POST))
    print(f"range shift {shift_d:.0f} m -> E {shift_m[0]:.1f} m, N {shift_m[1]:.1f} m (IoU vs JRC {iou:.3f})")

    db = {}
    for date in (PRE, POST):
        for pol in ("vv", "vh"):
            s, g, c = calibrate_window(RAW / date, pol)
            x = 10 * np.log10(geocode(s, g, c, shift_m))
            save_tif(INTERIM / f"{date}_{pol}_db.tif", x)
            db[date, pol] = ndimage.median_filter(x, size=MEDIAN_PX)

    delta_vv = db[POST, "vv"] - db[PRE, "vv"]
    delta_vh = db[POST, "vh"] - db[PRE, "vh"]
    save_tif(INTERIM / "delta_vv_db.tif", delta_vv)
    save_tif(INTERIM / "delta_vh_db.tif", delta_vh)

    raw_change = delta_vv < DELTA_DB
    post_dark_db = float(np.nanpercentile(db[POST, "vv"][jrc >= WATER_REF_PCT], WATER_REF_PCTL))
    post_dark = db[POST, "vv"] < post_dark_db
    print(f"post-dark threshold {post_dark_db:.2f} dB")
    candidate = raw_change & post_dark & ~steep & ~permanent
    labels, n = ndimage.label(candidate)
    sizes = ndimage.sum(candidate, labels, index=np.arange(1, n + 1))
    keep = np.isin(labels, np.flatnonzero(sizes >= MIN_PIXELS) + 1)
    save_tif(PROCESSED / "flood_mask_20240901.tif", keep, dtype="uint8", nodata=0)

    transform, _, _ = aoi_grid()
    to_wgs = Transformer.from_crs(DST_CRS, "EPSG:4326", always_xy=True).transform
    labels, _ = ndimage.label(keep)
    features = []
    for geom, lab in shapes(labels.astype(np.int32), mask=keep, transform=transform):
        sel = labels == lab
        poly = shape(geom)
        features.append({
            "type": "Feature",
            "properties": {
                "area_sqm": round(poly.area, 1),
                "delta_db_mean": round(float(delta_vv[sel].mean()), 2),
                "vh_agree_frac": round(float((delta_vh[sel] < DELTA_DB).mean()), 3),
            },
            "geometry": mapping(shapely.transform(poly, lambda xy: np.column_stack(to_wgs(xy[:, 0], xy[:, 1])))),
        })

    stats = {
        "pixels_aoi": int(keep.size),
        "frac_raw_change": round(float(raw_change.mean()), 4),
        "frac_excluded_steep": round(float((raw_change & steep).mean()), 4),
        "frac_excluded_not_post_dark": round(float((raw_change & ~post_dark).mean()), 4),
        "post_dark_threshold_db": round(post_dark_db, 2),
        "frac_excluded_permanent_water": round(float((raw_change & permanent).mean()), 4),
        "frac_candidate_final": round(float(keep.mean()), 4),
        "candidate_area_sqkm": round(float(keep.sum()) * RES_M ** 2 / 1e6, 2),
        "polygons": len(features),
    }
    fc = {
        "type": "FeatureCollection",
        "metadata": {
            "event": "Vijayawada Budameru Flood",
            "pre_scene": json.loads((RAW / PRE / "meta.json").read_text())["scene_id"],
            "post_scene": json.loads((RAW / POST / "meta.json").read_text())["scene_id"],
            "detection_method": f"Calibrated sigma0 VV, {MEDIAN_PX}x{MEDIAN_PX} median, delta dB < {DELTA_DB} and post VV < {post_dark_db:.2f} dB "
                                f"(p{WATER_REF_PCTL} of JRC>={WATER_REF_PCT}% water); "
                                f"slope > {SLOPE_MAX_DEG} deg and JRC occurrence >= {JRC_PERMANENT_PCT}% excluded; "
                                f"min {MIN_PIXELS} px",
            "geolocation": f"GCP TPS geocode + {shift_d:.0f} m near-range shift estimated vs JRC GSW "
                           f"(IoU {iou:.3f}); no DEM terrain correction",
            "resolution_m": RES_M,
            "status": "candidate observed inundation - not ground verified",
            "stats": stats,
        },
        "features": features,
    }
    (PROCESSED / "flood_mask_20240901.geojson").write_text(json.dumps(fc))
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
