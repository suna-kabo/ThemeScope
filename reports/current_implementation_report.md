# ThemeScope v7 implementation

## Delivered

ThemeScope now ranks the pinned 53 active ETF anchors from price-relative strength and calculates theme breadth from stable, configured stock watchlists. Breadth and watchlist membership do not enter Theme Score, state, or rank. The normal collector uses market/index data, active-anchor prices, and configured stock prices; it does not retrieve SEC filings, research company membership, rebuild theme lists, collect theme ETF holdings, or request AUM and spread data.

The migration preserves 16 existing watchlists with 265 memberships across 257 unique stocks and 8 overlaps. No irrelevant companies were added to fill short lists. The other 37 active exposures remain explicitly unconfigured because no TradingView scanner CSV or intended stock universe was available. The review-only importer is ready at `scripts/maintain_watchlists.py`.

The checked run uses the saved 23 October 2026 market session and performs an offline import/rerender. A live refresh was not completed. Its dashboard is 1.9 MB, primary snapshot 1.1 MB, raw inputs 6.4 MB, and complete bundle 16.3 MB. The bundle includes compressed market-breadth, watchlist, and IWM price histories. The ignored local price cache was seeded from the saved run with 2,671 price histories and 670 market-cap facts, without network requests.

An explicit comparison against the saved v6.2 snapshot found no changes to returns, Current, Medium, Theme Score, state, or current and historical ranks for the 53 exposures. The refreshed breadth and stock display now use configured watchlists.

## Verification

- `python3 -m unittest discover -s tests -v`: 78 tests passed.
- Python compile check, `node --check static/dashboard.js`, `node tests/test_dashboard.js`, `git diff --check`, and `tests/validate_output.py output` passed.
- Chromium 154 browser checks passed across desktop and mobile widths. Theme and stock table columns align, tooltips and downloads work, JavaScript errors were zero, and opening/reloading made no external requests.

## Remaining input

Please provide the TradingView scanner CSV or intended stock universe to curate the remaining 37 lists. The importer writes proposed changes and a diff for review; it does not overwrite the approved configuration. The newest completed US market session in the available data is 23 October 2026.
