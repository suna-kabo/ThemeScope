# Project map

| Location | Role |
| --- | --- |
| `README.md` | Product, Windows setup and local launch |
| `AGENTS.md`, `PRODUCT.md`, `DESIGN.md`, `MOTION.md` | Contributor and current product contracts |
| `setup.cmd`, `ThemeScope.cmd` | Current Windows setup and local app |
| `configure-credentials.cmd`, `backup-data.cmd` | Per-user encrypted credentials and online research backup |
| `src/themescope/local/` | Loopback API, refresh coordination and committed snapshot reads |
| `providers/`, `storage/`, `themes/`, `research/`, `market/` under `src/themescope/` | Current data, calculations and research layers |
| `config/vnext/`, `config/market_universes/`, `config/calendars/` | Versioned policies, memberships, evidence, rosters and schedule |
| `static/vnext/`, `static/Research*` | Approved frontend and pinned current font/license |
| `static/dashboard*`, `static/Inter*`, other legacy modules/config | Separate historical dashboard reproduction |
| `legacy-*.cmd` | Explicit legacy CSV setup, refresh, dashboard, site preparation and preview |
| `scripts/`, `tests/`, `.github/workflows/` | Current/legacy maintenance, offline regression and release gates |
| `requirements-vnext.txt` | Current runtime pins |
| `requirements.txt`, `requirements-dev.txt` | Legacy hashed pins and development/browser dependencies |
| `docs/getting-started/`, `methodology/`, `operations/` | Current user, methodology and operations guides |
| `docs/development/`, `architecture/` | Current contributor documentation |
| `docs/archive/`, `reports/archive/` | Historical plans, design captures and dated validation |
| `inspection/`, `tests/fixtures/` | Immutable synthetic checkpoint and compatibility provenance |

## Private/generated state

Preserve `.venv-vnext/`, `.venv/`, `runtime/`, `output/`, `dist/`, `site/`, `inputs/`,
`cache/` and backups unless a separately reviewed task permits removal.
`runtime/vnext/` contains real SQLite research history; fixture history is separate.
Ignored does not mean disposable. Never force-add credentials, raw bars or saved personal state. Saved lives under the per-user application-data directory.

## Compatibility boundaries

Legacy CSV reproduction uses `legacy-setup.cmd`, `legacy-refresh.cmd`,
`legacy-open-dashboard.cmd`, `legacy-prepare-site.cmd` and `legacy-preview-site.cmd`.
It retains separate dependencies, data, tests and history; it is not daily operation.
Historical browser programs for superseded interfaces are recoverable from Git
history. Current browser acceptance is the research-v2 release gate plus local
and pre-launch browser checks.

Inspection tooling still consumes `docs/vnext_preflight.md`, `docs/vnext_local_ui.md`,
`docs/vnext_provider.md` and the original `docs/vnext/` specification. Their stable
paths and the `inspection/` fixture remain intact. See the
[relocation map](../archive/relocations.md).
