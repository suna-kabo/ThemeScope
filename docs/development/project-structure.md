# Project map

| Location | Role |
| --- | --- |
| `ThemeScope.cmd`, `setup.cmd` | Launch and install the loopback dashboard |
| `configure-credentials.cmd`, `backup-data.cmd` | Windows credential setup and online SQLite backup |
| `src/themescope/local/` | API, refresh coordination, committed snapshots, and per-user state |
| `src/themescope/providers/`, `storage/`, `themes/`, `research/`, `market/` | Provider access, storage, calculations, and research selection |
| `config/vnext/`, `config/market_universes/`, `config/calendars/` | Versioned policy, membership, rosters, and completed-session calendar |
| `static/vnext/`, `static/Research*` | Current frontend and bundled font with license |
| `requirements-vnext.txt` | Runtime dependencies |
| `requirements-dev.txt` | Runtime dependencies plus Playwright for development and CI |
| `scripts/`, `tests/`, `.github/workflows/` | Maintenance tools, fixture checks, and CI |
| `docs/archive/`, `reports/archive/`, `inspection/` | Historical documentation, dated evidence, and the original synthetic inspection checkpoint |
| `tests/fixtures/market_matrix.json` | Frozen 64-case Market Matrix reference used by current tests |

## Private local data

The app stores SQLite history in `runtime/vnext/` and synthetic fixture state
in `runtime/vnext-fixture/`. Saved and encrypted credentials live under
the current user’s local application data directory. Keep existing databases,
inputs, backups, virtual environments, and generated outputs during upgrades.
See [maintenance and backups](../operations/refresh-and-maintenance.md).

## History and compatibility

The current app uses its own versioned storage and supports its SQLite schema
migrations. Earlier ETF dashboard code and test fixtures are available through
Git history. The approved specification, build evidence, permanent tags, and
original inspection copy are listed in the [historical archive](../archive/README.md)
and [checkpoint index](branch-checkpoints.md).
