"""
tests/test_export_overlays.py - checks the web overlays written by scripts/export_overlays.py.
Run: .venv/bin/python tests/test_export_overlays.py
"""
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "frontend" / "data"


def test_overlays():
    subprocess.run([sys.executable, str(ROOT / "scripts" / "export_overlays.py")], check=True)
    meta = json.loads((WEB / "overlays.json").read_text())
    assert meta["bounds"] == [[16.5, 80.5], [16.65, 80.7]]
    assert (meta["pre_date"], meta["post_date"]) == ("2024-08-20", "2024-09-01")
    for key in ("pre", "post", "mask"):
        img = Image.open(WEB / meta[key])
        assert img.mode == "RGBA" and img.size == (1600, 1200), (key, img.mode, img.size)
    mask_alpha = Image.open(WEB / meta["mask"]).getchannel("A")
    opaque = sum(1 for a in mask_alpha.getdata() if a > 0) / (1600 * 1200)
    # flood_mask_20240901.geojson metadata reports frac_candidate_final 0.126 of the UTM grid
    assert 0.05 < opaque < 0.25, f"mask opaque fraction {opaque:.3f}"
    urban = json.loads((WEB / "urban_core.geojson").read_text())
    assert urban["type"] == "FeatureCollection" and urban["features"]
    print(f"✓ overlays ok (mask opaque fraction {opaque:.3f})")


if __name__ == "__main__":
    test_overlays()
