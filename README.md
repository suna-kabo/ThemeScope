# ThemeScope

ThemeScope is an on-demand, end-of-day US equity sector and theme dashboard. It reports SPY, QQQ, IWM, and separate VIX facts, compares eligible ETF anchors, and provides an optional evidence-reviewed stock watchlist. It does not produce trade signals, entries, stops, position sizes, allocations, or orders. Scores and the 15/20-stock display limit are fixed browsing conventions, not a validated trading model.

## Open a generated dashboard

Open `dist/dashboard.html` in a browser. The file embeds the snapshot and all page assets; opening or reloading it does not request market data. Its displayed date is the date of the observations. Use **Download complete run ZIP** for the matching inputs, diagnostics, and exports.

## Generate a fresh run

Requires Python 3.10+ and internet access. On Windows:

```bat
py -3 -m pip install tzdata
py -3 scripts/generate_dashboard.py --output-dir dist
```

On macOS or Linux:

```sh
python3 scripts/generate_dashboard.py --output-dir dist
```

Optionally resolve a historical common session:

```sh
python3 scripts/generate_dashboard.py --as-of 2026-10-22 --output-dir dist
```

Wait for `SUCCESS: data date ...` and for the command prompt to return. The run collects configured ETF candidate charts, official holdings, mapped index constituents, constituent price histories, quote summaries, and requested SEC annual-filing checks. It is deliberately paced to reduce provider rate limits, so a complete refresh may take several minutes. A Yahoo HTTP 429 opens a run-local circuit. A failed refresh writes `dist/refresh_status.json` and `dist/failed_refresh.md` separately and preserves the prior successful dashboard and exports. Opening the HTML never retries collection.

The generator publishes only after validating dated SPY/QQQ prices and the eligible output. IWM and VIX have independent status; missing IWM breadth or VIX does not hide otherwise valid market facts. It stages files beside the target directory and rolls back a partial file replacement. It uses real retrieved values only; unavailable data remains blank or is listed with a reason.

## Import an existing real-data run

An existing run directory or `run_bundle.zip` can be rendered without network access:

```bat
py -3 scripts/generate_dashboard.py --import-run dist/run_bundle.zip --output-dir output
```

The imported data date and original generation time are retained. A v4/v5 run without v6 source diagnostics, official holdings freshness, or mapped breadth histories will show those values as unavailable. Import does not recreate missing source observations.

## What is configured and what remains incomplete

The registry has 65 sector/theme records from the v6 seed list, including all 11 US equity sectors and the listed theme alternatives. Every configured candidate ticker is queried for price, instrument, and ADV evidence on an explicit refresh. Anchor eligibility is based on reviewed ETF mandate, dated price history, and configured liquidity; a missing holdings adapter or incomplete holdings mapping affects breadth only. The repository currently has issuer holdings adapters for 17 primary anchors: the 11 Select Sector SPDR funds plus SMH, SKYY, CIBR, XBI, XAR, and ICLN. Other candidates remain in the audit until mandate and source requirements are reviewed.

ETF AUM and historical bid/ask spread sources are not configured. The run report records them as unavailable rather than estimating them. Theme stock watchlists use the existing reviewed membership set, not every ETF holding. Sector watchlists intersect the current S&P 500 sector classification with the sector ETF's official holdings, then apply the stock filters; this is a sourced S&P 500 subset, not every listed company in each sector. Nasdaq market-cap summaries do not expose a separate field observation time, so stock cap eligibility remains provisional. Business charters tagged `needs_review` are registry candidates, not confirmed claims that every company belongs to that theme.

The S&P 500 constituent source is a current Wikipedia table observed at retrieval, and the Nasdaq-100 list is retrieved from Nasdaq. These are not historical point-in-time universes. Yahoo Finance supplies adjusted closes and split-adjusted closes; those adjustment semantics are provider conventions. The cache manifest hashes normalized payloads retained in the run bundle; it is not a hash of the original HTTP wire bytes.

## Metrics and interface

- **Market:** SPY, QQQ, and IWM each have independent price cards with close, 5/21/63-session adjusted returns, and EMA21/EMA50 comparisons. IWM holdings breadth is a practical Russell 2000 proxy using official iShares IWM holdings; it is not official Russell 2000 breadth. VIX is shown as separate volatility context with no constituent breadth or score dependency.
- **Sectors & Themes:** one eligible primary ETF row per registry exposure. ETF excess returns are percentage-point differences against SPY. Current is the 21-session excess-return percentile; Medium is the 63-session excess-return percentile. Percentile ranks require the configured minimum of ten eligible peers. Theme Score is 60% Current + 40% Medium. Breadth and curated stocks are independent evidence and do not affect scores or states. Missing inputs are not imputed or reweighted.
- **States:** Leading, Improving, Fading, and Lagging describe whether Current and Medium are above or below 50 in the cross-sectional eligible ETF universe. Improving/Fading do not establish a time-series reversal.
- **Watchlist:** only individually sourced Core/Related memberships that pass the configured stock filters can be selected. Sorting and filtering do not refill the selected queue. ETF-only rows remain usable in the rankings without a fabricated stock list.

The three navigation pages are **Market**, **Sectors & Themes**, and **Watchlist**. Exports include the full ranking, a registry audit, visible-row CSV downloads, the 15- and 20-row stock lists, exchange-qualified TradingView text files, source matrix, raw inputs, snapshot, run report, and a complete run ZIP. A CSV blank means unavailable; `excess*_pp` is in percentage points.

## Project files

- `config/themes.json`: theme registry, settings, candidate ETFs, and score configuration.
- `config/sources.json`: provider priority/fallback order and documented source limitations.
- `config/evidence_reviews.json`: reviewed company-theme membership rationale.
- `src/themescope/sources.py`: public source adapters.
- `src/themescope/collect.py`: on-demand retrieval and stock curation.
- `src/themescope/metrics.py`: dated return, EMA, liquidity, breadth, and queue calculations.
- `src/themescope/v5.py`: index/holdings breadth and price-relative-strength calculations.
- `src/themescope/v6.py`: candidate audit, eligibility, source diagnostics, and snapshot contract.
- `scripts/generate_dashboard.py`: validation, staged publication, exports, and rollback.
- `static/`: data-neutral offline dashboard template, CSS, and JavaScript.

## Verification

```sh
python -m unittest discover -s tests -v
node tests/test_dashboard.js
```

Optional Chromium checks require Playwright and Chromium:

```sh
python tests/browser_check.py dist/dashboard.html
```

The browser check uses Chromium DevTools Network events and verifies that opening and reloading the exported HTML makes no automatic external requests. The default security policy also blocks page-initiated network connections.
