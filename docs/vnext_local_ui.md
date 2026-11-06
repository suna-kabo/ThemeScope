# Gate D — local market and research application

Gate C 7d3bf2e is approved. The user reports that the actual-account historical
SIP PoC passed for session 2026-11-04: three symbols, positive raw volume, six
pages, SIP 1Day, split/spin-off and raw liquidity requests, no IEX fallback.
Phase 6 is a8958f3; Phase 7 is 9080337; Phase 8 is this Gate D checkpoint.
Phase 9 has not started. Legacy launchers/runtime remain available.

## Windows launch

Extract the complete branch ZIP and install Python 3.12. Double-click ThemeScope.cmd
for the local vNext application, or run these commands from the repository root:

```powershell
.\ThemeScope.cmd --fixture
```

Fixture mode uses fictional symbols and a separate runtime database. It needs no
credentials. Click Refresh Data to exercise the provider/cache, calculations and
transactional publication. Stop the server with Ctrl+C in its console.

For actual SIP data, keep the local APCA_API_KEY_ID and APCA_API_SECRET_KEY
environment variables from the successful PoC, then run:

```powershell
.\ThemeScope.cmd
```

The launcher bootstraps the isolated runtime on first use and opens the browser at
http://127.0.0.1:8766. An optional --port changes the local port. The server always
binds loopback. ALPHAVANTAGE_API_KEY is optional; without it earnings is Unavailable.
No credentials are stored by the launcher, API, database or inspection bundle.
Do not put credentials in commands checked into Git.

For Python environments without the Windows py launcher, run:

```powershell
python scripts/bootstrap_dev.py
.\.venv-vnext\Scripts\python.exe scripts/run_vnext.py --fixture
```

## Manual roster workflow

User-approved TradingView snapshots are now recorded effective 2026-11-05:
SPY has 501 configured symbols and QQQ has 101. Earlier sessions have no backfilled
roster. Source hashes and import audit are in config/market_universes. These are
constituent identities only; Alpaca SIP still supplies all runtime price/volume data.
For later manual updates, provide a CSV with a ticker header, uppercase symbols
and no duplicates (or explicitly choose --symbol-column Symbol for TradingView). Import each benchmark separately, using its actual approved
roster effective date and a source description:

```powershell
python scripts/import_market_roster.py --benchmark SPY --effective-from YYYY-MM-DD --source "Approved manual source" --csv spy_roster.csv
python scripts/import_market_roster.py --benchmark QQQ --effective-from YYYY-MM-DD --source "Approved manual source" --csv qqq_roster.csv
```

Review/commit the resulting config/market_universes/rosters.json separately. The
command closes the preceding open interval and appends the new roster. It never
changes the earlier constituent lists. Historical lookups use half-open effective
intervals. A source older than 90 calendar days produces an advisory warning;
staleness never causes invented substitutions. No daily CSV input is required.
Roster updates share the application refresh lock and cannot change the roster
while a refresh is using it. IWM has no roster import or constituent-breadth vote.

## Market and earnings behavior

SPY/QQQ keep separate constituent universes. A constituent must have valid close,
EMA21 and EMA50 to enter either breadth numerator/valid denominator. Configured
members remain in the coverage denominator. Coverage >=80% is required. Both
breadth values >=50 means Positive; both <50 means Negative; otherwise Mixed.
One unavailable index breadth makes combined breadth Unavailable. Other valid
combinations combine exactly as specified. The existing Market Matrix function is
called unchanged, including its unanimous-price rules; all 64 frozen cases pass.
Missing prices yield Unavailable, never Mixed. IWM remains price context only.

Earnings uses only provider-reported dates. Missing key/event, quota responses,
malformed data and exceptions return Unavailable without failing market refresh.
Reported dates are highlighted beside stock candidates. No dates are inferred.

## Refresh concurrency and publication

The OS-held refresh lock covers configuration read, provider/cache preparation,
calculation, optional earnings and transactional persistence/publication. Another
thread/process cannot begin preparation or publish concurrently. The lock is
released by the OS on process death; its persistent file is never unlinked. On Windows, byte 0 is initialized only
when the file is empty; repeated acquisitions neither append nor truncate it.
There is no SQLite write transaction during network waits. SQLite's original
single-writer transaction/rollback, immutable input versions and replay protection
are preserved. Snapshot configuration hashes now include the exact roster ledger;
market results retain roster payloads for audit.

The API starts one background refresh and reports progress through status polling.
Conflicting refreshes return 409. Dashboard data and all TXT downloads read the
same committed publication, so failures preserve both dashboard and exports.
The target is the latest safely completed US session. Incremental missing/repair
fetches, corporate-action anchors and reseeds use Gate C's cache. No theme becomes
active while production blockers exist. In that state the app can show market
context and explicit theme activation blockers; it emits no live Primary list.

Loopback Host validation, same-origin POST validation and a restrictive content
security policy protect the local application. Assets make no external browser
requests. Runtime databases/status stay under ignored runtime directories.

## Inspection and validation

Open inspection/index.html and follow the Gate D UI link, or directly open
inspection/ui/index.html. The static preview is explicitly synthetic and needs no
server or credentials; Replay fixture replays its synthetic snapshot and its
combined download is generated locally. ThemeScope.cmd --fixture exercises the
actual server/cache/refresh lifecycle. The static preview cannot contact Alpaca.

Product flow: Market -> Daily Plan -> Theme Research -> Watchlist -> Methodology.
Daily Plan includes Today's Plan, decision path, Primary themes and New/Continuing/
comparison-unavailable state, independently qualified stock relationships, earnings,
and one combined TXT download. Watchlist choices are stored only in that browser.

Focused tests cover process/thread exclusion during both network and calculation,
absence of a SQLite write lock during network, successful background refresh,
failure preservation, API/download consistency, same-origin checks, pending launch
exclusion and non-blocking earnings failure. Chromium smoke exercises real loopback
HTTP, Refresh Data, combined TXT download, Watchlist, Methodology navigation and
mobile layout, with zero external requests or page errors. The standalone static
preview is also tested over a simple loopback static server. The managed browser
blocks file-scheme navigation; direct extracted-file opening remains a local check.

Small fixture timing covers 16 symbols x 64 sessions (1,024 cold observations),
then 48 warm observations (two repair sessions plus an anchor per symbol). Timings
are recorded in the inspection test report. They are not a full live-universe
throughput claim. Real Windows first-use/CMD, browser opening, native locking and
actual large-universe cold/warm SIP timings still require local validation.

## Current activation status (Phase 9)

Explicit approval now sets launch rebalance 2026-11-06 and all 726 retained
relationships effective 2026-11-09, with production enabled. Evidence queue is
zero and 75 industry rules remain approved. Effective SPY/QQQ roster gating is
unchanged; supplied rosters begin 2026-11-05. The user reports full SIP roster
compatibility passed locally for that session (501/101, no missing/unusable bars,
12 pages, adjusted and raw requests). No credentials or raw payloads are recorded.
See vnext_launch.md for launch regression results and remaining local checks.
Earlier Gate D sections below record the original checkpoint, which is preserved.

## Gate D hardening after independent review

The runtime activation gate now combines configuration blockers with target-session
roster checks. Both an effective SPY roster and an effective QQQ roster are required.
A missing, future-only or expired roster adds an explicit benchmark/session blocker
to the dashboard's activation list. Live theme membership and all Primary exports
remain disabled until both required rosters and all configuration gates pass.
IWM never requires a roster. Stale effective rosters still produce only advisory
warnings. The frozen Market Matrix and its Unavailable behavior are unchanged.

Windows refresh locking keeps the persistent-file/byte-0 design, using a non-append
open and writing the initialization byte only for an empty file. Existing file
contents are preserved; successful and rejected acquisitions do not grow the file.
Regression coverage exercises this branch with a mocked Windows lock API on Linux;
a native Windows repeated-acquisition test is included for local Windows execution.
Linux cross-process exclusion and full-refresh concurrency coverage remain passing.

This is one focused Gate D hardening change. The original inspection/vnext-d-ui
checkpoint remains at 02e7d63. Phase 9 has not started.

Hardening validation: full suite 277 passed / two Windows-only skips; focused
market/lock four passed / one skipped; focused local eight passed. Python
compilation passed. No native Windows execution is claimed by the Linux run.

## Native Windows status-file hardening

Native Windows testing after Gate D successfully launched ThemeScope.cmd --fixture,
but exposed WinError 5 in status publication at the calculation-progress update.
A second failure while reporting that error could terminate the background worker.
The accepted e3450ff roster activation and byte-0 refresh-lock fixes are unchanged.

Status is auxiliary operational metadata. Each update first changes guarded memory,
then writes a uniquely named status-*.tmp file in the same runtime directory. The
temporary handle is closed before replacement. PermissionError and Windows access/
sharing/lock violations (5/32/33) receive up to four replacement attempts with
10, 20 and 40 ms backoffs (70 ms total). Other filesystem failures do not retry.
The owned temporary file is removed in finally where possible; a still-locked temp
file may remain rather than causing another operational failure.

Creation, write, replacement and cleanup failures never abort refresh or recursively
report another status-write error. Memory retains the current status. While an
update is unpersisted, status polling uses that guarded memory instead of the stale
recovery file. Otherwise a valid persisted status remains available for recovery;
missing, inaccessible, malformed or invalid-shaped files fall back to memory.
A persisted running state with no active refresh lock still reports Interrupted.
SQLite remains the authority for successful dashboard/export publication and last
successful session metadata. A committed snapshot can succeed even if every status
replacement fails. An actual later refresh failure still preserves the prior snapshot.

Linux regressions simulate transient and permanent Windows-style failures, confirm
closed unique temp handles and cleanup, capture background thread exceptions, and
verify successful publication plus safe later error reporting under failed status
persistence. Native Windows revalidation of this fix remains a local check: run
ThemeScope.cmd --fixture, refresh repeatedly, and verify success/progress and downloads.
The original inspection/vnext-d-ui branch stays at 02e7d63. Phase 9 has not started.

Windows-status hardening validation: 285 full-suite cases, 283 passed and two
Windows-only skips. Focused local: 14 passed. Focused market/lock: four passed
and one native-Windows skip. Compilation passed. Native Windows retest pending.

## Approved TradingView roster import — 2026-11-05

SPY_2026-11-05.csv supplied 501 rows/unique symbols; QQQ_2026-11-05.csv supplied
101 rows/unique symbols. Only Symbol was read for configuration. No duplicates,
blank or invalid tickers were found. BF.B and BRK.B are preserved exactly in SPY.
The two effective rosters remain separate; IWM has none. All other scanner columns,
including price, EMA, performance, turnover, earnings and market cap, were ignored.
Full source CSV payloads are not committed. Audit metadata records source filenames,
SHA256 hashes, dates/counts and a hash of each exact ordered ticker list.

All tickers pass the existing Alpaca adapter's static symbol grammar. This does
not prove live retrieval. Codex has no Alpaca credentials for this import. To check
all configured symbols locally, retain APCA_API_KEY_ID/APCA_API_SECRET_KEY and run:

```powershell
.\.venv-vnext\Scripts\python.exe scripts/check_roster_symbols.py --roster-date 2026-11-05
```

The optional --session YYYY-MM-DD chooses a safely completed test session. By
default the check uses the latest safely completed session, which can precede the
snapshot date: this is a compatibility diagnostic, not a backdated roster import
or historical breadth calculation. Output shows both dates. Requests use the
existing historical SIP adapter (1Day, split/spin-off plus raw), in batches up to
100 symbols, with no cache writes, roster changes, IEX fallback or trading calls.
Shared symbols may be fetched once but retain their independent roster memberships.
Missing/unusable symbols are reported per benchmark and exit nonzero; request
errors report the affected requested symbols instead of silently dropping them.
The user reports the local SIP compatibility check passed for 2026-11-05 (501 SPY,
101 QQQ, zero missing/unusable, 12 pages). This was not rerun in cloud.

Staleness remains advisory; Market Matrix logic and all frozen cells are unchanged.
The roster effective date does not set the vNext theme launch session. Later
explicit user approval separately selected 2026-11-06 close / 2026-11-09 first
earned session and authorized Phase 9. Gate D inspection refs are preserved.


## Gate E native Windows SQLite contention blocker

A fresh Phase 9 Windows ZIP started Uvicorn normally, then `/api/status` failed
at SQLite PRAGMA user_version with `database is locked`. This differs from the
previously fixed Windows status-file replacement issue. The focused fix initializes
schema 2 before serving, serializes creation/migration with a version recheck,
and uses read-only polling connections with a 5.0-second bounded SQLite wait.
Only BUSY/LOCKED read errors use known committed snapshot fallback; other errors
remain visible. No uncommitted candidate enters the cache, failed refresh preserves
previous dashboard/TXT, and RefreshLock remains exclusive. No WAL switch or DB reset.

Exact native retest commands and test coverage:
[vnext_sqlite_lifecycle.md](vnext_sqlite_lifecycle.md). Keep existing runtime data.
Gate E remains open until native validation is rerun. Main, original inspection
checkpoints, launch dates, evidence, formulas and provider semantics are unchanged.
