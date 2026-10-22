# ThemeScope

An on-demand, end-of-day dashboard for comparing themed equity ETFs and reviewing sourced company watchlists. The 15/20 stock pool is a configurable browsing convention, not a validated trading model. The dashboard does not identify entries or issue buy/sell signals.

## Open the current snapshot

Open [`dist/dashboard.html`](dist/dashboard.html) in a current browser. It is self-contained: HTML, CSS, JavaScript, and the generated snapshot are embedded in one file. Reopening or reloading it does not fetch new data.

## Regenerate

Requirements: Python 3.10 or newer and network access. Collection uses only Python's standard library; Node.js 18 or newer is needed only for the optional JavaScript helper test. No database, backend, secret, paid package, or scheduled automation is needed.

From the repository root:

```sh
python3 scripts/generate_dashboard.py
```

The script makes fresh requests to fund issuers, Yahoo Finance chart, Nasdaq quote summary, and SEC EDGAR submissions. It regenerates:

- `dist/dashboard.html` — standalone interactive dashboard
- `data/latest_snapshot.json` — calculated current snapshot
- `data/raw_inputs.json` — retrieved source payloads and per-source errors for reproducibility
- `data/source_matrix.csv` — consumed fields, sources, methods, dates, limits, fallbacks, and last-run results
- `exports/watchlist_15.csv` and `exports/watchlist_20.csv` — theme-preserving selections
- `exports/tradingview_15.txt` and `exports/tradingview_20.txt` — flat exchange-qualified symbol lists
- `reports/latest_run.md` — run dates, coverage, source failures, and limitations

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

## Current scope and limits

The six configured ETF themes are semiconductors (SMH), cybersecurity (CIBR), clean energy (ICLN), aerospace & defense (XAR), cloud computing (SKYY), and biotechnology (XBI). Official issuer holdings were fetched and tested across VanEck JSON, First Trust HTML, iShares CSV, and State Street XLSX sources. The run report and dashboard show each actual as-of date and current retrieval status.

Business-evidence screening is incomplete across all six themes. Only the explicitly reviewed subset can enter provisional stock selection. Pending and unresolved holdings remain visible, and no full-universe breadth label is published. XBI currently provides ETF-level metrics only because issuer-level screening was not completed; the dashboard does not claim its eligible company universe is empty.

Price history is from Yahoo Finance's accessible but undocumented chart endpoint. Adjusted close is used for total-return-compatible endpoint returns under Yahoo's convention; split-adjusted close is used for trend; raw contemporaneous close and volume are reconstructed from split events for ADV$30. Nasdaq quote summaries do not include a separate market-cap field timestamp, so the cap screen remains provisional. These limitations, source delays, retrieval failures, and current coverage are disclosed in the generated source matrix and run report.

## Verify implementation

```sh
python3 -m unittest discover -s tests -v
node tests/test_dashboard.js
```
