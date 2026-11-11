# ThemeScope

ThemeScope is a local, end-of-day US equity research workspace. It organizes a
large stock universe into a practical **Market → Themes → Stocks** workflow:
understand the market, compare custom equity themes, then research liquid stocks
against their actual theme peers. It does not place trades or generate entry signals.

## Research workflow

1. **Market:** SPY and QQQ determine Market Bias; breadth and price/EMA evidence
   explain the result. IWM supplies small-cap context only.
2. **Themes:** compare Theme Strength, synthetic-index Trend, Research Priority,
   returns and breadth. The Theme Returns Map adds a compact cross-theme view.
3. **Stocks:** switch between Directional and Countertrend research, inspect a
   ticker's theme relationships, save research locally, and export TradingView TXT lists.

The midnight/cyan **Tidal Vector** interface includes contextual inspectors,
search and filters, grouped research tables, keyboard navigation, compact/comfortable
layouts, enlarged text, high contrast and reduced motion. See the
[UI and workflow guide](docs/getting-started/research-workflow.md) and
[design system](DESIGN.md). Historical review screenshots are indexed in the
[design archive](design-plans/README.md); no live market screenshots are bundled.

## Quick start on Windows

Install **Python 3.12 or newer** with the Python launcher, then clone or download
this repository. Run PowerShell from the repository folder:

```powershell
.\setup.cmd
$env:APCA_API_KEY_ID = '<your local Alpaca key>'
$env:APCA_API_SECRET_KEY = '<your local Alpaca secret>'
.\ThemeScope.cmd
```

The app opens at **http://127.0.0.1:8766**. Select **Refresh Data** after a US
session has completed. Alpaca historical **SIP access is required**; ThemeScope
never falls back to IEX. Keep keys in your local process environment, never in
Git, chat, screenshots or published output. Optional `ALPHAVANTAGE_API_KEY`
enables earnings dates; earnings are not required for refresh or qualification.

To try deterministic fictional data without credentials:

```powershell
.\ThemeScope.cmd --fixture
```

Fixture mode uses a separate database. Linux/macOS setup, local SIP diagnostics,
updates and troubleshooting are in the [setup guide](docs/getting-started/setup.md).
No daily CSV uploads are required.

## What Refresh does

Refresh selects the latest safely completed US session, retrieves historical SIP
bars and calculates the research snapshot locally. A first run seeds history;
warm runs fetch missing/new sessions and a bounded repair window using an
incremental, auditable SQLite cache. Successful results and TXT exports publish
atomically. A failed refresh leaves the previous successful snapshot available;
always check the reported session and refresh status.

SPY/QQQ constituent rosters and theme membership are versioned, manually reviewed
configuration. They are not daily scanner inputs. TradingView CSV market-data
columns are never runtime prices. See [operations](docs/operations/refresh-and-maintenance.md).

## Methodology at a glance

- **Theme Strength:** 60% of the 21-session cross-theme percentile plus 40% of
  the 63-session percentile, using median Core/Enabler stock price returns.
- **Theme Trend:** a chain-linked synthetic theme index versus EMA21/EMA50;
  holdings drift between approved rebalances.
- **Peer delta (W):** a 60%/40% blend of 1M/3M stock-minus-peer returns, using
  leave-one-out theme-peer medians.
  It measures relative performance, not an expected return or entry signal.
- **Daily eligibility:** close ≥ $5, 10-session average volume > 500,000 shares,
  and target-session turnover ≥ $10 million. Eligibility does not change membership.
- **Directional / Countertrend:** separate research lenses using the approved
  market, theme and peer-relative rules. One stock can qualify in multiple themes;
  combined TXT output uses deterministic deduplicated placement.

Thematic ETFs have no calculation role. Breadth does not enter Theme Strength.
Prices are split/spin-off adjusted, not dividend adjusted. Read the
[current methodology](docs/methodology/README.md) for validity, lifecycle and exact rules.

## Optional frozen public snapshots

The local Python/SQLite app remains the live research runtime. A separate workflow
can freeze an already committed local dashboard into a **read-only static site**;
it does not host the database, refresh data or call providers. A synthetic static
demo is also available. Both preserve browser-local Saved and TXT downloads.

Publishing is explicit and requires an existing Cloudflare Pages project and local
Wrangler authentication. The current publisher deliberately requires a clean
`refactor/themescope-vnext` checkout and matching Pages production branch, even
though `main` is the product branch. Disable automatic Git deployments before
using the real snapshot publisher. See [public snapshot operations](docs/operations/public-snapshots.md).

## Project and documentation

| Location | Purpose |
| --- | --- |
| [src/themescope](src/themescope/) | Providers, calculations, research, SQLite and local API |
| [static/vnext](static/vnext/) | Current UI; the directory name is a compatibility identifier |
| [config](config/) | Methodology, reviewed memberships, manual rosters and evidence provenance |
| [scripts](scripts/) | Launch, validation, maintenance and explicit snapshot tools |
| [tests](tests/) | Offline unit, integration, numerical and browser regressions |
| [docs](docs/README.md) | Setup, methodology, operations, architecture, development and archive |
| [Gate E closure](docs/operations/gate-e-closure.md) | User-confirmed real Nov 6, Nov 9 and Nov 10 validation |

Developer setup and checks: [development guide](docs/development/README.md).
The [project map](docs/development/project-structure.md) explains retained legacy
files and generated/private directories. Historical migration and Gate A–E records
remain in the [archive](docs/archive/README.md).

## Limits and non-goals

- End-of-day research only: no intraday monitoring, execution, technical entries,
  stops, position sizes or trade recommendations.
- Provider access and complete usable inputs are required; unknown missing bars
  fail closed. Only explicitly approved terminal events may supply holding-accounting values.
- Saved is local to the browser/origin, not account-synced. Export identifiers must
  be verified; no venue is guessed.
- Legacy ETF-based history remains readable but cannot be spliced into the current
  custom-theme series. Back up runtime data before updates.
- Public snapshot publication is opt-in. This repository supplies no provider
  redistribution rights. A project-wide software license has not been declared;
  bundled Inter retains its [SIL Open Font License](static/Inter-LICENSE.txt).
