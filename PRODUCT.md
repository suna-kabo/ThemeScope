# ThemeScope product boundary

ThemeScope is a local, end-of-day US equity research workspace: **Market → Themes
→ Stocks**. SPY/QQQ determine Market Bias; IWM is context only. Custom themes drive
Strength and synthetic Trend; stocks are researched against actual theme peers.
Directional and Countertrend are research lenses, not technical entries or orders.

Daily operation uses Alpaca historical SIP and a transactional SQLite snapshot,
without daily CSV uploads. Memberships and manual SPY/QQQ rosters are reviewed,
effective-dated configuration. Core/Enabler enter calculations; Related does not.
Multi-theme qualification is independent and combined exports deduplicate by the
approved deterministic rules. Thematic ETFs have no runtime calculation role.

The UI presents supplied results, contextual research inspectors, browser-local
Saved and TradingView TXT exports. Optional public snapshots are frozen/read-only;
the live backend remains local. No trade execution, stops, position sizing, intraday
feed, automatic constituent scraping or silent data-source substitution.

Launch rebalance remains Nov 6, 2026 close; first earned session is Nov 9.
Legacy series are retained separately, never spliced into current history.
[Gate E is CLOSED](docs/operations/gate-e-closure.md) after user-confirmed Nov 6,
Nov 9 and Nov 10 real validation. See the [README](README.md) for setup and
[current methodology](docs/methodology/README.md) for exact rules.
