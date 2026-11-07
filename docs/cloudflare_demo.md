# Static synthetic Cloudflare Pages demo

This optional public showcase uses the **current** `static/vnext/` UI unchanged.
It contains fictional deterministic research results, not current market output.
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

No authenticated Cloudflare Pages integration was available during this task;
no project or deployment has been created. To deploy the static showcase manually:

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
