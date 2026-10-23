# ThemeScope v6.1 run report

Market session: 2026-10-22
Dashboard generated: 2026-10-23T19:01:55+00:00 (24 Oct 2026, 03:01 AM HKT)
Latest source retrieval: 2026-10-23T18:53:49+00:00
Base collection: 2026-10-23T16:05:28+00:00 to 2026-10-23T16:35:50+00:00
Requested as-of: latest verified completed common session

## Market/index facts
- SPY (S&P 500 ETF): close 763.9600219726562; session 2026-10-22; price status valid; valid.
  - Return5: -0.010145190113378333; valid; Exact 5-session endpoints; 6/6 observations present.
  - Return21: -0.005014229559629713; valid; Exact 21-session endpoints; 22/22 observations present.
  - Return63: 0.03644068217649932; valid; Exact 63-session endpoints; 64/64 observations present.
  - Close at/below EMA21 (769.7018877774145); constituent breadth 355/499 valid, 500 eligible, 99.8% coverage, holdings/list as of 2026-10-23; valid: valid
  - Close at/below EMA50 (766.0690511548144); constituent breadth 320/497 valid, 500 eligible, 99.4% coverage, holdings/list as of 2026-10-23; valid: valid
- QQQ (Nasdaq-100 ETF): close 704.469970703125; session 2026-10-22; price status valid; valid.
  - Return5: -0.03232146881438869; valid; Exact 5-session endpoints; 6/6 observations present.
  - Return21: -0.04956766662672918; valid; Exact 21-session endpoints; 22/22 observations present.
  - Return63: 0.030653496750308484; valid; Exact 63-session endpoints; 64/64 observations present.
  - Close at/below EMA21 (729.6229044898745); constituent breadth 47/100 valid, 100 eligible, 100.0% coverage, holdings/list as of 2026-10-23; valid: valid
  - Close at/below EMA50 (726.2105471607608); constituent breadth 51/98 valid, 100 eligible, 98.0% coverage, holdings/list as of 2026-10-23; valid: valid
- IWM (Russell 2000 ETF proxy): close 276.6700134277344; session 2026-10-22; price status valid; valid.
  - Return5: 0.0057802345975142; valid; Exact 5-session endpoints; 6/6 observations present.
  - Return21: -0.018622303312800237; valid; Exact 21-session endpoints; 22/22 observations present.
  - Return63: -0.0473173917543811; valid; Exact 63-session endpoints; 64/64 observations present.
  - Close at/below EMA21 (278.1701417436802); IWM holdings breadth 60/180 valid, 1964 eligible, 9.164969450101832% coverage, holdings/list as of 2026-10-22; unavailable: Price coverage 180/1964 below 80%
  - Close at/below EMA50 (283.54190645586766); IWM holdings breadth 45/174 valid, 1964 eligible, 8.859470468431772% coverage, holdings/list as of 2026-10-22; unavailable: Price coverage 174/1964 below 80%

## Volatility context
- ^VIX: level 19.030000686645508; daily 0.14088731046009184; 5-session 0.15613619350667118; 21-session 0.25362320843676334; trailing 1-year percentile 75.7936507936508; observation date 2026-10-22; retrieved 2026-10-23T18:53:49+00:00; available: https://query1.finance.yahoo.com/v8/finance/chart/^VIX?period1=1729536829&period2=1792868029&interval=1d&events=div%2Csplits&includeAdjustedClose=true. No breadth fields or score dependency.

## Eligible primary ETF ranking
Current is the 21-session excess-return percentile; Medium is the 63-session excess-return percentile; Theme Score = 60% Current + 40% Medium. Percentiles require at least 10 valid peers. Breadth and curated stocks do not enter score or state.
- Communication Services (XLC), Sector: score 37.5; state Fading; curated stock drilldown available (18); anchor eligibility eligible.
  - percentile_excess21: 25.0; valid; valid
  - percentile_excess63: 56.25; valid; valid
  - etf_breadth21_pct: 36.8421052631579; valid; valid
  - etf_breadth50_pct: 26.31578947368421; valid; valid
  - current_strength_score: 25.0; valid; valid
  - medium_strength_score: 56.25; valid; valid
  - theme_score: 37.5; valid; valid
  - Score peers: 21-session 17; 63-session 17; method price_relative_strength_v6_1; unavailable reason none.
  - Breadth: EMA21 valid: valid; EMA50 valid: valid.
  - 2 excluded source rows; 1 unresolved equity mappings remain in coverage denominator.
- Consumer Discretionary (XLY), Sector: score 72.5; state Leading; curated stock drilldown available (20); anchor eligibility eligible.
  - percentile_excess21: 75.0; valid; valid
  - percentile_excess63: 68.75; valid; valid
  - etf_breadth21_pct: 72.34042553191489; valid; valid
  - etf_breadth50_pct: 65.95744680851064; valid; valid
  - current_strength_score: 75.0; valid; valid
  - medium_strength_score: 68.75; valid; valid
  - theme_score: 72.5; valid; valid
  - Score peers: 21-session 17; 63-session 17; method price_relative_strength_v6_1; unavailable reason none.
  - Breadth: EMA21 valid: valid; EMA50 valid: valid.
  - 2 excluded source rows; 1 unresolved equity mappings remain in coverage denominator.
- Consumer Staples (XLP), Sector: score 90.0; state Leading; curated stock drilldown available (20); anchor eligibility eligible.
  - percentile_excess21: 100.0; valid; valid
  - percentile_excess63: 75.0; valid; valid
  - etf_breadth21_pct: 93.93939393939394; valid; valid
  - etf_breadth50_pct: 90.9090909090909; valid; valid
  - current_strength_score: 100.0; valid; valid
  - medium_strength_score: 75.0; valid; valid
  - theme_score: 90.0; valid; valid
  - Score peers: 21-session 17; 63-session 17; method price_relative_strength_v6_1; unavailable reason none.
  - Breadth: EMA21 valid: valid; EMA50 valid: valid.
  - 3 excluded source rows; 1 unresolved equity mappings remain in coverage denominator.
- Energy (XLE), Sector: score 91.25; state Leading; curated stock drilldown available (20); anchor eligibility eligible.
  - percentile_excess21: 93.75; valid; valid
  - percentile_excess63: 87.5; valid; valid
  - etf_breadth21_pct: 80.95238095238095; valid; valid
  - etf_breadth50_pct: 76.19047619047619; valid; valid
  - current_strength_score: 93.75; valid; valid
  - medium_strength_score: 87.5; valid; valid
  - theme_score: 91.25; valid; valid
  - Score peers: 21-session 17; 63-session 17; method price_relative_strength_v6_1; unavailable reason none.
  - Breadth: EMA21 valid: valid; EMA50 valid: valid.
  - 2 excluded source rows; 1 unresolved equity mappings remain in coverage denominator.
- Financials (XLF), Sector: score 58.75; state Improving; curated stock drilldown available (20); anchor eligibility eligible.
  - percentile_excess21: 68.75; valid; valid
  - percentile_excess63: 43.75; valid; valid
  - etf_breadth21_pct: 78.94736842105263; valid; valid
  - etf_breadth50_pct: 63.1578947368421; valid; valid
  - current_strength_score: 68.75; valid; valid
  - medium_strength_score: 43.75; valid; valid
  - theme_score: 58.75; valid; valid
  - Score peers: 21-session 17; 63-session 17; method price_relative_strength_v6_1; unavailable reason none.
  - Breadth: EMA21 valid: valid; EMA50 valid: valid.
  - 3 excluded source rows; 1 unresolved equity mappings remain in coverage denominator.
- Health Care (XLV), Sector: score 81.25; state Leading; curated stock drilldown available (20); anchor eligibility eligible.
  - percentile_excess21: 81.25; valid; valid
  - percentile_excess63: 81.25; valid; valid
  - etf_breadth21_pct: 96.66666666666667; valid; valid
  - etf_breadth50_pct: 95.0; valid; valid
  - current_strength_score: 81.25; valid; valid
  - medium_strength_score: 81.25; valid; valid
  - theme_score: 81.25; valid; valid
  - Score peers: 21-session 17; 63-session 17; method price_relative_strength_v6_1; unavailable reason none.
  - Breadth: EMA21 valid: valid; EMA50 valid: valid.
  - 3 excluded source rows; 1 unresolved equity mappings remain in coverage denominator.
- Industrials (XLI), Sector: score 27.5; state Lagging; curated stock drilldown available (20); anchor eligibility eligible.
  - percentile_excess21: 37.5; valid; valid
  - percentile_excess63: 12.5; valid; valid
  - etf_breadth21_pct: 60.24096385542169; valid; valid
  - etf_breadth50_pct: 54.32098765432099; valid; valid
  - current_strength_score: 37.5; valid; valid
  - medium_strength_score: 12.5; valid; valid
  - theme_score: 27.5; valid; valid
  - Score peers: 21-session 17; 63-session 17; method price_relative_strength_v6_1; unavailable reason none.
  - Breadth: EMA21 valid: valid; EMA50 valid: valid.
  - 2 excluded source rows; 1 unresolved equity mappings remain in coverage denominator.
- Information Technology (XLK), Sector: score 36.25; state Fading; curated stock drilldown available (20); anchor eligibility eligible.
  - percentile_excess21: 18.75; valid; valid
  - percentile_excess63: 62.5; valid; valid
  - etf_breadth21_pct: 36.0; valid; valid
  - etf_breadth50_pct: 42.666666666666664; valid; valid
  - current_strength_score: 18.75; valid; valid
  - medium_strength_score: 62.5; valid; valid
  - theme_score: 36.25; valid; valid
  - Score peers: 21-session 17; 63-session 17; method price_relative_strength_v6_1; unavailable reason none.
  - Breadth: EMA21 valid: valid; EMA50 valid: valid.
  - 2 excluded source rows; 1 unresolved equity mappings remain in coverage denominator.
- Materials (XLB), Sector: score 57.5; state Leading; curated stock drilldown available (20); anchor eligibility eligible.
  - percentile_excess21: 62.5; valid; valid
  - percentile_excess63: 50.0; valid; valid
  - etf_breadth21_pct: 83.33333333333333; valid; valid
  - etf_breadth50_pct: 66.66666666666667; valid; valid
  - current_strength_score: 62.5; valid; valid
  - medium_strength_score: 50.0; valid; valid
  - theme_score: 57.5; valid; valid
  - Score peers: 21-session 17; 63-session 17; method price_relative_strength_v6_1; unavailable reason none.
  - Breadth: EMA21 valid: valid; EMA50 valid: valid.
  - 2 excluded source rows; 1 unresolved equity mappings remain in coverage denominator.
- Real Estate (XLRE), Sector: score 46.25; state Improving; curated stock drilldown available (20); anchor eligibility eligible.
  - percentile_excess21: 56.25; valid; valid
  - percentile_excess63: 31.25; valid; valid
  - etf_breadth21_pct: 80.0; valid; valid
  - etf_breadth50_pct: 50.0; valid; valid
  - current_strength_score: 56.25; valid; valid
  - medium_strength_score: 31.25; valid; valid
  - theme_score: 46.25; valid; valid
  - Score peers: 21-session 17; 63-session 17; method price_relative_strength_v6_1; unavailable reason none.
  - Breadth: EMA21 valid: valid; EMA50 valid: valid.
  - 2 excluded source rows; 1 unresolved equity mappings remain in coverage denominator.
- Utilities (XLU), Sector: score 62.5; state Improving; curated stock drilldown available (20); anchor eligibility eligible.
  - percentile_excess21: 87.5; valid; valid
  - percentile_excess63: 25.0; valid; valid
  - etf_breadth21_pct: 87.09677419354838; valid; valid
  - etf_breadth50_pct: 83.87096774193549; valid; valid
  - current_strength_score: 87.5; valid; valid
  - medium_strength_score: 25.0; valid; valid
  - theme_score: 62.5; valid; valid
  - Score peers: 21-session 17; 63-session 17; method price_relative_strength_v6_1; unavailable reason none.
  - Breadth: EMA21 valid: valid; EMA50 valid: valid.
  - 2 excluded source rows; 1 unresolved equity mappings remain in coverage denominator.
- Semiconductors (SMH), Theme: score 7.5; state Lagging; curated stock drilldown available (13); anchor eligibility eligible.
  - percentile_excess21: 0.0; valid; valid
  - percentile_excess63: 18.75; valid; valid
  - etf_breadth21_pct: 0.0; valid; valid
  - etf_breadth50_pct: 4.3478260869565215; valid; valid
  - current_strength_score: 0.0; valid; valid
  - medium_strength_score: 18.75; valid; valid
  - theme_score: 7.5; valid; valid
  - Score peers: 21-session 17; 63-session 17; method price_relative_strength_v6_1; unavailable reason none.
  - Breadth: EMA21 valid: valid; EMA50 valid: valid.
  - 2 excluded source rows; 1 unresolved equity mappings remain in coverage denominator.
- Cloud Computing (SKYY), Theme: score 66.25; state Fading; curated stock drilldown available (10); anchor eligibility eligible.
  - percentile_excess21: 43.75; valid; valid
  - percentile_excess63: 100.0; valid; valid
  - etf_breadth21_pct: 60.0; valid; valid
  - etf_breadth50_pct: 69.23076923076923; valid; valid
  - current_strength_score: 43.75; valid; valid
  - medium_strength_score: 100.0; valid; valid
  - theme_score: 66.25; valid; valid
  - Score peers: 21-session 17; 63-session 17; method price_relative_strength_v6_1; unavailable reason none.
  - Breadth: EMA21 valid: valid; EMA50 valid: valid.
  - 0 excluded source rows; 0 unresolved equity mappings remain in coverage denominator.
- Cybersecurity (CIBR), Theme: score 67.5; state Leading; curated stock drilldown available (10); anchor eligibility eligible.
  - percentile_excess21: 50.0; valid; valid
  - percentile_excess63: 93.75; valid; valid
  - etf_breadth21_pct: 51.21951219512195; valid; valid
  - etf_breadth50_pct: 73.17073170731707; valid; valid
  - current_strength_score: 50.0; valid; valid
  - medium_strength_score: 93.75; valid; valid
  - theme_score: 67.5; valid; valid
  - Score peers: 21-session 17; 63-session 17; method price_relative_strength_v6_1; unavailable reason none.
  - Breadth: EMA21 valid: valid; EMA50 valid: valid.
  - 0 excluded source rows; 4 unresolved equity mappings remain in coverage denominator.
- Biotechnology (XBI), Theme: score 33.75; state Lagging; curated stock drilldown unavailable; anchor eligibility eligible.
  - percentile_excess21: 31.25; valid; valid
  - percentile_excess63: 37.5; valid; valid
  - etf_breadth21_pct: 35.6687898089172; valid; valid
  - etf_breadth50_pct: 24.836601307189543; valid; valid
  - current_strength_score: 31.25; valid; valid
  - medium_strength_score: 37.5; valid; valid
  - theme_score: 33.75; valid; valid
  - Score peers: 21-session 17; 63-session 17; method price_relative_strength_v6_1; unavailable reason none.
  - Breadth: EMA21 valid: valid; EMA50 valid: valid.
  - 10 excluded source rows; 0 unresolved equity mappings remain in coverage denominator.
- Aerospace & Defense (XAR), Theme: score 3.75; state Lagging; curated stock drilldown available (10); anchor eligibility eligible.
  - percentile_excess21: 6.25; valid; valid
  - percentile_excess63: 0.0; valid; valid
  - etf_breadth21_pct: 28.0; valid; valid
  - etf_breadth50_pct: 17.391304347826086; valid; valid
  - current_strength_score: 6.25; valid; valid
  - medium_strength_score: 0.0; valid; valid
  - theme_score: 3.75; valid; valid
  - Score peers: 21-session 17; 63-session 17; method price_relative_strength_v6_1; unavailable reason none.
  - Breadth: EMA21 valid: valid; EMA50 valid: valid.
  - 2 excluded source rows; 0 unresolved equity mappings remain in coverage denominator.
- Clean Energy (ICLN), Theme: score 10.0; state Lagging; curated stock drilldown available (4); anchor eligibility eligible.
  - percentile_excess21: 12.5; valid; valid
  - percentile_excess63: 6.25; valid; valid
  - etf_breadth21_pct: 14.285714285714286; unavailable; Price coverage 14/103 below 80%
  - etf_breadth50_pct: 7.142857142857143; unavailable; Price coverage 14/103 below 80%
  - current_strength_score: 12.5; valid; valid
  - medium_strength_score: 6.25; valid; valid
  - theme_score: 10.0; valid; valid
  - Score peers: 21-session 17; 63-session 17; method price_relative_strength_v6_1; unavailable reason none.
  - Breadth: EMA21 unavailable: Price coverage 14/103 below 80%; EMA50 unavailable: Price coverage 14/103 below 80%.
  - 36 excluded source rows; 89 unresolved equity mappings remain in coverage denominator.

## ICLN score and breadth diagnostic
- Current 12.5; Medium 6.25; Theme Score 10.0; state Lagging.
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
  - CLOU: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $7,893,983 is below $10,000,000
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
  - THNQ: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $4,451,869 is below $10,000,000
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
  - FINX: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $990,969 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - ARKF: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $5,154,287 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Blockchain & Digital-Asset Companies (theme-blockchain): inactive_this_run; selected none.
  - BLOK: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - BKCH: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $4,716,240 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Data Centers & Digital Infrastructure (theme-data-centers): inactive_this_run; selected none.
  - SRVR: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $3,506,871 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - VPN: ineligible; ETF price history unavailable; Requires 64 valid price sessions; 0 available; Retrieved instrument is not verified as a USD ETF; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume unavailable; Price retrieval error: RuntimeError: Source request failed for https://query1.finance.yahoo.com/v8/finance/chart/VPN?period1=1729526980&period2=1792858180&interval=1d&events=div%2Csplits&includeAdjustedClose=true: HTTP Error 404: Not Found; Source request failed for https://query2.finance.yahoo.com/v8/finance/chart/VPN?period1=1729526980&period2=1792858180&interval=1d&events=div%2Csplits&includeAdjustedClose=true: HTTP Error 404: Not Found
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Autonomous & Electric Vehicles (theme-autonomous-electric-vehicles): inactive_this_run; selected none.
  - DRIV: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $1,343,613 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - KARS: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $254,478 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - IDRV: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Video Games & Esports (theme-video-games): inactive_this_run; selected none.
  - GAMR: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $52,695 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - HERO: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $353,779 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- E-Commerce (theme-ecommerce): inactive_this_run; selected none.
  - IBUY: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $555,237 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - ONLN: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $173,772 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Biotechnology (theme-biotechnology): selected_anchor; selected XBI.
  - XBI: eligible; passed configured runtime checks
  - IBB: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Pharmaceuticals (theme-pharmaceuticals): inactive_this_run; selected none.
  - XPH: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - PJP: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $4,572,923 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Medical Devices (theme-medical-devices): inactive_this_run; selected none.
  - IHI: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - XHE: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $3,704,232 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Healthcare Providers (theme-healthcare-providers): inactive_this_run; selected none.
  - IHF: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - XHS: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $5,204,255 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Genomics (theme-genomics): inactive_this_run; selected none.
  - ARKG: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - GNOM: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $2,478,954 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Cannabis (theme-cannabis): inactive_this_run; selected none.
  - MSOS: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - MJ: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $729,287 is below $10,000,000
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
  - BOAT: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $7,628,928 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Water (theme-water): inactive_this_run; selected none.
  - PHO: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $4,808,968 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - FIW: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $4,735,380 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Agribusiness (theme-agribusiness): inactive_this_run; selected none.
  - MOO: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - VEGI: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $2,214,708 is below $10,000,000
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
  - PBW: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $9,947,997 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - QCLN: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $5,165,856 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Solar (theme-solar): inactive_this_run; selected none.
  - TAN: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Wind Energy (theme-wind): inactive_this_run; selected none.
  - FAN: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $1,516,557 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Uranium Miners (theme-uranium-miners): inactive_this_run; selected none.
  - URA: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - URNM: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Nuclear Energy (theme-nuclear-energy): inactive_this_run; selected none.
  - NLR: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - NUKZ: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $6,190,369 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Lithium & Battery Technology (theme-lithium-batteries): inactive_this_run; selected none.
  - LIT: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - BATT: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $538,742 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Copper Miners (theme-copper-miners): inactive_this_run; selected none.
  - COPX: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Rare Earth & Strategic Materials (theme-rare-earths): inactive_this_run; selected none.
  - REMX: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - EART: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $533,995 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Gold Miners (theme-gold-miners): inactive_this_run; selected none.
  - GDX: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - RING: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Silver Miners (theme-silver-miners): inactive_this_run; selected none.
  - SIL: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - SLVP: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $7,513,955 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Steel Producers (theme-steel): inactive_this_run; selected none.
  - SLX: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $1,243,787 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Diversified Metals & Mining (theme-metals-mining): inactive_this_run; selected none.
  - PICK: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - XME: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Timber & Forestry (theme-timber-forestry): inactive_this_run; selected none.
  - WOOD: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $1,630,707 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - CUT: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $46,026 is below $10,000,000
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
  - RTH: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $850,663 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Leisure & Entertainment (theme-leisure-entertainment): inactive_this_run; selected none.
  - PEJ: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $2,847,712 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Food & Beverage (theme-food-beverage): inactive_this_run; selected none.
  - PBJ: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $1,149,534 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Residential Real Estate (theme-residential-real-estate): inactive_this_run; selected none.
  - REZ: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate; 30-session average dollar volume $9,936,846 is below $10,000,000
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
- Mortgage REITs (theme-mortgage-reits): inactive_this_run; selected none.
  - REM: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid
  - MORT: ineligible; Unleveraged diversified-equity mandate has not been reviewed for this candidate
    - Breadth only: Candidate-specific official holdings source and parser are not configured; Official holdings file unavailable or empty; Holdings effective date unavailable or invalid

## Methodology and limits
- ETF candidates require at least 64 valid price sessions and $10,000,000 30-session average dollar volume; AUM/spread are reported unavailable when a reproducible source is not configured.
- Holdings breadth requires a dated official equity holdings source, at least 8 valid companies, 80% price coverage, and holdings no older than 35 days. These checks do not enter scoring.
- Score weights are configured as {"current_strength_weights": {"excess21_percentile": 1.0}, "medium_strength_weights": {"excess63_percentile": 1.0}, "minimum_peers": 10, "purpose": "Consistent relative-strength ranking for manual review; not a prediction or entry signal", "score_method": "price_relative_strength_v6_1", "state_threshold": 50.0, "theme_score_weights": {"current_strength": 0.6, "medium_strength": 0.4}}. This is a consistent relative-strength ranking for manual review, not a prediction or entry signal.
- Missing score inputs are not imputed or reweighted. ETF and index breadth use complete sourced equity universes independently of curated stock watchlists.
- Index and ETF memberships are current source snapshots, not historical point-in-time universes. Yahoo adjusted-close semantics are vendor conventions.
- Nasdaq market-cap fields have no separate observation timestamps, so stock eligibility remains provisional. Sector stock watchlists use current S&P 500 classifications intersected with official sector ETF holdings and the configured price, cap and liquidity filters.
- Ineligible anchors, unavailable ETF scores, unavailable breadth, and missing curated stock drilldowns are separate statuses. Missing breadth or stocks does not make an ETF ineligible.

## Source errors
```json
{
  "core": {
    "charts": {
      "VPN": "RuntimeError: Source request failed for https://query1.finance.yahoo.com/v8/finance/chart/VPN?period1=1729526980&period2=1792858180&interval=1d&events=div%2Csplits&includeAdjustedClose=true: HTTP Error 404: Not Found; Source request failed for https://query2.finance.yahoo.com/v8/finance/chart/VPN?period1=1729526980&period2=1792858180&interval=1d&events=div%2Csplits&includeAdjustedClose=true: HTTP Error 404: Not Found"
    },
    "quotes": {
      "-": "RuntimeError: Nasdaq quote summary returned no summary fields for -",
      "2602335D": "RuntimeError: Nasdaq quote summary returned no summary fields for 2602335D",
      "BF-B": "RuntimeError: Nasdaq quote summary returned no summary fields for BF-B",
      "BRK-B": "RuntimeError: Nasdaq quote summary returned no summary fields for BRK-B",
      "IXAZ6": "RuntimeError: Nasdaq quote summary returned no summary fields for IXAZ6",
      "IXCZ6": "RuntimeError: Nasdaq quote summary returned no summary fields for IXCZ6",
      "IXIZ6": "RuntimeError: Nasdaq quote summary returned no summary fields for IXIZ6",
      "IXDZ6": "RuntimeError: Nasdaq quote summary returned no summary fields for IXDZ6",
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
dashboard.html, market.csv (SPY, QQQ, IWM, VIX with instrument-specific fields), themes.csv, registry_audit.csv, stock_diagnostics.csv, latest_snapshot.json, raw_inputs.json, source_matrix.csv, watchlist_15.csv, watchlist_20.csv, tradingview_15.txt, tradingview_20.txt, run_bundle.zip.
Opening HTML never retrieves data. Explicitly run python scripts/generate_dashboard.py. Failed refreshes preserve existing valid exports and write refresh_status.json/failed_refresh.md separately.
