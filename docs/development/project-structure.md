# Project map

| Location | Role |
| --- | --- |
| `README.md`, `PRODUCT.md` | Newcomer entry point and product boundary |
| `AGENTS.md`, `GOALS.md`, `PLANS.md` | Contributor rules, standing goals and current repository status |
| `DESIGN.md`, `MOTION.md` | Current Tidal Vector design/interaction contracts |
| `ThemeScope.cmd`, `setup.cmd` | Windows runtime launch/setup |
| `refresh.cmd`, `open-dashboard.cmd` | Compatibility aliases for the current local app |
| `src/themescope/local/` | FastAPI, guarded status, refresh and snapshot reads |
| `src/themescope/providers/`, `storage/`, `themes/`, `research/`, `market/` | Current provider/cache, persistence and pure research layers |
| `config/vnext/` | Stable current policy, reviewed memberships, evidence registry and terminal events |
| `config/market_universes/`, `config/calendars/` | Manual benchmark ledgers and versioned exchange schedule |
| Other `config/` and root Python modules | Shared identifiers/rules and retained legacy compatibility |
| `static/vnext/` | Current UI; keep the path for builders and compatibility |
| `static/dashboard*` | Legacy dashboard assets retained for historical reproduction |
| `scripts/` | Launch, validation, roster/review maintenance and explicit static builders/publisher |
| `tests/` | Current and legacy regressions; versioned synthetic history fixtures |
| `docs/getting-started/`, `methodology/`, `operations/` | Current user and operator documentation |
| `docs/development/`, `architecture/` | Contributor guides and implementation contracts |
| `docs/archive/` | Historical handoff, gate, migration, UI and legacy reports |
| `reports/archive/`, `design-plans/` | Historical implementation/design provenance and approved fixture reviews |
| `inspection/` | Preserved historical Gate D synthetic checkpoint, not current launch status |
| `legacy-*.cmd`, `prepare-site.cmd`, `preview-site.cmd` | Explicit historical workflow/site tools; not daily current refresh |
| `.github/workflows/` | Offline Linux and native-Windows regression workflows |
| `requirements-vnext.txt` | Current local runtime pins |
| `requirements.txt`, `requirements-dev.txt` | Legacy hashed dependencies and development/browser tools |

## Generated/private directories

`.venv-vnext/`, `.venv/`, `runtime/`, `output/`, `dist/`, `site/`, `inputs/`,
`cache/` and generated ZIPs are local ignored state. `runtime/vnext/` contains real
SQLite history; `runtime/vnext-fixture/` contains fictional history. Never force-add
runtime DBs, keys, raw market payloads or real frozen output. An ignored folder's
existence is not permission to delete it during cleanup.

`data/` and `downloads/` contain explanatory notes rather than promised prebuilt
market-data packages. Historical snapshots/fixtures, legacy readers and security/
evidence records are intentional compatibility/provenance, not disposable clutter.
The existing 11 design-review PNGs are approved deterministic history, not newly
added live screenshots. No new screenshots are needed for documentation maintenance.

## Stable historical document paths

Inspection tooling still consumes `docs/vnext_preflight.md`,
`docs/vnext_local_ui.md`, `docs/vnext_provider.md` (also an inspection test input),
and `docs/vnext/ThemeScope_vNext_Product_and_Methodology_Spec.md`.
They remain explicitly labelled historical with current-guide/closure links rather
than changing tooling or losing report content. Other relocations are recorded in
[the archive map](../archive/relocations.md).
