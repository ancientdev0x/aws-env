"""scripts/draw_architecture.py - render docs/architecture.png (README + video slide). Uses matplotlib only."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "docs" / "architecture.png"
# key: (x, y, w, h, label, fill)
BOXES = {
    "s1": (0.2, 4.3, 3.5, 1.0, "AWS Open Data (S3)\nSentinel-1 GRD 20 Aug / 1 Sep 2024", "#fbd38d"),
    "aux": (0.2, 2.9, 3.5, 1.0, "JRC water · Copernicus DEM\nGHSL population · OpenStreetMap", "#e2e8f0"),
    "pipe": (4.5, 3.6, 3.2, 1.3, "Offline Python pipeline (run once)\ncalibrate → flood mask →\nroad graph → triage bundle", "#bee3f8"),
    "data": (8.4, 3.6, 2.6, 1.3, "Amazon S3\nprecomputed bundle", "#c6f6d5"),
    "lambda": (8.4, 1.2, 2.6, 1.3, "AWS Lambda (Python)\nNetworkX reachability\nper officer action", "#fbd38d"),
    "ddb": (11.8, 1.2, 2.6, 1.3, "Amazon DynamoDB\nroad overrides\nstaging hubs", "#c3dafe"),
    "apigw": (4.5, 1.2, 3.2, 1.3, "Amazon API Gateway (HTTP)\nGET /api/triage\nPOST /api/road-status · /api/hubs", "#e9d8fd"),
    "officer": (0.2, 1.35, 3.5, 1.0, "District officer\n(browser)", "#ffffff"),
    "cf": (0.2, -0.3, 3.5, 1.1, "Amazon S3 static website\nindex.html + Leaflet", "#e9d8fd"),
}
ARROWS = [("s1", "pipe"), ("aux", "pipe"), ("pipe", "data"), ("data", "lambda"), ("lambda", "ddb"),
          ("officer", "apigw"), ("apigw", "lambda"), ("cf", "officer")]


def center(k):
    x, y, w, h = BOXES[k][:4]
    return x + w / 2, y + h / 2


def edge_point(k, toward):
    """Point where the line from box k's centre toward `toward` leaves the box."""
    x, y, w, h = BOXES[k][:4]
    cx, cy = x + w / 2, y + h / 2
    dx, dy = toward[0] - cx, toward[1] - cy
    s = min((w / 2) / abs(dx) if dx else float("inf"), (h / 2) / abs(dy) if dy else float("inf"))
    return cx + dx * s, cy + dy * s


def main():
    fig, ax = plt.subplots(figsize=(14, 6.6))
    ax.set_xlim(0, 14.6)
    ax.set_ylim(-0.5, 5.8)
    ax.axis("off")
    for x, y, w, h, label, fill in BOXES.values():
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.04,rounding_size=0.12", fc=fill, ec="#1a202c", lw=1.2))
        ax.text(x + w / 2, y + h / 2, label, ha="center", va="center", fontsize=9.5, color="#1a202c")
    for a, b in ARROWS:
        ax.annotate("", xy=edge_point(b, center(a)), xytext=edge_point(a, center(b)),
                    arrowprops=dict(arrowstyle="-|>", lw=1.5, color="#1a202c"))
    ax.text(7.3, 5.55, "Offline: heavy SAR/GIS processing, once", ha="center", fontsize=10, style="italic", color="#4a5568")
    ax.text(7.3, 0.25, "Online: officer edits → recompute in Lambda", ha="center", fontsize=10, style="italic", color="#4a5568")
    ax.set_title("BaadhDrishti on AWS", fontsize=15, weight="bold")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=150, bbox_inches="tight", facecolor="white")
    print(OUT)


if __name__ == "__main__":
    main()
