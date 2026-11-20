# ThemeScope

ThemeScope is a private, local dashboard for end-of-day US equity research. Work
through **Market → Themes → Primary** to review the market, compare themes, and
choose stocks for chart review. ThemeScope does not execute trades.

## Set up on Windows

ThemeScope requires Python 3.12 or newer. Install Python 3.12 with the Windows
Python Launcher to run the bundled commands. Run **setup.cmd** and enter your
Alpaca SIP key ID and secret once. Windows DPAPI encrypts the credentials for
your user account.

## Daily use

Run **ThemeScope.cmd**. It opens the dashboard on loopback and reuses a recognized
ThemeScope server. It checks the latest safely completed US session and starts
a refresh when needed. If a refresh fails, the previous successful snapshot
remains available. Use **Snapshot and refresh → Refresh Data** to retry or
refresh deliberately.

- **Market** shows the SPY and QQQ market environment, with IWM as context.
- **Themes** defaults to highest raw Theme Score first. Strong, Improving,
  Fading, and Weak describe the raw score and its raw five-session change.
  The table also shows 1M and 3M returns. Its scores, states, and default order
  are independent of the market side.
- **Primary** uses the current Long or Short market side to order eligible
  stocks for research.

| Command | Purpose |
| --- | --- |
| `ThemeScope.cmd` | Open the dashboard |
| `setup.cmd` | Install the application and configure credentials |
| `configure-credentials.cmd` | Replace stored provider credentials |
| `backup-data.cmd` | Create a timestamped backup of the research database |

[Setup guide](docs/getting-started/setup.md) ·
[Research methodology](docs/methodology/research-v2.md) ·
[Maintenance and backups](docs/operations/refresh-and-maintenance.md) ·
[Development checks](docs/development/README.md)
