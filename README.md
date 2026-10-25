# ThemeScope

ThemeScope is an end-of-day dashboard for US market context and ETF relative strength. It uses SPY, QQQ, IWM, market breadth, EMA context and VIX; ranks sector and theme anchor ETFs; and compares configured stock watchlists with their related ETF. It does not generate entries, trade recommendations, allocations or orders.

## Generate and rerender

Run a normal market refresh after the v7.1 configuration audit passes:

```sh
python3 scripts/generate_dashboard.py --output-dir output
```

The command runs the release audit before collecting data. It stops without network requests while the 53 watchlists are incomplete. Once approved, the collector reuses the ignored `cache/` price and universe files, updates only missing price sessions where supported, and saves a dated dashboard. Failed collection preserves the last successful publication.

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

Approved many-to-many memberships are stored in `config/theme_watchlists.json`. The current configuration has one reviewed record for each of the 53 active exposures: 44 complete lists and 9 documented `reviewed_short` lists. All 11 sectors have 20 members; complete ordinary themes have 15–20. Every member has a company-specific reason and saved eligibility facts.

Import the maintenance CSV to create an eligibility proposal and a 53-theme review template:

```sh
python3 scripts/maintain_watchlists.py --input csv_2026-10-15.csv --maintenance-date 2026-10-15
```

The CSV is a candidate universe, not a theme assignment, and its performance columns are ignored. The 15 October 2026 CSV has been used for the initial configuration. Future dashboard refreshes use the approved saved lists and do not require that CSV. For optional maintenance, complete the generated mapping with explicit `Core` or `Related` relationships and company-specific reasons, then apply it with `--review <completed-map.json> --apply`. Applying is rejected unless all 53 lists pass the deterministic release audit.

Check the configuration and optional generated bundle with:

```sh
python3 scripts/audit_release.py
python3 scripts/audit_release.py --snapshot output/latest_snapshot.json --registry-audit output/registry_audit.csv --output output/release_audit.json
```

An incomplete audit exits nonzero. A successful bundle contains `release_audit.json`, `membership_review.csv`, and `theme_watchlist_summary.csv`.

Stock price, average dollar volume, market-cap and history filters are configured under `settings.watchlist_stock_filters` in `config/themes.json`. Ordinary dashboard refresh does not conduct company research, retrieve SEC filings, request daily market caps, or reconstruct memberships from ETF holdings.

## Methodology

Current is the 21-session anchor ETF excess-return percentile versus SPY. Medium is the 63-session percentile. Theme Score remains `0.60 × Current + 0.40 × Medium`; four states compare those scores with the configured 50 threshold. Breadth, membership and market context never enter Theme Score, state or rank. Average ranks resolve exact ties.

Theme breadth uses the fixed configured stock list. EMA breadth is above-EMA members divided by valid configured members, with at least 8 valid histories and 80% membership coverage. The table shows the percentage and above/valid count; missing lists or price completeness produce a short reason. Five-session breadth change evaluates the same current membership at both observations. SPY, QQQ and IWM index breadth stays separate; IWM holdings remain a practical Russell 2000 proxy.

The currently eligible 53 ETF anchors are recorded in `config/active_anchors.json`; 12 inactive exposures are represented by 19 rejected candidate ETF rows. Anchor price history, instrument and the `$10 million` ADV30 floor remain separate eligibility checks. Anchor rankings do not depend on stock availability.

## Checks and files

Run the repository checks with:

```sh
python3 -m unittest discover -s tests -v
python3 -m compileall -q src scripts tests
node --check static/dashboard.js
node tests/test_dashboard.js
```

The browser check requires Playwright and Chromium. Generated runs belong in ignored `output/` or `dist/`; the persistent `cache/` is ignored by Git. Theme breadth snapshot and export fields use `theme_breadth21_*` and `theme_breadth50_*`; index breadth remains a separate market-context measure.

Key files:

- `config/themes.json`: exposure records, ranking, eligibility and watchlist-maintenance settings.
- `config/active_anchors.json`: the 53 active anchor choices and retained inactive-candidate notes.
- `config/theme_watchlists.json`: approved stable theme membership.
- `config/sources.json`: price and index-universe sources.
- `src/themescope/collect_v7.py`: lean normal-refresh collector.
- `src/themescope/price_cache.py`: persistent compressed history and universe cache.
- `src/themescope/watchlists.py`: membership validation, stock metrics and watchlist breadth.
- `scripts/maintain_watchlists.py`: one-time eligibility import, explicit theme assignment, and audited apply workflow.
- `scripts/audit_release.py`: deterministic nonzero-on-failure v7.1 release audit.
- `scripts/generate_dashboard.py`: calculations, exports, offline dashboard and staged publication.
