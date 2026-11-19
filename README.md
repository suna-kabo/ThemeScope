# ThemeScope

ThemeScope is a private, local-only end-of-day equity research dashboard. It uses
completed US market sessions to help you understand the market environment,
compare raw theme strength, and choose eligible stocks for directional chart review.

## Windows quick start

1. Install Python 3.12 with the Windows Python launcher, then double-click
   **setup.cmd**. Enter your Alpaca market-data credentials when prompted.
   Alpha Vantage is optional. The credentials are encrypted for your Windows user.
2. Double-click **ThemeScope.cmd**. It opens the dashboard at
   http://127.0.0.1:8766 and automatically starts a refresh when the latest safely
   completed session is missing.
3. Open **Market → Themes → Primary**. Click a theme name to open Full Theme or
   use **Quick View** for a brief review. **TradingView TXT** downloads the session
   watchlist. **Saved** follows your local app across browsers and ports.

Leave the server console open during use. An additional launch reuses a recognized
server on the same port. Use **Snapshot and refresh → Refresh Data** for a manual
retry or after editing reviewed configuration. A failed refresh retains the previous
successful results.

Use **configure-credentials.cmd** to replace keys and **backup-data.cmd** to back
up your research database while ThemeScope is running.

- [First-time setup and existing installations](docs/getting-started/setup.md)
- [Daily research workflow](docs/getting-started/research-workflow.md)
- [Refresh, backup and restore](docs/operations/refresh-and-maintenance.md)
- [Research rules](docs/methodology/research-v2.md)
- [Architecture and development](docs/README.md)

Legacy manual-CSV history and original inspection checkpoints are retained for
reproduction. Current research uses its separate SQLite history.
