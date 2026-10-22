# ThemeScope run report

- **Run ID:** `themescope-20261022T220415Z`
- **Generated:** 2026-10-22T22:04:15+00:00 UTC
- **Run date:** 2026-10-22 (America/New_York)
- **Market session:** 2026-10-22
- **Registry:** `2026-10-22.1`
- **Source retrieval status:** No retrieval failures reported.

This is an on-demand snapshot. It does not refresh when the HTML is reopened. It is a watchlist organization tool, not a trading model or signal. The 15/20 selection convention is configurable and has not been validated as an investment strategy.

## Theme coverage

| Theme | Anchor | Official position rows / unique tickers | As of / status | Reviewed-subset eligible | Selected | Pending / unresolved | Excluded | Breadth summary | Eligible / selected / compact weight |
|---|---|---:|---|---:|---:|---:|---:|---|---|
| Semiconductors | SMH | 25 / 25 | 2026-10-21 / current | 13 | 13 | 12 (0 unresolved evidence) | 0 | Unavailable (0/13, reviewed subset only) | 79.85% / 79.85% / 79.85% |
| Cybersecurity | CIBR | 45 / 45 | 2026-10-21 / current | 10 | 10 | 35 (0 unresolved evidence) | 0 | Unavailable (5/10, reviewed subset only) | 37.92% / 37.92% / 37.92% |
| Clean Energy | ICLN | 137 / 130 | 2026-10-21 / current | 4 | 4 | 126 (0 unresolved evidence) | 0 | Unavailable (0/4, reviewed subset only) | 21.55% / 21.55% / 21.55% |
| Aerospace & Defense | XAR | 52 / 51 | 2026-10-21 / current | 10 | 10 | 41 (0 unresolved evidence) | 0 | Unavailable (8/10, reviewed subset only) | 30.96% / 30.96% / 30.96% |
| Cloud Computing | SKYY | 65 / 65 | 2026-10-21 / current | 9 | 9 | 55 (2 unresolved evidence) | 1 | Unavailable (3/9, reviewed subset only) | 18.59% / 18.59% / 18.59% |
| Biotechnology | XBI | 167 / 160 | 2026-10-21 / current | 0 | 0 | 10 (0 unresolved evidence) | 150 | Unavailable (No eligible companies) | 0.00% / 0.00% / 0.00% |

Complete membership evidence screens: 0/6. Full-universe breadth summary labels are therefore unavailable. Subset fractions, where present, are selection-biased and do not replace full breadth.

ETF holdings weights are fund net-asset weights and are not renormalized. Current holdings not reviewed or mapped remain in the pending table. Data eligibility failures remain in the exclusions table. ETF-only performance remains available separately when stock screening is incomplete.

## Source and data limits

- Yahoo chart is an accessible but undocumented endpoint. Adjusted close is used for total-return-compatible endpoint returns using Yahoo's provider convention; split-adjusted close is used for trend; raw contemporaneous close and volume are reconstructed from Yahoo split events for ADV$30. Provider definitions and publication behavior are not guaranteed.
- A current day bar is accepted only after the 16:30 America/New_York cutoff and a same-date Yahoo regular-market timestamp. Before then the prior verified session is used. The completed session is `2026-10-22`.
- Nasdaq's quote summary supplies market cap, listing exchange, sector, and industry, but exposes no timestamp for the market-cap field. The value is retrieved on this run; its field age cannot be independently proven. It is therefore a provisional eligibility input.
- SEC submissions feeds are checked on each run for newer 10-K, 20-F, or 40-F filings than the cited evidence. Newer filings and unavailable checks block provisional selection. 8-K disclosure content is not automatically reviewed.
- ETF holdings are retrieved from each fund issuer and retain the actual as-of date. Retrieval does not make an old snapshot current. Failed refreshes do not mix in old fields; the entire last successful dashboard is preserved with its original data date.
- Theme evidence review is incomplete for every configured theme. The present curated lists are not full eligible universes; pending issuers, foreign mappings, and broader segment judgments remain unresolved.
- XBI industry screening runs for mapped tickers. Biotechnology classifications are excluded by the default rule; non-biotechnology and unmapped holdings remain pending business-evidence review. Zero selections is not a claim that its eligible universe is empty.
- Themes can overlap. Stock versus ETF excess is mechanically related where the fund owns the company; it is not independent alpha. No point-in-time membership, backtest, prediction, or execution quality assessment is provided.

## Exports

- `watchlist_15.csv` / `watchlist_20.csv`: each theme's current compact or expanded selected list, with theme, selection reason, filing, weight, and metrics columns. CSV retains repeated tickers under different theme IDs.
- `tradingview_15.txt`: 46 unique exchange-qualified symbols; 0 cross-theme/listing duplicates collapsed; 0 rows without confirmed NYSE/Nasdaq exchange omitted.
- `tradingview_20.txt`: 46 unique exchange-qualified symbols; 0 duplicates collapsed; 0 rows without confirmed exchange omitted.
- Browser exports use the active theme's filtered selected scope. CSV includes the theme field. TradingView text is flat and does not retain theme sections.
- TradingView text uses one `EXCHANGE:TICKER` symbol per line and passed local syntax/mapping checks. The platform's import dialog was not exercised in this environment, so confirm behavior with the current TradingView client.

## Retrieval failures

No chart, quote, holdings, or SEC submissions retrieval errors were reported in this run.

## Source matrix

Download `source_matrix.csv` from this run for the field-level provider, access method, adjustment or as-of definition, history/delay, limitations, fallback, last test, and URL for each consumed source.

## Regeneration

From the repository root, run `python3 scripts/generate_dashboard.py` with network access. The script performs a fresh retrieval and writes the dashboard, JSON input snapshots, CSV and TradingView exports, source matrix, this report, and a ZIP bundle to the local `output/` directory. That directory is ignored by Git; generated runs are not committed or pushed to a branch. No database, service, secret, scheduled job, or paid package is used.
