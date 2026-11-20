# Refresh, backup and maintenance

## Daily refresh

Launch **ThemeScope.cmd**. The app checks the versioned US calendar for a session
that closed at least 20 minutes ago and starts one automatic attempt when a newer
snapshot is due. Launching again does not repeat a failed attempt for the same
session. Open **Snapshot and refresh → Refresh Data** to retry, apply reviewed
configuration changes, or deliberately recalculate the current session.

First refresh seeds the required history. Warm refresh retrieves missing completed
sessions, a bounded repair window, and adjustment anchors. The refresh lock
excludes competing writes. A successful refresh commits provider inputs, research,
and the active snapshot pointer in one transaction. The browser keeps the previous
snapshot and downloads usable during refresh. Failure leaves those results intact.
Optional earnings failures do not block research.

## Backup and restore

Double-click **backup-data.cmd**. The command prints the timestamped SQLite backup
path under `%LOCALAPPDATA%\ThemeScope\Backups\`. You can run it while ThemeScope is
open. It uses SQLite's online backup operation and checks the resulting database.
The backup contains the research database. Saved bookmarks and provider credentials
live separately under the per-user application-data directory. Keep reviewed
configuration in version control alongside its matching research history.

To restore deliberately, stop every ThemeScope server and maintenance command
using this workspace. Move the existing `runtime/vnext/runtime.sqlite` and any
matching `-wal` and `-shm` files together to a separate recovery folder. Copy the
chosen backup to `runtime/vnext/runtime.sqlite` and reopen ThemeScope. Retain the
recovery folder until you've checked the session and history. The current
configuration is checked on startup and may require a refresh. The backup command
never restores or overwrites live data.

Fixture data uses a separate database under `runtime/vnext-fixture/`. See the
[storage design](../architecture/provider-and-storage.md).

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
