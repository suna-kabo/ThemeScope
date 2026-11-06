# ThemeScope vNext migration plan

## Resume here

Implementation branch: `refactor/themescope-vnext`.
Base main: `cf4fdb1e4784ff6fbc7183d5e709ffae044ec2fe` (includes PR #7).
Phase 0 commit: `8764575` — baseline and workflow/spec documentation.
Phase 1: domain/configuration work validated for **Gate A**.
Checkpoint: `inspection/vnext-a-domain`, pointing at the Phase 1 commit.
Phase 2 complete: `61fe259`. Phase 3 complete: `1c10c5c`.
Phase 4 validated for Gate B; checkpoint branch `inspection/vnext-b-engine`.
Gate C 7d3bf2e is approved; the real local SIP PoC passed (user-reported).
Phase 6: a8958f3. Phase 7: 9080337. Phase 8 validated for Gate D.
Gate D is closed; roster import 94050ac and membership/evidence review 150c47c complete.
Current scope: explicitly approved launch and Phase 9 only, then STOP.
Launch rebalance 2026-11-06 close; all 726 retained relationships effective 2026-11-09.
Production enabled; zero config blockers. Runtime SPY/QQQ roster gates remain.
Preserve inspection/vnext-d-ui at 02e7d63 and every original gate ref.
Gate E is NOT authorized in this task. SQLite schema remains 2; no main/deployment.
Historical phase notes below record restrictions/results applicable at each gate.
Do not restart the baseline or reimport/reclassify the proposed launch ledger.

Gate A at `359572c` was independently checked and approved. Do not redo it.
The user authorizes Phases 2–4 with separate tested commits, then stop at Gate B.

## Completed work

- Read all 14 initial bundle files and compared them with live GitHub main before
  code changes. Full comparison: [preflight](docs/vnext_preflight.md).
- Captured an unchanged-main synthetic manual-runtime regression fixture:
  January 3, 2024; 563 stocks, 53 anchors; all theme scores/ranks, Primary exports,
  legacy history identifiers and the complete 64-case Market Matrix.
- Installed the supplied AGENTS/GOALS drafts and handoff/spec documents.
- Read bundle v2. Its complete 1,525-row Stock review CSV resolves the missing
  universe finding. All launch and Watch-only tickers are present; every measurable
  scanner filter passes; no duplicate symbols.
- Installed versioned charters, 729 proposed relationships and 21 Watch-only
  candidates. No legacy config was overwritten. Raw scanner prices/volumes are
  excluded from the new committed configuration.
- Added typed theme/status/role, effective membership and market-roster models;
  duplicate/overlap/date/universe/Active-minimum validation. Pending and Watch-only
  memberships cannot calculate. No permanent home theme or 20-stock cap.
- Added a scanner validator and proposed-diff function that never writes membership.
  Exact private v2 source validation matches the committed identifier manifest.
- Added offline checks, isolated vNext bootstrap and safe inspection generation.
  Inspection rejects .env files, secret patterns, SQLite databases, provider payloads,
  personal absolute paths, symlinks and unrelated destination files.
- Replaced legacy test provider payloads with deterministic synthetic equivalents
  for inspection ZIP safety. Existing import/publication tests still pass.
  Original payloads remain in pre-migration Git history; genuine runtime history
  and legacy production code are unchanged.

## Approved timing clarification — do not change

Old membership earns the entire close-to-close return ending on approval session t.
Rebalance at t close. New membership first earns the next US trading session's
return. `effective_from` is that next session; `effective_to` is exclusive.

The user explicitly selected L=2026-11-06 before that market session. Old holdings
own L's return; rebalance at L close, initialize the new index at 100, and retained
memberships first earn 2026-11-09. Never infer L from the November 5 export filename
or splice legacy ETF returns into vNext. Bootstrap cannot supply live signals.

The methodology is amended. Phase 1 tests prove old/new membership assignment
across a Friday approval and Monday effective session. **Phase 3 now includes the numerical synthetic-index rebalance-boundary test**:
100 -> 110 on approval Friday (old holdings +10%), then 132 Monday (new +20%). Bootstrap initializes indicators only and must never
produce apparent live signal history.

## Historical Gate B blockers (all configuration items since resolved)

- 335 primary-source refresh relationships remain pending, preserved in status
  and in a sanitized review queue.
- Four additional AMZN/GOOGL cloud-platforms/internet-commerce relationships point
  to repository records explicitly labeled Unresolved. They need relationship-
  specific resolution; a cited URL alone is not evidence approval.
- The 318 industry-rule-accepted declarations need links to documented approved
  deterministic rules/explicit exceptions before final evidence clearance. Do not
  invent rules or relabel these declarations as primary-source verification.
- Launch rebalance session/effective dates are not approved. Production is off.
- Live SIP success and Windows-native launch validation remain later local checks.
- Actual dated SPY/QQQ rosters remain a later manual import requirement.

Common-stock status is user-attested from the scanner setup; the CSV has no
security-type column. Source SHA256:
`e2b271c54bde7498ff1d9712452b18977cf4321f8e755ec67ca0efbc64a9e374`.
The 151-row delta is not the authoritative review universe.

## Validation and safety

Unchanged-main baseline: 207 unittest cases, one Windows-only skip; JS checks,
compilation and clean-install/browser smoke passed. Phase 0: 209 cases, same skip.
Current Gate B test report is in `inspection/test-report.txt`; Gate A retains its
original report on `inspection/vnext-a-domain`.

Tests use fixtures/mocks. Linux smoke checks cover clean setup, two sessions,
failure preservation, older replay, HTTP previews/downloads, all 64 Market Matrix
cases and light/dark browser layouts. Native CMD/Windows locked-file semantics
were not executed here. Local HTTP tests require loopback socket access.

Legacy identifiers remain `manual-csv-2`, `manual-csv-1`,
`themescope-ranking-history-1`, `tradingview-daily-price-ema21-ema50-1`,
`ema-score-priority-2`. New config has schema 1 / `themescope-vnext-1` methodology;
the new isolated runtime SQLite schema is version 1.

Only source and synthetic inspection artifacts may be pushed to the implementation
and prescribed checkpoint branches. No main merge, deployment, trading endpoint,
live Alpaca credentials, IEX fallback or runtime DB is part of this gate.

## Handoff sequence — Phases 1–8 complete; Phase 9 authorized

1. Completed Phase 2: pure 21/63-session returns, member medians/coverage, tied percentiles,
   60/40 score, LOO W and SQLite storage; boundary/missing/corporate-action tests.
2. Completed Phase 3: chain-linked drifting index, approved timing, explicit bootstrap and
   compatible adjacent-session history.
3. Completed Phase 4: daily liquidity, independent qualifying relationships and deterministic
   combined placement; safe fixture report and **Gate B**.
4. Phase 5: FixtureProvider/Alpaca SIP adapters; paging, retries, auth/subscription
   failures, split/spin-off handling and local access PoC; **Gate C**. Live SIP may
   remain a local user validation item.
5. Phases 6–8: unchanged Market Matrix, dated manual rosters, optional earnings,
   loopback FastAPI/atomic refresh, Windows launcher/UI; **Gate D**.
6. Phase 9: retire legacy default calculations only when A–D and evidence/activation
   requirements permit cutover; retain legacy history readers.
7. Phase 10: independent review passes, E2E/failure/replay/corporate-action/provider
   tests, secret/data scan; **Gate E**, then PR to main. No self-merge/deployment.

## Phase 2 — storage and pure calculations

Implemented endpoint-based 21/63-session adjusted returns; per-horizon member
medians and coverage; tied percentiles; 60/40 scores; LOO W; context-only breadth.
Decimal arithmetic uses a fixed local 34-digit context. Raw close/volume remain
separate from split/spin-off adjusted prices. Missing dates never compress sessions.

SQLite schema 1 adds the eleven suggested tables (including schema_version) and a
publication pointer. All results are run-scoped; configuration stays in Git.
BEGIN IMMEDIATE serializes writers; errors roll back data and record an incomplete
run without replacing the successful publication. Older replay cannot supersede
a newer active session. Runtime databases exist only in temporary test folders.

Validation: full unittest suite 233 cases, one Windows-only skip; JavaScript
checks and Python compilation pass. Exact boundaries, missing endpoints, split/
spin-off/dividend fixtures, independent memberships, rollback and locks tested.
Next: Phase 3 synthetic index and compatible history. Production blockers unchanged.

## Phase 3 — index and compatible history

Implemented chain-linked price index with equal weight only at initialization,
effective membership changes or explicitly supplied formal rebalances. Holdings
drift between rebalances. Missing held/new constituent prices fail closed; the
80% cross-sectional threshold never silently reweights the synthetic portfolio.
Related and Watch-only cannot contribute; pending live membership cannot initialize.

SMA-seeded EMA21/50, strict trend boundaries and explicit bootstrap provenance are
implemented. Bootstrap is scaled to the live initialization level for indicators
only, never returned as live signals. History requires matching methodology,
series, theme and history schema plus adjacent completed sessions; migration,
bootstrap, gaps and missing prior data yield unavailable transitions.
SQLite schema remains 1; index rows and exact-session theme history round-trip.

Validation: full suite 240 tests, one Windows-only skip; compilation and JS checks
pass. Numerical t/t+1 fixture, natural drift versus daily equal weight, chain-link
continuity, split/spin-off price continuity, missing data, EMA boundaries and
bootstrap/legacy/gap incompatibility pass. No launch date selected or activated.
Next: Phase 4 eligibility, Primary relationships and deterministic exports.

## Phase 4 / Gate B — independent Primary engine and exports

Implemented exact daily liquidity checks on raw regular-session values; target
session is included in AvgVol10. Missing/incomplete bars are unavailable. Daily
liquidity never deletes membership or changes benchmark/peer coverage.

The offline session engine composes theme returns/scores, synthetic trends,
context-only breadth, compatible transitions and LOO W. Theme Priority matches
360 combinations of the existing policy; the Market Matrix implementation is
untouched. Every independently qualifying Core/Enabler relationship remains in
dashboard and individual exports. Combined placement uses role, directional W,
then lexical theme ID; ticker order and TXT sections are deterministic. Verified
TradingView mappings are required; no symbol guesses or 20-stock cap.

End-to-end synthetic fixture persistence exercises SQLite rollback, replay and
multi-theme history. It cannot publish an unlabeled production snapshot. A final
review strengthened fixed Decimal contexts (including traps) and rollback after
a publication-pointer update; no formula or threshold changed.

Validation: 252 full-suite tests, 251 pass and one Windows-only skip; 45 focused
vNext cases pass. Python compilation and JavaScript checks pass. Independent
rational oracle matches LOO W; formula report has expected/actual medians and
scores, long/short qualifications and TXT examples. Numerical index boundary
remains 100 -> 110 (old Friday) -> 132 (new Monday).

Inspection is configuration plus synthetic summaries only. Download the Gate B
branch ZIP and open inspection/index.html. Details: docs/vnext_engine.md.
SQLite schema remains 1; snapshot schema is themescope-vnext-snapshot-1 and live
history is themescope-vnext-history-1. No runtime database or source market bars
are included. Stop at Gate B; no provider/live SIP, launch choice, evidence
clearance, legacy retirement, main merge or deployment was performed.

## Phase 5 — Gate C provider and incremental cache

Gate B 0c0cff5 is independently approved. Added formula-independent protocol,
FixtureProvider and historical-only Alpaca SIP adapter with paired adjusted/raw
requests, pagination, explicit permanent errors and bounded transient retries.
All testing uses injected transports/fixtures; no real account credentials used.

SQLite explicitly migrates 1 -> 2: immutable observation versions, current cache
pointers and run input references replace duplicated run-scoped payloads. Cold
seed, grouped warm missing/repair ranges, anchor-driven corporate-action reseed,
explicit full repair and atomic cache/publication rollback are tested. Old runs
remain reproducible. Missing fresh target bars cannot be replaced by stale cache.
Details and exact local commands: docs/vnext_provider.md.

Real SIP access and throughput remain local validation items. Production blockers
are unchanged: pending launch/evidence, manual Phase 6 rosters, Windows validation.
No launch choice, evidence resolution, IEX fallback, Market Matrix modification,
legacy retirement, main merge or deployment. Stop at inspection/vnext-c-provider.

Phase 5 validation: 263 tests run, 262 pass, one Windows-only skip. Eleven focused
provider/cache/PoC tests pass; compilation and JS syntax/helper checks pass.

## Phase 6 — Market layer and approved Gate C

User approved Gate C 7d3bf2e and reported the real SIP PoC passed for 2026-11-04:
three symbols, positive raw volume, six pages, SIP 1Day split/spin-off plus raw,
no IEX fallback. No need to repeat that check in cloud.

Separate effective-dated SPY/QQQ roster ledger and manual CSV import command added.
No constituents invented: initial ledger is empty pending approved manual inputs.
90-calendar-day roster age warning is advisory only. Same valid constituent set
serves both EMA breadth values, >=80% coverage uses the full configured denominator.
IWM has price context only. Existing market_rule/breadth_consensus functions and
all 64 frozen Market Matrix cases remain unchanged.

Added an OS-held cross-process refresh lock (also used for manual roster updates).
Phase 8 must hold this across preparation, calculation and atomic publication.
Phase 6 validation: 266 full tests, 265 passed/one Windows skip; three focused market/
lock tests passed. Next Phase 7 optional earnings; then Phase 8/Gate D. All launch
and evidence blockers remain; legacy runtime and main untouched.

## Phase 7 — optional earnings

Added EarningsProvider protocol and Alpha Vantage EARNINGS_CALENDAR adapter.
Only reported calendar dates are returned. Missing key/event, quota JSON, malformed
CSV/date or provider exception returns Earnings Unavailable and cannot fail market
refresh. Credentials stay in the local environment. Validation: 268 full tests,
267 pass/one Windows skip; two focused earnings tests pass. Next Phase 8/Gate D.

## Phase 8 — local UI and Gate D

Implemented a private FastAPI application, background refresh status/progress,
loopback launcher ThemeScope.cmd, and zero-daily-CSV workflow using Gate C cache.
The OS refresh lock spans configuration/provider preparation -> calculations ->
optional earnings -> transaction/publication. Competing threads/processes cannot
prepare or publish; another SQLite connection can write during the network wait.
Dashboard and TXT downloads read one committed snapshot. Failures preserve both.

Production with unresolved blockers cannot activate theme membership. It can show
market context, roster warnings, target/completeness/provider health and explicit
activation blockers. Fixture mode uses a separate DB and fictional data. History
requires compatible adjacent live sessions; bootstrap never supplies transitions.
Snapshot hashes include exact roster configuration; market snapshots retain rosters.

New UI flow: Market, Daily Plan, Theme Research, Watchlist, Methodology. Includes
Today's Plan, decision path, Primary themes/comparison state, independent stock
qualifications, assigned/other sections, optional earnings and combined download.
Watchlist is local browser storage. No external browser requests. Same-origin POST,
loopback Host checks and CSP protect the local application. Legacy UI/runtime intact.

Phase 8 validation: 275 full tests; 274 pass/one Windows-only skip. Six focused local
API/refresh tests, three market/lock tests and two earnings tests pass. Frozen
64-case Market Matrix and migration/legacy suites pass. Python compilation and both
JS syntax/helper checks pass. Real Chromium/loopback smoke passes Refresh Data,
TXT download, Watchlist, Methodology navigation and mobile layout, with no external
requests/page errors. Native Windows checks remain local.

Measured small synthetic fixture: 16 symbols/64 sessions, cold 1024 observations
in 0.027s; warm 48 observations in 0.029s. These are functional fixture timings,
not full-universe live SIP throughput. No launch session chosen, all 729 dates
pending, evidence unchanged, approved actual SPY/QQQ roster inputs still required.
Documentation/local launch: docs/vnext_local_ui.md. Safe static UI under inspection/ui
is explicitly synthetic; no provider data, credentials or runtime DB included.
Stop at Gate D and wait for independent review before Phase 9.

## Gate D hardening — roster activation gate and Windows lock-file size

User approved Gate D subject to these two fixes only. Runtime blockers now include
missing effective SPY/QQQ rosters for the target session before live memberships
can calculate. Missing/future/expired roster cases are covered using otherwise
production-ready synthetic configuration; Primary outputs stay empty. Both stale
but effective rosters permit activation with advisory warnings. No IWM roster gate
or Market Matrix changes. Original production config/evidence/launch dates unchanged.

RefreshLock now opens without append/truncate and initializes Windows byte 0 only
when empty. Repeated/contended acquisitions preserve one-byte size; existing larger
files are preserved. Mocked Windows regression runs on Linux, with an additional
native Windows regression that is skipped here. Linux process exclusion unchanged.

One hardening commit on refactor/themescope-vnext only; do not move/recreate the
original Gate D checkpoint. No Phase 9, main changes, live credentials or deployment.

Hardening validation: 279 full-suite cases; 277 pass and two Windows-only skips.
Focused market/lock: four pass/one native-Windows skip; focused local: eight pass.
Python compilation and diff whitespace checks pass. Frozen Market Matrix unchanged.

## Windows status persistence — native validation finding after e3450ff

User reports native ThemeScope.cmd --fixture launched successfully but background
refresh hit WinError 5 replacing status.tmp/status.json at the calculation progress
update; its error-reporting path failed again. Fix only this auxiliary status path.
Do not redo e3450ff, move the original Gate D inspection ref, modify main or start Phase 9.

Guarded memory is updated first. A unique same-directory temporary file is closed
before atomic replacement. Four bounded attempts handle transient access/sharing
errors (10/20/40 ms delays). Creation/write/replacement/cleanup failures are nonfatal;
owned temporary files are cleaned where possible. Polling uses memory while the
new update is unpersisted so stale disk status cannot mask real success/failure.
Valid persisted recovery metadata remains useful otherwise; inaccessible/malformed
files fall back safely. Existing interrupted-process detection is preserved.

Targeted regressions prove successful background snapshot publication despite
permanent metadata failure, normal thread completion, safe actual-provider failure
reporting without recursion, exact previous snapshot/export preservation, transient
recovery, unique closed handles and best-effort cleanup. No SQLite transaction or
publication logic, roster gating, refresh-lock semantics or methodology changed.
Native Windows retest remains pending; cloud tests simulate the reported failure.

Windows-status hardening validation: 285 full-suite cases, 283 passed and two
Windows-only skips. Focused local: 14 passed. Focused market/lock: four passed
and one native-Windows skip. Compilation passed. Native Windows retest pending.

## User-approved constituent import after c60ae07 — Phase 9 not authorized

Imported only Symbol from user-supplied TradingView SPY_2026-11-05.csv (501/501)
and QQQ_2026-11-05.csv (101/101), each effective/snapshot date 2026-11-05 and with
the exact requested source description. No duplicates/blanks/invalids. BF.B/BRK.B
remain dotted. No constituents were added, removed or normalized. The full scanner
payloads stay outside Git; minimal audit hashes/counts accompany the roster ledger.

Both effective rosters resolve on 2026-11-05; neither is backdated. SPY/QQQ remain
separate, IWM has no roster, stale warnings and Market Matrix code unchanged.
All symbols pass the existing adapter grammar, but credentials are unavailable
in Codex. Local compatibility command: scripts/check_roster_symbols.py
--roster-date 2026-11-05. It uses SIP through the existing adapter and reports exact
missing/unusable symbols per benchmark; no automatic substitutions/drops or cache
writes. Real live retrieval remains pending; no real incompatibility is asserted.

Import CLI now supports explicit --symbol-column Symbol while keeping ticker as
the default. Tests validate exact roster hashes/counts, source/effectivity/dotted
symbols, strict invalid/duplicate rejection, ignored scanner columns, and local
diagnostic success/missing-symbol/no-credential paths with mocked market data.
All 729 theme dates and evidence remain unchanged; roster date is not a theme
launch approval. No Phase 9, main changes, inspection-ref moves or deployment.

Roster import validation: 288 full-suite cases, 286 passed/two Windows-only skips.
Three focused import/compatibility tests pass; market/lock four pass/one skip;
two frozen migration cases pass (all 64 Market Matrix cells). Compilation passes.

## Membership/evidence master review — 2026-11-06

Supplied master package applied mechanically, preserving taxonomy and all formulas.
Its 729 original keys/roles exactly match baseline 94050ac. Retained 726 rows across
668 tickers: 659 Core / 62 Enabler / 5 Related. Removed EXC/nuclear-energy,
ZG/internet-commerce (Z retained), SMG/agribusiness. Other material corrections
match the package exactly. Reapplication, including Food & Beverage, is idempotent.

Installed the supplied registry unchanged: 75 rules, 451 exact-covered relationships,
explicit allowlists retained. Gate approved only after validation. Attached all 167
tasks plus supplemental YOU/cybersecurity (master attachment decision outside task
list): 168 records/158 distinct inspected primary/official documents. Latest suitable
SEC annual reports preferred; five documented source choices use official company/
IR material, issuer annual report or SEC quarters. No evidence mismatches remain.
Four AMZN/GOOGL findings verified against their specified annual reports and cleared.
107 other primary-evidence rows retain the supplied completed-review citations.

Queue now zero; gate values match actual config. Master/rule/task hashes, exact
source URLs/content hashes, supporting paraphrases, review provenance and removed
records are versioned. Raw source HTML/PDF and private scanner-volume notes are not.
Runtime config loading validates rule/task/queue/role consistency fail closed. A
regression proves an unsupported attachment remains unresolved instead of forcing
queue zero. No activated history can be overwritten by the application script.

Validation: 295 full cases, 293 passed/two Windows-only skips; 88 focused vNext
cases, 87 passed/one Windows-only skip; seven evidence tests pass. Config/count/rule
validation, compilation, JS syntax/helpers and safe inspection generation pass.
Per-theme eligible counts and reproducibility details: docs/membership_review_2026-11-06.md.
All 44 Active themes retain >=5 Core+Enabler members. Related excluded from math.

At membership-review commit 150c47c, the only configuration blockers were pending effective dates; unapproved launch
rebalance session; production disabled. All 726 retained launch dates/end dates
remain blank. Runtime roster gating remains; Windows/performance validation items
are separate. No Phase 9, main changes, formula edits, live Alpaca use or deployment.
Do not move original inspection checkpoint branches for this review application.

## Phase 9 — approved launch and default-runtime cutover

User approval before the November 6 market session authorizes launch rebalance
2026-11-06, first earned session 2026-11-09 and production enabled. Mechanically
dated all 726 retained rows only; preserved 659 Core / 62 Enabler / 5 Related,
all evidence and removed relationships. Approval/gate metadata is validated
against membership and the XNYS calendar. No backdating or new evidence decisions.

Runtime fetches post-close launch holdings even though none earn L's return.
Pre-launch refresh remains market-only; L initializes every valid Active index at
100 with empty earned_symbols. Bootstrap index rows are explicitly flagged and
only seed indicators. Launch initialization is not an earned-session signal;
first-return transitions remain unavailable. Pure build_index and all formulas
are unchanged. Related remains excluded. SQLite schema remains 2.

Normal setup/refresh/open-dashboard launchers now use vNext. Explicit legacy
launchers/readers/reproduction fixtures remain; no historical payload is rewritten.
Reviewed TradingView Symbol/Exchange metadata supplements missing TXT identifiers
without inferred venues or changing the legacy symbol map. No thematic anchor,
ETF history or manual daily CSV enters the default computation path.

User-reported external prerequisite: live SIP roster check for 2026-11-05 passed,
501 SPY / 101 QQQ, zero missing/unusable, 12 pages, split/spin-off plus raw volume.
No real credentials or raw provider payload were used here. Native Windows Phase 9
launcher check, actual TradingView TXT import and full-universe live cold/warm
performance remain local validation items. Effective roster checks still fail
closed; stale-roster warnings remain advisory and IWM has no roster requirement.

Validation: full Python suite 302 cases, 300 passed/two native-Windows skips.
Focused vNext suite 95 cases, 94 passed/one native-Windows skip; seven launch
regressions passed. Local 14 passed. Frozen migration cases include exact equality
for all 64 Market Matrix cells. Real loopback browser refresh/TXT/watchlist/mobile
smoke passed with zero external requests/page errors. Evidence/config counts,
compilation and JavaScript checks passed. Safe inspection/source checks are
recorded in docs/vnext_launch.md. Stop after
the separate tested Phase 9 commit/push. Gate E has not started. No deployment,
main changes, checkpoint-ref moves or live runtime database changes.
