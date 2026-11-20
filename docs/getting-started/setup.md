# Set up ThemeScope on Windows

Install Python 3.12 with the Windows Python launcher. From your ThemeScope folder,
double-click **setup.cmd**. Setup creates an isolated Python environment, installs
the application dependencies, and prompts for your Alpaca key ID and secret if
credentials are missing. Use an Alpaca account with historical SIP market-data
access. Alpha Vantage is optional and supplies earnings context.

The credential prompts hide input. Windows DPAPI encrypts the file at
`%LOCALAPPDATA%\ThemeScope\provider.dpapi` for your Windows account. Double-click
**configure-credentials.cmd** to replace the stored keys. A running ThemeScope
reads the updated file on its next refresh.

Double-click **ThemeScope.cmd** to open the dashboard. Keep the console open while
using the app. Close it with Ctrl+C when finished. If an old ThemeScope or another
app owns the default port, close the known server or use
`ThemeScope.cmd --port 8767` from a terminal. ThemeScope never stops the port owner.

## Existing installation

Keep `runtime/vnext/` in place. If you are upgrading a running server, stop that
server once with Ctrl+C, then launch the current version. If the dashboard asks
for an updated snapshot, use **Refresh Data**. Saved is stored per Windows user
and is available across browsers and local ports.

Developers can run `ThemeScope.cmd --fixture` against isolated synthetic data. Use
**Refresh Data** to populate it. The fixture database and Saved list are separate.
