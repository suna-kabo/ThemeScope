#!/usr/bin/env python3
"""Browser acceptance check for the local manual CSV dashboard."""

from __future__ import annotations

import argparse
import http.server
import json
import shutil
import socketserver
import threading
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("dashboard", type=Path)
    args = parser.parse_args()
    dashboard = args.dashboard.resolve()
    snapshot = json.loads((dashboard.parent / "latest_snapshot.json").read_text(encoding="utf-8"))

    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *_args):
            pass

    handler = lambda *a, **kw: Quiet(*a, directory=str(dashboard.parent), **kw)
    server = socketserver.TCPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_address[1]}/{dashboard.name}"
    errors: list[str] = []
    requests: list[str] = []
    try:
        with sync_playwright() as playwright:
            options = {"headless": True, "args": ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]}
            chromium = shutil.which("chromium") or shutil.which("chromium-browser")
            if chromium:
                options["executable_path"] = chromium
            browser = playwright.chromium.launch(**options)
            context = browser.new_context(viewport={"width": 1536, "height": 864}, has_touch=True)
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("request", lambda request: requests.append(request.url))
            page.goto(url)
            page.wait_for_timeout(300)
            assert not errors, errors
            external = [request for request in requests if urlparse(request).hostname not in {"127.0.0.1", None}]
            assert not external, external
            assert page.locator(".side-nav [data-page]").count() == 4
            assert page.locator("#cards .market-card").count() == 3
            assert page.locator(".volatility-section").is_hidden()
            assert page.locator("#market-direction h2").inner_text() == snapshot["market_classification"]["direction"]
            assert page.locator("#market-direction .open-plan").is_visible()
            page.click("#market-direction .open-plan")
            assert page.locator("#daily-plan").is_visible()
            assert page.locator("#decision-path .decision-row").count() == 7
            assert page.locator("#daily-priorities .priority-card").count() == 4
            assert page.locator("#daily-classification").inner_text() == snapshot["decision"]["market_classification"]
            first_theme_link = page.locator("#daily-priorities [data-daily-theme]").first
            target_theme = first_theme_link.get_attribute("data-daily-theme")
            first_theme_link.click()
            assert page.locator("#watchlist").is_visible()
            assert page.locator("#watchlist-theme-selector").input_value() == target_theme
            page.go_back()
            assert page.locator("#daily-plan").is_visible()
            body = page.inner_text("body")
            assert "5-session change" not in body
            assert "IWM holdings Breadth" not in body
            assert "Russell 2000 Breadth" in body
            page.click('.side-nav [data-page="sectors-themes"]')
            assert page.locator("#theme-body tr[data-theme]").count() == len(snapshot["themes"])
            headers = page.locator("#theme-head").inner_text()
            for label in ("Current", "Medium", "1W", "1M", "3M", "EMA50"):
                assert label in headers
            assert "Δ5D" not in headers and "Rk−5D" not in headers and "Facts" not in headers and "Type" not in headers
            assert page.locator("#theme-cols col").count() == 14
            assert page.locator("#theme-head th").count() == 14
            assert page.locator("#theme-body tr[data-theme]").first.locator("td").count() == 14
            assert page.locator("#theme-body .type-tag").count() == len(snapshot["themes"])
            assert page.locator("#theme-body .breadth-unavailable-cell small").count() == 0
            assert page.locator("#theme-body .score-chip:not(.score-na)").count() > 0
            info = page.locator("#theme-head .info-button").first
            assert info.get_attribute("title") is None
            assert page.locator("#themescope-tooltip").count() == 1
            info.focus()
            page.wait_for_timeout(50)
            tooltip = page.locator("#themescope-tooltip")
            assert tooltip.is_visible() and tooltip.inner_text().strip()
            page.keyboard.press("Escape")
            info.tap()
            page.wait_for_timeout(50)
            assert tooltip.is_visible() and tooltip.inner_text().strip()
            box = tooltip.bounding_box()
            assert box and box["x"] >= 0 and box["y"] >= 0 and box["x"] + box["width"] <= 1536 and box["y"] + box["height"] <= 864
            page.click('.side-nav [data-page="market"]')
            assert tooltip.is_hidden()
            action_box = page.locator("#market-direction").bounding_box()
            cards_box = page.locator("#cards").bounding_box()
            assert action_box and cards_box and 20 <= cards_box["y"] - (action_box["y"] + action_box["height"]) <= 25
            assert page.locator("#cards .breadth-value.breadth-positive, #cards .breadth-value.breadth-negative").count() == 6
            # Required screenshot and alignment checks in both modes.
            artifact_dir = dashboard.parent / "browser_artifacts"
            artifact_dir.mkdir(exist_ok=True)
            for mode in ("dark", "light"):
                page.set_viewport_size({"width": 1536, "height": 864})
                if page.locator("html").get_attribute("data-mode") != mode:
                    page.click("#mode")
                for width, height in ((1920, 1080), (1536, 864), (1366, 768), (390, 844)):
                    page.set_viewport_size({"width": width, "height": height})
                    page.click('.side-nav [data-page="sectors-themes"]')
                    page.wait_for_timeout(50)
                    page.screenshot(path=str(artifact_dir / f"themes-{mode}-{width}x{height}.png"), full_page=True)
                    if width in (1920, 1536):
                        assert page.locator(".theme-table-wrap").evaluate("e => e.scrollWidth <= e.clientWidth + 1")
                        assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")
                        head_boxes = page.locator("#theme-head th").evaluate_all("els => els.map(e => ({x:e.getBoundingClientRect().x,w:e.getBoundingClientRect().width}))")
                        row_boxes = page.locator("#theme-body tr[data-theme]").first.locator("td").evaluate_all("els => els.map(e => ({x:e.getBoundingClientRect().x,w:e.getBoundingClientRect().width}))")
                        assert len(head_boxes) == len(row_boxes) == 14
                        assert all(abs(a["x"] - b["x"]) < .6 and abs(a["w"] - b["w"]) < .6 for a, b in zip(head_boxes, row_boxes))
                for page_id in ("market", "daily-plan"):
                    for width, height in ((1920, 1080), (1536, 864)):
                        page.set_viewport_size({"width": width, "height": height})
                        page.click(f'.side-nav [data-page="{page_id}"]')
                        page.wait_for_timeout(30)
                        page.screenshot(path=str(artifact_dir / f"{page_id}-{mode}-{width}x{height}.png"), full_page=True)
            page.set_viewport_size({"width": 1536, "height": 864})
            page.click('.side-nav [data-page="sectors-themes"]')
            page.select_option("#theme-type", "Theme")
            page.click('#theme-head button[data-sort="theme_score"]')
            saved_sort = page.locator('#theme-head th[aria-sort="ascending"] button[data-sort]').get_attribute("data-sort")
            page.click('.side-nav [data-page="daily-plan"]')
            page.go_back()
            assert page.locator("#sectors-themes").is_visible()
            assert page.locator("#theme-type").input_value() == "Theme"
            assert page.locator('#theme-head th[aria-sort="ascending"] button[data-sort]').get_attribute("data-sort") == saved_sort
            page.emulate_media(reduced_motion="reduce")
            assert page.locator("#sectors-themes").evaluate("e => getComputedStyle(e).animationName") == "none"
            page.emulate_media(reduced_motion="no-preference")
            page.set_viewport_size({"width": 1536, "height": 864})
            page.click('.side-nav [data-page="watchlist"]')
            headers = page.locator("#stock-head").inner_text()
            for label in ("1D %", "1W %", "1M %", "3M %", "ATR%14", "ADV$30", "Turnover 1D", "Rel Vol", "Sector / Industry", "Earnings"):
                assert label in headers
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
    print(json.dumps({"javascript_errors": errors, "automatic_external_requests": 0, "tabs": 4, "themes": len(snapshot["themes"]), "screenshots": 16}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
