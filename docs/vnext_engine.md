# Gate B — offline calculation engine

Gate A (`359572c`) remains approved and unchanged. Phase 2 is `61fe259`; Phase 3
is `1c10c5c`. The Gate B checkpoint adds Phase 4 without wiring the legacy runtime
to vNext. All launch dates, evidence statuses and production blockers are preserved.

## Calculation contract

`themes/calculations.py` consumes typed bars and an explicit ordered completed US
session calendar. The live calendar/provider adapters belong to later phases.
Each return uses its exact 21/63-session endpoints; absent bars never shorten the
calendar. Missing observations remain in configured coverage denominators.
Per-horizon median coverage and LOO coverage are independent. Single-valid-theme
percentiles are unavailable. Decimal operations use a local 34-digit context,
including fixed rounding and traps, independent of caller settings.

Adjusted prices must use split/spin-off adjustment without dividends. The raw
regular-session close and volume are separate fields for daily liquidity. Returns
are fractions (0.01 means 1%); percentiles, scores and breadth are on a 0–100 scale.
No rounding is applied before qualification boundaries.

`themes/index.py` initializes at an explicitly supplied close and never selects a
launch date. New live holdings are taken from membership effective on the next
session. Old holdings earn approval t; rebalance follows t's return; the new set
first earns t+1. A point records earned symbols separately from post-close weights.
Equal weighting occurs only at initialization, membership changes and explicitly
supplied formal rebalances. Missing held/new-member prices make the series
unavailable instead of dropping members or applying an 80% portfolio shortcut.

Bootstrap points are labeled and may only seed indicators. Their levels are scaled
to the live initialization close before SMA-seeded EMA21/50 calculation. Bootstrap
observations never become live history transitions. Live history compatibility
requires the same methodology, history schema, theme and series, and immediately
adjacent sessions on the supplied calendar. Legacy and missing prior history yield
unavailable transitions. Membership rebalances do not create a new methodology
series or an artificial index jump.

`research/engine.py` composes returns, scores, context-only breadth, index trends,
Primary priorities and LOO metrics. It takes the already-computed Market Matrix
direction; it does not calculate or change that matrix. Independent qualification
is retained for every effective Core/Enabler relationship. Daily liquidity failure
does not change membership, medians or peer denominators.

`research/exports.py` selects combined placement by Core before Enabler, stronger
directional W, then lexical theme ID. Themes and symbols are sorted for repeatable
TXT output. Individual theme exports retain all qualifying relationships. Dashboard
records include Assigned section and Also qualifies in. No hard stock cap exists.
An unresolved TradingView symbol mapping raises an error; exchange prefixes are
never guessed. The synthetic fixture supplies its own explicit mappings.

## Storage and history schemas

SQLite `PRAGMA user_version=1` and `schema_version(1)` describe the new isolated
runtime schema. No legacy database or history is migrated in place.

| Table | Identity and purpose |
| --- | --- |
| instruments | ticker; instrument metadata |
| daily_bars | run, ticker, session; exact typed price inputs |
| membership_reviews | review ID; review metadata, not an approval mechanism |
| theme_index | run, theme, session; level, weights and bootstrap provenance |
| theme_snapshot | run, theme; metrics and compatible-history metadata |
| stock_theme_snapshot | run, ticker, theme; independent relationship results |
| market_roster | benchmark, effective_from; manual roster metadata |
| market_snapshot | run; preserved market results |
| refresh_run | run ID; session, methodology, config hash, status, error class |
| earnings_event | ticker, event date; optional provider metadata |
| publication | singleton pointer to the active successful run and dashboard payload |

Payloads use canonical JSON with exact decimals serialized as strings. Foreign
keys bind results to refresh runs; primary keys reject duplicate observations and
relationships. New snapshots use `themescope-vnext-snapshot-1`; live theme history
uses `themescope-vnext-history-1`. Schema versions other than the supported version
are rejected. Tables for provider/roster/earnings integration are reserved; their
adapters remain later-phase work.

`BEGIN IMMEDIATE` serializes writers. Data, result rows and the publication pointer
commit together. Incomplete data or exceptions roll back all writes and record an
incomplete run; the prior publication survives. An older replay is retained but
cannot replace a newer active session. Same-session deterministic replay is
allowed. Exact-session history queries never fall back to older or legacy records.

The current end-to-end persistence helper accepts only explicitly labeled synthetic
fixtures. Production refresh orchestration, provider validation, local UI and
filesystem TXT publication remain later gates. Configuration remains versioned text
in Git; no runtime database is included in the checkpoint.

## Reproduce the inspection fixture

Run from the repository root with Python 3.12:

```sh
python -m unittest discover -s tests -v
python scripts/vnext_fixture_report.py --output /tmp/themescope-engine-report.json
python scripts/build_inspection_bundle.py --test-report inspection/test-report.txt --engine-report /tmp/themescope-engine-report.json
```

Open `inspection/index.html` locally. The fixture uses fictional symbols and an
explicit synthetic weekday calendar, not a claimed live US holiday calendar or
approved launch session. Its complete formula/LOO results and TXT exports are in
`inspection/engine-report.json`. Synthetic prices are generated in memory only.

Numerical rebalance regression: level 100 at Thursday close; old holdings gain
10% Friday, yielding 110; rebalance Friday close; new holdings gain 20% Monday,
yielding 132. Their Friday gain and the removed holdings' Monday loss do not enter
the index. A separate drift regression yields 160 naturally versus 144 when an
explicit close rebalance is requested.

## Remaining blockers

335 evidence refreshes, four inherited-evidence findings, documented deterministic
industry rules and an explicitly approved launch session remain outstanding. All
729 proposed launch effective dates stay pending. Live SIP, dated SPY/QQQ rosters,
Windows-native validation and later runtime integration remain future gates.
No evidence was resolved, no live credentials used, no IEX fallback introduced,
no main merge or deployment performed, and no legacy functionality retired.
