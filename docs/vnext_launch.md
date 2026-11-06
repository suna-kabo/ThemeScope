# Phase 9: approved launch and local cutover

This implementation follows explicit user authorization after membership review
150c47c. Gate D is closed. This is not Gate E; independent final review remains
separate. No main update, deployment, inspection-ref move or live database change.

## Exact approval

| Setting | Value |
|---|---|
| launch_rebalance_session | 2026-11-06 |
| production_enabled | true |
| first earned session / every retained effective_from | 2026-11-09 |
| effective_to | blank (exclusive when supplied) |
| retained relationships | 726 |
| roles | 659 Core / 62 Enabler / 5 Related |
| Active themes | 44, all with at least five Core+Enabler |
| evidence queue / inherited findings | 0 / 0 |
| industry registry | approved, 75 rules / 451 covered relationships |

Approval occurred before the November 6 US session. The XNYS calendar verifies
November 9 is the next trading session. No row is backdated to November 5 or 6.
EXC/nuclear-energy, ZG/internet-commerce and SMG/agribusiness remain removed; Z is
retained. Roles, sources, review records and taxonomy are unchanged from 150c47c.
`launch_approval.json` records authorization separately from the immutable review
provenance. Loading configuration checks approval, dates, roles and gate metadata.
The review-application script continues to refuse rewriting activated membership.

## Runtime boundary

Before L completes, required market context and effective roster breadth refresh
normally. The subsequent approved Gate E clarification now supplies full current
research using the approved launch universe: `pre_launch_research`, with separate
bootstrap-only trend and no official index rows or membership backdating. The
former market-only restriction is superseded. See vnext_prelaunch_research.md.
Official L/E semantics below remain unchanged.

At L close the orchestration selects Core+Enabler holdings from **the next earned
session**, fetches their historical inputs, and calls the unchanged `build_index`
with start=L. It no longer requires a relationship earning L before initializing.
Every valid Active theme initializes at exactly 100 with empty `earned_symbols`.
After-close holdings are the approved November 9 set. No November 6 return is
earned by that new series, and no membership date is altered as a workaround.

Bootstrap points are explicitly tagged in SQLite and excluded from live theme
history. They initialize EMA21/EMA50 only. Missing bootstrap data cannot erase a
valid launch point; its indicators remain unavailable where insufficient.
`ThemeHistory.signal_eligible=false` marks initialization/non-earned observations.
Compatibility requires both adjacent observations to be earned live signals with
matching methodology, series and schema. November 9 therefore cannot claim a
transition from launch initialization, bootstrap or legacy history. November 10
can compare with November 9 if both actual live observations are valid.

The first return is L close to November 9 close. Holdings drift naturally, with
no daily equal weighting. Related relationships never enter holdings, benchmarks,
peer calculations or Primary qualification. No formula, policy constant, Market
Matrix function or SPY/QQQ/IWM role changed. SQLite remains schema **2**; the
history JSON flag is additive, and no legacy payload is rewritten.

## Default local workflow and compatibility

`ThemeScope.cmd`, `refresh.cmd` and `open-dashboard.cmd` open the loopback vNext
application; `setup.cmd` installs the isolated vNext runtime. Refresh Data uses
Alpaca SIP and incremental caching, with no daily Stock/ETF CSVs, active-anchor
config or thematic ETF history/EMA/returns/liquidity in the calculation path.
Explicit `legacy-*` launchers, Python historical readers, archived manual guide,
fixtures and original history remain for viewing/reproduction. The clean legacy
smoke test calls these explicit aliases on Windows. Legacy and vNext series remain
incompatible; no history is spliced or rewritten.

261 of 664 eligible launch symbols lacked old verified TXT mappings. vNext now
supplements those from the already validated user TradingView review universe's
explicit Symbol/Exchange fields and source SHA256. It preserves existing verified
mappings and never guesses a missing venue or edits the legacy map. All eligible
identifiers match that reviewed metadata. Actual TradingView TXT import remains a
local check; provider market observations never supply guessed export venues.

Effective SPY 501 / QQQ 101 roster records remain byte-for-byte unchanged, dated
2026-11-05. Missing either target-session roster still blocks themes and Primary;
staleness is advisory. IWM has no constituent roster. User-reported local SIP
compatibility passed for market session 2026-11-05: all 501/101 usable, zero missing,
12 pages, SIP 1Day split/spin-off adjustment and raw liquidity requests. This is an
external prerequisite, not a cloud account test; no secrets/payloads are stored.

## Validation

- Full suite: **302 cases, 300 passed, two native-Windows skips**.
- Focused vNext: **95 cases, 94 passed, one native-Windows skip**.
- Launch: **7 passed**; local service/API/status/roster/locking: **14 passed**.
- Frozen migration and history tests pass; **all 64 Market Matrix cells match**
  the committed main baseline exactly. Matrix source remains unchanged.
- All 44 actual Active themes initialize at 100 in synthetic full-roster refresh.
  Every L point has empty earned_symbols and November 9 Core+Enabler holdings;
  bootstrap rows are tagged and strictly pre-L. No live index exists November 5.
- Numerical airline fixture: **100 (Nov 6) -> 120 (Nov 9) -> 160 (Nov 10)** as one
  of five equal initial holdings doubles twice. Daily reweighting would give 144;
  the actual result proves drift and no gap/double count. Related is excluded.
  November 9 transitions are unavailable; November 10 can compare genuine history.
- Configuration/evidence validation: zero config production blockers; exact role,
  removal, source-task, registry and membership-date checks pass. Missing each
  SPY/QQQ roster still fails closed at L and E; IWM/staleness behavior unchanged.
- Python compilation, legacy/vNext JS syntax and dashboard helper checks pass.
- Real loopback vNext browser smoke: refresh, combined download, watchlist and
  mobile layout pass; zero external requests and zero page errors. Historical
  Gate D static preview still opens independently over loopback.
- Safe inspection generation is temporary and credential-free; it is a validation
  of the builder/current source, not a Gate E checkpoint or review. Runtime data,
  raw provider payloads and credentials are excluded from committed changes.

All automated bars are synthetic; no real Alpaca credentials were used. Native
Windows Phase 9 launcher execution and full-universe live cold/warm performance
against the <10 minute hard target / <5 minute goal remain local checks. Actual
SIP availability for all theme-member tickers is not established by a roster-only
compatibility run; required missing target bars still fail publication. No IEX
fallback or automatic membership/roster replacement. Gate E has not started.
