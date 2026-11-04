# GOALS.md — ThemeScope vNext

ThemeScope vNext is complete when:

1. Thematic ETFs no longer affect calculations.
2. Normal daily use requires zero CSV uploads.
3. Custom themes and effective-dated Core/Enabler membership drive all theme metrics.
4. Theme median returns, Theme Score and LOO W are deterministic and tested.
5. Synthetic theme index safely handles splits, spin-offs and membership changes.
6. SPY/QQQ Market Matrix behavior is preserved.
7. SPY/QQQ roster updates remain manual and effective-dated initially.
8. Alpaca SIP historical-data PoC passes locally without IEX fallback.
9. SQLite persistence and atomic refresh preserve prior good state on failure.
10. Local Windows one-click launch and Refresh Data UX work.
11. TradingView TXT exports preserve multi-theme relationships while combined export deduplicates deterministically.
12. Legacy history stays readable and is never relabeled as vNext history.
13. No secrets, runtime DBs, public deployment or unauthorized scraping are introduced.
14. Tests pass and user can download inspection checkpoints from GitHub branches.
