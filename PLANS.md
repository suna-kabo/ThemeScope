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
Phase 9 is complete at 327fc2375ae0e4981af87d4b5136170ee542b60d.
SQLite lifecycle fix 0b51a0f and pre-launch research fix ed12ba4 are complete.
Current checkpoint: non-live Gate E correctness review and regression validation
completed after 860f87c / 4bc6656; no demonstrated runtime blockers. The user reports native Windows Nov 6 launch validation PASSED
(899/899 SIP symbols, ~52.5 seconds). UI remains frozen; Gate E stays OPEN for
real Nov 9/10 chronological checks. See docs/vnext_gate_e_review.md.
Launch rebalance 2026-11-06 close; all 726 retained relationships effective 2026-11-09.
Production enabled; zero config blockers. Runtime SPY/QQQ roster gates remain.
Preserve inspection/vnext-d-ui at 02e7d63 and every original gate ref.
Gate E is open pending real Nov 9/10 chronological checks. Do not close Gate E,
move inspection refs, merge or deploy. SQLite schema remains 2.
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
Original Phase 9 pre-launch refresh was market-only (superseded by the approved
Gate E research clarification below); L initializes every valid Active index at
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

## Gate E Windows SQLite lifecycle hardening after Phase 9

Native Windows on a clean Phase 9 ZIP reproduced `/api/status` ASGI failures at
Store's PRAGMA user_version: database is locked. Confirmed zero-wait read connections
could race lazy schema creation/migration or commit locks after the server started.

RefreshService now eagerly initializes before create_app/Uvicorn accepts requests.
SQLite BEGIN IMMEDIATE serializes schema creation/migration, with version recheck
inside the transaction; fresh 0 -> 1 -> 2 is atomic and failed initialization rolls
back/closes safely. Existing schema-1 databases migrate without deleting data.
Normal read-only snapshot connections never initialize or write. Default connection
wait is exactly 5.0 seconds (busy_timeout 5000ms); journal mode and schema 2 remain.

BUSY/LOCKED read failures alone use a guarded last-committed cache (or no snapshot
on first use), with an explicit API diagnostic and safe warning. Other DB errors
stay visible. Cache advances only after successful reads/COMMIT, resists late-reader
regression and caller mutations, and never exposes a candidate before commit.
Status samples operational state after DB waits, preserving interrupted recovery
without falsely calling a just-completed refresh interrupted. RefreshLock and the
refresh transaction/publication validation/rollback are unchanged.

Eleven new deterministic regressions cover thread/process initialization races,
concurrent schema-1 migration, rollback/retry, HTTP polling across fetch/calculate/
uncommitted publication/real COMMIT locks, first refresh, bounded busy fallback,
non-busy errors, cache ordering and actual commit failure preservation. Details and
native Windows commands: docs/vnext_sqlite_lifecycle.md. Native validation remains
pending; Gate E remains OPEN. No methodology/config/provider/Matrix/roster changes,
main/deployment/inspection-ref changes or real runtime DB edits.

Validation: full suite 313 cases, 311 passed/two native-Windows skips. Focused
vNext suite 106 cases, 105 passed/one native-Windows skip, including all eleven
new SQLite lifecycle regressions, five storage, fourteen local and market/locking
coverage. Seven launch and both frozen migration cases pass; all 64 Matrix cells
match the unchanged baseline. Config/evidence validation, Python compilation,
JavaScript syntax/helpers and loopback browser refresh/download smoke pass.
Temporary safe inspection and protected-source/runtime/secret checks pass.
Native Windows retest is still required before Gate E can close.

## Gate E approved pre-launch research clarification

The end-of-day swing workflow uses the latest safely completed US session before
the upcoming US open. Official synthetic-return effectivity is a separate concept
from the approved universe available for current research. The user explicitly
authorizes current pre-launch research without changing any launch dates/formulas.

LaunchResearchUniverse selects the approved future launch interval only before L
and only with zero config/runtime roster blockers. Original Membership objects,
active_on/members_on and all 726 dates remain untouched. Core+Enabler supplies
benchmarks, breadth, LOO W and eligibility; Related is retained as context only.
The engine has a separate research-universe/bootstrap-series input. All existing
formula functions and live build_index semantics remain; only membership wiring
changes. No hardcoded November 5 implementation exception.

Pre-launch bootstrap provides current EMA21/EMA50 trend and normal static priority,
so Primary candidates and deterministic individual/combined exports work. Published
metadata marks pre_launch_research, research_session, approved_launch_membership,
first-earned membership basis and official_live_history=false. Theme histories use
a separate research series ID, bootstrap=true and signal_eligible=false. Research
series points never enter theme_index. At L the path switches off automatically:
level 100 with empty earned_symbols, then E's first genuine return. No pre-launch
history supplies transitions or is spliced into the official series.

UI identifies the completed research session and official start, labels Pre-launch
research trend, and keeps comparisons unavailable. These are real research values
in normal operation, never labeled as fictional fixtures. Save/watchlist/download
flows remain unchanged. SQLite lifecycle/5s busy handling/atomic cache fix retained.

Validation: full suite 321 cases, 319 passed/two existing native-Windows skips.
Focused vNext: 114 cases, 113 passed/one native-Windows skip. Eight pre-launch,
seven official-launch and eleven SQLite lifecycle regressions pass; all 64 frozen
Market Matrix cases remain exact. Independent rational oracle matches all 44
research medians/scores and a selected LOO W. Both real-loopback browser checks
pass, including pre-launch export/Save and automatic official-launch cutover,
with zero external requests/page errors. Evidence/config, compilation, JS and
temporary safe inspection/protected-source/runtime/secret scans pass. Details and
native retest commands: docs/vnext_prelaunch_research.md. Gate E remains OPEN. No main/deployment/frozen
inspection changes, credential use, real runtime DB edits or evidence decisions.


## Lunar Lounge UI implementation after ed12ba4

The user selected one design direction from the completed exploration and authorized
HTML/CSS/JavaScript implementation, a tested commit/push and then a stop for review.
No competing prototype/branch, framework migration, backend/API changes or deployment.

- Dedicated Overview, Themes, Theme Detail, Candidates, Saved and Methodology
  surfaces with persistent labeled navigation and browser history/context restoration.
- Matte night/lavender token system, legible sans type, tabular numbers, original
  outline icons, compact research tables, narrow reflow and reduced motion.
- Search/filter/sort, separate 44 Active/eight Watch-only browsing, independent
  qualifications/unique ticker view, current Saved context, canonical TXT downloads.
- Identical snapshot polls no longer replace focused Save controls. Operational
  metadata stays compact; failure retains previous committed results and exports.
- Sequential specialist passes: better-ui, better-typography, better-accessibility.
  Public UI Craft and brand catalogs inspected without installation or new dependencies.
- Full suite: 321 run, 319 passed/two Windows skips. Focused vNext: 114 run,
  113 passed/one Windows skip. Includes pre-launch 8, launch 7, SQLite lifecycle 11
  and all 64 frozen Market Matrix cases. Three browser scripts, syntax/compilation
  and configuration validation pass. Chromium 1440/1600/1920 and 800/390/320 widths;
  200% root text resize; audited axe A/AA views have zero violations.
- Audit fixes include target sizes, stable focus, native fragment/skip navigation,
  missing platform glyphs, readable type and mobile breadth/Priority separation.

Detailed behavior, test evidence, limitations and screenshot links:
[docs/vnext_lunar_lounge.md](docs/vnext_lunar_lounge.md).
No src/config/financial/provider/storage/export/launch changes. Approved launch
2026-11-06 close and first earned session 2026-11-09 stay frozen. All original
inspection refs and main remain unchanged. Gate E is not closed; native Windows,
screen-reader speech and other browser engines remain local/platform checks.

## Gate E launch-close research correction

Launch L now selects approved first-earned-session membership for cross-sectional
research through an independent resolver. Official accounting and bootstrap/live
isolation remain unchanged: Nov 5 research; Nov 6 initialization at 100 plus research;
Nov 9 first earned return without transition; Nov 10 first possible live transition.
Tests cover 44 Active themes, 721 research rows, deterministic Candidate generation,
no launch earned symbols/signals, generic shifted dates, blockers and unchanged drift.
Native Windows validation and real Nov 9/10 checks remain open/deferred.

Stage 1 validation: focused vNext suite 115 tests (114 passed, one Windows skip).

## Gate E Windows reviewed-evidence line endings

Commit 860f87c preserves launch-close research independently of official accounting.
The separate evidence fix pins four reviewed JSON/provenance files to LF while
preserving CMD CRLF. A strict UTF-8 text hash replaces only CRLF pairs with LF in
memory; approved expected hashes and reviewed content stay unchanged. Tests cover
LF/CRLF full validation, actual content/format edits, provenance tampering, invalid
UTF-8 and lone CR sensitivity. No semantic evidence checks are relaxed.
See docs/vnext_gate_e_launch_windows.md for native validation and lifecycle checks.

Final two-fix validation: full 325 (323 passed/two native-Windows skips), focused
vNext 118 (117 passed/one skip), evidence 10 passed; all 64 frozen Matrix cases pass.
Both validators, compilation, both JS syntax checks and dashboard JS tests pass.
Only existing Starlette TestClient/httpx deprecation warning remains. No live calls.
Gate E remains OPEN for the user's Nov 6 native refresh; real Nov 9/10 checks deferred.

## Gate E final correctness review — 7 November 2026

User-reported real native Windows Nov 6 validation PASSED: success, healthy SIP,
899/899, 44 Active themes, Scores/W/eligibility/Candidates, official level 100,
no earned return or eligible signal/transition; elapsed about 52.5 seconds.
Earlier pending-Windows notes above are historical checkpoint records.
No demonstrated runtime blocker found in the final review. Added focused service/
HTTP regressions for provider/calculation/partial-publication failure preservation,
same-session replacement/failure and older replay. Documentation now distinguishes
pre-launch bootstrap stopping from continuing launch-close research. No runtime,
UI, schema, formulas, memberships or export semantics changed; no cleanup deletion.
See docs/vnext_gate_e_review.md for findings, validation and deferred live checks.

Final review validation: 327 full cases (325 pass/two native-Windows skips),
120 focused vNext (119 pass/one skip), all 64 Matrix cases unchanged. Both validators,
compilation, both JS syntax checks and dashboard JS tests pass. Findings are
non-blocking diagnostics/cache-policy/manual-integration limitations plus existing
TestClient deprecation. No actual runtime defect demonstrated; no runtime changes.

## Research Desk UI redesign after the final Gate E review

User authorized three focused UI commits, superseding the Lunar Lounge presentation
without changing its financial/runtime contract. Step 1 introduces compact navy/
indigo/lavender styling, Primary navigation, flatter market/research composition,
page-level table scrolling, semantic colors and separate browser Display choices.
Saved retains its existing ticker-array key. No src/config changes. Full suite:
327 cases, 325 passed/two native-Windows skips. Refresh/export/Saved and pre-launch
cutover browser smokes pass. Inspectors and lightweight research visualizations
are the next two authorized steps; Gate E remains open for real Nov 9/10 checks.
See docs/vnext_research_desk.md for current design and validation evidence.
Stage 1 final browser rerun passed all destinations/Display, nine axe A/AA views,
320px reflow and 200% text resize, with zero page errors/external requests. Visual
review confirmed mobile and high-contrast states. Accessible-label overflow and
large-text sidebar/reflow findings were fixed before the first focused UI commit.

Step 1 committed as 2c2d449. Step 2 adds one native theme/ticker Research Inspector
with persistent link chevrons, history/Back, source focus and filter preservation.
Repeated row disclosures move into the inspector; full Theme Detail stays optional.
Snapshot changes preserve inspector input/focus; failure retains published data.
Only presentation/tests/docs changed. Full 327-case suite and the two functional
browser smokes pass. Native mobile dialog alignment and forced-colors tokens were
hardened during visual/accessibility review before the second focused UI commit.
Step 2 acceptance complete: all three browser scripts pass, zero axe A/AA violations,
page errors or external requests. Covers inspector Back/Forward/Escape, source
focus/scroll, refresh preservation, 320px/200% text and forced colors. Default
1440p density measures 30 theme rows and 24 Primary rows. No runtime/config diff.

Step 2 committed as 739ad32. Step 3 retains market/theme breadth bars and an optional
raw-return Theme Map, using native SVG and the existing snapshot. Linear axes include
zero/outliers, and keyboard/select access preserves overlapping points. No percentage
rank substitution or financial calculation path. W distribution intentionally omitted
because signed sortable member rows already serve that comparison with less clutter.
Final full suite: 327 run, 325 pass/two Windows skips. Focused: 120 run, 119 pass/one
Windows skip; all 64 frozen Matrix cases. Validators, compilation, both JS syntax
checks and dashboard helper tests pass. Functional browser refresh/export/Saved and
fixture launch cutover checks pass. Final visual/browser artifacts are local-only.
Final browser acceptance PASSED: all three browser scripts; 14 axe A/AA views,
zero violations, page errors or external requests. Only the confirmed pre-existing
/favicon.ico 404 is recorded separately from unexpected console errors. Twelve
fixture screenshots are supplied in the local review gallery/ZIP, outside Git.
No src/config/runtime changes, no dependencies, merge or deployment. Gate E stays
open and real Nov 9/10 chronological checks remain deferred. Stop for visual review.

## Final Research Desk visual polish after 31b3f1a

User approved the current UI functionally and requested one presentation-only commit.
Inspected all requested desktop screenshots before editing. Refined warm violet tokens,
quiet navigation edges, partial accent rules, market/inspector hierarchy, dense row
styling and a softer Saved surface. Grouped existing Methodology disclosures without
changing their contents. Theme Map retained for useful raw-return positioning; rejected
extra cards, charts, settings or dramatic angles. app.js/src/config unchanged.
Full 327 tests (two existing Windows skips), focused 120 (one skip), all 64 Matrix
cases, both functional browser smokes, validators, compilation and JS checks pass.
The browser acceptance checks and fresh desktop/mobile/200%-text/high-contrast captures
validate the polish before the single commit. No runtime changes, dependencies,
financial assertions or private data. Gate E and real Nov 9/10 checks remain open/deferred.
Visual review also corrected missing/per-theme W emphasis on mobile. Density is
preserved/improved: 32 Theme rows and 24 Primary rows at 1440p. The final gallery
includes 15 fixture-only screenshots and explicit 200% text views outside Git.

## Targeted market overview interactions after 0b520b4

User requested only concrete presentation fixes. Routine initialized/live lifecycle
text moves to Refresh details; meaningful warnings remain. Theme Map opens by default.
Shared SPY/QQQ grid aligns ticker/price/state/EMA/breadth, with explicit larger
Above/Below/At EMA labels derived only from existing prices. Supplied breadth state
is compact and semantic; coverage/source/advisories remain in diagnostics. Direction
icon is aligned, route motion is 110ms/2px and refresh feedback finite; both motion
reduction modes remain respected. Dense tables remain 32/24 rows at 1440p.
Full 327 (two Windows skips), focused 120 (one skip), all 64 Matrix cases and both
functional browser smokes pass. Main browser covers exact alignment, EMA boundary
presentation, diagnostics, map default and reduced motion, with fresh visual review.
A 200%-text spacing finding widened the common ticker column before the final run.
No backend, financial/configuration changes or live chronological validation.
One commit, then stop for review; main/inspection refs and Gate E stay unchanged.
Final browser rerun PASSED with 14 axe audits/zero violations, no page errors,
external requests or unexpected console errors. Known favicon 404 remains isolated.
Nine fresh fixture-only screenshots are delivered in a local review gallery/ZIP.
Desktop grid rows align within one pixel; 200% text and both motion-reduction controls
pass. No src/config diff. Complete this single targeted commit and stop for review.

## Narrow UI consistency after 51839b3

Hide earnings fields/filter/column when existing records are globally unavailable;
clear the hidden filter without affecting qualification. Explicit available dates,
empty available records and failures keep distinct supplied-state labels. Existing
contract cannot distinguish disabled, failed and successful-empty all-Unavailable
results; no backend change or fabricated dates. Hide redundant earnings in full-theme
and Saved presentation too, preserving their behavior/storage.
IWM shares SPY/QQQ typography and existing-price EMA context, with no breadth/Matrix
role. Shared row rhythm centers values/controls; unavailable breadth keeps a dash
and supplied coverage metadata only. Full/focused suites and functional browser
smokes pass; final browser verifies earnings transitions, density, geometry, IWM,
320/390px, 200% text, reduced motion and accessibility. No src/config/financial test
changes. One commit, clean tree, stop for review; main and Gate E remain unchanged.
Final acceptance PASSED: 14 axe audits/zero violations, all browser scripts, exact
row-centering and IWM computed-type checks; 31 Theme/27 Primary rows at 1440p.
Eleven fresh fixture screenshots reviewed, including 390px and 200% text. Known
favicon 404 remains isolated; no page errors, external requests or other console
errors. Financial/runtime behavior and protected refs remain unchanged.

## Exact horizontal table/headline geometry after 40d54af

User limited scope to desktop Theme column geometry and exact market headline type.
Fixed tracks total 100% (3/33/8/9/9/12/14/12), with matching header/body widths and
separated Trend/Breadth regions. Desktop rules exclude existing labelled reflow.
Ticker/price share family, size, line-height, weight and tracking across SPY/QQQ/IWM;
all reuse header grid spacing. IWM has no breadth/Matrix role. No vertical padding,
navigation, filter, inspector, Map, animation, data or runtime changes.
Added exact browser geometry/style assertions and full-height Themes captures.
Reviewed desktop screenshots by eye before the single geometry commit. Existing
functional browser scripts, accessibility checks, JS syntax/helpers and compilation
are the relevant regressions. No financial tests changed; protected refs/Gate E and
real Nov 9/10 validation stay unchanged/deferred.
Final geometry acceptance PASSED: all three browser scripts, 14 axe audits with zero
violations, matching desktop header/body tracks and six identical headline computed
styles/baselines. Full-height Themes screenshots include actual equal-score labels;
visual review confirms separation and balanced tracks. Density stays 31/27 rows.
No page errors/external requests or unexpected console errors; known favicon 404
remains recorded. Nine fixture screenshots are supplied outside Git. Stop after push.

## Public entry point and synthetic static demo after 1222968

User explicitly authorized a public synthetic/read-only showcase, separate from the
private local live workflow. Repository inspected public with default branch still
main. Available GitHub integration has no settings-write capability, so no workaround
or metadata change was attempted; exact manual default-branch steps are documented.
No authenticated Cloudflare Pages integration is available; no deployment performed.

New stdlib builder copies the current static/vnext frontend byte-for-byte and generates
only synthetic preview data, Pages headers and a local original favicon. It extends
the authoritative offline fixture using unchanged pure engines and approved formula
settings; it reads no live memberships/rosters/mappings, provider, credentials or DB.
Output is ignored dist/cloudflare-pages, rebuilt deterministically with fixed files.
No frontend duplication, runtime dependencies, src/config or financial changes.
Historical inspection/ui remains untouched because inspection/browser tests use it;
it must never be used as the Pages source. Docs cover exact manual Pages settings,
no-secret build, disabled automatic dependencies/other-branch previews and removal.

Static browser validation applies the generated CSP and covers all views, inspectors,
Back, filters/sort, Map, Saved persistence, Display, replay, fixture-only exports and
390px. Eight axe audits pass, with zero external/API requests, console/page or HTTP
errors. Fresh desktop Overview/mobile Primary screenshots were visually inspected
outside Git. Focused build tests pass: isolated clean source build, identical rebuild,
stale cleanup, current asset equality, synthetic-only data/export, safety scanning,
no network/SQLite and symlink rejection. Existing local UI/assets/runtime are unchanged.
Gate E stays open, real Nov 9/10 checks deferred; no merge/main/inspection-ref changes.

Final validation: full suite 330 tests (328 passed, two existing native-Windows skips);
focused vNext 120 (119 passed, one skip); all three new build tests pass. All three
existing local browser smokes pass, including 14 axe audits with zero violations,
plus the static demo browser smoke/eight clear axe audits. Both config/evidence
validators, Python compilation, both JS syntax checks and JS helper tests pass.
Generated textual output safety scan passes; isolated canary checks confirm no
credential/path leakage. Sandbox TestClient stall required the same fixture-only
suite to run outside network isolation; no live calls or credentials were used.

## Local-to-Pages frozen public publishing after 229117a

User explicitly authorized publishing the already committed public research dashboard
from their local machine, with a mandatory matching completed-session argument. This
supersedes the earlier synthetic-only hosting restriction for this narrowly scoped
presentation artifact; local research/backend architecture and Gate E remain unchanged.
No authenticated Cloudflare Pages integration is available here, so no actual account
snapshot retrieval or deployment was performed. All test data are manufactured.

Added separate public builder and Windows publishing helper, preserving the synthetic
builder. Shared constants/favicon move to a presentation-only module, without changing
the synthetic fixture or weakening its safety checks. Real builder reads only the fixed
loopback dashboard endpoint, which already exposes committed publications/last-good
copies. Validates real-mode flag, schema, completeness, healthy publication metadata,
timestamp, session and presentation shapes. Copies an explicit nested allowlist of
existing metrics/relationships/eligibility/assignments and identifier-only TXT exports,
without recalculation. Excludes configuration hashes, serialized history, provider
identity, cache/performance/internal data and unknown fields. Six-file output is staged,
scanned and kept under ignored dist/cloudflare-public. Failed validation preserves the
previous prepared artifact; a separate OS-held publication lock covers build/upload.

Minimal frontend adds explicit frozen-public mode/banner, hides and guards Refresh,
keeps all requests/polling off and retains browser Saved/Display/inspectors/Map/exports.
Local live and synthetic fixture behavior are preserved. Public snapshots use the
current assets plus no-network CSP/no-store headers. No src/config/schema/provider/
calculation/export semantics changes. No real payload, credentials or binaries in Git.

Publisher requires the clean implementation branch, no tracked runtime/output artifacts,
explicit session and explicit existing project name. Uses normal local Wrangler OAuth;
market credentials are stripped from its process environment and upload runs away from
repo config/.env/Functions in an isolated allowlisted copy. Checks project existence and
latest recorded production branch, never creates a project, and confirms a new successful
Production deployment with branch/source commit after upload rather than trusting a
preview URL. Unknown/pending/failed confirmation returns nonzero. Pages production
branch and disabled automatic production/preview Git builds require the documented
one-time dashboard setup; scripts do not modify Cloudflare settings. Existing synthetic
Git builds would otherwise overwrite a real upload. Current Wrangler syntax and JSON
format were verified against official Cloudflare documentation and CLI source.

Focused tests use mocked loopback/CLI calls only. Static-public browser checks include
all destinations, Theme/ticker inspectors, Back, filters/sort, Map, Saved persistence,
Display, blob export, guarded hidden Refresh and 390px, with zero external/API requests,
console/page/HTTP errors and eight clear axe audits. Static synthetic smoke also passes.
Desktop/mobile public-mode screenshots were visually inspected outside Git; they contain
manufactured contract data, not real November 6 results. Native Windows launcher/OAuth,
actual Pages settings/account access and production domain session check remain local.
Main/inspection refs untouched; Gate E open and real Nov 9/10 checks still deferred.

Final acceptance: full 342 tests (340 passed/two existing Windows skips); focused
public-publishing 12 passed and synthetic build 3 passed; focused vNext 120
(119 passed/one skip). All five browser programs pass: existing local UI/refresh/
exports/launch-cutover plus both static modes. Thirty axe audits across these
checks have zero violations (14 local, eight synthetic, eight frozen-public).
Both static modes have zero external/API requests and page/console/HTTP errors.
Both validators, compilation, both JS syntax checks and JS helper tests pass.
No actual local real payload or Cloudflare upload was used for validation.

## Wrangler metadata framing fix after 85beb95

Publisher metadata parsing now uses strict JSON raw_decode to locate one top-level
array of objects amid ordinary Wrangler/npx informational text and known log tags.
Malformed/nested-wrapper/ambiguous payloads, wrong row types, duplicate keys and
non-finite values fail closed with the same non-secret diagnostic. Wrangler output
is explicitly decoded as strict UTF-8. Existing project, branch, source-commit and
production-environment verification are unchanged; no snapshot/financial/deployment
semantics changes and no actual upload. Added the five requested parsing regressions,
including non-ASCII messages and suffixes, plus noisy-output mocked publishing flow.
Validation: 17 focused publishing tests pass; full suite 347 tests (345 passed,
two existing native-Windows skips); publisher/test compilation and diff checks pass.
