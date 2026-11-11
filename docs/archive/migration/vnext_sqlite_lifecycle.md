> **Historical checkpoint.** Status, counts and instructions below describe that
> checkpoint, not current operation. Gate E is now **CLOSED**; Nov 6, Nov 9 and
> Nov 10 live validation passed per the user. See the [closure record](../../operations/gate-e-closure.md)
> and [current documentation](../../README.md).

# Gate E native Windows blocker: SQLite lifecycle and polling

Native Windows testing on a fresh Phase 9 ZIP reproduced repeated ASGI failures:
`/api/status -> status() -> snapshot() -> Store() -> PRAGMA user_version` raised
`sqlite3.OperationalError: database is locked`. The server had already started.
This focused hardening follows Phase 9 commit 327fc2375ae0e4981af87d4b5136170ee542b60d.
Gate E remains open until the user reruns native Windows validation.

## Confirmed cause

Storage was initialized lazily from ordinary polling connections, all with a
zero-second timeout. Two constructors could read the same old schema version
before either acquired the migration lock. Fresh schema creation committed
version 1 separately from migration to version 2; migration's version check also
occurred outside its writer transaction. Legitimate schema/commit contention
therefore became an immediate unhandled read error.

`create_app()` already constructs its RefreshService before FastAPI/Uvicorn starts
accepting requests. The service now completes storage initialization at that point,
instead of allowing the first status request to perform it.

## Lifecycle and bounded contention

- `Store` defaults to **5.0 seconds** SQLite connection timeout. SQLite exposes
  this as **PRAGMA busy_timeout=5000** milliseconds. Explicit shorter/nonblocking
  timeouts remain available for tests/tools. There is no indefinite retry loop.
- Schema creation/migration is serialized with **BEGIN IMMEDIATE**, followed by
  a **version recheck inside that same transaction**. A waiting constructor sees
  the completed version and skips duplicate work. This works across processes.
- Fresh **0 -> 1 -> 2** runs in one atomic transaction. Individual DDL statements
  replace `executescript`, which would implicitly commit an existing transaction.
  Existing **1 -> 2** uses the same owner transaction. Errors roll back and close
  the failed connection; retry uses the intact prior schema. No database deletion.
- A ready schema-2 writer connection does no initialization writes. Browser reads
  use **read-only URI connections**, correctly escaped for Windows paths, and
  never perform schema checks, creation, migration or writes. They use the same
  bounded timeout and read the publication pointer/payload in one SELECT.
- No WAL switch, shared-cache mode, dirty reads, schema version bump, formula
  change or provider request change. Journal mode is preserved.

Existing RefreshLock still excludes competing refresh threads/processes immediately
across the full provider/calculation/publication lifecycle. SQLite still admits
only one writer. Short COMMIT contention waits within the finite timeout rather
than falsely failing the refresh. A sustained startup/writer lock beyond the
bound remains a real reported failure; it cannot wait forever.

## Committed snapshots and status

A read inside a writer's uncommitted transaction continues to see the prior
committed publication. A read arriving while COMMIT holds a pending/exclusive lock
waits for the short lock to clear and then sees a committed publication. Each
individual response is one complete snapshot, never partial refresh rows.

Only SQLite **BUSY / LOCKED**, including extended error codes, permit snapshot
fallback after the bounded wait. Corruption, I/O, schema and other errors are
not swallowed. Fallback is logged with a non-secret warning and exposed in
`/api/status` and `/api/refresh/status` as `snapshot_read`:

| Value | Meaning |
|---|---|
| ready | The publication was read successfully |
| busy_last_committed | SQLite stayed busy; returning the known committed snapshot |
| busy_no_snapshot | SQLite stayed busy; no known successful snapshot exists yet |

The guarded cache is loaded at startup or after a committed publication read.
The refresh may capture its candidate pointer/payload privately in the write
transaction, but updates the shared cache **only after COMMIT returns successfully**.
An older replay retains the actual publication pointer. Increasing publication
run IDs prevent a late old read from regressing the cache. Returned snapshots are
copied so callers cannot mutate the fallback. Nothing uncommitted is exposed.

On first use `/api/dashboard-data` returns JSON null until publication; TXT routes
return their normal 404 and status remains valid. Existing dashboards/exports stay
available during refresh. Error reporting and status-file persistence retain their
previous nonfatal behavior. Operational status is sampled after any DB wait so
completion during that wait does not become a false interrupted-process report.

The data transaction, validation, publication pointer, COMMIT/rollback, failed-run
diagnostics, older replay protection and previous-success preservation remain
intact. A failure after a pointer write or at COMMIT never advances the cache.

## Regression coverage

`tests/test_vnext_sqlite_lifecycle.py` uses real SQLite locking and synthetic data:

- Eight simultaneous service constructors on an empty runtime, with a competing
  initializer proved to reach BEGIN while creation is paused. One schema creation,
  valid version 2, no duplicate/partial objects or polling exceptions.
- Four separate Python processes simultaneously opening a fresh database.
- Paused schema-1 migration, a second initializer proved to reach the migration
  lock, and an existing snapshot/status reader. One migration, original publication
  and bar provenance preserved; integrity/foreign-key checks pass.
- Failed fresh/existing migration rolls back and a later retry succeeds.
- Startup completes before ordinary reads; read-only connections cannot write.
  Exact 5000ms busy timeout, unchanged default journal mode and escaped paths.
- HTTP status, refresh status, dashboard and both TXT routes during provider work,
  calculations and an uncommitted publication-pointer update, with/without a prior
  publication. All show prior committed data or the normal empty state.
- Real rollback-journal COMMIT lock: an external SHARED reader holds the writer
  pending; a zero-wait probe reproduces BUSY. The ordinary status reader waits,
  COMMIT succeeds after release, and the background thread finishes successfully.
- Busy deadline returns only committed data/null, never marks refresh failed;
  callers cannot mutate fallback and normal reads resume after release.
- Non-busy errors remain visible; late readers cannot regress cache; failure after
  pointer update or at COMMIT preserves previous dashboard/TXT/cache exactly.

These tests run on Linux/cloud and are intentionally runnable unchanged on native
Windows. No real market credentials are needed. Existing lock/status/roster,
provider/cache, launch, frozen migration and Market Matrix tests remain required.

## Native Windows retest

Keep the user's existing database; do not delete runtime files. Stop the prior app,
update to this hardening commit on the implementation branch, then run PowerShell:

```powershell
.\.venv-vnext\Scripts\python.exe -m unittest discover -s tests -p "test_vnext_sqlite_lifecycle.py" -v
.\.venv-vnext\Scripts\python.exe -m unittest discover -s tests -p "test_vnext_local.py" -v
.\ThemeScope.cmd --fixture
```

In fixture mode, repeatedly refresh while status/dashboard polls, and check that
progress ends successfully without ASGI lock errors and downloads remain valid.
Stop that server before running `ThemeScope.cmd` normally with the already configured
local Alpaca environment. Verify the existing live database opens/migrates and
polling remains healthy through a real refresh. Cloud tests do not replace this
native validation or certify account/full-universe runtime throughput.

Validation: **313 full cases, 311 passed/two native-Windows skips**; **106 focused
vNext cases, 105 passed/one native-Windows skip**; **11 new lifecycle regressions
passed**. Existing storage/local/lock/provider/cache/launch/migration tests pass,
including all 64 frozen Market Matrix cases. Configuration/evidence checks,
compilation, JS checks, browser smoke and temporary safe inspection/source scans
pass. The skipped cases are existing native-Windows file-replacement/byte-lock
checks; the new lifecycle tests run on both platforms. Native retest remains open.
No main merge, deployment, inspection-ref changes or Gate E closure.
