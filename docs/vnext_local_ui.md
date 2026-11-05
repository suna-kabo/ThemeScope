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

Initial SPY/QQQ rosters are deliberately empty: no approved constituents were
supplied. Provide a periodic manual CSV with a ticker header, uppercase symbols
and no duplicates. Import each benchmark separately, using its actual approved
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
released by the OS on process death; its persistent empty file is never unlinked.
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

## Remaining production blockers

All 729 launch effective dates remain pending; no launch session has been chosen.
335 evidence refreshes, four inherited-evidence findings and documented industry
rules remain unresolved. Approved SPY/QQQ roster inputs are still required. Native
Windows and full-universe performance validation remain pending. No bootstrap
observations are presented as live signals, no evidence is auto-approved, no
Market Matrix formula changed, and no main merge, legacy retirement or deployment
occurred. Gate D stops before Phase 9.
