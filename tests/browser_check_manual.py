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
            context = browser.new_context(viewport={"width": 1440, "height": 1000}, has_touch=True)
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("request", lambda request: requests.append(request.url))
            page.goto(url)
            page.wait_for_timeout(300)
            assert not errors, errors
            external = [request for request in requests if urlparse(request).hostname not in {"127.0.0.1", None}]
            assert not external, external
            assert page.locator(".side-nav [data-page]").count() == 3
            assert page.locator("#cards .market-card").count() == 3
            assert page.locator(".volatility-section").is_hidden()
            assert page.locator("#market-direction h2").inner_text() == snapshot["market_classification"]["direction"]
            body = page.inner_text("body")
            assert "5-session change" not in body
            assert "IWM holdings Breadth" not in body
            assert "Russell 2000 Breadth" in body
            page.click('.side-nav [data-page="sectors-themes"]')
            assert page.locator("#theme-body tr[data-theme]").count() == len(snapshot["themes"])
            headers = page.locator("#theme-head").inner_text()
            for label in ("Current", "Medium", "1W", "1M", "3M", "EMA50"):
                assert label in headers
            assert "Δ5D" not in headers and "Rk−5D" not in headers
            info = page.locator("#theme-head .info-button").first
            info.focus()
            page.wait_for_timeout(50)
            tooltip = page.locator("#themescope-tooltip")
            assert tooltip.is_visible() and tooltip.inner_text().strip()
            page.keyboard.press("Escape")
            info.tap()
            page.wait_for_timeout(50)
            assert tooltip.is_visible() and tooltip.inner_text().strip()
            page.click('.side-nav [data-page="watchlist"]')
            headers = page.locator("#stock-head").inner_text()
            for label in ("1D %", "1W %", "1M %", "3M %", "ATR%14", "ADV$30", "Turnover 1D", "Rel Vol", "Sector / Industry", "Earnings"):
                assert label in headers
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
    print(json.dumps({"javascript_errors": errors, "automatic_external_requests": 0, "tabs": 3, "themes": len(snapshot["themes"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
