# Daily refresh and frozen public snapshots

`main` is the stable production branch. The local Python/SQLite app remains the
live research runtime; Cloudflare serves a frozen, read-only projection. Neither
the daily helper nor the publisher changes membership, calculates its own signals,
pulls Git updates, creates a Pages project or substitutes IEX.

## One-time setup and production cutover

Install Python 3.12+, Git, Node.js LTS/npx and the local runtime with `setup.cmd`.
Use a Git clone on **main**, not a plain ZIP, so publication can prove clean source
and record its commit. Authenticate locally with `npx wrangler@4 login` and keep
using the **existing** Pages project (`themescope` by default). No Cloudflare token
belongs in a CMD/source file.

Before the first main publication:

1. GitHub **Settings → General → Default branch**: set **main**.
2. Existing Cloudflare Pages **themescope → Settings → Builds & deployments →
   Production branch**: set **main**. Keep **automatic production Git deployments
   disabled**; leave preview Git deployments disabled unless deliberately intended.
   Ensure no queued Git build can overwrite real data with the synthetic demo.

During this maintenance task GitHub rejected the default-branch API mutation with
HTTP 403 (`Resource not accessible by integration`), and Codex had no authenticated
Cloudflare session. Those **two external settings remain unverified/unresolved**;
no setting change or live upload is claimed. Retain `refactor/themescope-vnext`
until the settings are resolved and the first main publication is confirmed.
This limitation does not reopen [Gate E](gate-e-closure.md).

The publisher now reads actual Pages settings through supported Wrangler
`whoami --json` / `auth token --json` and an authenticated **GET** to the Cloudflare
Pages project API. Auth remains ephemeral in memory and is never printed, written
to source or sent to any other host. Multiple available accounts require an explicit
local `CLOUDFLARE_ACCOUNT_ID`; it must match an authenticated account. The project
must exist, have `production_branch=main`, and have automatic production Git builds
disabled when Git-connected. Redirects, malformed/ambiguous metadata and unknown
settings fail closed.

An older production deployment may still name the old branch. This is allowed
**only after the actual current project settings prove main**. It enables the first
main upload without a manual deployment bypass. The upload must still be confirmed
as a **new successful Production deployment from main with the exact source commit**.

## Normal daily workflow

In PowerShell at a clean **main** checkout:

```powershell
$env:APCA_API_KEY_ID = '<your local Alpaca key>'
$env:APCA_API_SECRET_KEY = '<your local Alpaca secret>'
.\update-public.cmd
```

No session date is normally required. The default existing project is `themescope`;
use `--project EXISTING_NAME` only for a deliberately chosen alternative. Closing
the PowerShell session removes these process-local values; they are not persisted
by this command. A later shell does not inherit values from a closed shell.
Optional `ALPHAVANTAGE_API_KEY` enables earnings; it never changes qualification.

The helper:

- verifies clean main and required key presence without printing values;
- reuses a recognized live loopback server, or starts the existing normal launcher
  headlessly with `--no-browser` (never `--fixture`);
- POSTs `/api/refresh` with exact loopback Origin, then polls with a finite deadline
  (default/maximum 600 seconds; startup waits at most 30 seconds within it);
- accepts only success with matching target/last-successful/dashboard sessions and
  complete, non-fixture, healthy data validated by the existing public contract;
- requires a newly refreshed timestamp matching status, not a stale prior snapshot;
- rechecks the source commit and calls the existing strict publisher for that exact
  service-selected session, without independently implementing a trading calendar;
- stops only a headless process it owns. An existing user's server stays running,
  including on timeout. It never searches for or kills a port owner.

A second active refresh is rejected rather than adopted. A failure before upload
publishes nothing and leaves the prior public site intact. The previous successful
local SQLite snapshot remains protected by the existing refresh service. If an
existing server was launched without keys, setting them in another shell cannot
change that process's environment: restart it deliberately or let the helper start it.

After confirmed deployment, the final lines are:

```text
Refresh: YYYY-MM-DD PASS
Completeness: PASS
Public deployment: CONFIRMED
```

All failures return nonzero. After an upload, a confirmation/network failure can
leave an actual deployment whose result is unknown: inspect Pages before retrying;
nonzero exit is not a promise of rollback. No success is fabricated from a CLI exit
or Preview alias. Command logs never contain credentials or raw provider/CLI bodies.

## Manual fallback and debugging

Keep the app running in normal live mode with keys in its launching environment:

```powershell
.\ThemeScope.cmd
```

Select **Refresh Data**, verify success/completeness and its exact completed session,
then in another terminal at the same clean main checkout:

```powershell
.\publish-public-snapshot.cmd SESSION themescope
```

Replace `SESSION` with that verified `YYYY-MM-DD`, not today's guessed date. For
build-only inspection without uploading:

```powershell
.\.venv-vnext\Scripts\python.exe scripts\build_public_snapshot.py --session SESSION
```

The builder reads committed `http://127.0.0.1:8766/api/dashboard-data` only. It
preserves published financial values/TXT, drops private/unknown fields, pins font
integrity, validates the complete static allowlist and atomically prepares ignored
`dist/cloudflare-public`. The publisher isolates the upload from repo configuration,
strips all Alpaca/Alpha Vantage variables from Wrangler and confirms production
branch/environment/source. No database, raw bars, keys, Functions or cloud backend.

## Synthetic demo and public behavior

The separate demo never uses the private app or Alpaca:

```sh
python scripts/build_cloudflare_demo.py
python -m http.server 8767 --bind 127.0.0.1 --directory dist/cloudflare-pages
```

The real public banner identifies a completed session and read-only state. Refresh,
polling and provider calls are disabled; filters, inspectors, map, browser-local
Saved and TXT downloads work in the browser. Real frozen output stays ignored and
is never committed. This repository supplies no market-data redistribution rights.

Future UI experiments use a separate branch/worktree; daily publication stays on
clean main. See [development workflow](../development/production-and-ui.md) and
[permanent checkpoints](../development/branch-checkpoints.md).
