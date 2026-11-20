# Provider and storage contracts

## Historical market data

`MarketDataProvider` returns typed bars, provider/adjustment identity and pagination
provenance independently of ThemeScope formulas. `FixtureProvider` supplies deterministic
offline data; `AlpacaMarketDataProvider` uses only the historical Market Data API.

Requests explicitly use `feed=sip`, `timeframe=1Day`, `adjustment=split,spin-off`,
ascending order and every `next_page_token`. Paired `adjustment=raw` observations
provide actual regular-session close/volume. No dividend adjustment, IEX fallback,
trading/order endpoint or inferred symbol substitution. The schedule enforces a
20-minute completed-session safety delay and handles holidays/half days/DST.

401/403/422 fail permanently. Rate limits and supported transient server/transport
errors retry with finite backoff/Retry-After. Malformed, duplicate or inconsistent
bars and repeated page tokens fail closed. The loopback API exposes fixed refresh
error categories. Required target inputs must be complete before committing.
Only approved [terminal events](terminal-actions.md) can resolve their specific
accounting gap, without claiming a trading bar.

## Incremental observations

SQLite schema **2** explicitly migrates version 1 transactionally. Immutable,
content-addressed `observations` preserve provider/data versions; `bar_cache` points
to latest observations per provider/ticker/session; run-scoped `daily_bars` stores
references rather than duplicating all historical payloads every refresh. Earlier
runs remain pinned when data is repaired. Unknown migrated provenance is never
relabeled as Alpaca.

Cold refresh may seed the required history. Warm refresh batches missing/new sessions,
the default two-session repair window and historical adjustment anchors. A revised
anchor triggers a full retained-lookback reseed of that ticker; incomplete repairs
fail closed. Explicit full repair handles known older corrections; arbitrary old
revisions cannot be discovered without a scan. SPY/QQQ missing high/low inputs for
ATR are repaired through this same provider/cache boundary. Optional Bar fields
preserve old serialization compatibility. No formula is changed for caching speed.

Network retrieval precedes the SQLite writer transaction. Observations, cache
pointers, run inputs, results, corporate-action proof and the active snapshot
pointer commit together. The existing `publication` table stores that pointer.
Failed writes roll back together and older replay cannot advance the pointer.
The under-10-minute hard target / under-5-minute goal are design targets, not a
new benchmark claim from documentation or fixture timings.

## SQLite lifecycle and status

Storage initializes before HTTP polling starts. Schema creation/migration uses
`BEGIN IMMEDIATE` and a version recheck inside the owner transaction. Fresh 0→1→2
is atomic; default connection/busy timeout is five seconds. Browser reads use
read-only URI connections and never migrate/write schema. Journal mode is unchanged.

Only SQLite BUSY/LOCKED may fall back to a known committed snapshot after the finite
wait; other errors remain visible. The guarded cache advances only after COMMIT,
never from a candidate pointer. `/api/status` exposes `snapshot_read` as `ready`,
`busy_last_committed` or `busy_no_snapshot`. Empty first use remains an honest null
snapshot / missing TXT until publication.

At launch, the launcher verifies the loopback server identity before reusing a
port. It asks the recognized server to check for a newer safely completed session.
The live process loads DPAPI credentials when needed, with optional environment
overrides. A server that started before credentials were saved can use them on
its next refresh. The fixture uses its own database, lock and Saved file.

Status reads the committed run ID and uses cached metadata. The browser fetches
the snapshot once on load and again when the run ID or commit timestamp changes.
Status checks the latest eligible session and reviewed-input fingerprint, reusing
the fingerprint until the source files change. Contract revision 4 requires a
compatible refresh for older active snapshots. Existing official history stays in
SQLite. Windows backups use SQLite's online backup API. Saved is separate
per-user application state.

A persistent-file refresh lock excludes concurrent refreshes. Windows locks byte 0
without appending a byte on every acquisition; Unix retains OS file locking.
Status is guarded in memory. Unique same-directory temp files are closed before
atomic replacement; bounded sharing-violation retries clean abandoned files where
possible. Permanent status persistence failure is nonfatal and cannot recursively
crash refresh error reporting or prevent a valid SQLite publication.

Current operation: [refresh and maintenance](../operations/refresh-and-maintenance.md).
Detailed original reviews are retained in the [archive](../archive/README.md).
