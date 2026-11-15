# ThemeScope

ThemeScope is a local, private, end-of-day US equity research dashboard:
**Market Bias → Theme Changes → Primary Research**. It ranks custom equity
themes and organizes eligible stocks for chart review. It does not execute trades.

## Windows setup and launch

Install Python 3.12+ with the Windows Python launcher, then clone this repository.
In PowerShell from the repository folder:

```powershell
.\setup.cmd
$env:APCA_API_KEY_ID = '<your local Alpaca key>'
$env:APCA_API_SECRET_KEY = '<your local Alpaca secret>'
.\ThemeScope.cmd
```

Open **http://127.0.0.1:8766**. Under **Snapshot and refresh**, select **Refresh
Data**. ThemeScope selects the latest safely completed US session, retrieves
Alpaca historical SIP data, and atomically saves the snapshot and exports.
A failed refresh preserves the previous successful snapshot. No daily CSV uploads
are required. Optional `ALPHAVANTAGE_API_KEY` supplies earnings dates.

Keep credentials in the launching process environment. Historical SIP access is
required; there is no IEX fallback. To explore fictional data in separate storage:

```powershell
.\ThemeScope.cmd --fixture
```

Market explains SPY/QQQ bias with IWM context. Themes compares strength and
five-session changes. Primary includes every eligible Core/Enabler member of
researchable themes; peer strength orders stocks without filtering by sign.
Inspect themes/stocks, keep browser-local Saved research, and download full-session
TradingView TXT lists independently of visible filters.

## Public snapshots

After one-time Wrangler authentication and configuration of the existing Cloudflare
Pages project, run from a clean, up-to-date `main` checkout with the same provider
variables set:

```powershell
.\update-public.cmd
```

The helper refreshes locally, validates the exact completed session and uploads a
frozen static site. Success requires **Refresh PASS**, **Completeness PASS** and
**Public deployment CONFIRMED**. Public mode has no refresh or provider requests;
Saved remains browser-local. The local SQLite history stays private.

[Setup and troubleshooting](docs/getting-started/setup.md) ?
[Research workflow](docs/getting-started/research-workflow.md) ?
[Methodology](docs/methodology/research-v2.md) ?
[Refresh and backups](docs/operations/refresh-and-maintenance.md) ?
[Publication and manual fallback](docs/operations/public-snapshots.md) ?
[Development](docs/development/README.md) → [All documentation](docs/README.md)
