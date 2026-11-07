# Cloudflare Pages: synthetic demo and frozen public snapshots

Both workflows below use the **current** `static/vnext/` UI. The Git-built demo
contains fictional deterministic results. The separate local publisher freezes a
real successfully committed dashboard snapshot without recalculating its metrics.
The verified local Python/SQLite application remains the live research workflow.
Gate E stays open; real November 9/10 chronological checks remain deferred.

## GitHub public entry point

At task inspection the repository was public and its default branch was `main`.
The connected GitHub tools cannot change repository settings. No workaround or
metadata change was attempted. To make normal browsing, ZIP downloads and clones
start on vNext, use GitHub:

**suna-kabo/ThemeScope → Settings → General / Default branch → Change default
branch → refactor/themescope-vnext → Update.**

Keep the repository public. This changes its entry point only: `main` and old
public history remain accessible. Do not merge, delete branches or rewrite history.

## Build and local preview

From a checkout of `refactor/themescope-vnext`, using Python 3.12:

```sh
python scripts/build_cloudflare_demo.py
python -m http.server 8767 --bind 127.0.0.1 --directory dist/cloudflare-pages
```

Open `http://127.0.0.1:8767/`. The second command is only a local static-file preview;
Cloudflare serves the generated files directly and runs no Python application.
No dependency installation, credentials or environment secrets are required.

The build clears only `dist/cloudflare-pages/`, then copies the exact current
`index.html`, `app.css`, `app.js` and generates `preview.js`, `_headers` and an
original crescent favicon. `dist/` is ignored by Git. Do not upload the checkout.
There is no separately maintained demo UI. The historical `inspection/ui/` remains
because inspection tests/browser smoke still depend on it; it is **not** the demo
source or output and must never be selected as the Pages deployment directory.

The snapshot extends the existing `scripts/vnext_fixture_report.py` fixture,
using the unchanged pure engines and approved formula settings at **build time**.
All prices, volumes, dates and memberships are manufactured. Only formula settings
are read from production configuration: no live memberships, rosters, mappings,
provider payloads, database, account data or environment credentials are read.
The same sources produce byte-identical output. There are no runtime financial
calculations, APIs, provider access or database in the deployed artifact.

Fictional DEMO/TURN identifiers demonstrate overlapping themes, Core/Enabler,
positive/negative W, Bullish/Bearish/Mixed trends and unavailable breadth. SPY/QQQ
and context-only IWM prices/breadth are also fabricated. A fictional earnings date
exercises the supplied earnings presentation. This is not the approved live universe.

## Cloudflare Pages dashboard setup

The original synthetic build was prepared without an authenticated Cloudflare
Pages integration. The user now reports an existing Pages deployment, apparently
project `themescope`; this has not been verified from this environment. **Reuse
that project for real publication; do not create a replacement.** The following
creation instructions apply only to a separate first-time synthetic demo setup:

1. Open Cloudflare **Workers & Pages → Create application → Pages → Connect to Git /
   Import an existing Git repository**. Choose Pages, not a Worker application.
2. Connect GitHub and select **suna-kabo/ThemeScope**. Use a project name such as
   `themescope-demo` if available.
3. Set these build values:

| Setting | Value |
| --- | --- |
| Production branch | `refactor/themescope-vnext` |
| Framework preset | None |
| Root directory | Repository root (leave blank) |
| Build command | `python scripts/build_cloudflare_demo.py` |
| Build output directory | `dist/cloudflare-pages` |
| Build environment variable | `PYTHON_VERSION=3.12` (non-secret) |
| Skip automatic dependency installation | `SKIP_DEPENDENCY_INSTALL=true` (non-secret) |
| Secrets / bindings / Functions | None |

4. In **Settings → Builds & deployments → Branch control**, disable preview builds
   for all other branches. Do not deploy `main` or historical inspection branches.
   Check production branch again before the first build.
5. Save/deploy and open the generated Pages URL. Confirm the synthetic fixture
   warning, fictional symbols and browser-only replay before sharing it.

No Alpaca/Alpha Vantage keys, `.env`, API tokens, databases, Workers backend, D1, KV,
R2, schedules or authentication setup are needed. Do not add them. This procedure
is not a migration of FastAPI/SQLite or live financial processing to Cloudflare.
Skipping automatic dependency installation avoids installing the unrelated local
runtime requirements; the build itself uses only Python's standard library.

## Expected behavior and security

Hash routes (`#overview`, `#themes`, `#primary`, `#saved`, `#methodology`) need no
server rewrite. Inspectors, browser Back, Theme Map, filters, sort and Display work
in the browser. Saved keeps its existing `themescope-vnext-watchlist` contract and
is local to this browser/origin; it is not synced. Display has its separate key.
**Replay fixture** replays the embedded snapshot without any provider request.
TXT downloads are fixture-only blobs using `DEMO:` identifiers; they are not real
production exports. The existing visible fictional-fixture warning remains.

Pages applies `_headers`: restrictive same-origin scripts/styles/images, no
network connections (`connect-src 'none'`), no embedded frames, no referrer and
no camera/microphone/location permissions. All assets are local; no fonts,
analytics, CDN, chart data or external resources are loaded. A plain Python file
server does not itself apply `_headers`; the browser regression below does.

## Validation

```sh
python -m unittest discover -s tests -p 'test_cloudflare_demo.py' -v
THEMESCOPE_AXE_SCRIPT=/path/to/local/axe.min.js python tests/smoke_cloudflare_demo.py
```

The browser check requires local Playwright/Chromium; axe must be supplied locally
for accessibility auditing (never downloaded by the demo). Optional
`THEMESCOPE_DEMO_ARTIFACTS=/tmp/demo-review` captures fixture screenshots outside Git.
Build tests cover a clean isolated source tree without installed dependencies,
byte-identical rebuilds, current-asset equality, stale-file cleanup, synthetic-only
exports, output safety scanning, no network/SQLite use and output symlink rejection.
The static HTTP browser test applies Pages headers and covers all views, inspectors,
Back, Map, replay, filters/sort, Saved persistence, Display, TXT download and 390px
layout. It rejects console/page/HTTP errors, external requests and any `/api/`
request. Eight axe A/AA audits cover destinations, inspectors and mobile.
Run the existing full Python and local UI browser suites too before committing.

## Real frozen public snapshot: local-only workflow

| Workflow | Builder | Output | Data source |
| --- | --- | --- | --- |
| Synthetic Git-built demo | `scripts/build_cloudflare_demo.py` | `dist/cloudflare-pages` | Manufactured fixture |
| Real frozen public snapshot | `scripts/build_public_snapshot.py` | `dist/cloudflare-public` | Committed local dashboard API |

The public publisher never runs as a Cloudflare build. It runs on your Windows
machine, reads `http://127.0.0.1:8766/api/dashboard-data`, prepares static assets and
directly uploads them to the existing Pages project. It never reads SQLite, asks
Alpaca for data or commits the real snapshot. `dist/` stays ignored. Do not force-add
these artifacts to Git. No real snapshot is included in these source changes.

### One-time Pages setup before publishing

In the **existing** Pages project:

1. Open **Settings → Builds & deployments / Builds → Branch control / Configure
   Production deployments**. Ensure the production branch is
   **`refactor/themescope-vnext`**. This is the Pages production branch, independently
   of GitHub’s default branch.
2. **Uncheck Enable automatic production branch deployments**, then save. Set
   preview branch deployments to **None** unless you explicitly need them.
3. Confirm there is no currently queued Git build that could overwrite the upload.

This is essential: the existing Git build command generates synthetic data, so a
future automatic Git deployment would replace the real frozen snapshot with the
demo. No Cloudflare settings are changed by the scripts. Source pushes do not
publish real data. Keep the two build/output directories separate.

Install a current Node.js LTS release and authenticate normally in local PowerShell:

```powershell
npx wrangler@4 login
npx wrangler@4 pages project list --json
```

Confirm the existing project name and account. There is no default project name
in the helper: `themescope` below is an explicit example, not an automatic choice.
Do not supply an API token in source or chat; normal Wrangler browser/OAuth login
stores authentication locally. No Cloudflare credentials are copied to the site.

### Publish the November 6 snapshot

With the normal local ThemeScope application running, complete/verify the real
November 6 refresh. Open a second PowerShell terminal at this branch’s clean
checkout. Do not run the app with `--fixture`. Then:

```powershell
.\publish-public-snapshot.cmd 2026-11-06 themescope
```

The helper uses the existing vNext Python environment when present, otherwise
`py -3.12`. The build/publish scripts use only the Python standard library. An
optional build-only check, with Python 3.12, is:

```powershell
python scripts/build_public_snapshot.py --session 2026-11-06
```

The session is mandatory and must exactly equal the detected committed snapshot
session. A mismatch aborts. On later days, pass that explicitly approved completed
session; there is no automatic date selection or scheduled publishing. A failed
local refresh can leave an older last-good snapshot: the explicit session check
prevents unintentionally publishing it as the new day. Publication does not alter
local successful snapshots, official histories, launch rules or Gate E checks.

### Validation, upload and production confirmation

The local API already returns only committed publications (or its last committed
copy during storage contention), never in-flight calculations. The builder relies
on that existing endpoint contract. It additionally requires the vNext schema,
explicit `synthetic_fixture=false`, complete required-symbol counts, healthy
publication provider status, a valid publication timestamp and the exact session.
It rejects malformed/duplicate JSON, redirects, proxy routing, oversized responses
and missing data. It never queries refresh status or changes the refresh service.

An explicit nested field allowlist preserves supplied market/Theme/relative/Primary
metrics, membership relationships, eligibility, earnings, assignments and published
exports. It drops history serialization, configuration hashes, provider identity,
cache/performance details and unrecognized fields. It never reranks or recalculates
anything. Exports are retained verbatim after validating that their lines contain
only ticker/exchange identifiers and known theme grouping.

The build copies the exact current HTML/CSS/JS and generates explicit public-mode
metadata in `preview.js`. Six allowlisted files are staged and safety-checked before
replacing the prepared output. Both build and publish hold a separate OS lock under
ignored `dist/`, and a failed validation preserves the previous prepared artifact.
The helper checks the branch, clean tree and absence of tracked runtime/output files.
It verifies the project already exists and its latest recorded production deployment
uses the expected branch; it never creates a project or modifies settings. This
recorded deployment check does not replace the one-time dashboard settings check.

The helper uploads an isolated validated copy using the supported equivalent of:

```powershell
npx wrangler@4 pages deploy dist/cloudflare-public --project-name=themescope --branch=refactor/themescope-vnext
```

Prefer the helper to this bare command: it also supplies the source commit, strips
market-data credentials from the Wrangler process environment, runs away from repo
configuration/Functions files and verifies deployment results. No raw CLI diagnostics
are relayed; a failure gives a non-secret login/account/project instruction and a
non-zero exit. A normal CLI exit or preview alias alone is insufficient: the helper
checks for a **new successful Production deployment** with the expected branch and
source commit, using bounded polling. If this cannot be proved, it exits non-zero
and asks you to check Pages; an upload may already exist, so inspect before retrying.
Finally open your existing production Pages/custom domain and verify its session
banner. Cloudflare publishes the uploaded static asset set; the local database
and prior deployed site are not modified by a failed build.

Official references checked for this implementation:
[Wrangler Pages commands](https://developers.cloudflare.com/workers/wrangler/commands/pages/),
[branch deployment controls](https://developers.cloudflare.com/pages/configuration/branch-build-controls/),
and [direct uploads to existing Git-integrated projects](https://developers.cloudflare.com/pages/get-started/direct-upload/).

### Public-mode behavior and security

The real site says **Public snapshot · Completed US session YYYY-MM-DD · Read-only**.
It does not claim to be live, synthetic or automatically updated. Refresh is hidden
and guarded; no polling or `/api/*` calls occur. The existing synthetic builder
still shows its fixture warning and Replay fixture behavior. Local live mode keeps
its normal refresh behavior. Views, research inspectors, Map, filters, sorting,
Back, Display, Saved and static blob TXT exports remain browser-only. Saved is
still browser-local, using the same storage key and origin; it is not cloud-synced.
The phrase “Synthetic index” remains the financial metric name in Theme Inspector;
it does not label the real public snapshot as fixture data.

Only public dashboard information is uploaded. The output scanner rejects known
credential names, secrets/tokens, bearer strings, environment-file markers, local
paths, runtime/database names and raw provider payload markers. Exact output
allowlists reject extra files, symlinks, unexpected headers and non-generated icon
payloads. The strict CSP forbids runtime network connections; public assets also
use `Cache-Control: no-store` to avoid stale browser assets between publications.
No SQLite, runtime directory, raw bars, account information, provider credentials,
Functions/Workers backend, D1, KV or R2 are uploaded.

### Tests and remaining local checks

```sh
python -m unittest discover -s tests -p 'test_public_snapshot.py' -v
THEMESCOPE_AXE_SCRIPT=/path/to/local/axe.min.js python tests/smoke_public_snapshot.py
```

All public-mode tests use manufactured contract data with a mocked loopback API;
publishing tests mock Wrangler. Browser screenshots are also manufactured test
data, not November 6 market output. No actual real snapshot has been read or
deployed from Codex. Native Windows `.cmd`/Wrangler OAuth, account/project production
settings and the final production-domain banner must be checked locally using the
commands above. No authenticated Cloudflare Pages connection was available here.

## Remove the demo

In Cloudflare **Workers & Pages → the demo Pages project → Settings → Delete
project**, confirm deletion of this demo project. This removes its Pages deployment
and leaves the GitHub repository, branch, local application and research data
unchanged. Remove any demo custom-domain association if one was added manually.

Validated for this change: full Python suite **330 run, 328 passed, two existing
native-Windows skips**; focused vNext **120 run, 119 passed, one skip**. All three
new build tests, all three existing local browser smokes, 14 local UI axe audits,
the static demo smoke/eight axe audits, both validators, compilation and JS checks
pass. Static demo has zero external/API requests, page/console errors or HTTP
errors. Generated textual assets pass the existing secret/path/raw-payload scanner.
No account credentials or live data were used, and no deployment was performed.

Frozen-publishing validation: **342 full tests** (340 passed/two existing Windows
skips), **12 focused public tests**, **3 synthetic build tests**, and **120 focused
vNext tests** (119 passed/one skip). All five browser programs pass with **30 clear
axe audits** across local, synthetic and frozen-public modes. Static modes make
zero external/API requests and have no page/console/HTTP errors. Both validators,
Python compilation, JS syntax and helper checks pass. These are fixture/mocked
results; actual local OAuth/production-domain validation remains as described above.
