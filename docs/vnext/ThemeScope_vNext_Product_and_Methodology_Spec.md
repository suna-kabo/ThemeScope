# ThemeScope vNext Product and Methodology Specification

Status: proposed implementation baseline  
Research-universe snapshot: 2026-11-05  
Purpose: local, private, end-of-day US equity theme-rotation research dashboard

## 1. Product boundary

ThemeScope vNext is a research tool, not an execution system.

It must:
- determine the SPY/QQQ market regime using deterministic rules;
- rank internally defined equity themes;
- compare stocks with their actual theme peers;
- produce a Daily Primary research list and TradingView-compatible TXT exports;
- preserve effective-dated membership and historical state;
- run locally with one-click data refresh.

It must not:
- generate entries, stops, position sizes or exits;
- place orders;
- connect to any brokerage trading endpoint;
- scrape TradingView automatically;
- publish licensed market data publicly by default;
- silently change methodology based on provider availability.

## 2. Major architectural change

Thematic ETFs are removed entirely from ThemeScope calculations.

Old:
ETF -> Theme Score -> stock-vs-ETF -> Primary list

vNext:
Theme Charter -> effective-dated stock membership -> custom theme metrics ->
Theme Score -> stock-vs-peer relative performance -> Primary list

SPY and QQQ remain market benchmarks. IWM remains context only.

Thematic ETFs may still be viewed manually by the user outside ThemeScope, but no
ETF ticker, holding, return, EMA or liquidity metric may affect theme ranking,
membership or Primary qualification.

## 3. Stock scanner policy

The quarterly/ad-hoc membership-review candidate universe is the user's TradingView
Stock scanner with all of these filters:

- Market capitalization >= USD 2,000,000,000
- Price >= USD 5
- Security type = Common Stock
- Exchange = NYSE or NASDAQ only
- NYSE Arca is excluded
- Average Volume 10D > 500,000 shares
- Price x Volume (Turnover), 1D >= USD 10,000,000

The 2026-11-05 CSV is the first vNext review snapshot.

SPY, QQQ, IWM and ETF scanners have no filters. In vNext:
- ETF scanner is retired.
- IWM constituent scanner is retired because IWM has no breadth vote.
- SPY and QQQ constituent scanners are used only for periodic manual roster updates.
- Stock scanner is used only for quarterly/ad-hoc membership review, not daily refresh.

## 4. Membership model

Each stock-theme relationship is one of:

Core:
The theme is a principal or material business exposure of the company.

Enabler:
The company materially supplies specialized products/services required by the
theme, but the theme is not necessarily the company's main economic identity.

Related:
The relationship is real but too indirect or immaterial to enter the benchmark or
Primary stock filter. Related rows may be kept for context but are not benchmark-eligible.

Only Core and Enabler relationships enter:
- Theme 1M/3M benchmark
- Theme breadth
- synthetic theme index
- stock-vs-peer Primary qualification

Multi-theme membership is allowed.

No permanent "home theme" is required. Combined-export placement is dynamic and
must not be treated as a statement of the company's only true theme.

## 5. Evidence hierarchy

Use this order when reviewing membership:
1. SEC filing / annual report / regulatory filing
2. official investor-relations or company business description
3. official segment/product revenue evidence
4. reliable industry classification
5. multiple independent thematic/index memberships as validation only
6. general news only for discovery, never as sole final evidence

If reliable revenue segmentation is available:
- >=50% directly attributable exposure is strong Core evidence;
- 25% to <50% is material and can be Core or Enabler depending on the Charter;
- <25% is normally Related unless the company's principal-business test clearly
  supports a stronger classification.

Avoid fake precision. Do not invent a 0-100 relevance score without a defensible
data source.

## 6. Membership review cadence

Normal review: quarterly.  
Ad-hoc review: major IPO, spin-off, acquisition, divestiture or material business-model change.

The scanner determines eligibility for review. It must not automatically edit membership.

A review tool should:
- validate the supplied CSV against the exact scanner policy;
- show newly eligible stocks;
- show existing active members absent from the candidate universe;
- show possible classification changes;
- output a proposed diff;
- require explicit approval before writing membership config.

Every accepted membership has effective_from. Removed relationships receive effective_to.
Historical membership is never retroactively rewritten.

User clarification (5 November 2026): effective_from is the first US trading
session whose close-to-close return the new membership earns. A review approved
on session t takes effect through a rebalance at t close; the old membership
earns all of t's return and the new set earns the next trading session's return.
effective_to is exclusive: the old relationship stops earning returns on that
session. Do not backdate approval to the prior close.

Launch dates remain pending. The 2026-11-05 review/export filename is not a
go-live session. When launch session L is explicitly approved, old membership
owns L's return, rebalance occurs at L close and effective_from is the next US
trading session. For a new vNext series, initialize its level at L close without
splicing legacy ETF returns into the vNext series; bootstrap is indicator-only.

## 7. Active-theme requirements

A theme is Active only if:
- it has a clear economic activity;
- inclusion and exclusion rules are written;
- it has a distinct economic driver or a justified parent/child relationship;
- it has at least 5 launch-eligible Core+Enabler members;
- the relationship can be classified consistently from public evidence.

A concept with fewer than 5 Core+Enabler members is Watch-only:
- visible in research configuration if desired;
- no Theme Score;
- no synthetic benchmark;
- no Primary filtering.

## 8. Launch taxonomy

Proposed Active themes: 44  
Proposed Watch-only themes: 8  
Launch Core/Enabler relationships: 729  
Unique launch member tickers: 671

### Active themes

| Theme | Core | Enabler | Total |
|---|---:|---:|---:|
| Airlines | 5 | 0 | 5 |
| Copper Miners | 5 | 0 | 5 |
| Mortgage REITs | 5 | 0 | 5 |
| Solar | 5 | 0 | 5 |
| Timber & Forest Products | 5 | 0 | 5 |
| AI Applications & Platforms | 5 | 1 | 6 |
| Data Centers & Digital Infrastructure | 6 | 0 | 6 |
| Homebuilders | 7 | 0 | 7 |
| Silver Miners | 7 | 0 | 7 |
| Natural Gas Producers | 6 | 2 | 8 |
| Water Infrastructure & Utilities | 7 | 1 | 8 |
| Residential REITs | 9 | 0 | 9 |
| Robotics & Physical Automation | 4 | 6 | 10 |
| Marine Shipping | 11 | 0 | 11 |
| Electric & Autonomous Vehicles | 4 | 8 | 12 |
| Space Economy | 9 | 3 | 12 |
| Digital Assets & Crypto Infrastructure | 12 | 1 | 13 |
| Gold Miners & Royalties | 10 | 3 | 13 |
| Agribusiness | 13 | 1 | 14 |
| Nuclear Energy | 7 | 7 | 14 |
| Leisure & Entertainment | 15 | 0 | 15 |
| Clean Energy & Grid Transition | 9 | 7 | 16 |
| Cloud Infrastructure & Platforms | 13 | 3 | 16 |
| Genomics & Precision Medicine | 14 | 2 | 16 |
| Midstream & LNG Infrastructure | 17 | 0 | 17 |
| Pharmaceuticals | 17 | 0 | 17 |
| Cybersecurity | 15 | 3 | 18 |
| Oil Services & Drilling | 19 | 0 | 19 |
| Fintech & Digital Payments | 19 | 1 | 20 |
| Retail | 20 | 0 | 20 |
| Aerospace & Defense | 21 | 0 | 21 |
| Construction & Infrastructure | 19 | 2 | 21 |
| Food & Beverage | 23 | 0 | 23 |
| Medical Devices & Diagnostics | 23 | 0 | 23 |
| Oil & Gas Producers | 23 | 0 | 23 |
| Internet Platforms & Digital Commerce | 24 | 0 | 24 |
| Regional Banks | 24 | 0 | 24 |
| AI Compute & Connectivity Infrastructure | 8 | 17 | 25 |
| Capital Markets | 25 | 0 | 25 |
| Healthcare Providers & Services | 26 | 0 | 26 |
| Insurance | 27 | 0 | 27 |
| Enterprise & Application Software | 31 | 0 | 31 |
| Semiconductors | 38 | 2 | 40 |
| Biotechnology | 47 | 0 | 47 |

### Watch-only themes

| Theme | Core candidates | Enabler candidates | Reason |
|---|---:|---:|---|
| Quantum Computing | 4 | 0 | fewer than 5 launch-eligible Core/Enabler members |
| Video Games & Interactive Entertainment | 3 | 0 | fewer than 5 launch-eligible Core/Enabler members |
| Wind Energy | 1 | 3 | fewer than 5 launch-eligible Core/Enabler members |
| Uranium Miners | 2 | 0 | fewer than 5 launch-eligible Core/Enabler members |
| Lithium & Battery Technology | 1 | 0 | fewer than 5 launch-eligible Core/Enabler members |
| Rare Earth & Critical Materials | 3 | 0 | fewer than 5 launch-eligible Core/Enabler members |
| Steel | 4 | 0 | fewer than 5 launch-eligible Core/Enabler members |
| Cannabis | 0 | 0 | fewer than 5 launch-eligible Core/Enabler members |

Broad GICS-like sectors (Technology, Energy, Healthcare, etc.) are retained only
as navigation/context families. They do not compete with themes in Theme Score or
Daily Primary research.

## 9. Return definitions

Do not use provider-specific "Perf.1M" or "Perf.3M" fields.

For a target US session t:
- R1M = adjusted_close[t] / adjusted_close[t-21 trading sessions] - 1
- R3M = adjusted_close[t] / adjusted_close[t-63 trading sessions] - 1

Use completed US sessions only.

Historical bars used for price calculations must be adjusted for:
- stock splits
- spin-offs

Do not dividend-adjust. ThemeScope is measuring price behavior, not total return.

## 10. Theme cross-sectional benchmark

For Active theme T:

Valid members = active Core+Enabler members with required observations.

Coverage:
valid_count / configured_active_member_count

Metric is available only when:
- valid_count >= 5
- coverage >= 80%

Theme1M(T) = median(member R1M)
Theme3M(T) = median(member R3M)

Median is intentional. ThemeScope wants the typical stock in the theme rather
than a market-cap-weighted portfolio dominated by the largest constituents.

## 11. Theme Score

Across all Active themes with valid metrics:

P1M = percentile rank of Theme1M
P3M = percentile rank of Theme3M

Use deterministic average-rank percentiles:
percentile = (average_rank - 1) / (N - 1) * 100

Thus:
- weakest valid theme = 0
- strongest valid theme = 100
- ties receive the average tied rank

Theme Score = 0.60 * P1M + 0.40 * P3M

Theme breadth is context only and never enters Theme Score.

## 12. Synthetic theme index

Each Active theme has a chain-linked synthetic price index.

Purpose:
- EMA21 / EMA50 theme trend
- visible theme chart/history
- transition detection

Rules:
- starting level for a new methodology series = 100
- equal-weight members at each formal rebalance
- rebalance at the close immediately preceding effective_from, after the old
  membership has earned that close-to-close session's return
- new membership first earns the return ending on effective_from; a change
  approved on t cannot earn t's return
- between rebalances, holdings drift naturally; do not re-equal-weight daily
- corporate-action-adjusted price returns
- chain-link at membership changes to avoid false jumps

At vNext launch, a bootstrap history using launch-date membership may be built only
to initialize indicators. It must be explicitly tagged bootstrap and must not be
presented as historical live ThemeScope signals.

Live vNext history begins on the first actual vNext session.

Theme Trend:
- Bullish if synthetic index > EMA21 and > EMA50
- Bearish if synthetic index < EMA21 and < EMA50
- Mixed otherwise
- missing/invalid is Unavailable, never Mixed

## 13. Theme Priority

Preserve the existing deterministic market-regime logic.

For Long / Selective Long:
- Theme Score >= 50
- Theme Trend is Bullish or Mixed
- retain the existing valid Newly Bullish one-session exception

For Short / Selective Short:
- Theme Score < 50
- Theme Trend is Bearish or Mixed
- retain the existing valid Newly Bearish one-session exception

Neutral / Unclassified market:
- all themes are Watch

At methodology migration:
- Priority Change = N/A
- Newly Bullish/Bearish = N/A
until genuine compatible vNext prior-session history exists.

## 14. Stock-vs-peer relative performance

For stock S in theme T:

Peer1M(S,T) = median(R1M of other valid Core+Enabler members in T)
Peer3M(S,T) = median(R3M of other valid Core+Enabler members in T)

The stock itself is excluded: Leave-One-Out.

ER1M = Stock R1M - Peer1M
ER3M = Stock R3M - Peer3M
W = 0.60 * ER1M + 0.40 * ER3M

Peer comparison is valid only when:
- at least 4 other valid peers exist;
- valid peer coverage is >=80% of the other configured members.

Primary Long stock:
W > 0

Primary Short stock:
W < 0

W == 0 or unavailable:
excluded

## 15. Daily stock eligibility

Membership is stable between reviews. Daily liquidity does not delete membership.

For Daily Primary inclusion, recompute:
- Close >= USD 5
- Average Volume 10D > 500,000 shares
- 1D Turnover >= USD 10,000,000

Average Volume 10D:
SMA of regular-session daily volume over the latest 10 completed daily bars,
including the target session once it is complete.

1D Turnover:
target-session Close * target-session regular-session Volume.

Market cap, exchange and Common Stock status come from the latest approved
membership review and are not re-screened daily.

## 16. Combined Primary export

Never use the old global "first qualifying theme wins" policy.

A stock may qualify independently in multiple themes.

Individual-theme export:
show the stock in every theme where it independently qualifies.

Combined TradingView TXT export:
emit each ticker once.

Deterministic placement:
1. Core qualification beats Enabler qualification.
2. If role ties, select the theme with stronger directional W:
   - Long: larger positive W
   - Short: more negative W
3. Stable theme_id lexical order is the final tie-break.

The dashboard must show:
- Assigned section
- Also qualifies in: [other qualifying themes]

Combined-export placement is not stored as permanent company identity.

## 17. Theme breadth

For each Active theme:
- % valid members above own EMA21
- % valid members above own EMA50

Use active Core+Enabler membership.
Minimum valid = 5.
Coverage >=80%.
Missing values are excluded from the numerator and valid-value denominator but
remain in the configured coverage denominator.

Breadth is context only.

## 18. Market layer

Preserve existing SPY/QQQ Market Matrix exactly unless a separately approved
migration test finds an existing bug.

Price state per index:
- Bullish: close > EMA21 and EMA50
- Bearish: close < EMA21 and EMA50
- Mixed: otherwise
- missing: Unavailable

SPY and QQQ breadth are calculated from separate effective-dated constituent rosters.
Never merge universes.

IWM remains context only and has no vote.

SPY/QQQ rosters are manual initially. Store roster effective date and source.
Do not silently scrape issuer or TradingView pages.

## 19. Daily data architecture

Normal daily use must require zero CSV uploads.

Recommended provider interface:
MarketDataProvider
- get_daily_bars(symbols, start, end)
- get_latest_completed_session()
- health_check()

First live adapter: Alpaca historical Market Data API.

Critical provider rules:
- market-data only;
- never call Alpaca trading/order endpoints;
- request SIP explicitly;
- free-plan use is acceptable only if the historical SIP request is older than
  Alpaca's current restriction window and actually succeeds;
- never silently fall back to IEX because IEX volume would change liquidity rules;
- paginate until next_page_token is null;
- use adjustment=split,spin-off;
- validate target-session presence for every required symbol.

Provider code must be replaceable without changing ThemeScope formulas.

## 20. Storage

Use local SQLite.

Suggested tables:
- schema_version
- instruments
- daily_bars
- membership_reviews
- theme_index
- theme_snapshot
- stock_theme_snapshot
- market_roster
- market_snapshot
- refresh_run
- earnings_event

Configuration source of truth remains versioned text/CSV in Git:
- config/themes_vnext.csv or equivalent structured file
- config/memberships_vnext.csv
- config/market_universes/sp500.csv
- config/market_universes/nasdaq100.csv
- config/methodology_vnext.json

Runtime DB, credentials and personal data must not be committed.

## 21. Transactional refresh

Refresh must be atomic.

If any required current-session data is missing:
- mark run incomplete;
- preserve previous successful active snapshot;
- do not partially publish new dashboard/exports.

80% coverage thresholds apply to breadth/theme metrics only.
They do not mean the overall refresh is complete.

Use a single refresh lock to prevent concurrent writers.

## 22. Session behavior

Default target:
latest completed US session.

A same-day refresh must not treat the current session as complete until after
the configured close plus data-delay safety window.

Use America/New_York and the existing US-session calendar logic.
Support an explicit advanced session override for replay/debugging.

## 23. Earnings

Earnings is optional and must never block refresh.

Suggested optional provider:
Alpha Vantage EARNINGS_CALENDAR.

If no API key or provider failure:
Earnings = Unavailable.

Never substitute stale/fabricated dates.

## 24. Local UI

vNext is private/local-first.

Target flow:
ThemeScope.cmd
-> loopback-only local server
-> browser opens local dashboard

Top-level action:
Refresh Data

Show:
- target data session
- last successful refresh
- current refresh state/progress
- completeness
- provider health

Bind to 127.0.0.1, not 0.0.0.0, unless user explicitly changes it.

Retain:
Market -> Daily Plan -> Sectors & Themes/Theme Research -> Watchlist -> Methodology

Update wording so all ETF-relative language disappears.

## 25. Public site

Do not publish provider-derived market data in vNext by default.

Existing public-site code stays legacy until redistribution rights are separately
reviewed. Do not deploy from Codex during this migration.

## 26. Migration

Do not mutate legacy history.

Old ETF-based history and vNext custom-theme history are incompatible series.

Keep the existing system operational until vNext passes all gates.

Legacy files such as active_anchors.json and ETF-related logic may be removed
from the default runtime only after vNext validation. Preserve legacy history
readability.

## 27. Acceptance criteria

vNext is not complete until all are true:

- no thematic ETF affects any calculation;
- no Daily ETF CSV is required;
- normal daily refresh requires no manual Stock/SPY/QQQ/IWM CSV;
- quarterly membership review accepts the exact filtered Stock CSV policy;
- SPY/QQQ roster import is manual and effective-dated;
- IWM constituent scanner is unnecessary;
- median theme benchmark is deterministic;
- LOO peer W is deterministic and tested;
- synthetic theme index is chain-linked and corporate-action safe;
- multi-theme stocks are not lost in combined export;
- Theme Score/rules do not change when market-data provider changes;
- SIP data failure never silently falls back to IEX;
- missing required target-session data preserves prior successful state;
- no credentials or runtime DB are committed;
- local server binds loopback only;
- all methodology migration history is labeled incompatible rather than faked;
- Windows setup/launch path is tested;
- warm refresh target <10 minutes, goal <5 minutes;
- full unit/integration/regression test suite passes.

## 28. Launch membership evidence gate

The launch ledger is a proposed classification set, not a claim that every
relationship has already received a fresh SEC/IR review.

Current evidence status:
- industry-rule accepted: 318
- existing repository primary-source evidence: 65
- newly verified official-source relationships: 11
- primary-source refresh required: 335

`membership_evidence_review_queue.csv` is a mandatory pre-cutover review queue.

Implementation may proceed while this queue exists, but vNext must not become the
default production membership set until every queued relationship is resolved by:
- primary-source confirmation;
- downgrade to Related;
- removal; or
- an explicitly documented deterministic industry rule approved for that theme.

Codex must never invent evidence URLs or silently mark queued rows as verified.


## 29. Reviewed membership-data amendment — 2026-11-06

The preceding proposal/evidence counts describe the original handoff baseline.
The user-supplied membership master review supersedes that proposed data with
726 retained relationships: 659 Core, 62 Enabler and 5 Related across 668 tickers.
EXC/nuclear-energy, ZG/internet-commerce and SMG/agribusiness are removed; Z remains
Zillow's representative. All other reviewed corrections follow the package exactly.
Taxonomy and formulas are unchanged. All 44 Active themes retain at least five
Core+Enabler members. The source queue is resolved, all four inherited findings
are validated, and 451 relationships are covered by the 75 documented supplied
industry rules. See config/vnext and docs/membership_review_2026-11-06.md.
No launch effective dates, end dates or launch session are assigned by this review;
production remains disabled and Phase 9 is not authorized.
