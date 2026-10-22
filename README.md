# ThemeScope v5

An on-demand, end-of-day dashboard with **Market, Themes, and Watchlist**. It organizes ETFs and stocks for manual chart review. It does not generate entries, stops, position sizes or trades. The 15/20 pool and score weights are explicit conventions, not validated trading models.

## Open the delivered dashboard

Download/extract the project and open **`dist/dashboard.html`**. This is a dated real-data demonstration; opening or reloading it never collects data. Use **Download complete run ZIP** for its inputs and exports. The date displayed is the date of the data, not the time you opened the file.

## Generate on your own device

Python 3.10+ and internet access are required. Windows:

```bat
py -3 -m pip install tzdata
py -3 scripts/generate_dashboard.py
```

macOS/Linux:

```sh
python3 scripts/generate_dashboard.py
```

Wait for **`SUCCESS: data date ...`** and the terminal prompt to return, then open **`output/dashboard.html`**. A full v5 run collects hundreds of constituent histories and can take 20–40 minutes at default sequential 1.5-second pacing, plus network delays. Progress is printed every 50 additional histories. A rate-limited Yahoo host is disabled for the rest of that process; both hosts being rate-limited stops the breadth refresh.

All ordinary run outputs remain local in Git-ignored `output/`. The program does not commit or push files. Choose a different local directory with `--output-dir`. There is no database, account, backend service or scheduler.

If access fails, explicitly render a previously saved real-data run:

```bat
py -3 scripts/generate_dashboard.py --import-run dist/run_bundle.zip
```

A directory containing `latest_snapshot.json` and `raw_inputs.json` also works. Imports make no network requests, preserve the original data date/collection time and show an import timestamp. A v4 input lacking constituent histories will correctly show unavailable v5 breadth; importing does not create missing observations.

## What changed in v5

- Separate S&P 500 and Nasdaq-100 constituent breadth and short/medium market conditions.
- Anchor ETF holdings breadth independent of curated watchlist membership or filing reviews.
- Sector/Industry/Theme level metadata and filters.
- CurrentStrength = 70% 1M excess-return percentile + 30% EMA21 breadth.
- MediumStrength = 70% 3M excess-return percentile + 30% EMA50 breadth.
- ThemeScore = 60% CurrentStrength + 40% MediumStrength.
- Supported `Core`/`Related` non-anchor stocks can enter curated watchlists; their ETF weight is missing, not zero. Obvious cases do not require an annual filing check. Ambiguous records can require one via `requires_filing_review`.
- Original liquidity filters, stock-versus-ETF excess returns and Liquid/Liquid/Strong/Weak selection remain. Individual biotechnology exclusion remains; XBI remains a valid ETF.

**The registry still has six ETFs. Scores and percentiles require at least ten valid peers and therefore remain unavailable for this registry.** Raw returns, price-only rankings, EMA facts and valid breadth remain usable. No ETFs were added merely to meet the threshold. Score fields work for a deliberately expanded qualifying registry and are tested with hand-calculated fixtures.

Breadth uses equal-company counts, not portfolio weights. Validity requires a universe no older than 35 days, eight valid companies and at least 80% price coverage. Missing prices are excluded from that metric's valid denominator but retained in its eligible coverage count. Cash, funds and other identified non-equities are excluded separately. Company share classes are deduplicated using verified issuer IDs; the alphabetically first mapped share class is used, never the best performer. Unverified foreign mappings remain missing rather than borrowing similarly named US tickers.

## Sources and limits

- **S&P 500:** current Wikipedia constituent table, with CIKs, retained rows and response hash. Its date means observed at retrieval, not an official constituent effective date.
- **Nasdaq-100:** Nasdaq's dated `api/quote/list-type/nasdaq100` list.
- **Issuer/listing map:** SEC `company_tickers_exchange.json`.
- **ETF holdings:** official VanEck, First Trust, iShares and State Street sources. VanEck has a verified direct-dataset fallback.
- **Prices:** Yahoo chart hosts query1/query2, with adjusted close for returns and split-adjusted close for EMAs. Exact common-session endpoints are used; unavailable data is never filled with zero.
- **Market capitalization/industry/exchange:** Nasdaq summaries. The cap field has no separate observation timestamp, so stock eligibility remains provisional.
- **Company-theme membership:** recorded reliable source and rationale in `config/evidence_reviews.json`. No automatic agent decision makes unsupported membership valid.

The common US session is accepted after the v4 conservative closing cutoff. Foreign exchange/currency/share-class coverage is not assumed complete. Current universes are not historical point-in-time universes. No market score averages SPY/QQQ, and index breadth never enters ThemeScore. See `reports/v5_implementation_report.md` for the delivered run's exact availability and limitations.

## Safe refresh and local exports

Mandatory market/anchor return data, primary holdings collection and index-universe collection must succeed. Core prices/returns are validated against retrieved observations. Optional constituent histories, stock curation and score eligibility can remain unavailable with explicit reasons; they do not invalidate unrelated ETF returns. Rate-limit/constituent transport aborts and mandatory collection/validation failures return exit code 1, write `refresh_status.json` and `failed_refresh.md`, and preserve the last valid HTML, downloads and original date.

Outputs are staged before publication; replacement errors roll back changed files. Invalid preexisting HTML is retained as `rejected_dashboard.html`, not advertised as successful. No empty first run is presented as completed. Imported v4 runs with valid ETF prices may be displayed as dated references with unavailable v5 fields.

Run ZIP contents:

- `dashboard.html`, `latest_snapshot.json`, `raw_inputs.json`, `source_matrix.csv`, `latest_run.md`
- `market.csv`, `themes.csv` including raw values, dates, field statuses/reasons
- `watchlist_15.csv`, `watchlist_20.csv` with company-theme pairs and membership tags
- `tradingview_15.txt`, `tradingview_20.txt` with deduplicated exchange-qualified symbols

CSV return fields use decimal fractions; `excess*_pp` uses percentage points, while breadth `_pct` and scores use 0–100 values. Blank numeric cells mean unavailable.

Browser CSV/TXT exports use the visible stock rows; the full run ZIP includes both configured pools and diagnostics. TradingView links only open after a user click. TradingView's external import dialog has not been automated here.

## Project and validation

- `src/themescope/sources.py`: public-source adapters
- `src/themescope/collect.py`: retrieval and curated eligibility/selection
- `src/themescope/metrics.py`: original return/EMA/selection calculations
- `src/themescope/v5.py`: constituent collection, security mapping, independent breadth and approved scores
- `src/themescope/presentation.py`: display fields and publication validation
- `scripts/generate_dashboard.py`: staging, exports, imports, reports and rollback
- `static/`: self-contained UI template/CSS/JS
- `docs/ThemeScope_v5_Implementation_Change_Brief.md`: implemented product direction

```sh
python3 -m unittest discover -s tests -v
node tests/test_dashboard.js
```

Optional browser checks require Playwright and Chromium:

```sh
python3 tests/browser_check.py output/dashboard.html
```

They use Chromium DevTools Protocol Network events. Managed development Chromium blocks `file://`, so the exact exported bytes are served over loopback; the check requires zero automatic external requests. A regular local browser needs no server. The HTML embeds all assets and sets `connect-src 'none'`.

## Distribution

A source license and public repository visibility remain owner decisions. No license or visibility change was made by this implementation. Running the collector locally always keeps generated files on that user's device.
