# ThemeScope

ThemeScope vNext is a private local end-of-day equity-theme research dashboard.
The user reads the unchanged SPY/QQQ Market Matrix, compares custom themes, and
examines stocks against their actual theme peers. Research priorities are not
trade entries. IWM supplies context only.

Normal operation uses Alpaca historical SIP, calculated EMAs/returns and atomic
SQLite snapshots; no daily CSV upload. Effective-dated manual SPY/QQQ rosters and
quarterly/ad-hoc membership reviews remain separate configuration workflows.
Only Core and Enabler enter calculations; multi-theme qualification is independent
and combined export placement is deterministic. Thematic ETFs have no runtime role.

Launch rebalance: 2026-11-06 close; first earned session: 2026-11-09. Pre-launch
market context is useful without fabricated theme history. Bootstrap initializes
indicators only, never signals. Legacy historical readers remain explicitly
available and their series cannot be spliced into vNext. No trading or deployment.
