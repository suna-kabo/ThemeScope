# ThemeScope v6.2 run report

Market session: 2026-10-23
Dashboard generated: 2026-10-23T21:54:53+00:00 (24 Oct 2026, 05:54 AM HKT)
Latest source retrieval: 2026-10-23T21:21:54+00:00
Base collection: 2026-10-23T20:56:51+00:00 to 2026-10-23T21:21:54+00:00
Requested as-of: latest verified completed common session

## Market/index facts
- SPY (S&P 500 ETF): close 759.969970703125; session 2026-10-23; price status valid; valid.
  - Return5: -0.004297450765640365; valid; Exact 5-session endpoints; 6/6 observations present.
  - Return21: -0.009398083945736158; valid; Exact 21-session endpoints; 22/22 observations present.
  - Return63: 0.030804215094042187; valid; Exact 63-session endpoints; 64/64 observations present.
  - Close at/below EMA21 (768.8171680433882); constituent breadth 338/499 valid, 500 eligible, holdings/list as of 2026-10-23; valid: valid; t-5 63.92785571142284; change 3.807615230460918 pp.
  - Close at/below EMA50 (765.829871529258); constituent breadth 300/497 valid, 500 eligible, holdings/list as of 2026-10-23; valid: valid; t-5 53.118712273641854; change 7.243460764587525 pp.
- QQQ (Nasdaq-100 ETF): close 704.4000244140625; session 2026-10-23; price status valid; valid.
  - Return5: -0.007607725375843866; valid; Exact 5-session endpoints; 6/6 observations present.
  - Return21: -0.049520918068927; valid; Exact 21-session endpoints; 22/22 observations present.
  - Return63: 0.03373894157057622; valid; Exact 63-session endpoints; 64/64 observations present.
  - Close at/below EMA21 (727.3299153920734); constituent breadth 50/100 valid, 100 eligible, holdings/list as of 2026-10-23; valid: valid; t-5 45.0; change 5.0 pp.
  - Close at/below EMA50 (725.3552325432433); constituent breadth 50/98 valid, 100 eligible, holdings/list as of 2026-10-23; valid: valid; t-5 41.83673469387755; change 9.183673469387756 pp.
- IWM (Russell 2000 ETF proxy): close 275.75; session 2026-10-23; price status valid; valid.
  - Return5: 0.019634660222813016; valid; Exact 5-session endpoints; 6/6 observations present.
  - Return21: -0.02098275788279569; valid; Exact 21-session endpoints; 22/22 observations present.
  - Return63: -0.05612576610726416; valid; Exact 63-session endpoints; 64/64 observations present.
  - Close at/below EMA21 (277.95012885789106); IWM holdings breadth 925/1943 valid, 1957 eligible, holdings/list as of 2026-10-22; valid: valid; t-5 29.62962962962963; change 17.977163988486684 pp.
  - Close at/below EMA50 (283.236341496814); IWM holdings breadth 775/1899 valid, 1957 eligible, holdings/list as of 2026-10-22; valid: valid; t-5 28.31578947368421; change 12.495163659543802 pp.

## IWM holdings breadth collection
- Classification: 1986 source rows; 1980 rows labeled Equity; 11 description exclusions; 19 total excluded.
- Ticker normalization/mapping: 2 normalization failures; 1967 normalized equity rows; 1967 unique symbols; 1949 SEC CIK matched; 8 direct ticker fallback.
- History collection: 175 reused; 1792 requested; 1788 new responses; 1963 histories retained; 1910 met the 205-session t-5 warmup; 53 short histories: AADX 100, ADIG 61, AKTS 199, ALMR 132, APC 176, APMD 60, AVEX 132, AVLN 123, +45 more; 4 retrieval errors.
- EMA observations: EMA21 1943/1957; EMA50 1899/1957. The 80% completeness rule remains in force.
- EMA21 breadth: valid; valid.
- EMA50 breadth: valid; valid.

IWM history retrieval errors:
- ADRO: HTTP Error 404: Not Found; no chart returned by either Yahoo host.
- PDLI: HTTP Error 404: Not Found; no chart returned by either Yahoo host.
- SBT: HTTP Error 404: Not Found; no chart returned by either Yahoo host.
- THRD: HTTP Error 404: Not Found; no chart returned by either Yahoo host.

## Volatility context
- ^VIX: level 19.450000762939453; daily 0.0220704183467888 (up); 5-session -0.02701345744680339 (down); 21-session 0.24122531386352764 (up); trailing 252-session percentile 77.97619047619048; direction Volatility direction is mixed across the displayed periods.; observation date 2026-10-23; retrieved 2026-10-23T20:58:00+00:00; available: https://query1.finance.yahoo.com/v8/finance/chart/^VIX?period1=1729544280&period2=1792875480&interval=1d&events=div%2Csplits&includeAdjustedClose=true.

## Eligible primary ETF ranking
Current is the 21-session excess-return percentile; Medium is the 63-session excess-return percentile; Theme Score = 60% Current + 40% Medium. Percentiles require at least 10 valid peers. Breadth and curated stocks do not enter score or state.
- Communication Services (XLC), Sector: score 22.5; state Lagging; current rank 14; t-5 rank 11.0; rank change -3.0; historical peers 17; curated stock drilldown available (18); anchor eligibility eligible.
  - percentile_excess21: 12.5; valid; valid
  - percentile_excess63: 37.5; valid; valid
  - etf_breadth21_pct: 31.57894736842105; valid; valid
  - etf_breadth50_pct: 26.31578947368421; valid; valid
  - current_strength_score: 12.5; valid; valid
  - medium_strength_score: 37.5; valid; valid
  - theme_score: 22.5; valid; valid
  - Score peers: 21-session 17; 63-session 17; method price_relative_strength_v6_2; unavailable reason none.
  - Breadth: EMA21 valid: valid; t-5 26.31578947368421; change 5.2631578947368425 pp. EMA50 valid: valid; t-5 31.57894736842105; change -5.2631578947368425 pp.
  - 2 excluded source rows; 1 unresolved equity mappings remain in coverage denominator.
- Consumer Discretionary (XLY), Sector: score 62.5; state Leading; current rank 8; t-5 rank 5.0; rank change -3.0; historical peers 17; curated stock drilldown available (20); anchor eligibility eligible.
  - percentile_excess21: 62.5; valid; valid
  - percentile_excess63: 62.5; valid; valid
  - etf_breadth21_pct: 61.702127659574465; valid; valid
  - etf_breadth50_pct: 55.319148936170215; valid; valid
  - current_strength_score: 62.5; valid; valid
  - medium_strength_score: 62.5; valid; valid
  - theme_score: 62.5; valid; valid
  - Score peers: 21-session 17; 63-session 17; method price_relative_strength_v6_2; unavailable reason none.
  - Breadth: EMA21 valid: valid; t-5 68.08510638297872; change -6.382978723404257 pp. EMA50 valid: valid; t-5 53.191489361702125; change 2.1276595744680904 pp.
  - 2 excluded source rows; 1 unresolved equity mappings remain in coverage denominator.
- Consumer Staples (XLP), Sector: score 80.0; state Leading; current rank 3; t-5 rank 3.0; rank change 0.0; historical peers 17; curated stock drilldown available (20); anchor eligibility eligible.
  - percentile_excess21: 87.5; valid; valid
  - percentile_excess63: 68.75; valid; valid
  - etf_breadth21_pct: 90.9090909090909; valid; valid
  - etf_breadth50_pct: 75.75757575757575; valid; valid
  - current_strength_score: 87.5; valid; valid
  - medium_strength_score: 68.75; valid; valid
  - theme_score: 80.0; valid; valid
  - Score peers: 21-session 17; 63-session 17; method price_relative_strength_v6_2; unavailable reason none.
  - Breadth: EMA21 valid: valid; t-5 87.87878787878788; change 3.030303030303031 pp. EMA50 valid: valid; t-5 78.78787878787878; change -3.030303030303031 pp.
  - 3 excluded source rows; 1 unresolved equity mappings remain in coverage denominator.
- Energy (XLE), Sector: score 97.5; state Leading; current rank 1; t-5 rank 1.0; rank change 0.0; historical peers 17; curated stock drilldown available (20); anchor eligibility eligible.
  - percentile_excess21: 100.0; valid; valid
  - percentile_excess63: 93.75; valid; valid
  - etf_breadth21_pct: 85.71428571428571; valid; valid
  - etf_breadth50_pct: 85.71428571428571; valid; valid
  - current_strength_score: 100.0; valid; valid
  - medium_strength_score: 93.75; valid; valid
  - theme_score: 97.5; valid; valid
  - Score peers: 21-session 17; 63-session 17; method price_relative_strength_v6_2; unavailable reason none.
  - Breadth: EMA21 valid: valid; t-5 80.95238095238095; change 4.761904761904759 pp. EMA50 valid: valid; t-5 76.19047619047619; change 9.523809523809518 pp.
  - 2 excluded source rows; 1 unresolved equity mappings remain in coverage denominator.
- Financials (XLF), Sector: score 51.25; state Improving; current rank 9; t-5 rank 7.0; rank change -2.0; historical peers 17; curated stock drilldown available (20); anchor eligibility eligible.
  - percentile_excess21: 56.25; valid; valid
  - percentile_excess63: 43.75; valid; valid
  - etf_breadth21_pct: 65.78947368421052; valid; valid
  - etf_breadth50_pct: 55.26315789473684; valid; valid
  - current_strength_score: 56.25; valid; valid
  - medium_strength_score: 43.75; valid; valid
  - theme_score: 51.25; valid; valid
  - Score peers: 21-session 17; 63-session 17; method price_relative_strength_v6_2; unavailable reason none.
  - Breadth: EMA21 valid: valid; t-5 63.1578947368421; change 2.6315789473684177 pp. EMA50 valid: valid; t-5 46.05263157894737; change 9.210526315789473 pp.
  - 3 excluded source rows; 1 unresolved equity mappings remain in coverage denominator.
- Health Care (XLV), Sector: score 81.25; state Leading; current rank 2; t-5 rank 2.0; rank change 0.0; historical peers 17; curated stock drilldown available (20); anchor eligibility eligible.
  - percentile_excess21: 81.25; valid; valid
  - percentile_excess63: 81.25; valid; valid
  - etf_breadth21_pct: 90.0; valid; valid
  - etf_breadth50_pct: 90.0; valid; valid
  - current_strength_score: 81.25; valid; valid
  - medium_strength_score: 81.25; valid; valid
  - theme_score: 81.25; valid; valid
  - Score peers: 21-session 17; 63-session 17; method price_relative_strength_v6_2; unavailable reason none.
  - Breadth: EMA21 valid: valid; t-5 90.0; change 0.0 pp. EMA50 valid: valid; t-5 83.33333333333333; change 6.666666666666671 pp.
  - 3 excluded source rows; 1 unresolved equity mappings remain in coverage denominator.
- Industrials (XLI), Sector: score 27.5; state Lagging; current rank 13; t-5 rank 12.0; rank change -1.0; historical peers 17; curated stock drilldown available (20); anchor eligibility eligible.
  - percentile_excess21: 37.5; valid; valid
  - percentile_excess63: 12.5; valid; valid
  - etf_breadth21_pct: 57.83132530120482; valid; valid
  - etf_breadth50_pct: 48.148148148148145; valid; valid
  - current_strength_score: 37.5; valid; valid
  - medium_strength_score: 12.5; valid; valid
  - theme_score: 27.5; valid; valid
  - Score peers: 21-session 17; 63-session 17; method price_relative_strength_v6_2; unavailable reason none.
  - Breadth: EMA21 valid: valid; t-5 57.83132530120482; change 0.0 pp. EMA50 valid: valid; t-5 41.97530864197531; change 6.172839506172835 pp.
  - 2 excluded source rows; 1 unresolved equity mappings remain in coverage denominator.
- Information Technology (XLK), Sector: score 41.25; state Fading; current rank 10; t-5 rank 8.5; rank change -1.5; historical peers 17; curated stock drilldown available (20); anchor eligibility eligible.
  - percentile_excess21: 18.75; valid; valid
  - percentile_excess63: 75.0; valid; valid
  - etf_breadth21_pct: 46.666666666666664; valid; valid
  - etf_breadth50_pct: 46.666666666666664; valid; valid
  - current_strength_score: 18.75; valid; valid
  - medium_strength_score: 75.0; valid; valid
  - theme_score: 41.25; valid; valid
  - Score peers: 21-session 17; 63-session 17; method price_relative_strength_v6_2; unavailable reason none.
  - Breadth: EMA21 valid: valid; t-5 28.0; change 18.666666666666664 pp. EMA50 valid: valid; t-5 36.0; change 10.666666666666664 pp.
  - 2 excluded source rows; 1 unresolved equity mappings remain in coverage denominator.
- Materials (XLB), Sector: score 67.5; state Leading; current rank 5; t-5 rank 4.0; rank change -1.0; historical peers 17; curated stock drilldown available (20); anchor eligibility eligible.
  - percentile_excess21: 75.0; valid; valid
  - percentile_excess63: 56.25; valid; valid
  - etf_breadth21_pct: 75.0; valid; valid
  - etf_breadth50_pct: 70.83333333333333; valid; valid
  - current_strength_score: 75.0; valid; valid
  - medium_strength_score: 56.25; valid; valid
  - theme_score: 67.5; valid; valid
  - Score peers: 21-session 17; 63-session 17; method price_relative_strength_v6_2; unavailable reason none.
  - Breadth: EMA21 valid: valid; t-5 83.33333333333333; change -8.333333333333329 pp. EMA50 valid: valid; t-5 62.5; change 8.333333333333329 pp.
  - 2 excluded source rows; 1 unresolved equity mappings remain in coverage denominator.
- Real Estate (XLRE), Sector: score 37.5; state Improving; current rank 12; t-5 rank 13.0; rank change 1.0; historical peers 17; curated stock drilldown available (20); anchor eligibility eligible.
  - percentile_excess21: 50.0; valid; valid
  - percentile_excess63: 18.75; valid; valid
  - etf_breadth21_pct: 76.66666666666667; valid; valid
  - etf_breadth50_pct: 46.666666666666664; valid; valid
  - current_strength_score: 50.0; valid; valid
  - medium_strength_score: 18.75; valid; valid
  - theme_score: 37.5; valid; valid
  - Score peers: 21-session 17; 63-session 17; method price_relative_strength_v6_2; unavailable reason none.
  - Breadth: EMA21 valid: valid; t-5 53.333333333333336; change 23.333333333333336 pp. EMA50 valid: valid; t-5 26.666666666666668; change 19.999999999999996 pp.
  - 2 excluded source rows; 1 unresolved equity mappings remain in coverage denominator.
- Utilities (XLU), Sector: score 66.25; state Improving; current rank 6; t-5 rank 6.0; rank change 0.0; historical peers 17; curated stock drilldown available (20); anchor eligibility eligible.
  - percentile_excess21: 93.75; valid; valid
  - percentile_excess63: 25.0; valid; valid
  - etf_breadth21_pct: 87.09677419354838; valid; valid
  - etf_breadth50_pct: 80.64516129032258; valid; valid
  - current_strength_score: 93.75; valid; valid
  - medium_strength_score: 25.0; valid; valid
  - theme_score: 66.25; valid; valid
  - Score peers: 21-session 17; 63-session 17; method price_relative_strength_v6_2; unavailable reason none.
  - Breadth: EMA21 valid: valid; t-5 93.54838709677419; change -6.451612903225808 pp. EMA50 valid: valid; t-5 70.96774193548387; change 9.677419354838705 pp.
  - 2 excluded source rows; 1 unresolved equity mappings remain in coverage denominator.
- Semiconductors (SMH), Theme: score 12.5; state Lagging; current rank 16; t-5 rank 14.0; rank change -2.0; historical peers 17; curated stock drilldown available (13); anchor eligibility eligible.
  - percentile_excess21: 0.0; valid; valid
  - percentile_excess63: 31.25; valid; valid
  - etf_breadth21_pct: 4.3478260869565215; valid; valid
  - etf_breadth50_pct: 8.695652173913043; valid; valid
  - current_strength_score: 0.0; valid; valid
  - medium_strength_score: 31.25; valid; valid
  - theme_score: 12.5; valid; valid
  - Score peers: 21-session 17; 63-session 17; method price_relative_strength_v6_2; unavailable reason none.
  - Breadth: EMA21 valid: valid; t-5 0.0; change 4.3478260869565215 pp. EMA50 valid: valid; t-5 8.695652173913043; change 0.0 pp.
  - 2 excluded source rows; 1 unresolved equity mappings remain in coverage denominator.
- Cloud Computing (SKYY), Theme: score 66.25; state Fading; current rank 7; t-5 rank 8.5; rank change 1.5; historical peers 17; curated stock drilldown available (10); anchor eligibility eligible.
  - percentile_excess21: 43.75; valid; valid
  - percentile_excess63: 100.0; valid; valid
  - etf_breadth21_pct: 73.84615384615384; valid; valid
  - etf_breadth50_pct: 76.92307692307692; valid; valid
  - current_strength_score: 43.75; valid; valid
  - medium_strength_score: 100.0; valid; valid
  - theme_score: 66.25; valid; valid
  - Score peers: 21-session 17; 63-session 17; method price_relative_strength_v6_2; unavailable reason none.
  - Breadth: EMA21 valid: valid; t-5 46.15384615384615; change 27.692307692307686 pp. EMA50 valid: valid; t-5 55.38461538461539; change 21.538461538461533 pp.
  - 0 excluded source rows; 0 unresolved equity mappings remain in coverage denominator.
- Cybersecurity (CIBR), Theme: score 76.25; state Leading; current rank 4; t-5 rank 10.0; rank change 6.0; historical peers 17; curated stock drilldown available (10); anchor eligibility eligible.
  - percentile_excess21: 68.75; valid; valid
  - percentile_excess63: 87.5; valid; valid
  - etf_breadth21_pct: 82.92682926829268; valid; valid
  - etf_breadth50_pct: 82.92682926829268; valid; valid
  - current_strength_score: 68.75; valid; valid
  - medium_strength_score: 87.5; valid; valid
  - theme_score: 76.25; valid; valid
  - Score peers: 21-session 17; 63-session 17; method price_relative_strength_v6_2; unavailable reason none.
  - Breadth: EMA21 valid: valid; t-5 31.70731707317073; change 51.21951219512195 pp. EMA50 valid: valid; t-5 51.21951219512195; change 31.707317073170728 pp.
  - 0 excluded source rows; 4 unresolved equity mappings remain in coverage denominator.
- Biotechnology (XBI), Theme: score 38.75; state Fading; current rank 11; t-5 rank 15.0; rank change 4.0; historical peers 17; curated stock drilldown unavailable; anchor eligibility eligible.
  - percentile_excess21: 31.25; valid; valid
  - percentile_excess63: 50.0; valid; valid
  - etf_breadth21_pct: 28.662420382165607; valid; valid
  - etf_breadth50_pct: 22.22222222222222; valid; valid
  - current_strength_score: 31.25; valid; valid
  - medium_strength_score: 50.0; valid; valid
  - theme_score: 38.75; valid; valid
  - Score peers: 21-session 17; 63-session 17; method price_relative_strength_v6_2; unavailable reason none.
  - Breadth: EMA21 valid: valid; t-5 11.464968152866241; change 17.197452229299365 pp. EMA50 valid: valid; t-5 15.032679738562091; change 7.18954248366013 pp.
  - 10 excluded source rows; 0 unresolved equity mappings remain in coverage denominator.
- Aerospace & Defense (XAR), Theme: score 3.75; state Lagging; current rank 17; t-5 rank 16.0; rank change -1.0; historical peers 17; curated stock drilldown available (10); anchor eligibility eligible.
  - percentile_excess21: 6.25; valid; valid
  - percentile_excess63: 0.0; valid; valid
  - etf_breadth21_pct: 30.0; valid; valid
  - etf_breadth50_pct: 13.043478260869565; valid; valid
  - current_strength_score: 6.25; valid; valid
  - medium_strength_score: 0.0; valid; valid
  - theme_score: 3.75; valid; valid
  - Score peers: 21-session 17; 63-session 17; method price_relative_strength_v6_2; unavailable reason none.
  - Breadth: EMA21 valid: valid; t-5 32.0; change -2.0 pp. EMA50 valid: valid; t-5 6.521739130434782; change 6.521739130434782 pp.
  - 2 excluded source rows; 0 unresolved equity mappings remain in coverage denominator.
- Clean Energy (ICLN), Theme: score 17.5; state Lagging; current rank 15; t-5 rank 17.0; rank change 2.0; historical peers 17; curated stock drilldown available (4); anchor eligibility eligible.
  - percentile_excess21: 25.0; valid; valid
  - percentile_excess63: 6.25; valid; valid
  - etf_breadth21_pct: 14.285714285714286; unavailable; Price coverage 14/103 below 80%
  - etf_breadth50_pct: 7.142857142857143; unavailable; Price coverage 14/103 below 80%
  - current_strength_score: 25.0; valid; valid
  - medium_strength_score: 6.25; valid; valid
  - theme_score: 17.5; valid; valid
  - Score peers: 21-session 17; 63-session 17; method price_relative_strength_v6_2; unavailable reason none.
  - Breadth: EMA21 unavailable: Price coverage 14/103 below 80%; t-5 None; change None pp. EMA50 unavailable: Price coverage 14/103 below 80%; t-5 None; change None pp.
  - 36 excluded source rows; 89 unresolved equity mappings remain in coverage denominator.

## ICLN score and breadth diagnostic
- Current 25.0; Medium 6.25; Theme Score 17.5; state Lagging.
- EMA21 breadth: unavailable; Price coverage 14/103 below 80%.
- EMA50 breadth: unavailable; Price coverage 14/103 below 80%.
- Mapped holdings: 103; unresolved equity mappings: 89; official source rows: 139.

## Layer totals
- Eligible ETF anchors with no configured holdings parser (restored by removing holdings-parser eligibility gate): 0.
- ETF score failures: 0; only ETF/SPY return data and peer availability affect these.
- ETF breadth failures: 1; they do not affect ETF eligibility or score.
- Curated stock drilldown unavailable: 1; it does not affect ETF eligibility or score.

## Registry audit
- Registry records: 65; runtime eligible anchors: 17; inactive or unresolved this run: 48.
- Communication Services (sector-communication-services): selected_anchor; selected XLC.
  - XLC: eligible; passed configured runtime checks
- Consumer Discretionary (sector-consumer-discretionary): selected_anchor; selected XLY.
  - XLY: eligible; passed configured runtime checks
- Consumer Staples (sector-consumer-staples): selected_anchor; selected XLP.
  - XLP: eligible; passed configured runtime checks
- Energy (sector-energy): selected_anchor; selected XLE.
  - XLE: eligible; passed configured runtime checks
- Financials (sector-financials): selected_anchor; selected XLF.
  - XLF: eligible; passed configured runtime checks
- Health Care (sector-health-care): selected_anchor; selected XLV.
  - XLV: eligible; passed configured runtime checks
- Industrials (sector-industrials): selected_anchor; selected XLI.
  - XLI: eligible; passed configured runtime checks
- Information Technology (sector-information-technology): selected_anchor; selected XLK.
  - XLK: eligible; passed configured runtime checks
- Materials (sector-materials): selected_anchor; selected XLB.
  - XLB: eligible; passed configured runtime checks
- Real Estate (sector-real-estate): selected_anchor; selected XLRE.
  - XLRE: eligible; passed configured runtime checks
- Utilities (sector-utilities): selected_anchor; selected XLU.
  - XLU: eligible; passed configured runtime checks
- Semiconductors (theme-semiconductors): selected_anchor; selected SMH.
  - SMH: eligible; passed configured runtime checks
  - SOXX: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - XSD: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Software (theme-software): inactive_this_run; selected none.
  - IGV: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - XSW: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Cloud Computing (theme-cloud-computing): selected_anchor; selected SKYY.
  - SKYY: eligible; passed configured runtime checks
  - CLOU: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $7,780,396 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - WCLD: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Cybersecurity (theme-cybersecurity): selected_anchor; selected CIBR.
  - CIBR: eligible; passed configured runtime checks
  - HACK: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - BUG: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Internet (theme-internet): inactive_this_run; selected none.
  - FDN: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Artificial Intelligence & Big Data (theme-artificial-intelligence): inactive_this_run; selected none.
  - AIQ: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - THNQ: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $4,278,916 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Robotics & Automation (theme-robotics-automation): inactive_this_run; selected none.
  - BOTZ: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - ROBO: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Quantum Computing (theme-quantum-computing): inactive_this_run; selected none.
  - QTUM: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Fintech (theme-fintech): inactive_this_run; selected none.
  - FINX: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $973,945 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - ARKF: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $5,090,389 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Blockchain & Digital-Asset Companies (theme-blockchain): inactive_this_run; selected none.
  - BLOK: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - BKCH: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $4,729,674 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Data Centers & Digital Infrastructure (theme-data-centers): inactive_this_run; selected none.
  - SRVR: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $3,548,022 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - VPN: ineligible; ETF price history unavailable; Requires 64 valid price sessions; 0 available; Retrieved instrument is not verified as a USD ETF; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume unavailable; Price retrieval error: RuntimeError: Source request failed for https://query1.finance.yahoo.com/v8/finance/chart/VPN?period1=1729544270&period2=1792875470&interval=1d&events=div%2Csplits&includeAdjustedClose=true: HTTP Error 404: Not Found; Source request failed for https://query2.finance.yahoo.com/v8/finance/chart/VPN?period1=1729544270&period2=1792875470&interval=1d&events=div%2Csplits&includeAdjustedClose=true: HTTP Error 404: Not Found
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Autonomous & Electric Vehicles (theme-autonomous-electric-vehicles): inactive_this_run; selected none.
  - DRIV: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $1,376,545 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - KARS: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $219,654 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - IDRV: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Video Games & Esports (theme-video-games): inactive_this_run; selected none.
  - GAMR: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $55,092 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - HERO: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $364,759 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- E-Commerce (theme-ecommerce): inactive_this_run; selected none.
  - IBUY: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $553,809 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - ONLN: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $173,212 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Biotechnology (theme-biotechnology): selected_anchor; selected XBI.
  - XBI: eligible; passed configured runtime checks
  - IBB: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Pharmaceuticals (theme-pharmaceuticals): inactive_this_run; selected none.
  - XPH: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - PJP: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $4,489,284 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Medical Devices (theme-medical-devices): inactive_this_run; selected none.
  - IHI: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - XHE: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $3,722,888 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Healthcare Providers (theme-healthcare-providers): inactive_this_run; selected none.
  - IHF: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - XHS: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $5,232,190 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Genomics (theme-genomics): inactive_this_run; selected none.
  - ARKG: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - GNOM: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $2,475,767 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Cannabis (theme-cannabis): inactive_this_run; selected none.
  - MSOS: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - MJ: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $723,067 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Aerospace & Defense (theme-aerospace-defense): selected_anchor; selected XAR.
  - ITA: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - XAR: eligible; passed configured runtime checks
  - PPA: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Space Economy (theme-space): inactive_this_run; selected none.
  - UFO: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - ARKX: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- US Infrastructure (theme-us-infrastructure): inactive_this_run; selected none.
  - PAVE: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - IFRA: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Transportation (theme-transportation): inactive_this_run; selected none.
  - IYT: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - XTN: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Airlines (theme-airlines): inactive_this_run; selected none.
  - JETS: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Shipping (theme-shipping): inactive_this_run; selected none.
  - BOAT: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $7,630,248 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Water (theme-water): inactive_this_run; selected none.
  - PHO: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $4,788,136 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - FIW: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $4,775,037 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Agribusiness (theme-agribusiness): inactive_this_run; selected none.
  - MOO: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - VEGI: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $2,004,358 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Oil & Gas Exploration & Production (theme-oil-gas-exploration): inactive_this_run; selected none.
  - XOP: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - IEO: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Oil Services (theme-oil-services): inactive_this_run; selected none.
  - OIH: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - IEZ: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Midstream & MLP Infrastructure (theme-midstream): inactive_this_run; selected none.
  - AMLP: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - MLPX: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Natural Gas Companies (theme-natural-gas-equities): inactive_this_run; selected none.
  - FCG: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Clean Energy (theme-clean-energy): selected_anchor; selected ICLN.
  - ICLN: eligible; passed configured runtime checks
  - PBW: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - QCLN: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $5,019,953 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Solar (theme-solar): inactive_this_run; selected none.
  - TAN: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Wind Energy (theme-wind): inactive_this_run; selected none.
  - FAN: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $1,515,400 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Uranium Miners (theme-uranium-miners): inactive_this_run; selected none.
  - URA: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - URNM: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Nuclear Energy (theme-nuclear-energy): inactive_this_run; selected none.
  - NLR: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - NUKZ: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $6,185,044 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Lithium & Battery Technology (theme-lithium-batteries): inactive_this_run; selected none.
  - LIT: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - BATT: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $547,780 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Copper Miners (theme-copper-miners): inactive_this_run; selected none.
  - COPX: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Rare Earth & Strategic Materials (theme-rare-earths): inactive_this_run; selected none.
  - REMX: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - EART: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $535,493 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Gold Miners (theme-gold-miners): inactive_this_run; selected none.
  - GDX: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - RING: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Silver Miners (theme-silver-miners): inactive_this_run; selected none.
  - SIL: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - SLVP: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $7,558,988 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Steel Producers (theme-steel): inactive_this_run; selected none.
  - SLX: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $1,219,731 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Diversified Metals & Mining (theme-metals-mining): inactive_this_run; selected none.
  - PICK: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - XME: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Timber & Forestry (theme-timber-forestry): inactive_this_run; selected none.
  - WOOD: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $1,645,789 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - CUT: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $45,398 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Regional Banks (theme-regional-banks): inactive_this_run; selected none.
  - KRE: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - IAT: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Insurance (theme-insurance): inactive_this_run; selected none.
  - KIE: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - IAK: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Broker-Dealers & Capital Markets (theme-capital-markets): inactive_this_run; selected none.
  - IAI: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Homebuilders (theme-homebuilders): inactive_this_run; selected none.
  - ITB: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - XHB: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Retail (theme-retail): inactive_this_run; selected none.
  - XRT: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - RTH: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $844,702 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Leisure & Entertainment (theme-leisure-entertainment): inactive_this_run; selected none.
  - PEJ: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $2,834,073 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Food & Beverage (theme-food-beverage): inactive_this_run; selected none.
  - PBJ: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $1,145,304 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Residential Real Estate (theme-residential-real-estate): inactive_this_run; selected none.
  - REZ: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Mortgage REITs (theme-mortgage-reits): inactive_this_run; selected none.
  - REM: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - MORT: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid

## Methodology and limits
- ETF candidates require at least 64 valid price sessions and $10,000,000 30-session average dollar volume; AUM/spread are reported unavailable when a reproducible source is not configured.
- Holdings breadth requires a dated official equity holdings source, at least 8 valid companies, 80% price coverage, and holdings no older than 35 days. These checks do not enter scoring.
- Score weights are configured as {"current_strength_weights": {"excess21_percentile": 1.0}, "medium_strength_weights": {"excess63_percentile": 1.0}, "minimum_peers": 10, "purpose": "Consistent relative-strength ranking for manual review; not a prediction or entry signal", "score_method": "price_relative_strength_v6_2", "state_threshold": 50.0, "theme_score_weights": {"current_strength": 0.6, "medium_strength": 0.4}}. This is a consistent relative-strength ranking for manual review, not a prediction or entry signal.
- Missing score inputs are not imputed or reweighted. ETF and index breadth use complete sourced equity universes independently of curated stock watchlists.
- Index and ETF memberships are current source snapshots, not historical point-in-time universes. Yahoo adjusted-close semantics are vendor conventions.
- Nasdaq market-cap fields have no separate observation timestamps, so stock eligibility remains provisional. Sector stock watchlists use current S&P 500 classifications intersected with official sector ETF holdings and the configured price, cap and liquidity filters.
- Ineligible anchors, unavailable ETF scores, unavailable breadth, and missing curated stock drilldowns are separate statuses. Missing breadth or stocks does not make an ETF ineligible.

## Source errors
```json
{
  "core": {
    "charts": {
      "VPN": "RuntimeError: Source request failed for https://query1.finance.yahoo.com/v8/finance/chart/VPN?period1=1729544270&period2=1792875470&interval=1d&events=div%2Csplits&includeAdjustedClose=true: HTTP Error 404: Not Found; Source request failed for https://query2.finance.yahoo.com/v8/finance/chart/VPN?period1=1729544270&period2=1792875470&interval=1d&events=div%2Csplits&includeAdjustedClose=true: HTTP Error 404: Not Found"
    },
    "quotes": {
      "-": "RuntimeError: Nasdaq quote summary returned no summary fields for -",
      "2602335D": "RuntimeError: Nasdaq quote summary returned no summary fields for 2602335D",
      "BF-B": "RuntimeError: Nasdaq quote summary returned no summary fields for BF-B",
      "BRK-B": "RuntimeError: Nasdaq quote summary returned no summary fields for BRK-B",
      "IXCZ6": "RuntimeError: Nasdaq quote summary returned no summary fields for IXCZ6",
      "IXAZ6": "RuntimeError: Nasdaq quote summary returned no summary fields for IXAZ6",
      "IXDZ6": "RuntimeError: Nasdaq quote summary returned no summary fields for IXDZ6",
      "IXIZ6": "RuntimeError: Nasdaq quote summary returned no summary fields for IXIZ6",
      "IXRZ6": "RuntimeError: Nasdaq quote summary returned no summary fields for IXRZ6",
      "IXPZ6": "RuntimeError: Nasdaq quote summary returned no summary fields for IXPZ6",
      "IXSZ6": "RuntimeError: Nasdaq quote summary returned no summary fields for IXSZ6",
      "IXTZ6": "RuntimeError: Nasdaq quote summary returned no summary fields for IXTZ6",
      "IXYZ6": "RuntimeError: Nasdaq quote summary returned no summary fields for IXYZ6",
      "XARZ6": "RuntimeError: Nasdaq quote summary returned no summary fields for XARZ6",
      "XASZ6": "RuntimeError: Nasdaq quote summary returned no summary fields for XASZ6"
    },
    "holdings": {},
    "sec": {}
  },
  "constituent_histories": {}
}
```

## Sector stock-list scope
Sector stock candidates are the current S&P 500 sector classification intersected with official selected-sector ETF holdings, then filtered by the configured listed-equity, price, market-cap and ADV rules. This is not every listed company in each sector. Per-company evidence and exclusions are in stock_diagnostics.csv.

## Local files
dashboard.html, market.csv, themes.csv, registry_audit.csv, stock_diagnostics.csv, latest_snapshot.json, raw_inputs.json, iwm_breadth_prices.csv.gz, Inter-LICENSE.txt, source_matrix.csv, watchlist_15.csv, watchlist_20.csv, tradingview_15.txt, tradingview_20.txt, run_bundle.zip.
Refresh with python scripts/generate_dashboard.py. Failed refreshes preserve existing valid exports and write refresh_status.json/failed_refresh.md separately.
