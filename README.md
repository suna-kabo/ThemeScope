# ThemeScope

An on-demand, end-of-day dashboard for comparing themed equity ETFs and reviewing sourced company watchlists. The 15/20 stock pool is a configurable browsing convention, not a validated trading model. The dashboard does not identify entries or issue buy/sell signals.

## Run it on your device

Requirements: Python 3.10 or newer and an internet connection. From a clone of this repository, run:

```sh
python3 scripts/generate_dashboard.py
```

Open `output/dashboard.html` in a browser. Each run writes its dashboard, actual retrieved inputs, source matrix, report, CSVs, TradingView lists, and `run_bundle.zip` into `output/` on that device. The dashboard's **Download run files (.zip)** button saves the run's files through the browser to the user's normal Downloads location. The output directory is ignored by Git, so running the program does not create or update a branch.

To choose another local output directory, pass `--output-dir`, for example `python3 scripts/generate_dashboard.py --output-dir ~/Downloads/themescope-run`.

`dist/dashboard.html` is the checked-in demonstration snapshot from the implementation run. Reopening it does not fetch new data. To get current data, run the generator locally as above.

## Regenerate

Collection uses only Python's standard library; Node.js 18 or newer is needed only for the optional JavaScript helper test. No database, hosted backend, secret, paid package, or scheduled automation is needed.

The script makes fresh requests to fund issuers, Yahoo Finance chart, Nasdaq quote summary, and SEC EDGAR submissions. It creates locally under `output/`:

- `dashboard.html` — standalone interactive dashboard for that run
- `latest_snapshot.json` and `raw_inputs.json` — calculated snapshot, retrieved source payloads, and per-source errors
- `source_matrix.csv` — consumed fields, sources, methods, dates, limits, fallbacks, and last-run results
- `watchlist_15.csv` and `watchlist_20.csv` — theme-preserving selections
- `tradingview_15.txt` and `tradingview_20.txt` — flat exchange-qualified symbol lists
- `latest_run.md` — run dates, coverage, source failures, and limitations
- `run_bundle.zip` — all the run files above, ready to save or share

The dashboard also downloads the active theme's filtered CSV and TradingView text directly through the browser. `output/` is excluded from Git. The program never commits or pushes run outputs.

If a source is unavailable, dependent values are marked unavailable; the generator does not silently reuse an older snapshot. The SEC freshness check blocks a provisional stock candidate when a newer annual report is found or its feed cannot be checked. The check does not classify 8-K disclosures.

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

Business-evidence screening is incomplete across all six themes. Only the explicitly reviewed subset can enter provisional stock selection. Pending and unresolved holdings remain visible, and no full-universe breadth label is published. XBI currently provides ETF-level metrics only because issuer-level screening was not completed; the dashboard does not claim its eligible company universe is empty.

Price history is from Yahoo Finance's accessible but undocumented chart endpoint. Adjusted close is used for total-return-compatible endpoint returns under Yahoo's convention; split-adjusted close is used for trend; raw contemporaneous close and volume are reconstructed from split events for ADV$30. Nasdaq quote summaries do not include a separate market-cap field timestamp, so the cap screen remains provisional. These limitations, source delays, retrieval failures, and current coverage are disclosed in the generated source matrix and run report.

## Verify implementation

```sh
python3 -m unittest discover -s tests -v
node tests/test_dashboard.js
```
