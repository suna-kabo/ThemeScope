# ThemeScope

ThemeScope is an end-of-day dashboard for US market context and ETF relative strength. It uses SPY, QQQ, IWM, market breadth, EMA context and VIX; ranks sector and theme anchor ETFs; and compares configured stock watchlists with their related ETF. It does not generate entries, trade recommendations, allocations or orders.

## Generate and rerender

Run a normal market refresh with:

```sh
python3 scripts/generate_dashboard.py --output-dir output
```

The collector reuses the ignored `cache/` price and universe files, updates only missing price sessions where supported, and saves a dated dashboard. A same-session rerender uses the cache. Failed collection preserves the last successful publication.

Rerender a saved bundle without network access with:

```sh
python3 scripts/generate_dashboard.py --import-run output/run_bundle.zip --output-dir output
```

The run bundle includes compact snapshots, user-facing CSVs, the approved watchlist and anchor configuration, and compressed price-history sidecars. The dashboard itself is self-contained and works offline.

If migrating from an existing run, the local cache can be seeded once without network access:

```sh
python3 scripts/seed_price_cache.py --input output
```

## Maintain stock watchlists

Approved many-to-many memberships are stored in `config/theme_watchlists.json`. Current data migrates 16 populated exposure lists (265 memberships, 257 unique stocks, 8 overlapping tickers). The other 37 active exposures stay explicitly unconfigured until their stock universe is reviewed. Lists may contain fewer than 15 stocks when that is the relevant liquid universe; the default display is 15 and capacity is 20.

Import a TradingView scanner export to create a review proposal:

```sh
python3 scripts/maintain_watchlists.py --input tradingview.csv
```

This writes a JSON proposal and Markdown summary. It never overwrites the approved configuration. Include a theme or theme ID column to produce per-theme additions and removals; otherwise the proposal marks theme assignment for review. Missing market-cap or history fields remain review items.

Stock price, average dollar volume, market-cap and history filters are configured under `settings.watchlist_stock_filters` in `config/themes.json`. Ordinary dashboard refresh does not conduct company research, retrieve SEC filings, request daily market caps, or reconstruct memberships from ETF holdings.

## Methodology

Current is the 21-session anchor ETF excess-return percentile versus SPY. Medium is the 63-session percentile. Theme Score remains `0.60 × Current + 0.40 × Medium`; four states compare those scores with the configured 50 threshold. Breadth, membership and market context never enter Theme Score, state or rank. Average ranks resolve exact ties.

Theme breadth uses the fixed configured stock list. EMA breadth is above-EMA members divided by valid configured members, with at least 8 valid histories and 80% membership coverage. The table shows the percentage and above/valid count; missing lists or price completeness produce a short reason. Five-session breadth change evaluates the same current membership at both observations. SPY, QQQ and IWM index breadth stays separate; IWM holdings remain a practical Russell 2000 proxy.

The currently eligible 53 ETF anchors are recorded in `config/active_anchors.json`; 12 previously inactive registry records remain inactive. Anchor price history, instrument and the `$10 million` ADV30 floor remain separate eligibility checks. Anchor rankings do not depend on stock availability.

## Checks and files

Run the repository checks with:

```sh
python3 -m unittest discover -s tests -v
python3 -m compileall -q src scripts tests
node --check static/dashboard.js
node tests/test_dashboard.js
```

The browser check requires Playwright and Chromium. Generated runs belong in ignored `output/` or `dist/`; the persistent `cache/` is ignored by Git. See `reports/v7_migration_report.md` for the current migration counts and remaining scanner-input request.

Key files:

- `config/themes.json`: exposure records, ranking, eligibility and watchlist-maintenance settings.
- `config/active_anchors.json`: the 53 active anchor choices and retained inactive-candidate notes.
- `config/theme_watchlists.json`: approved stable theme membership.
- `config/sources.json`: price and index-universe sources.
- `src/themescope/collect_v7.py`: lean normal-refresh collector.
- `src/themescope/price_cache.py`: persistent compressed history and universe cache.
- `src/themescope/watchlists.py`: membership validation, stock metrics and watchlist breadth.
- `scripts/maintain_watchlists.py`: review-only TradingView import.
- `scripts/generate_dashboard.py`: calculations, exports, offline dashboard and staged publication.
