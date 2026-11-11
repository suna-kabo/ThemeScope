# Frozen public snapshots and synthetic demo

The live research application runs locally. Public presentation is a separate,
explicit static workflow: no refresh, API, provider credentials, SQLite or cloud
research backend. This guide describes commands; documenting them does not deploy.

| Mode | Command / builder | Output | Input |
| --- | --- | --- | --- |
| Synthetic demo | `python scripts/build_cloudflare_demo.py` | `dist/cloudflare-pages` | Deterministic fictional data |
| Real frozen snapshot, build only | `python scripts/build_public_snapshot.py --session YYYY-MM-DD` | `dist/cloudflare-public` | Already committed loopback dashboard |
| Explicit real publication | `publish-public-snapshot.cmd YYYY-MM-DD PROJECT` | Existing Pages project | Validated frozen output |

The two output folders stay ignored. Do not force-add a real snapshot to Git.
Gate E is [CLOSED](gate-e-closure.md); that is not authorization for automatic uploads.

## Synthetic preview

From the repository root with Python 3.12 or newer:

```sh
python scripts/build_cloudflare_demo.py
python -m http.server 8767 --bind 127.0.0.1 --directory dist/cloudflare-pages
```

Open `http://127.0.0.1:8767`. The builder uses the standard library and current UI;
it does not access Alpaca, runtime SQLite or private files. Fixture/replay wording
is explicit. If deliberately configuring a separate synthetic Pages site, the
build command is `python3 scripts/build_cloudflare_demo.py`, output
`dist/cloudflare-pages`, repository root working directory. Keep it distinct from
a real snapshot project. Historical setup details are in the
[archived implementation](../archive/operations/cloudflare_demo.md).

## Before publishing a real snapshot

Use Python 3.12+, current Node.js LTS/npx, an existing Cloudflare Pages project, and
local Wrangler OAuth authentication. No project is automatically created.

The current publisher intentionally requires:

- a **clean `refactor/themescope-vnext` checkout**, including untracked-file checks;
- Pages production branch **`refactor/themescope-vnext`**, matching the existing
  recorded production deployment;
- automatic production Git deployments **disabled** in that Pages project;
  disable preview Git deployments too unless explicitly intended;
- no queued Git build that could overwrite real data with the synthetic build.

`main` is the product branch; merging source does **not** change these publisher
checks. Maintain a clean implementation-branch checkout for publishing. Do not
change its branch guard or use a bare Wrangler deploy to bypass verification.
No repository/Pages settings are modified by the helper.

Authenticate and inspect the existing project locally:

```powershell
npx wrangler@4 login
npx wrangler@4 pages project list --json
```

Keep market/Cloudflare secrets out of source, chat and screenshots. Use your own
permitted publication data; this repository grants no market-data redistribution rights.

## Build or publish

Start normal ThemeScope (not `--fixture`) with local SIP credentials, refresh, and
verify success and the exact completed snapshot session. In a second PowerShell
window at the clean publishing checkout, for an explicitly chosen completed session
and existing project:

```powershell
.\publish-public-snapshot.cmd YYYY-MM-DD PROJECT
```

Replace both placeholders deliberately. To inspect static output without uploading:

```powershell
.\.venv-vnext\Scripts\python.exe scripts\build_public_snapshot.py --session YYYY-MM-DD
```

The builder reads only the committed `http://127.0.0.1:8766/api/dashboard-data`
contract. It rejects a mismatched session, fixture payload, incomplete/unhealthy
publication, malformed JSON and unsafe output. A prior snapshot opening after a
failed refresh does not establish success for a new session.

An explicit allowlist retains published research and TXT files without recalculating
metrics. Histories/config hashes, provider/cache diagnostics and unknown fields are
omitted. The complete asset set is validated under a separate OS lock; failed
validation preserves the prior prepared output. Pinned font/license hashes remain
strict; LF/binary Git attributes make assets deterministic across platforms.

The publisher verifies an existing project/production source, uploads an isolated
validated copy with the source commit, and confirms a **new successful Production**
deployment with matching branch/source. It strips market-data credentials from the
Wrangler environment. UTF-8 metadata parsing tolerates surrounding informational
text while requiring the expected JSON list of objects. Errors stay sanitized and
fail closed. If confirmation fails after upload, inspect Pages before retrying;
nonzero exit does not prove no upload occurred.

## Public behavior

The banner identifies **Public snapshot · Completed US session · Read-only**.
Refresh/polling/provider calls are disabled. Filters, map, inspectors, browser Back,
Display, browser-local Saved and TXT downloads work entirely in the browser.
The public projection is frozen until another explicit upload. The CSP forbids
runtime connections; no Workers/Functions, D1, KV, R2 or account database is supplied.

Build and fixture-browser tests are described in the
[development guide](../development/README.md). No Cloudflare command is part of
normal setup, refresh, unit testing or the final repository merge.
