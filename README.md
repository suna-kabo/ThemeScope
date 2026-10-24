# ThemeScope live run — 2026-10-23

This is the live public-source run generated on 2026-10-24 for the latest completed US market session, Friday, 2026-10-23. The dashboard is a self-contained HTML file and works offline after download.

## Download

- [Standalone dashboard](https://github.com/suna-kabo/ThemeScope/raw/refs/heads/themescope-downloads-2026-10-24/dashboard.html) — 3.1 MB.
- [Complete run ZIP](https://github.com/suna-kabo/ThemeScope/raw/refs/heads/themescope-downloads-2026-10-24/run_bundle.zip) — 22 MB; includes the dashboard, run report, snapshot, source inputs, IWM history sidecar, exports, and diagnostics.
- [Snapshot JSON](https://github.com/suna-kabo/ThemeScope/raw/refs/heads/themescope-downloads-2026-10-24/latest_snapshot.json) — 28 MB.
- [Run report](latest_run.md).

Open a download link in a browser. If GitHub shows a file page, use its **Download raw file** control. The `screenshots/` folder contains before-and-after captures at 1600px and 390px widths; the after set also includes the horizontally scrolled table and the ICLN coverage row.

## Availability in this run

- SPY breadth is valid: 338/499 above EMA21 (67.7%) and 300/497 above EMA50 (60.4%). Its constituent list is labeled as a current observed list, not an official point-in-time universe.
- QQQ and IWM breadth are valid. IWM uses current iShares holdings as a practical Russell 2000 proxy.
- Thirty-six themes have no configured holdings breadth source. Clean Energy (ICLN) has a configured source but remains unavailable at 14/103 holdings with usable price data, below the 80% threshold.
- Thirty-seven themes have no configured stock drilldown and remain ETF-only. Their ETF scores, ranks, returns, and states are still available.

See [the full availability list](availability.md) for the affected themes.

The release files are kept on this dedicated branch to keep generated outputs separate from source code.
