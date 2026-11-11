> **Historical checkpoint.** Status, counts and instructions below describe that
> checkpoint, not current operation. Gate E is now **CLOSED**; Nov 6, Nov 9 and
> Nov 10 live validation passed per the user. See the [closure record](../../operations/gate-e-closure.md)
> and [current documentation](../../README.md).

# ThemeScope vNext — Codex Implementation Handoff

You are implementing a major architecture migration in:
https://github.com/suna-kabo/ThemeScope

Read the repository first. Do not assume the current code structure from this
instruction is exact. The current `main` branch is the working legacy system and
must remain usable.

Before editing, read:
- `ThemeScope_vNext_Product_and_Methodology_Spec.md`
- `themes_vnext.csv`
- `memberships_vnext_launch.csv`
- `watch_only_membership_candidates.csv`
- root `AGENTS.md` after installing the supplied draft
- existing README/DESIGN/PRODUCT docs
- current tests and current local-history/publication code

The methodology specification is authoritative for vNext. If existing code
conflicts with it, do not silently preserve the legacy behavior. If the spec is
ambiguous, stop that specific design choice, document the ambiguity in
`PLANS.md`, and continue other non-conflicting work.

## Branch strategy

1. Start from the latest clean `main`.
2. Run the full existing test suite and record the baseline.
3. Create:
   `refactor/themescope-vnext`
4. Never implement this migration directly on `main`.
5. Do not delete legacy functionality until its vNext replacement passes the
   required gate.
6. Do not deploy anything.

Major user-inspection branches:
- `inspection/vnext-a-domain`
- `inspection/vnext-b-engine`
- `inspection/vnext-c-provider`
- `inspection/vnext-d-ui`
- `inspection/vnext-e-final`

Each inspection branch is a checkpoint from the implementation branch, not a
development fork. It must be safe to download as a ZIP from GitHub.

Do not force-push or rewrite Git history.

## Repository workflow files

Add/update at repository root:
- `AGENTS.md`
- `GOALS.md`
- `PLANS.md`

Add scripts:
- `scripts/bootstrap_dev.py`
- `scripts/check_vnext.py`
- `scripts/build_inspection_bundle.py`
- `scripts/test_alpaca_access.py`
- Windows `.cmd` wrappers where useful

`build_inspection_bundle.py` must reject:
- `.env*`
- API keys/secrets
- SQLite runtime databases
- raw provider market-data caches
- personal absolute paths
- unrelated generated junk

It should create an `inspection/` folder containing:
- a local static preview when possible;
- methodology/config summaries;
- test report;
- migration/diff report;
- no restricted/private data.

## Environment

Target Python: 3.12.

Keep dependencies lean. A reasonable runtime set is:
- fastapi
- uvicorn
- httpx
- tzdata

Use standard-library sqlite3.
Do not add a trading SDK solely to fetch data unless there is a demonstrated
benefit over a small provider REST adapter.

Development:
- pytest
- existing repo dev tools

No Node requirement unless the current frontend genuinely requires it.

Codex Cloud must not require real Alpaca credentials.
Use fixtures/mocks for cloud work.

## Absolute prohibitions

- Do not use undocumented TradingView scanner endpoints.
- Do not automate TradingView scraping.
- Do not call Alpaca order/trading endpoints.
- Do not place trades.
- Do not silently use IEX when SIP is unavailable.
- Do not publish or deploy provider-derived market data.
- Do not commit credentials.
- Do not commit a personal/runtime SQLite database.
- Do not retroactively rewrite legacy history.
- Do not restore a 20-stock membership cap.
- Do not replace custom theme methodology with ETF returns.
- Do not add extra technical-entry/stop/position-sizing signals.
- Do not change the existing Market Matrix rules unless a failing regression
  proves a legacy bug and the change is separately documented.

# PHASE 0 — Baseline and migration fixtures

Before new behavior:

1. Run all current tests.
2. Capture current 2026-11-04/legacy fixture behavior if the repo has those
   fixture inputs available.
3. Record:
   - Market Matrix result;
   - current theme/rank outputs;
   - current Primary export;
   - existing history schema/version;
   - current generated-dashboard/publication behavior.
4. Add regression fixtures without modifying genuine user runtime history.
5. Document baseline in `PLANS.md`.

Commit:
`test: establish ThemeScope vNext migration baseline`

## Membership evidence gate

Read:
- `membership_evidence_status_summary.csv`
- `membership_evidence_review_queue.csv`

The launch membership ledger is intentionally conservative about evidence.
Do not interpret proposed relationships as automatically verified.

You may implement the data model and calculation engine before the queue is
fully resolved, but do not make vNext the default production membership set
while any row remains `primary_source_refresh_required`.

For queued rows, never invent citations. A row must be confirmed from a primary
source, downgraded to Related, removed, or covered by an explicitly documented
deterministic rule before production cutover.

# PHASE 1 — Domain model and configuration

Install the supplied vNext taxonomy and membership ledger as new versioned config.
Do not overwrite legacy config yet.

Implement models for:
- Theme Charter
- theme status: Active / Watch-only / Retired/Merged
- membership role: Core / Enabler / Related
- effective_from / effective_to
- review metadata/evidence
- market roster effective dates
- methodology version

Validation:
- every Active theme has >=5 active Core+Enabler launch members;
- no membership ticker outside the supplied 2026-11-05 review universe is
  silently activated;
- Watch-only themes cannot produce Theme Score or Primary qualification;
- duplicate relationship rows are rejected;
- invalid date intervals are rejected.

No permanent `home_theme` is required.

Commit and test.

Gate A:
build `inspection/`, push `inspection/vnext-a-domain`, report commit SHA.

# PHASE 2 — SQLite and calculation engine

Create a clean storage layer under modules such as:
- `src/themescope/storage/`
- `src/themescope/themes/`
- `src/themescope/research/`
- `src/themescope/market/`

Do not keep growing monolithic legacy generator files.

Suggested SQLite tables are in the spec.

Implement pure calculation functions first:

## Returns
R1M = close[t] / close[t-21 sessions] - 1
R3M = close[t] / close[t-63 sessions] - 1

## Theme benchmark
Theme1M = median(valid Core+Enabler R1M)
Theme3M = median(valid Core+Enabler R3M)

Availability:
- >=5 valid members
- >=80% configured-member coverage

## Percentiles
average-rank ties:
(rank - 1)/(N - 1)*100

## Theme Score
0.60*P1M + 0.40*P3M

## Leave-One-Out
Peer1M/Peer3M exclude the current stock.
Require >=4 other valid peers and >=80% peer coverage.

ER1M = stock1M - peer1M
ER3M = stock3M - peer3M
W = 0.60*ER1M + 0.40*ER3M

Long Primary W > 0.
Short Primary W < 0.
Zero/unavailable excluded.

Write exhaustive unit tests:
- ties;
- odd/even medians;
- one missing stock;
- coverage boundary;
- exactly 5 members;
- exactly 4 LOO peers;
- W exactly zero;
- multiple memberships;
- duplicate symbols;
- split-event fixture.

# PHASE 3 — Synthetic theme index and history

Implement a chain-linked synthetic index:
- initial level 100;
- equal weight at formal rebalance;
- drift between rebalances;
- rebalance on effective membership changes;
- split/spin-off adjusted price returns;
- no dividend total-return adjustment.

EMA21/EMA50:
- Bullish above both;
- Bearish below both;
- Mixed otherwise;
- Unavailable if data invalid.

Bootstrap history:
allowed only to initialize indicators.
Tag it explicitly as bootstrap.
Never show bootstrap dates as if ThemeScope had emitted live historical signals.

At the vNext methodology boundary:
- previous Priority Change = N/A
- Newly Bullish/Bearish = N/A

Only compatible vNext prior sessions may generate transitions.

# PHASE 4 — Primary engine and exports

Implement daily eligibility:
- Close >= 5 USD
- AvgVol10 > 500,000 shares
- 1D Turnover >= 10,000,000 USD

AvgVol10 = SMA of latest 10 completed regular-session daily volume bars,
including target session after close.

Turnover = target close * target regular-session volume.

Quarterly-review structural fields:
market cap, common-stock status and NYSE/NASDAQ membership are not re-screened
daily.

Replace the global `first qualifying theme wins` behavior.

Individual export:
retain every independently qualifying relationship.

Combined export:
one ticker once, placement:
1. Core beats Enabler.
2. Role tie:
   Long -> higher positive W.
   Short -> more negative W.
3. lexical theme_id final tie-break.

Dashboard data must retain all qualifying relationships.

Gate B:
generate inspection artifacts and push `inspection/vnext-b-engine`.
Include a deterministic fixture report comparing formulas and showing sample
multi-theme stocks.

# PHASE 5 — Provider abstraction

Create a provider interface, e.g.:
`src/themescope/providers/base.py`

Required behavior:
- historical daily bars for many symbols;
- completed-session identification/health;
- explicit error classification;
- no formula knowledge inside provider.

Create:
- `FixtureProvider`
- `AlpacaMarketDataProvider`

Alpaca adapter:
- Market Data API only;
- use `data.alpaca.markets`;
- headers from environment;
- `feed=sip`;
- `timeframe=1Day`;
- `adjustment=split,spin-off`;
- paginate `next_page_token`;
- validate target-session bar per required symbol;
- never silently change feed to IEX;
- exponential/backoff retry only for transient HTTP errors;
- surface 401/403/422 subscription/auth errors clearly.

Do not require live credentials for tests.

`scripts/test_alpaca_access.py` must be a local-only PoC:
- read credentials from environment;
- request several liquid NYSE/NASDAQ names;
- use an end time safely older than 15 minutes;
- require SIP;
- print only non-secret diagnostics;
- prove volume, pagination, adjustment behavior and target session;
- return non-zero on failure;
- never call trading endpoints.

If SIP historical data is unavailable on the user's actual free account:
the migration pauses at provider selection.
Do not switch to IEX and do not subscribe the user to a paid plan.

Gate C:
push `inspection/vnext-c-provider` only after fixture tests pass.
Live SIP success is a local user validation item and may remain pending.

# PHASE 6 — Market layer migration

Preserve Market Matrix formulas.

Replace daily breadth CSV dependency with:
- versioned/effective-dated manual S&P 500 roster;
- versioned/effective-dated manual Nasdaq-100 roster;
- daily price bars from provider.

IWM:
context quote/history only, no constituent roster.

Add a manual roster import command/UI.
Do not scrape issuer or TradingView pages.

Keep:
- missing constituent data in configured coverage denominator;
- >=80% breadth coverage;
- separate SPY and QQQ universes;
- Unavailable behavior.

# PHASE 7 — Earnings optional provider

Make earnings a non-blocking adapter.
Preferred first adapter: Alpha Vantage EARNINGS_CALENDAR.

No key:
Unavailable.

Provider failure:
Unavailable.

Market refresh still succeeds.

Never infer future earnings dates.

# PHASE 8 — Local server and one-click Windows UX

Implement a local FastAPI application.

Default bind:
127.0.0.1 only.

Provide:
- `ThemeScope.cmd`
- setup/bootstrap path
- local browser launch
- Refresh Data action
- progress/status endpoint
- last successful session/completeness/provider health

Suggested API:
- GET /api/status
- POST /api/refresh
- GET /api/refresh/status
- GET /api/dashboard-data

Use a refresh lock.
Atomic publication/DB state:
failed run cannot replace the last successful active snapshot.

Normal daily use must need zero CSV uploads.

Update UI wording:
- remove ETF-relative terminology;
- replace "vs ETF" with "vs Theme Peers";
- retain Market / Daily Plan / Themes / Watchlist / Methodology flow;
- show ThemeScope synthetic trend;
- show assigned section plus other qualifying themes.

Gate D:
push `inspection/vnext-d-ui`.
Inspection bundle must be usable without live credentials through fixture mode.

# PHASE 9 — Legacy retirement

Only after Gates A-D pass:

Remove thematic ETF calculations from the default path:
- active anchor dependency;
- anchor comparison;
- Daily ETF CSV;
- ETF EMA theme trend;
- stock-vs-ETF W;
- old combined first-theme dedup.

Preserve legacy files/history readers where required for old snapshots.

Do not rewrite old snapshots into the new schema.

Update README, DESIGN, PRODUCT and Methodology docs.

# PHASE 10 — Final audit

Use independent review passes for:
1. methodology/formula correctness;
2. database/history/migration correctness;
3. data-provider/failure/security behavior;
4. export/multi-theme correctness;
5. Windows launch/UI regressions;
6. dead code and documentation consistency.

Resolve findings.

Run:
- unit tests;
- integration tests;
- deterministic fixture E2E;
- failure injection;
- same-session replay;
- missing-symbol run;
- split/spin-off fixture;
- provider auth/subscription error fixtures;
- inspection-bundle secret scan.

Gate E:
push `inspection/vnext-e-final`.

Then prepare a PR from:
`refactor/themescope-vnext` -> `main`

Do not merge it yourself unless explicitly instructed.

# Final handoff report

Return:
- branch and final commit SHA;
- all commits by phase;
- test commands and results;
- active/watched theme counts;
- membership relationship and unique ticker counts;
- schema version;
- known limitations;
- exact local commands for setup/start/live SIP PoC;
- which user checks are still required;
- inspection branch URLs/names;
- explicit confirmation that no credentials, runtime DB, raw private data or
  public deployment were committed.
