# ThemeScope product boundary

ThemeScope is a local, private, completed-session equity research application.
Its workflow is Market → Themes → Daily Research List → chart review. The user
judges actual chart setups; ThemeScope never selects entries, stops, positions,
reversal trades or executions.

SPY/QQQ determine market direction; IWM is context only. Reviewed effective-dated
Core/Enabler memberships drive theme calculations; Related is context. Thematic
ETFs have no calculation role. Research v2 separates structural theme strength
from five-session change. Leading, Improving and Fading themes retain all
daily-eligible members. Peer strength orders stocks; its sign never hides them.

The manually supplied TradingView Base Market Universe is a maintenance input,
not a daily dependency. Daily operation uses swappable market-data providers,
Alpaca historical SIP and transactional SQLite publication. Failed refresh keeps
the prior successful snapshot. No silent SIP/IEX substitution, scanner scraping
or trading endpoints are permitted.

The UI presents deterministic results, contextual inspectors, compatible
browser-local Saved research and TradingView watchlists. Optional public snapshots
are frozen/read-only and require explicit publication authorization. Provider
credentials, runtime databases and raw private market data never enter output.

Launch rebalance remains November 6, 2026 close; first earned session November 9.
Legacy and vNext history remain separate. Gate E is CLOSED, as recorded in
[the closure record](docs/operations/gate-e-closure.md). Current selection rules
are defined in [Research Logic v2](docs/methodology/research-v2.md).
