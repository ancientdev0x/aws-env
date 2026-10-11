"""
tests/frontend_smoke.py - headless-browser check of the frontend (local or CloudFront).

Usage (from aws-env/):
  uv run --with playwright python -m playwright install chromium     # once
  uv run --with playwright python tests/frontend_smoke.py <url>          # read-only + docs/screenshot.png
  uv run --with playwright python tests/frontend_smoke.py <url> --write  # also clears the top row's blocking roads
After --write run: AWS_PROFILE=baadh scripts/reset_demo_state.sh
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent


def main(url, write):
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.on("console", lambda m: m.type == "error" and "tile.openstreetmap.org" not in m.text and errors.append(m.text))
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(url)
        page.wait_for_selector("#queue .row[data-id]", timeout=30000)

        cut = page.inner_text("#s-cut").strip()
        assert cut.isdigit() and int(cut) > 0, f"stats not loaded: {cut!r}"
        rows = page.locator("#queue .row[data-id]").count()
        assert rows == int(cut), f"'Only cut-off' filter should list {cut} rows, got {rows}"
        assert page.locator("#caveats li").count() >= 3, "caveats from API missing"
        assert page.locator(".leaflet-image-layer").count() == 3, "pre/post/mask overlays missing"
        assert "NOT official rescue orders" in page.inner_text("footer")

        # clicking a disrupted road on the map must open its popup (canvas stacking bug, fixed 2026-10-11)
        page.evaluate("""() => new Promise(r => {
            const f = S.data.disrupted_edges.features.find(f => f.properties.status === 'AUTO_SUSPECTED');
            const c = f.geometry.coordinates[Math.floor(f.geometry.coordinates.length / 2)];
            map.once('moveend', () => r(1)); map.setView([c[1], c[0]], 17, { animate: false }); })""")
        page.wait_for_timeout(500)
        xy = page.evaluate("""() => { const f = S.data.disrupted_edges.features.find(f => f.properties.status === 'AUTO_SUSPECTED');
            const c = f.geometry.coordinates[Math.floor(f.geometry.coordinates.length / 2)];
            const p = map.latLngToContainerPoint([c[1], c[0]]), r = document.getElementById('map').getBoundingClientRect();
            return [r.left + p.x, r.top + p.y]; }""")
        page.mouse.click(*xy)
        page.wait_for_selector(".leaflet-popup-content button[data-s=FORCE_BLOCKED]", timeout=5000)
        page.evaluate("() => { map.closePopup(); map.fitBounds([[16.50, 80.50], [16.65, 80.70]]); }")

        page.uncheck("#f-cut")
        assert page.locator("#queue .row[data-id]").count() > rows, "unchecking filter should show PATH_EXISTS rows"
        page.check("#f-cut")

        with page.expect_download() as dl:
            page.click("#b-csv")
        csv_text = Path(dl.value.path()).read_text()
        assert csv_text.splitlines()[0].startswith("rank,id,name,status"), csv_text[:80]

        page.wait_for_timeout(2500)  # let basemap tiles draw
        page.screenshot(path=str(ROOT / "docs" / "screenshot.png"))

        if write:
            first = page.locator("#queue .row[data-id]").first
            name = first.locator(".nm").inner_text()
            first.locator("button[data-act=clear]").click()
            page.fill("#dlg input[name=officer_name]", "smoke-test")
            page.click("#dlg button[value=ok]")
            page.wait_for_function("document.getElementById('toast').textContent.includes('Restored')", timeout=90000)
            print(f"cleared {name}: {page.inner_text('#toast')}")
        browser.close()

    assert not errors, f"console errors: {errors}"
    print("✓ frontend smoke passed" + (" (write flow)" if write else ""))


if __name__ == "__main__":
    main(sys.argv[1], "--write" in sys.argv)
