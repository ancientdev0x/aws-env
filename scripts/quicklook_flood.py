"""scripts/quicklook_flood.py - render candidate mask + named places in lon/lat for NRSC/APSAC visual comparison."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from rasterio.warp import Resampling, reproject
from rasterio.transform import from_bounds

ROOT = Path(__file__).resolve().parent.parent
AOI = [80.50, 16.50, 80.70, 16.65]
W, H = 1200, 900
NAMES = ["Rayanapadu", "Elaprolu", "Kavuluru", "Nunna", "Ambapuram", "Jakkampudi", "Gollapudi",
         "Ajit Singh Nagar", "Ramavarappadu", "Payakapuram", "Gunadala", "Vijayawada"]


def to_ll(path, resampling):
    dst = np.full((H, W), np.nan, np.float32)
    with rasterio.open(path) as src:
        reproject(rasterio.band(src, 1), dst, dst_transform=from_bounds(*AOI, W, H), dst_crs="EPSG:4326",
                  dst_nodata=np.nan, resampling=resampling)
    return dst


def main():
    pre = to_ll(ROOT / "data/interim/20240820_vv_db.tif", Resampling.bilinear)
    post = to_ll(ROOT / "data/interim/20240901_vv_db.tif", Resampling.bilinear)
    mask = to_ll(ROOT / "data/processed/flood_mask_20240901.tif", Resampling.nearest) == 1
    places = [e for e in json.loads((ROOT / "data/raw/osm/places_aoi.json").read_text())["elements"]
              if e["tags"].get("name") in NAMES]
    ext = [AOI[0], AOI[2], AOI[1], AOI[3]]
    fig, ax = plt.subplots(1, 3, figsize=(27, 7.5))
    for a, img, title in [(ax[0], pre, "VV 2024-08-20 (dB)"), (ax[1], post, "VV 2024-09-01 (dB)"),
                          (ax[2], pre, "Candidate flood mask (red) over pre-event VV")]:
        a.imshow(img, cmap="gray", vmin=-22, vmax=0, extent=ext)
        a.set_title(title)
    ax[2].imshow(np.ma.masked_where(~mask, mask), cmap="autumn", alpha=0.6, extent=ext)
    for a in ax:
        for p in places:
            a.plot(p["lon"], p["lat"], "c^", ms=5)
            a.annotate(p["tags"]["name"], (p["lon"], p["lat"]), color="cyan", fontsize=8, xytext=(3, 3),
                       textcoords="offset points")
    plt.tight_layout()
    out = ROOT / "data/interim/flood_mask_quicklook.png"
    plt.savefig(out, dpi=60)
    print(out)


if __name__ == "__main__":
    main()
