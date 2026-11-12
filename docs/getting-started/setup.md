# Install and run ThemeScope

Requires Python **3.12 or newer**, a modern browser, and internet access for first
setup. Live refresh also requires Alpaca historical SIP access. Node.js is only
needed for frontend helper checks or optional Wrangler publishing, not daily use.

## Windows

Install Python with the Windows Python launcher (`py`). Clone the repository or
extract a complete source ZIP, then open PowerShell in its root:

```powershell
.\setup.cmd
$env:APCA_API_KEY_ID = '<your local Alpaca key>'
$env:APCA_API_SECRET_KEY = '<your local Alpaca secret>'
.\ThemeScope.cmd
```

Setup creates `.venv-vnext/` and installs `requirements-vnext.txt`. The launcher
also bootstraps a missing environment. The browser opens **http://127.0.0.1:8766**;
select **Refresh Data**. `refresh.cmd` and `open-dashboard.cmd` open the same app;
they do not accept legacy CSV/session arguments. Stop the server with Ctrl+C in
its terminal before updating or switching modes. To choose another local port:

```powershell
.\ThemeScope.cmd --port 8767
```

The default binding is loopback only. Do not expose the private API publicly.

## Linux / macOS

From the repository root, using Python 3.12 or newer:

```sh
python3 scripts/bootstrap_dev.py
export APCA_API_KEY_ID='<your local Alpaca key>'
export APCA_API_SECRET_KEY='<your local Alpaca secret>'
.venv-vnext/bin/python scripts/run_vnext.py
```

If a server has no desktop browser, append `--no-browser` and open the loopback URL
in a local browser. These commands do not deploy a website.

## Credentials and SIP diagnostics

Keys are read from the **launching process environment**. The launcher does not
load an `.env` file. Set variables in the same shell used to launch ThemeScope, or
use your operating system's local environment management. Never paste keys into
issues, chat, screenshots or Git. `.env` and runtime directories are ignored, but
do not force-add them. Do not change trading permissions or invoke order endpoints.

Run the account diagnostic locally, with those environment variables set:

```powershell
.\.venv-vnext\Scripts\python.exe scripts\test_alpaca_access.py
```

On Unix use `.venv-vnext/bin/python scripts/test_alpaca_access.py`. It tests SIP
historical daily multi-symbol retrieval, usable raw volume, forced pagination,
split/spin-off adjustment and a safely delayed completed session. It prints only
sanitized diagnostics and exits nonzero on failure. If SIP is denied, stop live
refresh; there is no IEX substitution or automatic subscription action.

`ALPHAVANTAGE_API_KEY` optionally enables earnings dates. Missing/failed earnings
never block refresh or change qualification. When globally unavailable, earnings
controls are hidden. Available dates are shown only when supplied.

## Try without credentials

```powershell
.\ThemeScope.cmd --fixture
```

Or on Unix: `.venv-vnext/bin/python scripts/run_vnext.py --fixture`.
This uses fictional deterministic inputs and `runtime/vnext-fixture/`, separate
from live `runtime/vnext/`. A fixture result is never live chronological evidence.
Stop the fixture server before starting normal mode on the same port.

## Updates and troubleshooting

Stop the app, back up live/legacy history, then update your clean checkout with
`git pull --ff-only` on `main`. Preserve local edits and configuration deliberately;
do not reset or delete a database to fix an update. Rerun setup when dependencies
change. The snapshot publisher has a separate branch requirement documented in
[public operations](../operations/public-snapshots.md).

- No snapshot yet: run a successful refresh; an empty first-use page is not data loss.
- Refresh failed: check session/status and the sanitized error. The old dashboard
  may still be usable; that alone does not prove the refresh succeeded.
- Port occupied: stop the old instance or choose `--port`. Do not launch parallel
  live/fixture instances against the same port.
- Required symbol missing: review the diagnostic and approved configuration.
  Do not drop constituents or invent trading bars. See [terminal events](../architecture/terminal-actions.md).

See [refresh and backup](../operations/refresh-and-maintenance.md) for cache,
recovery, rosters and reviewed membership maintenance.

## Daily public update from main

For publication use a Git clone, not a plain ZIP. Select stable main explicitly
while the external default-branch change is pending:

```powershell
git switch main
$env:APCA_API_KEY_ID = '<your local Alpaca key>'
$env:APCA_API_SECRET_KEY = '<your local Alpaca secret>'
.\update-public.cmd
```

Closing that PowerShell session removes the temporary variables. One-time Wrangler
login and the existing Pages project's main production setting are prerequisites;
see [daily publication and manual fallback](../operations/public-snapshots.md).
The command never pulls updates or publishes from a dirty/experimental checkout.
