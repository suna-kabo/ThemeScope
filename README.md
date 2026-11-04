# ThemeScope: local CSV refresh and optional Cloudflare Pages

ThemeScope is an offline end-of-day research dashboard. **Use branch `download`, not the older `main`.** Daily use needs Python and five TradingView CSVs. It needs no market-data API, credentials, Node, database, backend or scheduler. The Cloudflare deployment branch is `pages`; publishing is a separate, deliberate operation.

## First-time Windows setup

These commands are for Windows 10/11 in **PowerShell**. Software on your PC has not been inspected. Install **Git for Windows** and **Python 3.12** first:

```powershell
winget install --id Git.Git --exact --source winget
winget install --id Python.Python.3.12 --exact --source winget
```

If `winget` is unavailable, use the official [Git Windows installer](https://git-scm.com/downloads/win) and [Python 3.12 Windows installer](https://www.python.org/downloads/release/python-31210/). Include the Python launcher (`py`) and Git command-line tools. Close and reopen PowerShell after installation, then verify:

```powershell
git --version
py -3.12 --version
Set-Location $env:USERPROFILE
git clone --branch download https://github.com/suna-kabo/ThemeScope.git ThemeScope
Set-Location .\ThemeScope
.\setup.cmd
```

The repository is private: sign into GitHub through Git's browser/credential-manager prompt. Never paste credentials into chat or files in the repository. If `ThemeScope` already exists, stop and inspect it rather than overwriting it. An alternative is GitHub's **download branch → Code → Download ZIP**; extract it, open that folder, and run `setup.cmd`. Git updates and Pages staging require a clone.

Setup creates **`.venv` inside this folder**, installs the pinned, hash-checked `tzdata` package required for Windows timezone support, verifies the actual manual-CSV imports, and creates collection lists. Everything else in the daily Python path uses the standard library. No PowerShell activation or execution-policy change is needed. Setup can be rerun; it does not erase an existing environment, collect data, refresh a dashboard or publish anything.

The `.cmd` launchers work from another working directory and keep their console open after an error. You may double-click them. `refresh.cmd` and `prepare-site.cmd` ask for the US session when no arguments are supplied.

## Exact daily TradingView CSV exports

Export **after the intended US trading session closes**, using daily EMA/ATR/volume fields. Export the complete requested universe, without performance, turnover, price or market-cap screener filters. The code joins the fixed memberships; it does not rebuild them from that day's screen.

| Role | TradingView universe | Simple filename |
|---|---|---|
| Stock | Every fixed configured stock from `inputs\_lists\Daily_Data_Stocks.txt` | `Daily_Stock.csv` |
| ETF | Every anchor plus SPY, QQQ and IWM from `inputs\_lists\Daily_ETFs.txt` | `Daily_ETF.csv` |
| SPY breadth | Full S&P 500 constituent universe | `SPY.csv` |
| QQQ breadth | Full Nasdaq-100 constituent universe | `QQQ.csv` |
| IWM context breadth | Full Russell 2000 constituent universe | `IWM.csv` |

Setup currently exports 563 unique stock identities and 56 ETFs/benchmarks, derived from configuration. Import those two TXT collection lists into TradingView to select the required instruments. They contain symbols, not prices. The three breadth CSVs contain **constituent rows**, not one ETF row; an IWM price row or an arbitrary small-cap screen cannot replace Russell 2000 breadth. Your TradingView account must allow the relevant universe/CSV exports. The account UI and constituent selection were not tested here; existing supplied files were used for end-to-end validation.

Required exported **column headers** (header aliases are in `src/themescope/manual_csv.py`; extra columns are allowed):

- **Stock and ETF:** `Symbol`, `Description`, `Price`, `Price change %, 1 day`, `Performance %, 1 week`, `Performance %, 1 month`, `Performance %, 3 months`, `Exchange`, `Exponential moving average, 21, 1 day`, `Exponential moving average, 50, 1 day`, `Average true range %, 14, 1 day`, `Price × volume (turnover), 1 day`, `Relative volume, 1 day`.
- **Additional Stock fields:** `Market capitalization`, `Industry`, `Sector`, `Price × average volume, 30 days`.
- **Each breadth CSV:** `Symbol`, `Price`, `Exponential moving average, 21, 1 day`, `Exponential moving average, 50, 1 day`.
- **Optional:** `Upcoming earnings date` (ISO `YYYY-MM-DD` expected dates; blank means unavailable), currency and other recognized fields. Use USD quotes for the configured US instruments; no FX conversion is performed.

Keep TradingView's native CSV headers and numeric values. Percent values are parsed as percentage units and normalized once. Duplicate symbols and malformed numbers are rejected. Stock and required-anchor numeric cells must be valid; Market Cap can be unavailable with a warning. Blank numeric cells on unrelated ETFs in a broader ETF file are audited but do not enter calculations. Breadth rows with blank Price/EMA stay in the denominator, reducing coverage. Current sanity ranges are 350–700 SPY rows, 70–150 QQQ rows and 1,000–3,000 Russell 2000 rows; these checks do not prove constituent identity or licensing.

## Input folder and session date

Make a **new folder for the US session**, not the Hong Kong export date. For the supplied 3 November Hong Kong exports, the US session is 2 November:

```powershell
Set-Location "$env:USERPROFILE\ThemeScope"
New-Item -ItemType Directory -Force .\inputs\2026-11-02
```

Put exactly these five files into it; either naming style below works:

```text
C:\Users\Alice\ThemeScope\inputs\2026-11-02\
    Daily_Stock_2026-11-03.csv
    Daily_ETF_2026-11-03.csv
    SPY_2026-11-03.csv
    QQQ_2026-11-03.csv
    IWM_2026-11-03.csv
```

`Alice` is a folder example, not text to put into commands. Undated `Daily_Stock.csv`, `Daily_ETF.csv`, `SPY.csv`, `QQQ.csv`, `IWM.csv` are also accepted. One Windows download suffix such as `(1)` is accepted if it is the only matching export. **Two matching files for a role cause an error; the script never chooses whichever is newest.** Dated names must agree with the US date or the next calendar day. The folder date must match `--session`.

You explicitly select `--session`. The wrapper checks the versioned US calendar, holidays, actual close times and DST, and rejects a session that has not closed. It never infers the session from the filename or silently advances it to today's date. CSVs generally lack quote timestamps: the program cannot independently certify when every row was exported. Export fresh files after the declared close. Reusing byte-identical inputs from the previous successful session is rejected; rerunning the same explicitly declared session is allowed.

## Daily refresh

From PowerShell in the repository:

```powershell
.\refresh.cmd --session 2026-11-02
```

For a later day, create that US session's folder, export all five fresh files, and supply that session date. Double-clicking `refresh.cmd` prompts for it. A specific input folder is optional; relative paths are always resolved from the repository:

```powershell
.\refresh.cmd --session 2026-11-02 --input-dir inputs\2026-11-02
```

The launcher uses the existing manual-CSV generator, equivalent to:

```powershell
.\.venv\Scripts\python.exe .\scripts\generate_dashboard.py --source tradingview-csv --as-of 2026-11-02 --stock-csv .\inputs\2026-11-02\Daily_Stock_2026-11-03.csv --etf-csv .\inputs\2026-11-02\Daily_ETF_2026-11-03.csv --spy-csv .\inputs\2026-11-02\SPY_2026-11-03.csv --qqq-csv .\inputs\2026-11-02\QQQ_2026-11-03.csv --iwm-csv .\inputs\2026-11-02\IWM_2026-11-03.csv --output-dir output\manual_csv
```

Use the launcher for the additional date/folder/stale-file checks. The lower-level command is shown to make the real entry point explicit. **Do not run the legacy generator without `--source tradingview-csv`; its default is an older collection path, not this setup.**

Validation and calculation happen before staged publication. Failed imports preserve the last successful HTML, real dates and history. A failure may create `output\manual_csv\failed_attempt_audit.json` locally; it is not a new successful run. Refresh never changes `site/`, runs Git, pushes or deploys.

## Opening and checking the dashboard

```powershell
.\open-dashboard.cmd
```

Double-click **open-dashboard.cmd** after refresh. Its console prints the absolute folder, preview type, real US session, generation time, HTML fingerprint and **exact URL**. Use that URL; do not reuse a tab/bookmark from another downloaded copy. The server binds **127.0.0.1 only**, normally on port 8000 for dashboard output. It selects an available port if the default is busy and opens the browser only after binding succeeds. Leave the console open; Ctrl+C stops that preview.

Double-click **preview-site.cmd** only after preparing the desired session. Prepared-site preview normally uses **8001**, so it can coexist with dashboard preview. Both defaults can select another free port; the printed URL is authoritative. Explicit `--port` remains strict: an occupied requested port fails clearly, opens no browser and stops no process. For a chosen alternative use `.\open-dashboard.cmd --port 8002` or `.\preview-site.cmd --port 8003`.

Preview HTML and metadata use no-store/no-cache responses, and preview does not return a stale 304 after regeneration. URLs include the project-copy identity and a versioned static-file prefix. Reloading an old HTML URL redirects to the current completed version. An old tab's download links return a clear reload message instead of downloading files from a newer run under an older date. No polling or automatic requests were added to the exported dashboard.

If preview shows the wrong date: compare **Serving directory**, **Actual snapshot session**, **Exact URL**, and **Latest metadata URL** in the intended console. Check whether you launched dashboard output or prepared site. Close only the known old preview console with Ctrl+C, then launch from the intended project folder and use its newly printed URL. Clearing cache is not the first diagnostic step. Refresh/preparation may run while preview stays open; reload after success. Requests during publication return a temporary-unavailable response, never staging/mixed files. Moving a project or updating from a ZIP requires stopping active refresh/preparation operations first; relaunch preview from its new folder afterward. Launchers work from another working directory and with spaces/Unicode in the project path.

The local folder contains private audits, input metadata, normalized raw payloads and a run ZIP. Do not publish that folder. Expected earnings dates remain unverified. Primary long, Watch and Primary short are research priorities, not entry signals. Missing daily rows do not remove configured stocks. Full individual watchlists contain configured memberships. Daily Primary downloads are filtered research lists that change each session; complete stock/ETF collection lists remain separate.

## Common errors and recovery

| Error | What to do |
|---|---|
| `py`, `python` or `git` not found | Install the software above; reopen PowerShell and verify versions. |
| Missing/incomplete `.venv` or timezone error | Run `setup.cmd`. If an existing environment is invalid, rename `.venv` as a backup first; setup never deletes it automatically. |
| Setup cannot download `tzdata` | Check your internet/proxy access and retry setup. Daily refresh itself does not need network access. |
| Missing role, duplicate file or wrong filename date | Correct the five-file folder; remove obsolete duplicates from that folder. No cached file will be selected. |
| Weekend, holiday, future or not-yet-closed session | Use the US session you actually exported after close, not the next Hong Kong calendar date. |
| Input identical to previous session | Re-export that universe. If this really is the same historical session, explicitly rerun that date. |
| Missing columns, malformed values or missing anchor | Export the listed fields/instruments again. Do not fill a missing value with invented data. |
| Breadth unavailable or missing stock rows | Check exported universe/coverage; use complete collection lists without screener filters. Existing minimum-eight/80% rules still apply. |
| Existing same-session history is malformed | Back up the entire output folder, inspect the reported record, and restore the genuine backup; never invent prior ranks. |
| Site validation finds extra/modified files | Do not force a build. Move the edited site aside as a backup, inspect it, then prepare a clean site. |

An error leaves the previous success intact. Its older **Data through** date remains real; success is not inferred from the fact that an HTML file exists.

## History storage and backup

Daily rank history lives at **`output\manual_csv\local_history\YYYY-MM-DD.json`**, locally and outside Git. Always reuse `output\manual_csv`. Matching methodology, anchors and eligible universe plus the immediately preceding US session are required for comparisons. A first run or a missing/incompatible prior session shows N/A; same-session reruns replace that date only.

Back up the complete private output folder outside the repository before moving PCs, replacing a checkout or repairing history:

```powershell
Copy-Item -Recurse .\output\manual_csv (Join-Path $env:USERPROFILE ("ThemeScope-backup-" + (Get-Date -Format yyyyMMdd-HHmmss)))
```

To restore history, copy the genuine backup's `local_history` folder into `output\manual_csv\local_history` before refreshing. A downloaded older private run bundle may contain real history, but do not assume it includes every prior session. Never replace history with test fixtures. Cloudflare is **not** the history store: it receives only already computed display values, including the visible Δ Rank and comparison date, not internal history records/fingerprints or raw inputs. A Pages build does not calculate or retain local history.

## Updating local source from GitHub safely

From the `download` checkout:

```powershell
git status --short
git fetch origin
git log --oneline HEAD..origin/download
git pull --ff-only origin download
.\setup.cmd
```

If `git status` lists changes to source/config, stop and back them up or commit your intentional edits before pulling. Do not use `reset --hard`, force-push or delete the folder. A non-fast-forward error needs review, not a forced update. Inputs, outputs, `.venv`, caches and prepared `site/` are ignored. Existing legacy bundles/audit documents already tracked by the private repository remain historical; they are never selected as Pages assets. Do not use `git add .` to publish.

## Prepare `site/` separately — no deployment

After a successful refresh:

```powershell
.\prepare-site.cmd --session 2026-11-02
.\preview-site.cmd
```

Prepared-site preview uses the exact URL printed by `preview-site.cmd`, normally on port 8001 (or an automatically selected free port). Only **`site/`** is deployable. It contains `index.html` with inline code/fonts and a sanitized display payload, the intended CSV/TXT downloads and individual-watchlist ZIP, font license, public snapshot summary, headers and a hashed file manifest. It does **not** contain the whole repository, private run ZIP, raw CSVs/normalized inputs, audits, configuration review evidence, absolute input paths or internal history files. CSVs are regenerated from the same sanitized payload; TXT contents are checked against configured identities.

Preparation requires the saved session to match explicitly; it cannot relabel an old dashboard. A staged/validated, journaled publication preserves the previous site on failure and refuses to discard unrecognized edits. Neither preparation nor preview performs a Git commit, push or Cloudflare operation. `site/` is ignored in the source checkout to prevent accidental publishing.

## Cloudflare Pages Git integration (when you choose to deploy)

No Cloudflare project, domain or deployment is created by these scripts. When ready, connect the **private** `suna-kabo/ThemeScope` repository using Cloudflare Pages' GitHub integration and grant access only as needed. Use these exact settings:

| Setting | Value |
|---|---|
| Production branch | **`pages`** |
| Framework preset | **None** |
| Root directory | Repository root (leave blank) |
| Build command | **`python scripts/pages_build.py`** |
| Build output directory | **`site`** |
| Build environment variable | **`PYTHON_VERSION=3.12`** |
| Preview branch deployments | **None / disabled** (default all-branch previews would publish other branches) |
| Production automatic deployment | Leave disabled while preparing; enable only when you intend `pages` pushes to publish |
| Secrets/API keys | None for this static/manual workflow |

The `pages` branch is prepared with source and **no committed market site**. A fresh checkout's build creates an empty placeholder if no `site/` was explicitly committed. It never opens an old download ZIP or looks for CSVs. Once a dated site is committed, the build validates its file hashes/allowlist and uploads only `site/`. Unexpected/private artifacts make it fail. Even connecting a new Pages project can deploy its placeholder; **do not create/connect/save a deployment now if you want no public deployment yet**.

The public data workflow below is for a later, deliberate deployment; **do not run the commit/push steps until you intend the snapshot to be hosted**. Keep source and Pages worktrees separate. First time only, from the source checkout:

```powershell
git fetch origin
git worktree add --track -b pages ..\ThemeScope-pages origin/pages
```

After preparing and reviewing `site/`, stage it in the separate worktree:

```powershell
.\.venv\Scripts\python.exe .\scripts\stage_site.py ..\ThemeScope-pages
git -C ..\ThemeScope-pages add -f -- site
git -C ..\ThemeScope-pages diff --cached --stat
```

`stage_site.py` checks that this is a clean `pages` worktree of the same repository and copies only the validated website. It does not commit or push. Review the session/data/downloads first. When you explicitly want publication:

```powershell
git -C ..\ThemeScope-pages commit -m "Publish reviewed ThemeScope snapshot"
git -C ..\ThemeScope-pages push origin pages
```

For subsequent publication, first ensure the Pages worktree is clean, then `git -C ..\ThemeScope-pages pull --ff-only origin pages`. After source updates, fetch and run `git -C ..\ThemeScope-pages merge --no-edit origin/download` in the deployment worktree before staging, so its validator/template source is current. Resolve any conflict without discarding work. Refresh and site preparation alone never publish. Source-only pushes to `download` do not deploy when previews are disabled and production is `pages`.

Official references: [Pages Git integration](https://developers.cloudflare.com/pages/configuration/git-integration/), [build configuration](https://developers.cloudflare.com/pages/configuration/build-configuration/), [branch controls](https://developers.cloudflare.com/pages/configuration/branch-build-controls/). Settings/build behavior were prepared and tested locally; your Cloudflare account integration, permissions and actual deployment remain untested.

## Code privacy versus website data

A private GitHub repository hides its source from unauthenticated GitHub visitors; Cloudflare's authorized build still reads the repository. A normal Pages website is publicly accessible. Visitors can read its inline HTML/JavaScript/data and download every deployed asset, including visible prices, ranks, configured memberships and CSVs. Private Git does **not** make website data private. The sanitizer removes internal artifacts, not the financial information the dashboard intentionally displays. Decide whether that public access is intended before enabling deployment; no authentication or access-protection system is added here.

## Methodology and developer checks

Score remains **60% Current (1M ascending average-rank percentile) + 40% Medium (3M)**. Equal observations receive average ranks, using the same eligible ETF universe for both components; the all-equal fallback is 50. Raw returns never replace these percentiles. Score measures relative ETF momentum, not absolute direction or readiness. Fixed weights and the boundary of 50 live in `src/themescope/research_policy.py` and generate the on-screen methodology.

Market uses valid same-session SPY/QQQ Price versus daily EMA21/EMA50: above both is Bullish, below both Bearish, otherwise Mixed (including equality); missing/invalid inputs are unavailable. Unanimous Bullish means Long bias and unanimous Bearish means Short bias, regardless of breadth. Otherwise: Bullish+Mixed permits only Selective long on Positive consensus; Bearish+Mixed permits only Selective short on Negative consensus. Opposed prices or both Mixed use Positive→Selective long, Negative→Selective short, Mixed→Neutral. Other valid breadth combinations in the first two cases are Neutral. Required unavailable evidence means Unclassified. IWM never votes. **SPY/QQQ Breadth Consensus** compares two index classifications, not a merged roster; either unavailable index makes consensus unavailable. Each index requires 80% valid paired EMA coverage. The complete 64-cell matrix is generated by the same function as the current result and displayed in Daily Plan methodology.

Only three priorities are shown: **Primary long / Watch / Primary short**. Full and Selective markets use identical theme rules. Long: valid Score ≥50 and a Bullish/Mixed ETF, or a Newly bullish transition. Short: valid Score <50 and a Bearish/Mixed ETF, or Newly bearish. Both exceptions still require a valid current Score and EMA inputs. Neutral/Unclassified means all Watch. Theme breadth remains independent (minimum eight valid members and 80% coverage); it does not affect Score or Priority. The retired four-quadrant relative labels are absent from the active manual workflow. Legacy diagnostic code/files remain historical.

A Newly transition requires the immediately preceding genuine US session, the same validated anchor identifier, compatible EMA/input methodology, and valid raw Price/EMA21/EMA50 at both endpoints. No inference from historical relative labels, missing days or same-day earlier runs. Priority Change is New long/New short (including direction switches), Removed, unchanged —, or N/A without comparable priority history. Daily Plan shows **all** Primary themes in New Primary Today, Continuing Primary or Comparison unavailable, without a five-theme cap. Watchlist has one Performance table, with 1M/3M stock-minus-ETF columns. Its **vs ETF** filter defaults to All and uses the same weighted calculation as exports: W >0 Outperforming, W <0 Underperforming, W =0 Flat, missing endpoints Unavailable. It combines with search and EMA filters using AND. Relative performance is a filter, not a sort mode. Price, market cap and stock returns remain sortable; the two excess-return columns stay visible with non-sortable headers. Configured stock #, membership, breadth, downloads and collection lists are independent of browser filters. Old view/both-horizon filters reset safely; no new meaning is silently applied to saved settings. Search/navigation/per-tab scroll restoration remain available.

### Daily research downloads versus complete collection

- **Data Collection: All Configured Stocks** / `inputs\_lists\Daily_Data_Stocks.txt`: every configured member, including missing daily rows and stocks excluded from today's research.
- **Data Collection: All ETFs** / `inputs\_lists\Daily_ETFs.txt`: every anchor and SPY/QQQ/IWM. The website exposes equivalent complete `tradingview_configured_stocks.txt` and `tradingview_sector_theme_etfs.txt` lists. The three unfiltered index CSV exports remain separate.
- **Research: Daily Primary**: only themes matching today's directional Primary label. For each membership, Weighted Excess Return = 0.60 × (Stock 1M − ETF 1M) + 0.40 × (Stock 3M − ETF 3M), in raw percentage points. Long includes values >0, short <0; zero/invalid endpoints are excluded without substitution, refill or extra filters. Each stock is evaluated independently against each anchor.

Daily Plan shows one full-width grouped priority table and one **Download Today's Primary Research Watchlist** action. It uses a dated `tradingview_daily_primary_YYYY-MM-DD.txt` with comma-separated TradingView section tokens (`###ETF — Readable theme name`), each followed by the anchor and qualifying stocks. Themes follow directional priority/score order; all anchor identifiers are reserved before stocks are distributed. A shared qualifying stock appears under its first qualifying theme only. Long stocks sort by weighted excess descending, short ascending, with an identifier tie-break. ETF-only qualifying sections still contain their anchor. Full per-theme relationships and Primary-filtered individual files remain available internally; the UI does not expose redundant ZIP/relationship buttons.

Ordinary full individual-theme TXT/ZIP downloads remain unfiltered. The Sectors & Themes page has three matching downloads: **Download Individual Watchlists**, **Download All Stocks**, **Download All Themes**. The latter two remain complete collection universes; All Themes retains all anchors and index context ETFs. No reimport of existing ordinary individual TradingView watchlists is required. The optional broad-scan controls are removed. The Themes table omits visible 1W, Δ Rank and inline Sector/Theme badges; Priority Change remains, and internal classifications plus historical rank changes are retained. The underlying export fields are unchanged; underlying 1W data and Market/Watchlist 1W remain.

The **Methodology** main-navigation tab documents the full generated Market matrix and matched-rule definitions, breadth, Score, Primary policy, configured-stock maintenance, weighted comparisons, exports and history. Daily Plan's decision path shows only contributing inputs: unanimous prices use the two price readings and price-consensus rule; other combinations show required breadth; Unclassified identifies missing required evidence. IWM never appears as a voting input. Earnings display Today / In 1 day / In N days / N/A / Past date relative to the saved US session, not browser today. Original supplied dates remain stored; no next event is inferred. Earnings tickers are deduplicated without visible theme relationships.

Private `daily_primary_audit.json` records endpoint values and exact exclusion reasons. It does not enter `site/`. All instruments use the unchanged shared verified TradingView identifiers. TradingView's [official import/export guide](https://www.tradingview.com/support/solutions/43000487233-how-to-import-or-export-a-watchlist/) confirms TXT, exchange prefixes and comma separation (reviewed 3 November 2026). The grouped exporter uses the `###` section convention and has local structural tests; the public guide does not establish that this new file imports correctly. **Actual TradingView import remains unverified.** Import the daily file into a temporary new watchlist, check section labels and each anchor-first order, confirm instruments resolve, and confirm shared stocks occur only once. Keep existing ordinary watchlists.

Stable configured membership is based on material business relevance and US-tradeable identity; ETF holdings membership is not mandatory, meaningful overlap is allowed, and direct exposure is preferred over peripheral exposure. Maintenance retains $15 Price, $2 billion market cap with existing missing-fact treatment, $20 million liquidity proxy, 205 sessions of history and maximum 20 stocks. These are maintenance settings, not daily replacement filters or a claim of fresh revalidation. TradingView **Price × average volume, 30 days** is a liquidity proxy, not the exact mean of daily Price × Volume. There is no new single-day turnover gate.

### History migration and updating

Research history uses priority version `ema-score-priority-2`, independently of unchanged rank compatibility. Records store raw Price/EMA inputs, anchor identity, priority, transition and Priority Change. Old incompatible priorities show N/A; compatible Δ Rank comparisons continue. The first same-session methodology migration saves the exact prior record in `output\manual_csv\local_history\backups\`. Older session records are preserved. Same-session reruns always compare against the preceding US session. Invalid inputs or publication failures retain the previous dashboard, downloads, history and separately prepared site.

Runtime dependencies are unchanged: **setup need not be rerun** if the existing `.venv` is healthy. To update your existing Windows clone, first copy `inputs` and `output\manual_csv\local_history` to a backup outside the repository. Then:

```powershell
git status --short --branch
git fetch origin
git switch download
git pull --ff-only origin download
```

Preserve any source edits before pulling; never reset/delete the working folder. Refresh with the actual saved US session and its five CSVs (for the example above, `.\refresh.cmd --session 2026-11-02`). Review the dated dashboard, then run `.\prepare-site.cmd --session 2026-11-02` separately if desired. These commands do not push or deploy. Existing local inputs/history remain ignored and retained.

Developer/browser checks are optional, **not daily dependencies**. The existing `requirements-dev.txt` pins Playwright; installing it and its Chromium browser is needed only for browser tests. Node is needed only for JS helper tests. Standard checks are `python -m unittest discover -s tests`, `node tests/test_dashboard.js`, `python tests/check_scanning_exports.py output/manual_csv`, and `python tests/browser_check_site.py site`. Windows launchers and a clean synthetic end-to-end install also have a separate Windows CI check. This does not mean the code has been tested on your particular Windows PC.

### Updating an existing ZIP installation safely

Download the latest **download** branch ZIP and extract it into a **separate temporary folder**. Stop local previews and back up your existing `inputs`, `output\manual_csv\local_history` and other local data first. Keep the existing installation folder and its data; do not extract the ZIP over the entire folder.

For older installations that also need the earlier UI/workflow refinements, copy these program files **in addition to the current preview/workflow file list below** (add the new module):

- `static/dashboard.js`, `static/dashboard.css`, `static/dashboard_template.html`
- `src/themescope/daily_lists.py`, **`src/themescope/relative_performance.py` (new)**
- `src/themescope/manual_csv.py`, `src/themescope/research_policy.py`
- `src/themescope/site_output.py`, `src/themescope/tradingview.py`
- `README.md`

Leave `inputs/`, all of `output/` (especially `output/manual_csv/local_history/`), `site/`, `.venv/`, caches, personal configuration and other local data in place. The membership/anchor/identifier configuration is unchanged by this refinement; do not replace it unnecessarily. Tests/CI files may be copied if you run developer checks; they are not daily runtime files. No setup rerun is needed when the existing environment works, since dependencies are unchanged.

Refresh through `refresh.cmd` using the actual selected US session and its five CSVs, review with `open-dashboard.cmd`, then prepare `site/` separately if desired. For the supplied example: `.\refresh.cmd --session 2026-11-02`, followed by `.\open-dashboard.cmd`. Existing ordinary individual watchlists do not need reimporting. ZIP installations cannot use Git pull; use this selective program-file replacement for this version.

## Multiple dates, completed updates and safe recovery

The Daily Plan's **How this list is built** action opens **Methodology → How Today's Primary Research Watchlist Is Built** at `#methodology/primary-research-watchlist`. It remains available when there is no Primary download, supports keyboard focus and browser Back, and explains the existing theme rules, weighted stock comparison and export ordering/deduplication. The complete Market Matrix is grouped by Result in this order: Long bias, Selective long, Neutral, Selective short, Short bias; Unclassified has its own missing/invalid-input group. Today's matching row and group are marked. These are documentation and navigation changes; classification, priority, membership and export calculations are unchanged.

Keep all dated input folders. `refresh.cmd --session 2026-11-03` reads only `inputs\2026-11-03` unless you explicitly supply `--input-dir`. A complete older folder and an incomplete newer folder may coexist; missing, duplicate or incorrectly dated files in the selected folder cause failure. There is no newest-file search, date fallback or role merging across folders. Windows `(1)` suffixes are accepted only when a role still has one matching file. HK next-day filenames are allowed inside the explicitly selected US-session folder. Filenames and hashes **cannot prove quote freshness**: the CSV has no reliable per-row session timestamp. Verify that you exported after the selected US close; unchanged-content checks are a conservative guard, not proof of observation time.

| Artifact | Where to check its real session | Changes when |
|---|---|---|
| Latest refreshed dashboard | `output/manual_csv/dashboard.html`, `latest_snapshot.json`, successful `refresh_status.json` | Refresh succeeds |
| Latest prepared site | `site/index.html`, `snapshot_summary.json`, `site_manifest.json` | Explicit matching-session prepare-site succeeds |
| Running local preview | Its console directory/type/URL plus response `X-ThemeScope-Session`, `X-ThemeScope-Root-ID` and `X-ThemeScope-Run` headers | Serves completed files from its own fixed folder; reload after updates |
| Previously uploaded Cloudflare site | The deployed website and its displayed date | Separate, explicitly authorized publication only |

A local refresh never updates Cloudflare, and it does not prepare `site/`. Even the two local outputs can differ. Preparing another date cannot relabel the current successful output. An explicit replay of an older session may become the displayed dashboard, but later-session history is retained byte-for-byte. A replay that would change history already used by later sessions is refused; use original inputs/configuration or a separate output folder for alternate historical calculations.

Refresh and site publication now use process locks, durable backups and a journal **beside** their output folder. Completed files are verified before success. Locked files or ordinary write failures roll back; close Excel/editor handles and retry. If a process was interrupted and restoration is incomplete, preview refuses the partial output. Do not delete journals/backups or edit staging files. Close active refresh/preparation operations and any locked files, then run:

```powershell
.\refresh.cmd --recover
.\prepare-site.cmd --recover
```

Recovery reads no CSVs and publishes no new session. Run only the command for the affected artifact, then retry its normal refresh/preparation with the intended date. A second writer briefly waits for short preview reads, then waits or fails clearly if another writer is active; it never kills that process. Temporary directories are never preview assets. Old generated daily research download files retire after successful publication; ordinary watchlists, inputs, history and unrelated local files are retained. Same-session reruns use the genuine preceding US session, never an earlier run that day. This protects against interrupted processes and locked-file failures; it is not a claim of protection from physical disk failure.

### Updating this preview/workflow fix in a ZIP installation

Extract the new **download** ZIP into a separate folder, stop active previews/refresh/preparation, and back up inputs/history. Preserve your existing `inputs/`, `output/manual_csv/local_history/`, `.venv/`, configuration, site and other local data. If the preceding UI release is already installed, copy only these changed/new program files into their matching existing paths:

- `scripts/serve_local.py`, `scripts/refresh_local.py`, `scripts/prepare_site.py`, `scripts/generate_dashboard.py`
- **`src/themescope/local_publication.py` (new)**, `src/themescope/local_history.py` and `src/themescope/site_output.py`
- `README.md`

The existing `.cmd` launchers already call these scripts relative to their own folder; no dependency change or setup rerun is required. Stop old preview consoles, refresh the intended date, prepare that same date if needed, and launch the desired preview. Use its exact printed URL. Do not overwrite the entire installation folder or reimport unchanged TradingView watchlists.

For the current Methodology/navigation update, also replace **`static/dashboard.js`** and **`static/dashboard.css`** from the latest ZIP, plus this README. If the preview/workflow fix is already installed, these are the only changed runtime files. Refresh the same genuine saved session to rebuild the local dashboard, then prepare that matching session separately to rebuild `site/`.
