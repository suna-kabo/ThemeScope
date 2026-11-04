> Historical record. Current setup and audit: [README](../README.md) and [repository audit](repository_audit.md). Bundle paths below refer to retained local files or historical Git commits, not current source downloads.

# ThemeScope UI and local-history refinement — 31 October 2026 HKT

Baseline: 88e64c92a320cfed59d995a0356e345ba658d972. Unrelated dirty/untracked files preserved.

## Changes

- `static/dashboard.js`, `static/dashboard_template.html`, `static/dashboard.css`: final guarded Primary categories drive subtle green/red row highlights and the new All/Primary/Secondary/Exceptions/Observation filter. Selected styling overrides the tint, hover strengthens the tint, Primary retains its 3px left marker, and keyboard focus uses an outline. Sorting is unchanged.
- Name cells use a fixed 54px Type column, 8px gap and flexible ellipsized accessible name. Both Sector and Theme names begin at the same measured x position.
- Watchlist now has 14 fixed columns and a colgroup: #, Ticker, Price, 1D, 1W, 1M, 3M, EMA21, EMA50, ATR%14, Avg $Vol30, Turnover 1D, Rel Vol and Earnings. Ticker plus shared info tooltip replaces visible company/exchange/details; canonical company, exchange, relationship, sector, industry and rationale remain available. Earnings includes an accessible ISO date, compact month/day, and a year suffix when it differs from the session year.
- Rows selector, its handlers/view-state fields and selector-dependent slicing removed. All configured members remain available subject to explicit search/EMA filters. TXT exports still use anchor plus stable configured membership, independent of visible sorting/filtering.
- Shared semantic direction/status resolvers color Market, prominent 32px Daily Plan headline, Decision Path and methodology cells. The methodology display now consumes the calculation layer's full Market matrix rather than duplicating it in JavaScript.
- SPY/QQQ/IWM cards share explicit ticker/name, Price/1D grid, equal-width 1W/1M/3M row and divider. Missing-chart dashes and repeated date footers removed. Prices are labeled ETF prices; Russell Breadth describes its supplied exported universe.
- Shared 34px controls/font/padding/radius tokens replace special navigation-control font rules. Obsolete company/details/membership/retired-column CSS removed. Legacy public helper interfaces used by tests remain; they no longer truncate the Watchlist.

## Terminology

The reusable frontend label registry centralizes Avg $Vol30, Turnover 1D, ATR%14 and Rel Vol definitions. `adv30_usd` remains the compatibility machine key for TradingView **Price × Average Volume30**, not mean daily Close × Volume. Turnover 1D is supplied **Price × Volume**, not a verified sum of trades. ATR%14 is volatility context; Relative Volume is a multiple. TradingView 1W/1M/3M Performance remains calendar-period Performance; Current/Medium are 1M/3M percentiles, Score is 60/40 and stock excess values are matching-horizon percentage-point differences. Research Priority remains research context, not an entry signal. Missing numeric values display N/A. Existing legacy return5/21/63 and adv30 machine keys remain for compatibility; visible definitions identify their actual TradingView inputs.

## Local history

`src/themescope/local_history.py` adds schema `themescope-ranking-history-1`. Each successful publication stores `local_history/YYYY-MM-DD.json` under the chosen output directory. The current record is also included in the run ZIP. README documents reusing the same output directory and retaining this folder.

Records contain session, methodology version, SHA-256 ranking-configuration fingerprint, deterministic eligible theme/anchor universe and sorted rows with 1M/3M Performance, Current, Medium, Score and canonical average rank. The fingerprint includes methodology, weights/state settings, percentile method, ranking coverage requirement, configured anchors and eligible anchors. It deliberately excludes daily values and presentation settings.

Δ Rank is immediately preceding US session canonical rank minus current canonical rank, without rounding. It uses the supplied XNYS session calendar, not last-imported date. Missing intervening sessions, changed universe/anchors/methodology/configuration or malformed previous records produce N/A with an explicit reason. Same-session reruns never compare to themselves. A malformed same-session record blocks publication rather than being silently overwritten. Date-keyed writes leave all other history files, including newer sessions, untouched.

History is validated and staged alongside generated output, then published with the existing backup/rollback transaction. An exception after replacing history and before replacing the dashboard rolls back both. This is exception rollback, not a power-loss/concurrent-writer durability guarantee. Standalone HTML embeds the result and needs no history file fetch. No ranking, State, Market, priority or membership formula changed.

## Verification

- Full Python suite: **148 passed**, 3.550s. Node helper tests and JavaScript syntax check passed; Python compile check passed.
- `tests/test_local_history.py`: first run, missing intervening session, two-session fractional ties, invariance of existing theme values, universe/anchor/weight changes, same-session baseline rejection, corrupt history preservation, newer-record preservation, final long/short Primary categories after EMA50 guard.
- `tests/check_history_publication.py output/manual_csv/latest_snapshot.json`: real five-CSV CLI publication into temporary storage, first-run N/A; explicit synthetic previous-session record and second publication; unchanged Score/State/Priority/rank; injected final-dashboard publication failure rolls back every prior artifact and both history records. Synthetic records never enter real output history.
- Real manual CSV command rerun with all latest supplied files and explicit US session **2026-10-30**. Generator measured runtime **0.389665s**. Inputs remain Stock 1535, ETF 56, SPY 503, QQQ 101, Russell 1921; all 53 anchors present. All 53 real Δ Rank values are N/A because no real comparable 2026-10-29 snapshot exists. No real prior-day movement is claimed.
- Real CLI rejection tests for missing file/header, duplicate symbol, NaN required number, missing anchor and invalid session preserve prior output; low Breadth coverage remains unavailable without altering unanimous price classification. Network-forbidden calculation still passes.
- `tests/browser_check_manual.py output/manual_csv/dashboard.html`: four-page navigation, Back state, priority filtering, canonical Primary counts, aligned Type/name starts, no Rows selector, full member availability, ticker info focus/touch/Escape, Previous/Next, configured-order TXT download, consistent control heights/font families, aligned Market metric rows and reduced motion pass. Zero JavaScript errors and zero automatic external requests.
- **32 screenshots captured**, light/dark at **1920×1080, 1536×864, 1366×768 and 390×844** across all four pages. Screenshots inspected directly at 1536 and through labeled contact sheets for the complete viewport/mode set. Both tables fit at 1920 and 1536 with Earnings visible and no horizontal scroll; header/body x coordinates agree within 0.6px. Narrow tables scroll intentionally. Essential table text remains 12px, State chips 11px. Theme names align; N/A rank/Breadth cells stay single-line. Market prices/1D align, Daily Plan direction is prominent, and only one custom tooltip portal exists.

## Remaining limitations

No real comparable prior-session snapshot was supplied; first-day N/A is expected. Maintain the same output folder for subsequent daily runs. History publication assumes sequential local commands; no database, scheduler or cross-process locking was introduced. TradingView account import and grouped duplicate behavior remain untested as documented in the earlier export audit. No public publication, live provider collection or longitudinal reliability claim is made.
