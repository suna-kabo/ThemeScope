# AGENTS.md — ThemeScope

## Product scope
ThemeScope is a local, private, end-of-day research dashboard.
It ranks custom equity themes and filters research candidates.
It is not a trade-execution or signal-execution system.

## Non-negotiable methodology
- Thematic ETFs have zero calculation role.
- SPY/QQQ remain the Market Matrix benchmarks; IWM is context only.
- Theme 1M = median of valid Core+Enabler 21-session price returns.
- Theme 3M = median of valid Core+Enabler 63-session price returns.
- Theme Score = 60% 1M cross-theme percentile + 40% 3M percentile.
- Stock relative performance uses Leave-One-Out peer medians.
- W = 60% ER1M + 40% ER3M.
- Long Primary requires W > 0; Short Primary requires W < 0.
- Theme breadth is context only.
- Synthetic theme trend uses a chain-linked index and EMA21/EMA50.
- Do not invent or change formulas without explicit user approval.

## Membership rules
- Core and Enabler enter calculations; Related does not.
- Multi-theme relationships are valid.
- Membership is effective-dated and never rewritten retrospectively.
- Quarterly scanner review proposes changes; it never auto-applies membership.
- Do not recreate a hard 20-stock cap.

## Data safety
- Do not automate TradingView scraping/scanner endpoints.
- Market-data provider must be swappable.
- Alpaca integration is market-data only. Never call order/trading endpoints.
- Never silently fall back from SIP to IEX.
- Never commit credentials, .env files, local DBs or raw private market data.
- Never publish market data or deploy a public site without explicit authorization.
- Local web server must bind 127.0.0.1 by default.

## Branch and compatibility safety
- main must stay usable.
- Use a task branch for changes; keep main usable. Merge only within user-authorized scope.
- Preserve legacy history.
- Old ETF history and vNext history are incompatible.
- Failed refresh must preserve the prior successful snapshot.
- Use fixtures before live-provider tests.

## Engineering expectations
- Python 3.12.
- Prefer small modules over expanding generate_dashboard.py.
- SQLite is standard-library sqlite3 unless a strong reason requires otherwise.
- Provider calls must be mockable.
- Every calculation has unit tests with edge cases.
- Each bounded implementation change ends with relevant checks and a commit.
- Keep methodology constants centralized and versioned.

## Inspection workflow
Permanent annotated gate-a, gate-b, gate-c, gate-d and gate-e-closed tags preserve
the original reviewed checkpoints. Do not move or replace them. The historical
inspection/ fixture remains unchanged provenance. Merged inspection heads may be
retired only after tag verification and an explicit branch-cleanup authorization.
New inspection bundles must be allowlisted and explicitly requested; never include
secrets, runtime DB, raw market data or absolute personal paths.

## Current milestone and documentation
Gate E is CLOSED after user-confirmed real Nov 6, Nov 9 and Nov 10 validation.
See [the closure record](docs/operations/gate-e-closure.md) and
[current docs](docs/README.md). Original gate/phase reports are historical and do
not reinstate obsolete blockers. Stable vnext schema/path identifiers remain intact.

## Production workflow
main is stable production and the only public publishing source. Future visual
experiments start from main on feature/ui-v3 (or another scoped task branch).
Production maintenance lands on main only after relevant checks and preserves
financial/research rules. Keep the old implementation
branch until the external default/Pages cutover and a real main publication succeed.
