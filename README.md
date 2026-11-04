# ThemeScope (WIP): local CSV research dashboard

ThemeScope builds an offline end-of-day dashboard from five TradingView CSVs.
Daily refresh needs Python, with no API credentials, backend or scheduled service.
Market direction, priorities and weighted stock comparisons are research tools;
chart/entry assessment remains separate.

## Branches and consolidation status

**`main` is now the authoritative development branch.** The owner merged
[PR #5](https://github.com/suna-kabo/ThemeScope/pull/5) as `234c462` on 4 November
2026. This Daily Stock change builds on that merged audit; it does not restore an
old downloaded bundle. [Current scanner/schema details](docs/daily_stock_policy.md).

| Branch | Purpose |
|---|---|
| `main` | Normal development, setup and local updates. |
| `review/final-repository-audit` | Merged historical audit reference; not needed for daily use. |
| `download` | Older compatibility reference; not needed when using main. |
| `pages` | Optional separate publication worktree; update from main before any later authorized deployment. |

Other historical branches are retained, not deleted. The formerly local-only
`696e2d7` contained documentation, not missing runtime fixes; its useful trigger
history and corrected merge status are folded into these docs. Original unrelated
experimental/provider files remain preserved in their original checkout.

GitHub reports this repository as **public**, checked 4 November 2026. Do not
commit inputs, history, credentials or run bundles. Previously tracked bundles
remain accessible through old Git commits even after removal from the current
tree. Repository visibility and existing history were not changed by this audit.

## First-time Windows setup

Windows 10/11, PowerShell. Your PC has not been inspected. Install Git for Windows
and Python 3.12 if missing:

```powershell
winget install --id Git.Git --exact --source winget
winget install --id Python.Python.3.12 --exact --source winget
```

If `winget` is unavailable, use the official [Git](https://git-scm.com/download/win)
and [Python](https://www.python.org/downloads/windows/) installers, including the
`py` launcher. Reopen PowerShell, then:

```powershell
git --version
py -3.12 --version
Set-Location $env:USERPROFILE
git clone --branch main https://github.com/suna-kabo/ThemeScope.git ThemeScope
Set-Location .\ThemeScope
.\setup.cmd
```

If that destination already exists, inspect it instead of overwriting it. You
can alternatively download this branch's ZIP into a new folder and run
`setup.cmd` there. Git updates and Pages worktrees require a clone.

Setup creates `.venv` inside the project, installs hash-pinned `tzdata`, checks
imports/timezones and writes collection lists under `inputs\_lists`. No global
Python changes, PowerShell activation, Node or developer dependencies are needed.
Healthy existing environments need no reinstall. Setup never refreshes or deploys.
The `.cmd` launchers use their own folder and keep useful errors visible.

## Exact daily TradingView exports

Export after the selected **US market session closes**. For Daily Stock, keep
all other user-approved scanner settings and replace only the liquidity conditions:

- **Price × volume (turnover), 1 day ≥ $10,000,000**, in USD. Exactly $10M passes.
- **Average volume, 10 days > 500,000 shares per trading session**. Exactly 500,000 fails.

Both must pass. These thresholds are not claimed optimal or equivalent to the old
30-day proxy. Daily Stock may be filtered and omit configured stocks; membership,
stock # and ordinary TXT lists stay fixed. Export **all ETF anchors/context ETFs**
and **unfiltered SPY/QQQ/IWM constituent breadth CSVs**; do not apply these stock
liquidity conditions to those four exports.

| CSV role | Required universe | Simple filename |
|---|---|---|
| Stock | Configured-stock collection list `inputs\_lists\Daily_Data_Stocks.txt`, using the revised Daily Stock filters | `Daily_Stock.csv` |
| ETF | All anchors and SPY/QQQ/IWM from `inputs\_lists\Daily_ETFs.txt` | `Daily_ETF.csv` |
| SPY breadth | Full S&P 500 constituent export | `SPY.csv` |
| QQQ breadth | Full Nasdaq-100 constituent export | `QQQ.csv` |
| IWM breadth | Full Russell 2000 constituent export | `IWM.csv` |

Setup reports configuration-derived counts. The last three CSVs contain
constituent rows, not one ETF price row. Their access, constituent selection and
actual TradingView imports remain dependent on your platform/account; no account
credentials belong in chat or source files.

Use TradingView's native headers. Supported aliases are in
[manual_csv.py](src/themescope/manual_csv.py).

- Stock and ETF: `Symbol`, `Description`, `Price`, `Price change %, 1 day`,
  `Performance %, 1 week`, `Performance %, 1 month`, `Performance %, 3 months`,
  `Exchange`, `Exponential moving average, 21, 1 day`,
  `Exponential moving average, 50, 1 day`, `Average true range %, 14, 1 day`,
  `Price × volume (turnover), 1 day`, `Relative volume, 1 day`.
- Additional Stock fields: `Market capitalization`, `Industry`, `Sector`,
  **`Average volume, 10 days`**, in shares per trading session. The former
  `Price × average volume, 30 days` column is no longer required; it may be removed.
- Breadth CSVs: `Symbol`, `Price`, both daily EMA columns above.
- Optional: `Upcoming earnings date` as `YYYY-MM-DD`, currency and other recognized
  fields. Use USD quotes; no FX conversion is performed.

The native header **`Average volume, 10 days`** is confirmed in the supplied
`Daily_Stock_2026-11-04 (1).csv`. Matching is case-insensitive;
deliberate aliases are `Average Volume 10D` and
`average_volume_10d_shares`. Today's volume, relative volume, 30-day average volume
and dollar volume cannot substitute. A missing header reports this exact list.
Do not rename a different metric or derive shares from turnover/price.

One-day turnover is today's price × volume in USD. Average Volume 10D is shares,
not dollars. Blank/malformed/negative required values fail the import; numerical
zero is measured but fails the thresholds. An explicit non-USD turnover currency
is rejected, without conversion. An optional old 30-day value never affects the
new eligibility result. ETF thresholds and breadth input schemas are unchanged.

Percent values are normalized once. Duplicate symbols and malformed required
numbers fail validation. Missing market cap is N/A with an audit warning. Blank
numeric fields on unrelated ETFs do not enter required-anchor calculations.
Blank unused metrics on extra, unconfigured stock rows are also audited and
left unavailable without blocking configured stocks. Both liquidity fields stay
required on every stock row; configured stock metrics remain strictly validated.
Missing breadth Price/EMA values stay in the denominator and reduce coverage.
Sanity ranges check likely swapped/truncated breadth files; they do not prove
constituent identity, licensing or complete current-session observations.

## Input folder and selected session

Keep multiple dated folders. The folder name is the **US session**, even when
filenames use the next Hong Kong date. For example:

```text
ThemeScope\
  inputs\
    2026-11-02\
      Daily_Stock_2026-11-03.csv
      Daily_ETF_2026-11-03.csv
      SPY_2026-11-03.csv
      QQQ_2026-11-03.csv
      IWM_2026-11-03.csv
    2026-11-03\
      Daily_Stock.csv
      Daily_ETF.csv
      SPY.csv
      QQQ.csv
      IWM.csv
```

You explicitly select `--session`; a valid completed calendar session is required,
including holidays, early closes and DST. Undated filenames or dates matching the
US session/next calendar day are accepted. A Windows suffix such as `(1)` is
accepted only when exactly one file matches that role. Duplicates, missing roles,
wrong dates or an incomplete selected folder fail; no newest-file search,
cross-folder mixing or fallback occurs.

CSV filenames and hashes cannot prove quote freshness: these exports lack a
reliable session timestamp on every row. Confirm you exported after the declared
close. Byte-identical inputs from a previous successful session are rejected for
a forward refresh, including direct generator calls. Same-session and unchanged
older-session replays are explicit, separate operations.

Build success and data completeness are separate. `data_complete` now reports
whether all configured stock/anchor/context identities are present, with its
scope recorded alongside it. Missing stocks remain configured with N/A metrics.
This flag does not certify breadth constituent identity, source rights, row quote
timestamps, TradingView imports or longitudinal reliability.

## Daily refresh and local preview

Double-click `refresh.cmd` and enter the US session, or use:

```powershell
.\refresh.cmd --session 2026-11-02
.\open-dashboard.cmd
```

For another folder use `--input-dir inputs\2026-11-02`; relative paths resolve
from the project. Refresh validates and stages files before journaled publication
to `output\manual_csv`. Failure preserves the previous successful dashboard,
exports, dates and history. It never changes `site/`, pushes or deploys.

The preview console prints its **absolute directory, type, real session and exact
bound URL**. Use that URL, not another copy's old tab/bookmark. Dashboard preview
prefers port 8000, site preview 8001; a busy default selects a free bound port.
Explicit `--port 8002` is strict and fails if occupied. No arbitrary process is
killed and the browser opens only after a successful loopback-only bind.

Keep the console open; Ctrl+C stops that known preview. Reload after refresh.
No-cache responses and versioned URLs prevent stale conditional 304s and block
downloads from a newer run under an older tab until reload. No polling or automatic
external requests were added to the dashboard.

If dates disagree, compare console directory/type/session, exact browser URL and
metadata URL first. Generated dashboard, prepared site, running preview and an
older Cloudflare deployment can all differ. Exact cause of the previously reported
PC mismatch remains unconfirmed; old-copy serving and a legacy conditional-cache
failure were independently reproduced. Do not assume browser cache is the cause.

## History, backup and recovery

Persistent history lives in `output\manual_csv\local_history\YYYY-MM-DD.json`.
Keep the complete output folder between runs. Comparisons require the immediately
preceding US trading session and compatible identities/methodology. Missing or
incompatible history gives N/A; same-session reruns do not compare with themselves.
An older replay that would change evidence already used by later history is refused.

Before source updates, backup the complete local output and inputs outside the
repository. The local `.venv` and personal configuration stay in place:

```powershell
$themeScopeBackup = Join-Path $env:USERPROFILE ("ThemeScope-backup-" + (Get-Date -Format yyyyMMdd-HHmmss))
New-Item -ItemType Directory -Path $themeScopeBackup
foreach ($name in @('inputs','output','downloads','reports','site')) {
  if (Test-Path $name) { Copy-Item -Recurse $name $themeScopeBackup }
}
```

Recovery never invents history. If interrupted publication or locked files are
reported, stop active writers, close Excel/editors and run the affected command:

```powershell
.\refresh.cmd --recover
.\prepare-site.cmd --recover
```

These read no CSVs and select no new session. Do not delete pending journals or
backups. Retry the normal command after recovery. To restore history, copy a
genuine complete backup, not a test fixture or an assumed-complete old bundle.

| Error | Recovery |
|---|---|
| Git/Python missing | Install, reopen PowerShell and verify versions. |
| Broken `.venv` | Rename it as a backup, then rerun setup; do not delete local data. |
| Missing/duplicate/wrong-date CSV | Correct only the selected folder and retry. |
| Future, holiday or not-yet-closed session | Select the actual completed US session. |
| Reused input hash | Export fresh files, or explicitly select the same historical session. |
| Missing anchor, bad number/schema | Re-export; do not invent a replacement value. |
| Unavailable breadth/stock metrics | Check exported coverage; browser filters do not alter breadth/membership. |
| Malformed history | Preserve it and restore a genuine backup before retrying. |
| Legacy/modified/extra site artifacts | Back up the site; re-prepare with current source. Never force deployment. |

## Prepare and audit `site/` — no deployment

```powershell
.\prepare-site.cmd --session 2026-11-02
.\preview-site.cmd
```

The requested date must match the successful saved dashboard. The website is
freshly staged, sanitized, allowlisted and hash-validated. Failed preparation
preserves the preceding site. Only `site/` is a deployment artifact.

Its public purposes are defined in `public_artifact_purposes` in
[site_output.py](src/themescope/site_output.py): inline website; hosting headers;
font license; ranking/configured-stock CSV links; snapshot summary; complete
individual TXT downloads and their ZIP; All Stocks/All Themes collection TXT;
and the current grouped Primary TXT when available. `site_manifest.json` contains
asset checksums for validation, not internal ranking/history fingerprints.

Optional broad scans, Primary-filtered individual files/ZIPs, qualifying
relationships, run audits/bundles, raw CSVs, normalized inputs, review metadata,
absolute input paths and private history are excluded. Unlinked files are still
public, so the validator rejects extras even after checksums are regenerated.
Older site schemas must be re-prepared. Ordinary individual-watchlist contents
and complete collection universes are unchanged; **existing TradingView individual
watchlists do not require reimporting**.

The Daily Plan's **How this list is built** opens
`#methodology/primary-research-watchlist`, including when no download is available.
The guide uses the shared policy/weights; the complete Market Matrix groups all
64 input cases by Result, with Unclassified separate from Neutral.

## Safe Windows source updates

Stop previews/refresh/preparation and make the backup above first. The audit
removes tracked old bundles/reports from the source index; preserve any local
copies you want before switching branches. No Git history is rewritten.

Git users, with no uncommitted source/config edits:

```powershell
git status --short --branch
git fetch origin
git switch main
git pull --ff-only origin main
```

If source/config edits exist, stop and preserve/review them before updating.
Never reset hard, force-push or delete the project directory. Main is now the
authoritative merged branch. Review any new local/source conflicts rather than
discarding them; old branches are optional references, not required setup steps.

ZIP users: extract the reviewed branch ZIP into a separate temporary folder.
For an installation already on the merged PR #5 version, copy these program files to their
matching paths, plus this README and audit document:

- `scripts/generate_dashboard.py`, `scripts/refresh_local.py`,
  `scripts/prepare_site.py`, `scripts/serve_local.py`,
  `scripts/pages_build.py`, `scripts/stage_site.py`.
- `src/themescope/manual_csv.py`, `src/themescope/local_publication.py`,
  `src/themescope/site_output.py`, `src/themescope/tradingview.py`,
  **`src/themescope/daily_stock_policy.py` (new)** and `src/themescope/daily_lists.py`.
- `static/dashboard.js` and **`config/manual_csv.json`**. The latter changes the
  Daily Stock policy only. Preserve other configuration and all memberships.
  If you customized this file, merge the new `schema_version` and
  `daily_stock_policy` block instead of overwriting your other values.

Do not replace the entire folder, `.venv`, configuration, inputs, output/history
or personal files. Older installations must also carry forward their missing UI
updates; compare versions before copying. Then refresh the actual saved session,
prepare it separately, and open the intended preview's printed URL. Dependencies
are unchanged; rerun setup only for first use or an unhealthy environment.

## Cloudflare Pages: separate, deliberate publication

The earlier Workers integration attempted a source preview and failed because
Worker `themescope` did not exist in that account. The owner reports removing it
on 4 November 2026. No Worker or deployment was created by these scripts; verify
source changes have no external build checks before any later publication.
Cloudflare Pages account settings remain unverified. No hosting settings were
changed and no deployment command is part of this update. Webhook access is unavailable through
the current GitHub integration. Confirm production and preview branch behavior
before enabling publishing.

When you later authorize website publication, intended settings are:

| Setting | Intended value |
|---|---|
| Production branch | `pages` |
| Framework | None |
| Root directory | Repository root |
| Build command | `python scripts/pages_build.py` |
| Build output | `site` only |
| Build variable | `PYTHON_VERSION=3.12` |
| Preview branch deployments | Disabled, including `main` and `review/*` |
| Automatic deployment | Disabled until you deliberately enable it |
| API secrets | None for this static/manual workflow |

The build validates `site/` only. Without an explicitly committed site it creates
a known empty placeholder, never a snapshot from an archive or fixture. Even a
placeholder build is an external deployment if you connect/enable a hosting
project; these instructions do not authorize doing that now.

For a later publication, keep a separate `pages` worktree, update its validator
from the then-authoritative source branch, and resolve conflicts without
discarding work. `scripts/stage_site.py` verifies the same repository/branch,
locks both sites, and stages only validated files; it never commits or pushes.
The generated lock file is excluded from its cleanliness check, while other edits
still block staging. Review the dated output before any explicit site commit/push.
Source refresh/preparation never deploys. A branch name alone does not prove that
an external Git integration will not deploy it.

Official references: [Git integration](https://developers.cloudflare.com/pages/configuration/git-integration/),
[build configuration](https://developers.cloudflare.com/pages/configuration/build-configuration/),
[branch controls](https://developers.cloudflare.com/pages/configuration/branch-build-controls/).

Public source and a public website are separate exposures: website visitors can
read every deployed file, linked or not. A private source repository would not
make published quote data private. Changing repository visibility or removing old
data from Git history requires a separate deliberate action; no such change is
silently made here.

## Historical Daily Stock CSV compatibility

New imports default to `--stock-csv-schema current-v2`, which requires Average
Volume 10D. Old CSVs are never inferred to pass. For a deliberate historical
replay with the old 30-day field, use:

```powershell
.\refresh.cmd --session 2026-11-02 --stock-csv-schema legacy-v1
```

This is labelled `daily-stock-csv-1` with `legacy_unverified` stock eligibility.
Prices/performance can be shown; Primary themes still contribute anchors, but
unverified legacy stocks cannot enter a new-policy Primary export. Historical
HTML and genuine history remain readable; a new site must be prepared from an
explicitly refreshed, versioned run. Theme Score/rank/EMA-priority history remains
compatible because stock liquidity versioning is separate.

Current Primary stock inclusion requires verified Daily Stock eligibility **and**
the existing weighted relative result (long > 0; short < 0; zero/missing excluded).
The visible vs ETF filter still uses the weighted result alone, including for
measured ineligible rows. Present valid EMA rows still enter theme breadth even
if liquidity fails; missing members remain in the full configured coverage
denominator. No missing stock's filter-exclusion cause is inferred or old data reused.

## Developer checks and legacy diagnostics

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
node --check static/dashboard.js
node tests/test_dashboard.js
```

Developer browser tests additionally need `requirements-dev.txt` and Playwright
Chromium; Node and Playwright are not daily runtime dependencies. CI covers a
clean two-session manual build, actual HTTP previews/downloads, history/failure
preservation, browser navigation and light/dark layouts, plus native Windows CMD.
CI success does not mean your PC or actual TradingView import was tested.

`generate_dashboard.py` defaults to manual CSV and never silently collects.
`--import-run` remains an explicit offline historical diagnostic used by retained
tests/fixtures. Legacy provider collectors/cache tools remain isolated for those
diagnostics and maintenance dependencies. Live collection requires both
`--source live --legacy-live`, is unsupported for daily use, and was not run in
this audit. No methodology, memberships, anchors or symbol mappings were changed.
