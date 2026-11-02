# ThemeScope

ThemeScope is an on-demand, offline end-of-day dashboard for US market context, ETF momentum ranking and configured stock watchlists. It does not generate entries, trade recommendations, allocations or orders.

## Manual CSV release

The release accepts five user-selected TradingView CSV exports and makes no network requests during import or when the generated HTML opens. Input roles are explicit; filenames are not interpreted. The declared `--as-of` value is the US market session, even when Hong Kong export filenames show the following calendar day.

Generate the dashboard with:

```sh
python3 scripts/generate_dashboard.py \
  --source tradingview-csv \
  --as-of 2026-10-30 \
  --stock-csv /path/to/Daily_Stock.csv \
  --etf-csv /path/to/Daily_ETF.csv \
  --spy-csv /path/to/SPY_constituents.csv \
  --qqq-csv /path/to/QQQ_constituents.csv \
  --iwm-csv /path/to/Russell_2000_constituents.csv \
  --output-dir output/manual_csv
```

The command validates all five schemas, the session, anchor completeness and breadth-universe sanity checks before calculation. Outputs are staged and validated before publication. A failed import writes `failed_attempt_audit.json` and preserves the previous dashboard and its original session.

The dashboard is self-contained. The output directory also contains `run_audit.json`, canonical JSON/CSV exports, grouped TradingView lists, 53 individual theme lists and `run_bundle.zip`. These files remain local unless the user explicitly moves them.

## Maintain stock watchlists

The fixed many-to-many memberships are in `config/theme_watchlists.json`: all 53 active exposures, up to 20 configured companies per list, with honest shorter lists retained for narrow themes. Daily CSV import does not change this file.

Membership maintenance is separate from daily refresh. The manual import joins CSV rows to configured memberships and never removes an absent member or rebuilds lists from performance, turnover, Sector or Industry. An explicit maintenance workflow remains available:

```sh
python3 scripts/maintain_watchlists.py --input licensed_candidate_snapshot.csv --maintenance-date YYYY-MM-DD
```

Stock price, average dollar volume, market-cap and history filters are configured under `settings.watchlist_stock_filters` in `config/themes.json`. Ordinary dashboard refresh does not conduct company research, retrieve SEC filings, request daily market caps, or reconstruct memberships from ETF holdings.

## Methodology

Current is the ascending percentile of TradingView 1-month Performance. Medium is the ascending percentile of TradingView 3-month Performance, using the same eligible anchor set. Theme Score is `0.60 × Current + 0.40 × Medium`; four states compare those percentiles with 50. TradingView 1-week Performance is context only. EMA, Breadth, stocks and market context never enter Theme Score, State or rank. Average ranks resolve exact ties.

Theme Breadth uses the fixed configured stock list. It requires at least 8 valid rows and 80% configured-list coverage. SPY, QQQ and Russell 2000 Breadth come from their explicitly assigned TradingView exported-universe snapshots. Russell 2000 Breadth and the IWM price-state card remain context only.

SPY and QQQ price consensus plus combined SPY/QQQ Breadth produce the five-level Market classification. IWM, Russell 2000 Breadth and VIX do not vote. VIX is hidden when no optional current input exists.

## Checks and files

Run the repository checks with:

```sh
python3 -m unittest discover -s tests -v
python3 -m compileall -q src scripts tests
node --check static/dashboard.js
node tests/test_dashboard.js
python3 tests/browser_check_manual.py output/manual_csv/dashboard.html
```

The browser check requires Playwright and Chromium. Generated runs belong in ignored `output/` or `dist/`; the persistent `cache/` is ignored by Git. Theme breadth snapshot and export fields use `theme_breadth21_*` and `theme_breadth50_*`; index breadth remains a separate market-context measure.

Key files:

- `config/themes.json`: exposure records, ranking, eligibility and watchlist-maintenance settings.
- `config/active_anchors.json`: the 53 active anchor choices and retained inactive-candidate notes.
- `config/theme_watchlists.json`: approved stable theme membership.
- `config/calendars/xnys_2020_2035_v1.json`: versioned XNYS sessions and actual close times.
- `src/themescope/manual_csv.py`: TradingView header normalization, validation and manual-input calculations.
- `src/themescope/watchlists.py`: membership validation, stock metrics and watchlist breadth.
- `scripts/maintain_watchlists.py`: one-time eligibility import, explicit theme assignment, and audited apply workflow.
- `scripts/generate_dashboard.py`: calculations, exports, offline dashboard and staged publication.

### Local daily rank history

Successful manual imports save `local_history/YYYY-MM-DD.json` inside the output directory and include the current session record in the run ZIP. Reuse the same output directory for daily runs and preserve its `local_history` folder. Δ Rank compares canonical ranks only against the immediately preceding US trading session with matching methodology, ranking configuration and eligible anchors. First runs and missing or incompatible prior sessions show N/A. Same-session reruns replace that date only; failed imports preserve existing dashboard/history. Synthetic history tests use temporary directories.

### Daily scanning files and views

The five versioned groups in `config/watchlist_exports.json` provide stable thematic chart navigation. Use `tradingview_configured_stocks.txt` (stocks only, deduplicated) to collect the daily Stock CSV for every fixed member without screener filters. Candidate screening CSV remains an optional maintenance input; daily generation still requires only the existing five CSV roles. Missing daily rows remain configured and are reported.

Daily Plan contains the deduplicated Daily Primary Candidates view, a complete **Export all Primary stocks** action, and expected earnings within the session date through seven calendar days later. Per-stock anchor selectors retain separate comparisons for overlapping Primary themes. Watchlist offers Performance and Relative Strength views; matching TradingView stock-minus-selected-ETF differences are percentage points. These are browsing tools, not stock entry qualification.

All thematic files count repeated symbols and anchors against the configured 1,000-instrument limit and split only at theme boundaries; stock-only lists split deterministically. Optional individual-theme files preserve complete overlapping memberships. Grouped-section acceptance and duplicate handling have not been tested in a TradingView account.
