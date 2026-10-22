# ThemeScope v5 run report

Data session: 2026-10-22
Collected: 2026-10-22T23:27:51+00:00

## Market/index participation
- SPY: Internal strength, index below EMA21 / Internal strength, index below EMA50
  - EMA21: 355/499, eligible 500, coverage 99.8%, as of 2026-10-22; valid: valid
  - EMA50: 320/497, eligible 500, coverage 99.4%, as of 2026-10-22; valid: valid
- QQQ: Broad short-term weakness / Internal strength, index below EMA50
  - EMA21: 47/100, eligible 100, coverage 100.0%, as of 2026-10-22; valid: valid
  - EMA50: 51/98, eligible 100, coverage 98.0%, as of 2026-10-22; valid: valid

## Primary ETF registry
- Semiconductors (SMH), Industry: score None; Unavailable; 13 selected stocks.
  - percentile_excess21: None; unavailable; Requires 10 valid ETF peers; 6 available
  - percentile_excess63: None; unavailable; Requires 10 valid ETF peers; 6 available
  - etf_breadth21_pct: 0.0; valid; valid
  - etf_breadth50_pct: 4.3478260869565215; valid; valid
  - current_strength_score: None; unavailable; Requires 10 valid ETF peers; 6 available
  - medium_strength_score: None; unavailable; Requires 10 valid ETF peers; 6 available
  - theme_score: None; unavailable; CurrentStrength and MediumStrength must both be valid
  - 2 excluded source rows; 1 unresolved equity mappings remain in coverage denominator.
- Cybersecurity (CIBR), Theme: score None; Unavailable; 10 selected stocks.
  - percentile_excess21: None; unavailable; Requires 10 valid ETF peers; 6 available
  - percentile_excess63: None; unavailable; Requires 10 valid ETF peers; 6 available
  - etf_breadth21_pct: 51.21951219512195; valid; valid
  - etf_breadth50_pct: 73.17073170731707; valid; valid
  - current_strength_score: None; unavailable; Requires 10 valid ETF peers; 6 available
  - medium_strength_score: None; unavailable; Requires 10 valid ETF peers; 6 available
  - theme_score: None; unavailable; CurrentStrength and MediumStrength must both be valid
  - 0 excluded source rows; 4 unresolved equity mappings remain in coverage denominator.
- Clean Energy (ICLN), Theme: score None; Unavailable; 4 selected stocks.
  - percentile_excess21: None; unavailable; Requires 10 valid ETF peers; 6 available
  - percentile_excess63: None; unavailable; Requires 10 valid ETF peers; 6 available
  - etf_breadth21_pct: 14.285714285714286; unavailable; Price coverage 14/103 below 80%
  - etf_breadth50_pct: 7.142857142857143; unavailable; Price coverage 14/103 below 80%
  - current_strength_score: None; unavailable; Requires 10 valid ETF peers; 6 available; Price coverage 14/103 below 80%
  - medium_strength_score: None; unavailable; Requires 10 valid ETF peers; 6 available; Price coverage 14/103 below 80%
  - theme_score: None; unavailable; CurrentStrength and MediumStrength must both be valid
  - 34 excluded source rows; 89 unresolved equity mappings remain in coverage denominator.
- Aerospace & Defense (XAR), Industry: score None; Unavailable; 10 selected stocks.
  - percentile_excess21: None; unavailable; Requires 10 valid ETF peers; 6 available
  - percentile_excess63: None; unavailable; Requires 10 valid ETF peers; 6 available
  - etf_breadth21_pct: 28.0; valid; valid
  - etf_breadth50_pct: 17.391304347826086; valid; valid
  - current_strength_score: None; unavailable; Requires 10 valid ETF peers; 6 available
  - medium_strength_score: None; unavailable; Requires 10 valid ETF peers; 6 available
  - theme_score: None; unavailable; CurrentStrength and MediumStrength must both be valid
  - 2 excluded source rows; 0 unresolved equity mappings remain in coverage denominator.
- Cloud Computing (SKYY), Theme: score None; Unavailable; 10 selected stocks.
  - percentile_excess21: None; unavailable; Requires 10 valid ETF peers; 6 available
  - percentile_excess63: None; unavailable; Requires 10 valid ETF peers; 6 available
  - etf_breadth21_pct: 60.0; valid; valid
  - etf_breadth50_pct: 69.23076923076923; valid; valid
  - current_strength_score: None; unavailable; Requires 10 valid ETF peers; 6 available
  - medium_strength_score: None; unavailable; Requires 10 valid ETF peers; 6 available
  - theme_score: None; unavailable; CurrentStrength and MediumStrength must both be valid
  - 0 excluded source rows; 0 unresolved equity mappings remain in coverage denominator.
- Biotechnology (XBI), Industry: score None; Unavailable; 0 selected stocks.
  - percentile_excess21: None; unavailable; Requires 10 valid ETF peers; 6 available
  - percentile_excess63: None; unavailable; Requires 10 valid ETF peers; 6 available
  - etf_breadth21_pct: 35.6687898089172; valid; valid
  - etf_breadth50_pct: 24.836601307189543; valid; valid
  - current_strength_score: None; unavailable; Requires 10 valid ETF peers; 6 available
  - medium_strength_score: None; unavailable; Requires 10 valid ETF peers; 6 available
  - theme_score: None; unavailable; CurrentStrength and MediumStrength must both be valid
  - 10 excluded source rows; 0 unresolved equity mappings remain in coverage denominator.

## Methodology and limits
- Scores require 10 valid primary ETF peers. Six registry ETFs are retained; no padding to manufacture percentile scores.
- 70/30 relative-percentile/breadth horizon scores; 60/40 current/medium final score. Fixed conventions, not optimized or validated trading signals.
- ETF and index breadth use complete sourced equity universes independently of curated watchlists; price coverage thresholds are 8 valid companies, 80%, 35-day freshness.
- Nasdaq cap field timestamp is unavailable. Supported membership rationale is required; filings are mandatory only for records marked requires_filing_review.
- Current constituents are observed snapshots, not point-in-time historical membership. Wikipedia S&P 500 as-of is the retrieval observation date, not an official rebalance date.
- Unverified foreign listing mappings remain missing; no substitution with a US ticker sharing the same letters.
- Optional constituent/stock metrics can be unavailable without invalidating core ETF returns. Mandatory core return/holdings or index-universe collection failures reject refresh publication.

## Source errors
```json
{
  "core": {
    "charts": {},
    "quotes": {},
    "holdings": {},
    "sec": {}
  },
  "constituent_histories": {}
}
```

## Local files
dashboard.html, market.csv, themes.csv, latest_snapshot.json, raw_inputs.json, source_matrix.csv, watchlist_15.csv, watchlist_20.csv, tradingview_15.txt, tradingview_20.txt, run_bundle.zip.
Opening HTML never retrieves data. Explicitly run python scripts/generate_dashboard.py. Failed refreshes preserve existing valid exports and write refresh_status.json/failed_refresh.md separately.
