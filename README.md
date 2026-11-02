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

The dashboard is self-contained. The output directory also contains `run_audit.json`, canonical JSON/CSV exports, individual TradingView watchlists and their ZIP, optional flat broad scans and `run_bundle.zip`. These files remain local unless the user explicitly moves them.

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
python3 tests/browser_check_navigation.py output/manual_csv/dashboard.html
python3 tests/browser_check_terminal.py output/manual_csv/dashboard.html
python3 tests/browser_check_manual.py output/manual_csv/dashboard.html
python3 tests/check_scanning_exports.py output/manual_csv
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

Individual sector/theme files are the primary research export: one per configured active exposure, named ETF first (for example `SMH_Semiconductors.txt`), with the resolved ETF anchor followed by up to 20 configured stocks. They have no section tokens. Download all from `individual_theme_watchlists.zip`, or download the selected Watchlist. Cross-theme memberships remain complete in separate files. Update these lists only when memberships or validated identifiers change.

**Daily Data Stocks — export CSV only** (`tradingview_configured_stocks.txt`) is the separate stock-only, section-free, deduplicated collection list. Import it into TradingView to export daily data for all configured members without screener filters. It does not require reimporting individual research lists every day. Candidate screening CSV remains optional maintenance input; generation still requires only the existing five CSV roles. Missing daily rows remain configured and are reported.

The five versioned groups in `config/watchlist_exports.json`, plus the retained all-theme filename, are optional broad scans. They contain unique instruments without theme sections. The user confirmed through round-trip exports that TradingView deduplicated repeated symbols in a grouped list, losing later membership occurrences. The raw round-trip artifacts are unavailable in this session, so this observation is user-confirmed rather than independently reproduced here; it is not a guarantee about future platform versions.

Daily Plan previews five themes per research group, reports the full count and offers Show all / Show less and Score order. Short groups default to ascending Score; long and observation groups default to descending Score with stable identity ties. Preview order does not imply entry readiness. Expected earnings is a visible section based independently on configured members of final Primary themes, deduplicated by validated instrument identity, from the as-of session through seven calendar days later. Unknown dates remain accessible. Daily Primary Candidates and their dedicated exports have been removed.

Watchlist initially opens in Relative Strength and remembers an explicit view choice. Its # column is stable configured membership position in both views. Matching TradingView stock-minus-selected-ETF differences are percentage points. Navigation restores each page's scroll and each theme/view's table scroll, search and sort; priority expansion and methodology state survive navigation. Local UI state is namespaced by schema/session and storage failures are tolerated.

The interface uses neutral charcoal, restrained amber controls, local monospace data and bundled Inter explanations. Light mode and mobile tables remain available. See `PRODUCT.md`, `DESIGN.md` and `docs/navigation_export_release_audit.md`.

Each individual file contains its anchor in addition to configured stock slots. Optional broad scans and Daily Data Stocks split deterministically at the configured 1,000-instrument limit. All files reuse `config/tradingview_symbols.json`; unresolved identities fail generation rather than acquiring guessed prefixes. Actual imports of the revised files have not been performed in a TradingView account.

Sectors & Themes includes sortable **1D %** directly after ETF. It displays the existing canonical fractional `daily_change` as percent; full and visible CSV exports use `change_1d_pct` in percentage units. Score, State, rank and Priority do not use this column.

Watchlist's upper **Find** field navigates by ticker, company, theme or ETF anchor. Stocks have separate results for every theme membership, including missing daily rows. Results rank exact ticker/anchor, prefix, substring, then text, with stable ties and no Score/Performance influence. Results initially show up to 12 per group, with exact counts and Show more. Arrow keys, Enter, Escape, mouse and touch are supported. Stock selection keeps the chosen view, reveals/highlights the row and clears only hiding filters; Back restores the previous filters, sort and scroll. The lower Search field continues to filter the selected Watchlist.
