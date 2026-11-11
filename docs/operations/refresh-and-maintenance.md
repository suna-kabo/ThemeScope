# Refresh, backup and maintenance

## Daily refresh

Run the private loopback application and select **Refresh Data**. It chooses the
latest US session closed at least 20 minutes ago using the versioned calendar;
there is no intraday mode or daily CSV upload. First refresh seeds the required
history. Warm refresh retrieves missing/new completed sessions, a bounded repair
window and adjustment anchors. See [provider/cache design](../architecture/provider-and-storage.md).

Provider completeness, effective membership/rosters and calculation validation
precede one atomic SQLite publication. The dashboard and TXT routes read one
committed snapshot. Failure leaves the prior successful snapshot available; an
older replay cannot replace a newer publication. Check `state`, target session and
last successful session rather than assuming an opening dashboard proves success.

The process/thread refresh lock excludes competing refreshes. Auxiliary status
metadata is authoritative in memory and best-effort on disk; status-file failure
does not abort snapshot publication. An interrupted process can recover useful
persisted status; it does not turn partial calculations into a successful snapshot.
Missing earnings never block market refresh.

## Private storage and backups

Live storage: `runtime/vnext/runtime.sqlite`; fictional mode:
`runtime/vnext-fixture/runtime.sqlite`. Keep them separate. With the app **stopped**,
back up `runtime/vnext/` together with the corresponding versioned configuration.
Preserve legacy `output/manual_csv/local_history` independently. Runtime, outputs,
keys and `.env` files do not belong in Git or public static output.

Update source without resetting local edits, deleting databases or replacing genuine
history with fixtures. Storage migration is transactional. Sustained lock, corruption
or provider errors are reported; do not bypass validation to make a refresh green.
Known older provider corrections may need an explicit full repair through the cache
integration; there is no daily CLI repair shortcut. Preserve prior observation versions.

## SPY and QQQ rosters

The effective-dated ledger is [rosters.json](../../config/market_universes/rosters.json).
The initial user-approved TradingView exports are separate SPY 501 / QQQ 101
universes, effective **2026-11-05**. Only `Symbol` was imported; all scanner
prices, EMA, returns, volume, earnings and cap columns were ignored. Dotted symbols
such as `BF.B` and `BRK.B` are retained. No fixed arbitrary constituent count is imposed.

Import reviewed changes deliberately, separately per benchmark, for example:

```powershell
.\.venv-vnext\Scripts\python.exe scripts\import_market_roster.py --benchmark SPY --effective-from YYYY-MM-DD --source "Approved source description" --csv C:\path\to\SPY.csv --symbol-column Symbol
```

`YYYY-MM-DD` and the file/source are placeholders for an approved change, not a
request to overwrite the initial snapshot. The importer rejects blank/invalid or
duplicate symbols. Review the resulting ledger diff before committing it.
Validate compatibility locally with the existing SIP adapter:

```powershell
.\.venv-vnext\Scripts\python.exe scripts\check_roster_symbols.py --roster-date 2026-11-05 --session 2026-11-05
```

For later rosters use their explicitly approved date/session. Missing/unusable
symbols must be reported, never dropped silently. Missing either effective SPY or
QQQ roster blocks theme activation/Directional outputs. Staleness is advisory only;
IWM never needs a roster. No automatic constituent scraper exists.

## Membership and corporate actions

Membership reviews are quarterly/ad hoc, explicitly approved and effective-dated.
Daily liquidity does not add/delete memberships. Configuration and source/evidence
records live in `config/vnext/`; review tools are developer/maintenance tools, not
normal startup. Do not rewrite earned history or reactivate terminated holdings.
Unknown missing bars fail closed. Only deliberately approved
[terminal corporate actions](../architecture/terminal-actions.md) may supply
existing-holding values; they never create OHLCV or liquidity.

## Current release status

[Gate E is CLOSED](gate-e-closure.md): real Nov 6, Nov 9 and Nov 10 passed per the
user. Ordinary future refresh failures remain real failures; closure is not a waiver
of completeness, account access or methodology. Publishing remains a separate
explicit [public snapshot workflow](public-snapshots.md).
