# Architecture

ThemeScope is a local Python/FastAPI application with a vanilla HTML/CSS/JavaScript
research UI. SQLite stores auditable observations, calculated results and the active
publication. External provider retrieval is separate from deterministic calculations.

```mermaid
flowchart LR
  Config[Versioned policy, memberships and rosters] --> Refresh[RefreshService]
  SIP[Alpaca historical SIP] --> Cache[Provider adapter and incremental cache]
  Cache --> Refresh
  Refresh --> Calc[Market, theme and research calculations]
  Calc --> Store[Atomic SQLite snapshot and input references]
  Store --> API[Loopback read-only dashboard and TXT routes]
  API --> UI[Browser workspace and local Saved]
  API --> Frozen[Explicit frozen static builder]
```

| Layer | Main paths | Contract |
| --- | --- | --- |
| Domain/config | `domain.py`, `config/vnext/` | Validated policy and effective-dated reviewed inputs |
| Providers | `providers/` | Historical bars/identity; no ThemeScope formulas or trading endpoints |
| Market | `market/`, `research_policy.py` | Separate SPY/QQQ breadth, frozen Market Matrix, IWM context |
| Calculations/history | `themes/`, `relative_performance.py` | Deterministic returns, index and compatible history |
| Research | `research/` | Independent relationships, eligibility, lenses and deterministic TXT |
| Persistence | `storage/` | Immutable data versions, run references and transactional publication |
| Local application | `local/` | Startup, refresh coordination, guarded status and loopback API |
| UI | `static/vnext/` | Snapshot presentation; no browser financial-rule reconstruction |
| Static build | `scripts/build_*`, `scripts/static_pages.py` | Synthetic demo or allowlisted frozen snapshot |

See [provider/storage](provider-and-storage.md), [terminal actions](terminal-actions.md),
[methodology](../methodology/README.md), and [project map](../development/project-structure.md).
`vnext` identifiers remain stable for configuration, history, schema and Saved
compatibility. Legacy modules/fixtures are retained for reproduction, not used to
splice old ETF-based history into the current series.
