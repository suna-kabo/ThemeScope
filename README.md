# ThemeScope v7 — 23 October 2026 run

The dashboard and run bundle were regenerated offline on 24 October 2026 from the saved 23 October US-market session. The run retains the saved market prices; it contains the v7 watchlist breadth and simplified outputs. No later completed market session was available for this release.

## Download

- [Open or download the standalone dashboard](https://github.com/suna-kabo/ThemeScope/raw/refs/heads/themescope-downloads-2026-10-24/dashboard.html) — 1.8 MB; works offline.
- [Download the complete run bundle](https://github.com/suna-kabo/ThemeScope/raw/refs/heads/themescope-downloads-2026-10-24/run_bundle.zip) — 16.3 MB; includes the dashboard, compact snapshot, CSVs, watchlist and anchor configuration, and compressed price histories.
- [Download the latest snapshot](https://github.com/suna-kabo/ThemeScope/raw/refs/heads/themescope-downloads-2026-10-24/latest_snapshot.json) — 1.1 MB.
- Download the [theme ranking CSV](https://github.com/suna-kabo/ThemeScope/raw/refs/heads/themescope-downloads-2026-10-24/themes.csv), [market CSV](https://github.com/suna-kabo/ThemeScope/raw/refs/heads/themescope-downloads-2026-10-24/market.csv), or [15-row](https://github.com/suna-kabo/ThemeScope/raw/refs/heads/themescope-downloads-2026-10-24/watchlist_15.csv) / [20-row](https://github.com/suna-kabo/ThemeScope/raw/refs/heads/themescope-downloads-2026-10-24/watchlist_20.csv) watchlist export.
- Download the [approved theme watchlists](https://github.com/suna-kabo/ThemeScope/raw/refs/heads/themescope-downloads-2026-10-24/theme_watchlists.json) and [active anchors](https://github.com/suna-kabo/ThemeScope/raw/refs/heads/themescope-downloads-2026-10-24/active_anchors.json).
- [Read the latest run report](latest_run.md) or [watchlist migration report](v7_migration_report.md).
- [Browser verification results](browser_verification.json): Chromium 154, zero JavaScript errors and zero external requests.
- [Download the v7 source branch as a ZIP](https://github.com/suna-kabo/ThemeScope/archive/refs/heads/codex/themescope-v6.2-fix.zip).

Open a raw download link in a browser. If GitHub shows a file page, use **Download raw file**. The `screenshots/after/` folder shows the current dashboard at desktop and mobile widths.

## Why some themes have no breadth

The 53 ETF rows and their price-based rankings remain available. Fifteen exposures have valid theme-watchlist breadth for both EMA periods. Thirty-seven have no configured stock list because the intended TradingView scanner CSV was not in the supplied inputs. Clean Energy has a four-stock list; its breadth is unavailable because fewer than eight members have valid data. SPY, QQQ, and IWM index breadth remains available separately.

The v7 migration preserves the existing 16 lists: 265 memberships across 257 unique stocks, with 8 overlapping tickers. Short lists are not padded with unrelated companies. [The availability report](availability.md) and [full missing-list report](v7_migration_report.md) explain what still needs input.

Please provide the TradingView scanner CSV or intended stock universe to curate the remaining 37 lists. The source workflow proposes changes for review and never overwrites the approved list automatically.
