# Set up ThemeScope on Windows

Install Python 3.12 with the Windows Python launcher. From your ThemeScope folder,
double-click **setup.cmd**. Setup creates an isolated Python environment, installs
the application dependencies, and prompts for your Alpaca key ID and secret if
credentials are missing. Use an Alpaca account with historical SIP market-data
access. Alpha Vantage is optional and supplies earnings context.

The credential prompts hide input. Windows DPAPI encrypts the file at
`%LOCALAPPDATA%\ThemeScope\provider.dpapi` for your Windows account. Double-click
**configure-credentials.cmd** to replace the stored keys. A running ThemeScope
reads the updated file on its next refresh. The developer environment overrides
`APCA_API_KEY_ID`, `APCA_API_SECRET_KEY` and `ALPHAVANTAGE_API_KEY` take precedence
for each value when set in the server environment.

Double-click **ThemeScope.cmd** to open the dashboard. Keep the console open while
using the app. Close it with Ctrl+C when finished. If an old ThemeScope or another
app owns the default port, close the known server or use
`ThemeScope.cmd --port 8767` from a terminal. ThemeScope never stops the port owner.

## Existing installation

Keep `runtime/vnext/` in place. If you are upgrading a running server, stop that
server once with Ctrl+C, then launch the current version. The first successful
current-rules refresh supplies the new Themes and Primary contract. Use **Refresh
Data** if an earlier automatic attempt has already run. History stays in the same
database and remains readable.

To import old Saved research, first open the new ThemeScope server at the same
address and port in the browser profile where you saved the tickers. The app merges
existing bookmarks and remembered themes into local application state once and
then uses that shared state across browsers and ports.

Developers can run `ThemeScope.cmd --fixture` against isolated synthetic data. Use
**Refresh Data** to populate it. The fixture database and Saved list are separate.
