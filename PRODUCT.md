# ThemeScope product scope

ThemeScope is an end-of-day equity research application that runs on the user's
computer. Market data, reviewed research, and personal bookmarks stay local.
ThemeScope supports chart review through TradingView TXT downloads.

- **Market** identifies the research side from the SPY and QQQ Market Matrix. IWM
  supplies small-cap context.
- **Themes** lists tracked themes by Research Priority and shows State, raw
  5-session Change, and 1M / 3M returns. Full Theme and Quick View hold the secondary
  price, participation, and membership evidence.
- **Primary** orders daily-eligible Core and Enabler members of researchable themes
  for chart review. Filters affect the view. TXT downloads use the full committed
  session in research order.
- **Saved** stores tickers and their remembered theme context per local user.

The Windows launcher uses a loopback server, a versioned completed-session calendar
and an atomic SQLite snapshot. Provider credentials are encrypted with Windows
DPAPI and are read only by the server. A refresh failure leaves prior research
available. See the versioned [research rules](docs/methodology/research-v2.md).
