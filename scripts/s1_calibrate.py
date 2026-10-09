"""
scripts/s1_calibrate.py - raw S1 GRD DN window -> calibrated, noise-removed sigma0, geocoded to the AOI grid.

sigma0 = (DN^2 - noise_range * noise_azimuth) / sigmaNought_LUT^2   (ESA S1 radiometric calibration)
Geocoding is GCP-based (thin-plate spline on the 210 annotation GCPs) - no DEM terrain correction.
"""

import json
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.control import GroundControlPoint
from rasterio.transform import from_origin
from rasterio.warp import Resampling, reproject

AOI = [80.50, 16.50, 80.70, 16.65]
DST_CRS = "EPSG:32644"  # UTM 44N covers 78-84E
RES_M = 20.0


def aoi_grid():
    """Fixed 20 m UTM grid covering the AOI; shared by every layer."""
    t = Transformer.from_crs("EPSG:4326", DST_CRS, always_xy=True)
    lon0, lat0, lon1, lat1 = AOI
    xs, ys = t.transform([lon0, lon1, lon0, lon1], [lat0, lat0, lat1, lat1])
    x0, x1 = np.floor(min(xs) / RES_M) * RES_M, np.ceil(max(xs) / RES_M) * RES_M
    y0, y1 = np.floor(min(ys) / RES_M) * RES_M, np.ceil(max(ys) / RES_M) * RES_M
    width, height = int((x1 - x0) / RES_M), int((y1 - y0) / RES_M)
    return from_origin(x0, y1, RES_M, RES_M), width, height


def _floats(el):
    return np.array(el.text.split(), dtype=np.float64)


def _interp_lines(vec_lines, values, lines):
    """values: (n_vectors, n_cols) already interpolated in range; linear interp in azimuth."""
    idx = np.clip(np.searchsorted(vec_lines, lines) - 1, 0, len(vec_lines) - 2)
    l0, l1 = vec_lines[idx], vec_lines[idx + 1]
    w = ((lines - l0) / (l1 - l0))[:, None]
    return values[idx] * (1 - w) + values[idx + 1] * w


def _lut_2d(root, vec_tag, lut_tag, lines, pixels):
    vec_lines, rows = [], []
    for v in root.iter(vec_tag):
        vec_lines.append(float(v.find("line").text))
        rows.append(np.interp(pixels, _floats(v.find("pixel")), _floats(v.find(lut_tag))))
    return _interp_lines(np.array(vec_lines), np.vstack(rows), lines)


def _noise_azimuth(root, lines, pixels):
    az = np.ones((len(lines), len(pixels)))
    for b in root.iter("noiseAzimuthVector"):
        fl, ll = int(b.find("firstAzimuthLine").text), int(b.find("lastAzimuthLine").text)
        fp, lp = int(b.find("firstRangeSample").text), int(b.find("lastRangeSample").text)
        r = (lines >= fl) & (lines <= ll)
        c = (pixels >= fp) & (pixels <= lp)
        if not r.any() or not c.any():
            continue
        vals = np.interp(lines[r], _floats(b.find("line")), _floats(b.find("noiseAzimuthLut")))
        az[np.ix_(r, c)] = vals[:, None]
    return az


def calibrate_window(scene_dir: Path, pol: str):
    meta = json.loads((scene_dir / "meta.json").read_text())["pols"][pol]
    with rasterio.open(scene_dir / f"{pol}_dn.tif") as src:
        dn = src.read(1).astype(np.float64)
        gcps, gcp_crs = src.gcps
    lines = meta["row_off"] + np.arange(dn.shape[0], dtype=np.float64)
    pixels = meta["col_off"] + np.arange(dn.shape[1], dtype=np.float64)

    cal = ET.parse(scene_dir / f"calibration-{pol}.xml").getroot()
    noise = ET.parse(scene_dir / f"noise-{pol}.xml").getroot()
    a_sigma = _lut_2d(cal, "calibrationVector", "sigmaNought", lines, pixels)
    n_range = _lut_2d(noise, "noiseRangeVector", "noiseRangeLut", lines, pixels)
    n_az = _noise_azimuth(noise, lines, pixels)

    sigma0 = (dn ** 2 - n_range * n_az) / a_sigma ** 2
    sigma0 = np.where(dn > 0, np.maximum(sigma0, 1e-5), np.nan).astype(np.float32)  # floor at -50 dB
    return sigma0, gcps, gcp_crs


def shift_gcps(gcps, east_m, north_m):
    """Translate GCP ground coords by a metric offset (range-direction geolocation fix)."""
    out = []
    for g in gcps:
        dlon = east_m / (111320.0 * np.cos(np.radians(g.y)))
        dlat = north_m / 110540.0
        out.append(GroundControlPoint(row=g.row, col=g.col, x=g.x + dlon, y=g.y + dlat, z=g.z, id=g.id))
    return out


def geocode(sigma0, gcps, gcp_crs, shift_m=(0.0, 0.0)):
    transform, width, height = aoi_grid()
    out = np.full((height, width), np.nan, dtype=np.float32)
    gcps = shift_gcps(gcps, *shift_m)
    reproject(sigma0, out, gcps=gcps, src_crs=gcp_crs, src_nodata=np.nan,
              dst_transform=transform, dst_crs=DST_CRS, dst_nodata=np.nan,
              resampling=Resampling.average, SRC_METHOD="GCP_TPS")
    return out


def warp_to_grid(path, resampling, env=None):
    """Read any georeferenced raster (local or /vsi*) into the AOI grid."""
    transform, width, height = aoi_grid()
    out = np.full((height, width), np.nan, dtype=np.float32)
    with rasterio.Env(**(env or {})), rasterio.open(path) as src:
        reproject(rasterio.band(src, 1), out, dst_transform=transform, dst_crs=DST_CRS,
                  dst_nodata=np.nan, resampling=resampling)
    return out
