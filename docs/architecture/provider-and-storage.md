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

401/403/422 fail permanently; 429, supported transient server/transport errors retry
with finite backoff/Retry-After. Malformed, duplicate/inconsistent bars or repeated
page tokens fail closed. Sanitized diagnostics contain codes/symbols, not headers,
credentials or raw responses. Required target inputs must be complete before publication.
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

Network retrieval precedes the writer lock. Insertion of observations/cache pointers,
run inputs, calculation results, corporate-action proof and the publication pointer
commits in one transaction. Any failure rolls back the new publication; older replay
cannot replace a newer active session. Prior successful data/exports remain usable.
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

A persistent-file refresh lock excludes concurrent refreshes. Windows locks byte 0
without appending a byte on every acquisition; Unix retains OS file locking.
Status is guarded in memory. Unique same-directory temp files are closed before
atomic replacement; bounded sharing-violation retries clean abandoned files where
possible. Permanent status persistence failure is nonfatal and cannot recursively
crash refresh error reporting or prevent a valid SQLite publication.

Current operation: [refresh and maintenance](../operations/refresh-and-maintenance.md).
Detailed original reviews are retained in the [archive](../archive/README.md).
