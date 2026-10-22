# ThemeScope

An on-demand, end-of-day dashboard for comparing themed equity ETFs and reviewing sourced company watchlists. The 15/20 stock pool is a configurable browsing convention, not a validated trading model. The dashboard does not identify entries or issue buy/sell signals.

## Run it on your device

Requirements: Python 3.10 or newer and an internet connection. From a clone of this repository, run:

Windows (Command Prompt or PowerShell):

```bat
py -3 -m pip install tzdata
py -3 scripts/generate_dashboard.py
```

macOS / Linux:

```sh
python3 scripts/generate_dashboard.py
```

Open `output/dashboard.html` in a browser. Each run writes its dashboard, actual retrieved inputs, source matrix, report, CSVs, TradingView lists, and `run_bundle.zip` into `output/` on that device. The dashboard's **Download complete run ZIP** button saves the run's files through the browser to the user's normal Downloads location. The output directory is ignored by Git, so running the program does not create or update a branch.

To choose another local output directory, pass `--output-dir`, for example `python3 scripts/generate_dashboard.py --output-dir ~/Downloads/themescope-run`.

`dist/dashboard.html` is the checked-in demonstration snapshot from the implementation run. Reopening it does not fetch new data. To get current data, run the generator locally as above.

## Regenerate

Collection uses Python's standard library; Windows also needs the IANA time-zone data package `tzdata` (installed once above); Node.js 18 or newer is needed only for the optional JavaScript helper test. No database, hosted backend, secret, paid package, or scheduled automation is needed.

The script makes fresh requests to fund issuers, Yahoo Finance chart, Nasdaq quote summary, and SEC EDGAR submissions. It creates locally under `output/`:

Yahoo chart requests are serialized with a 1.5-second pause to reduce HTTP 429 rate-limit responses. A full run may take two to five minutes, depending on provider response times and retries.

- `dashboard.html` — standalone interactive dashboard for that run
- `latest_snapshot.json` and `raw_inputs.json` — calculated snapshot, retrieved source payloads, and per-source errors
- `source_matrix.csv` — consumed fields, sources, methods, dates, limits, fallbacks, and last-run results
- `watchlist_15.csv` and `watchlist_20.csv` — theme-preserving selections
- `tradingview_15.txt` and `tradingview_20.txt` — flat exchange-qualified symbol lists
- `latest_run.md` — run dates, coverage, source failures, and limitations
- `run_bundle.zip` — all the run files above, ready to save or share

The dashboard also downloads the active theme's filtered CSV and TradingView text directly through the browser. `output/` is excluded from Git. The program never commits or pushes run outputs.

Wait for `SUCCESS: data date ...` and for your terminal prompt to return. Only then open `output/dashboard.html`. Opening or reloading it makes no market-data requests and never retries collection.

A refresh is published only after validation: complete source retrieval, a dated shared session, valid aligned SPY/QQQ and theme price/return metrics, and at least one provisional stock selection. Incomplete business screening is disclosed separately. Files are staged before publication; publication errors roll back changed files. Unrelated files in a custom output directory are preserved.

On retrieval or validation failure, the script prints `GENERATION FAILED`, exits with code 1, and writes `refresh_status.json` plus `failed_refresh.md`. The last successful dashboard, raw data, exports and original date remain unchanged. If the existing dashboard is itself invalid, it is retained as `rejected_dashboard.html`, not presented as a successful export. With no successful prior snapshot, no dashboard is produced. Failed refresh information is separate because the offline HTML never reads mutable files or refreshes itself.

For an explicitly dated real-data fallback, import a previously successful run directory (containing both JSON files):

```bat
py -3 scripts/generate_dashboard.py --import-run data
```

This uses the checked-in real demonstration inputs, makes **no network requests**, retains their original collection time/data date, and marks the result as imported. You can instead point `--import-run` at an extracted trusted `run_bundle.zip`. Imports are validated, not relabeled as current data.

Yahoo requests use two hosts with the same schema and adjustment convention. After HTTP 429, a host receives no further requests in that process. Other transient failures have bounded retries. VanEck can use the verified direct official dataset if fund-page discovery fails. Stooq's tested endpoint returned a browser challenge; Alpha Vantage's demo did not supply the requested adjusted series. Neither is substituted. The SEC freshness check blocks a provisional stock candidate when a newer annual report is found or its feed cannot be checked. The check does not classify 8-K disclosures.

TradingView text is written as one `EXCHANGE:TICKER` symbol per line and checked locally for mappings and duplicates. This environment did not exercise TradingView's import dialog, so importer behavior should be confirmed against the current client.

## Project layout

- `config/themes.json` — stable theme registry, ETF anchors, scope, and thresholds
- `config/evidence_reviews.json` — issuer evidence excerpts, filings, and review status
- `config/anchor_comparisons.json` — mandate-fit alternatives considered for two anchors
- `src/themescope/sources.py` — replaceable public-source adapters
- `src/themescope/metrics.py` — return, excess, relative-state, trend, breadth, split, and selection calculations
- `src/themescope/collect.py` — retrieval, eligibility, provisional breadth, and snapshot assembly
- `static/dashboard_template.html`, `static/dashboard.css`, `static/dashboard.js` — standalone presentation assets
- `tests/` — Python metric acceptance checks and Node dashboard/export checks

## Open-source distribution

To make the program open source, publish the source repository publicly and add a license you choose. Without a license, other people generally do not have permission to reuse or redistribute the code. MIT is a short permissive option; Apache-2.0 adds an express patent grant; GPL-3.0 requires distributed derivative works to keep the same license. A GitHub Pages site can host a demonstration snapshot, but it cannot run this Python data collector on each visitor's click. The documented local run keeps retrieval and generated files on each user's device, and the dashboard downloads the run bundle to that user's browser.

## Current scope and limits

The six configured ETF themes are semiconductors (SMH), cybersecurity (CIBR), clean energy (ICLN), aerospace & defense (XAR), cloud computing (SKYY), and biotechnology (XBI). Official issuer holdings were fetched and tested across VanEck JSON, First Trust HTML, iShares CSV, and State Street XLSX sources. The run report and dashboard show each actual as-of date and current retrieval status.

Business-evidence screening is incomplete across all six themes. Only the explicitly reviewed subset can enter provisional stock selection. Pending and unresolved holdings remain in the diagnostic JSON, and no full-universe breadth label is published. XBI now screens mapped holdings against the industry exclusion: biotechnology classifications are excluded; other industries and unmapped identifiers remain pending evidence review. Its zero stock selections do not establish an empty eligible universe.

Price history is from Yahoo Finance's accessible but undocumented chart endpoint. Adjusted close is used for total-return-compatible endpoint returns under Yahoo's convention; split-adjusted close is used for trend; raw contemporaneous close and volume are reconstructed from split events for ADV$30. Nasdaq quote summaries do not include a separate market-cap field timestamp, so the cap screen remains provisional. These limitations, source delays, retrieval failures, and current coverage are disclosed in the generated source matrix and run report.

## Verify implementation

```sh
python3 -m unittest discover -s tests -v
node tests/test_dashboard.js
```

Browser verification (optional development dependencies: Playwright and Chromium):

```sh
python3 tests/browser_check.py output/dashboard.html
```

The check uses Chromium DevTools Protocol Network events, the same network backend as the Network panel. It exercises opening/reloading, controls, downloads and theme preference. Managed Chromium in the development environment blocks `file://`, so it serves the exact HTML over loopback and checks for zero external requests. No server is needed to open the export on an ordinary local browser. The document also has a restrictive Content Security Policy (`connect-src 'none'`).

Return columns use 5 / 21 / 63 trading sessions. Returns use adjusted close; daily change, price charts and EMA distances use split-adjusted close. Excess is a percentage-point difference. Theme ranks retain their full-universe positions through filtering. Stock ranks apply within the chosen fixed selection pool; sorting never chooses new candidates. “All reviewed eligible” is explicitly incomplete.
