> **Historical checkpoint.** Status, counts and instructions below describe that
> checkpoint, not current operation. Gate E is now **CLOSED**; Nov 6, Nov 9 and
> Nov 10 live validation passed per the user. See the [closure record](operations/gate-e-closure.md)
> and [current documentation](README.md).

> Historical gate report. Launch/evidence status below describes that gate.
> Current approved activation and Phase 9: [vnext_launch.md](archive/migration/vnext_launch.md).

# Gate C — provider and incremental cache

Phase 5 extends approved Gate B 0c0cff5. Phase 6 has not started.

## Interface and requests

MarketDataProvider returns Batch(identity, typed bars, page count), provides latest
completed session identification and an explicit health check. FixtureProvider
uses deterministic in-memory observations. The Alpaca adapter uses only GET
https://data.alpaca.markets/v2/stocks/bars with explicit feed=sip, timeframe=1Day,
adjustment=split,spin-off, ascending order and pagination through every token.
A paired adjustment=raw SIP request supplies actual close and traded volume for
liquidity; adjusted volumes are never used for liquidity. Both observation sets
must match. The provider has no theme, membership or scoring formulas.

The versioned US exchange schedule supplies closes (including half days and DST).
A target must be closed plus 20 minutes; request end is also capped at now minus
20 minutes. NY-local session dates are decoded from timestamps. Auth 401, SIP 403
and request/subscription 422 are permanent failures. Only 429 and transient
500/502/503/504 or transport failures retry, with bounded backoff and Retry-After.
Diagnostic codes omit headers, request objects and response bodies. Malformed,
duplicate or inconsistent observations and repeated page tokens fail explicitly.
The cache/publication boundary requires fresh positive-volume target bars for
every required symbol. Missing history stays missing and never compresses dates.

## SQLite migration and cache

Schema 2 migrates schema 1 transactionally, retaining publications and every run's
input references. Old source provenance is explicitly unknown, never guessed as
Alpaca. Tables added: observations (immutable content-addressed payload/version,
provider identity, ticker, session and observation time) and bar_cache (latest
observation pointer per provider/ticker/session). daily_bars now holds run/input
references instead of repeated payloads. Identical observations deduplicate across
runs. Changed data creates a new version; earlier runs remain pinned to old versions.

Cold seed fetches the supplied required lookback. Warm plans group missing/new
sessions and the explicit repair window (default two completed sessions) into
multi-symbol requests. A historical anchor is fetched for each warm ticker; any
anchor revision triggers a full retained-lookback reseed of that ticker. This
prevents mixing old split/spin-off adjustments with newly adjusted observations.
A changed anchor with an incomplete reseed fails closed. Explicit full_repair=True
handles known older corrections that do not affect the adjustment anchor. Arbitrary
provider corrections outside the window cannot be discovered without a full scan;
operators must request full repair when such a correction is identified. No
optimization changes the calculation formulas or required observation endpoints.

Network fetches occur before the SQLite writer lock. Prepared immutable values are
then inserted/pinned in the same transaction as snapshot publication. A failed
publication rolls back cache pointers, observations and snapshot updates together.
Older replay cannot replace a newer active session, and previous runs retain their
original input versions even after a repair. Cached target bars cannot mask a new
response missing that symbol's target. Production refresh UI wiring remains a later
gate; publish_prepared is the tested storage integration boundary.

Warm transfer is proportional to missing/repair sessions plus one anchor per
symbol, rather than 252 sessions per symbol every day. Typical complete-universe
warm refresh uses two batched ranges, each with raw and adjusted requests and any
required pages. Payload storage grows only for new/revised observations; run audit
references still grow per run. Architecture supports the under-10-minute hard
limit and under-5-minute goal, but actual SIP throughput requires local measurement.
No cloud timing claim substitutes for real account validation.

## Run the real SIP PoC locally

From the downloaded repository root, first install the isolated vNext runtime:

```powershell
python scripts/bootstrap_dev.py
.\.venv-vnext\Scripts\python.exe scripts/test_alpaca_access.py
```

Set APCA_API_KEY_ID and APCA_API_SECRET_KEY in that local process environment using
your Alpaca account credentials. The script does not read or write credential files.
An optional --session YYYY-MM-DD selects a specific safely completed US session;
omitting it uses the latest close plus the safety delay from the repository calendar.

The PoC requests AAPL, MSFT and JPM; limit=1 forces pagination. Success requires
positive raw volume for all three target bars, matched adjusted/raw observations,
and more than two pages. It prints only safe status/session/count/request-semantics
diagnostics and exits zero. Any missing credential, access failure, malformed data,
unproven pagination or incomplete volume exits nonzero. Run only on your local
machine with your actual account. Cloud tests use injected transports and fixtures.

If the account rejects historical SIP, live-provider cutover is blocked. There is
no IEX fallback and no subscription action. Real SIP success is pending at Gate C.
All pending launch dates/evidence, Phase 6 SPY/QQQ rosters, Windows validation,
legacy runtime, main and deployment restrictions are preserved.
