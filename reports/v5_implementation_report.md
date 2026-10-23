# ThemeScope implementation and category expansion report

Latest data session: **2026-10-22**. The current project includes the approved v5 calculations plus the follow-up sector/industry catalog and dashboard redesign requested on 2026-10-23.

## Category coverage

- **11 standard GICS sectors** are represented by the corresponding State Street Select Sector SPDR ETF and its official dated holdings file.
- **126 GICS sub-industries** appear in the retrieved S&P 500 classification, covering **500 companies**. The industry page groups their actual constituent price histories by sub-industry and parent sector.
- The six existing curated non-sector ETF exposures remain: Semiconductors, Aerospace & Defense, Biotechnology, Cybersecurity, Clean Energy, and Cloud Computing. The project did not contain the external proprietary 400-theme taxonomy mentioned in the conversation; those memberships were not invented.
- Sector ETF metrics use ETF prices and official ETF holdings breadth. Industry metrics use S&P 500 constituent prices. They are separate views with separate source universes.

The industry table shows each category's median 1M and 3M adjusted return, count and coverage, and the number and share of constituents above their own EMA21 and EMA50. These are descriptive S&P 500 subset measures, not whole-market breadth or a composite score. The scatter plot uses median 1M and 3M constituent returns; point colors distinguish positive, negative, and mixed return signs.

## Visual and navigation changes

- Added separate Market, Sectors, Industries, Themes, and Watchlist pages in a left sidebar. Only the selected page is visible; mobile navigation switches to a horizontal menu.
- Market cards separate EMA position, index breadth, valid-price coverage, and short/medium market condition. Breadth includes numerator and denominator; coverage states how many eligible constituents had usable prices. The state pill and card edge use distinct colors for broad strength, narrow strength, internal strength, weakness, and unavailable data.
- Added a local system font stack that prefers Inter, Aptos, and Segoe UI without requesting a font from the network.
- Standardized page spacing, table alignment, numeric columns, status badges, and responsive layouts. Sector and industry tables fit the tested 1440-pixel viewport without horizontal overflow.
- Kept all browser code and snapshot data inside the exported HTML. Opening or reloading it does not request market data or fonts.

## Actual collection and results

- Market data session: **2026-10-22**.
- S&P 500 classification table observed on **2026-10-23**; Nasdaq-100 constituent response dated **2026-10-22**.
- Sector ETF official holdings files were dated **2026-10-21**.
- Retrieved **68 core price histories** and **727 additional unique constituent histories**, for **795 unique histories** total. The live run reported zero chart, quote, holdings, SEC, or constituent-history errors.
- All 11 sector ETFs have valid holdings breadth. Across all 17 primary ETF anchors, **16 scores are available**. ICLN remains unavailable because only 14 of 103 eligible equity holdings have valid prices (**13.6% coverage**, below the 80% rule); its raw breadth fractions remain visible with a warning.
- The existing five non-ETF-only curated watchlists contain **47 provisional selections**. The sector funds are ETF-only and do not create stock memberships.
- The downloaded `dist/run_bundle.zip` contains the dashboard, raw inputs, snapshot, diagnostics, market/sector/industry/theme CSVs, watchlist CSVs, and TradingView text exports.

## Method and limitations

- Sector ETF relative ranks and scores use the approved v5 formulas: 70/30 excess-return percentile/breadth by horizon, then 60/40 CurrentStrength/MediumStrength. At least ten valid primary ETF peers are required. No missing component is imputed or reweighted.
- This expanded dated universe contains 17 primary anchors (11 sectors plus six curated exposures). The 15/20 selection convention remains a browsing convention, not a validated trading model.
- The source's industry labels are GICS Sub-Industry values. S&P 500 membership came from the current Wikipedia constituent table, whose as-of date is when the page was observed; it is not an official historical membership-effective date.
- Unverified foreign ETF holdings remain in the eligible price-coverage denominator. No ticker collision is guessed. ICLN's low coverage remains disclosed.
- Industry categories with small constituent counts are still displayed, with their sample size and coverage; their breadth values are descriptive and are not scored.
- Scores are fixed prioritization conventions, not demonstrated predictions, profitability, or entry instructions.

## Validation

- **36 Python tests passed**, including the sector registry, industry aggregation, v5 score/coverage rules, generation/import/export, and failure preservation.
- **Node dashboard checks passed** for sort direction, stable ranks, missing-value placement, filtering, 15/20 pools, and browser export helpers.
- Chromium checks passed for all five page routes, 11 sector rows, the 126-industry table and scatter, theme selection, watchlist controls, CSV/TXT/ZIP downloads, dark/light persistence, and the failed-snapshot state. There were zero JavaScript errors.
- Chromium DevTools Network instrumentation recorded zero automatic external requests on open and reload. Managed Chromium blocks `file://`, so the exact exported HTML bytes were served over loopback; the check used the browser Network backend and does not claim a manual graphical Network panel inspection.
- The browser screenshots were visually inspected at 1440 pixels. Category tables fit within the available content width, and page/table headings align with the shared content grid.

## Regeneration

Use Python 3.10+ and run `py -3 scripts/generate_dashboard.py` on Windows or `python3 scripts/generate_dashboard.py` on macOS/Linux. Generated files stay in the user's local `output/` folder. To render this dated retrieved run offline, run `py -3 scripts/generate_dashboard.py --import-run dist/run_bundle.zip`.
