# ThemeScope vNext migration plan

## Resume here

Implementation branch: `refactor/themescope-vnext`.
Base main: `cf4fdb1e4784ff6fbc7183d5e709ffae044ec2fe` (includes PR #7).
Phase 0 commit: `8764575` — baseline and workflow/spec documentation.
Phase 1: domain/configuration work validated for **Gate A**.
Checkpoint: `inspection/vnext-a-domain`, pointing at the Phase 1 commit.
Next unfinished phase: **Phase 2, SQLite and pure calculation functions**.
Do not restart the baseline or reimport/reclassify the proposed launch ledger.

The user's latest continuation request ends at the next meaningful gate. Gate A
is the current checkpoint; no Phase 2+ runtime has been implemented yet.

## Completed work

- Read all 14 initial bundle files and compared them with live GitHub main before
  code changes. Full comparison: [preflight](docs/vnext_preflight.md).
- Captured an unchanged-main synthetic manual-runtime regression fixture:
  January 3, 2024; 563 stocks, 53 anchors; all theme scores/ranks, Primary exports,
  legacy history identifiers and the complete 64-case Market Matrix.
- Installed the supplied AGENTS/GOALS drafts and handoff/spec documents.
- Read bundle v2. Its complete 1,525-row Stock review CSV resolves the missing
  universe finding. All launch and Watch-only tickers are present; every measurable
  scanner filter passes; no duplicate symbols.
- Installed versioned charters, 729 proposed relationships and 21 Watch-only
  candidates. No legacy config was overwritten. Raw scanner prices/volumes are
  excluded from the new committed configuration.
- Added typed theme/status/role, effective membership and market-roster models;
  duplicate/overlap/date/universe/Active-minimum validation. Pending and Watch-only
  memberships cannot calculate. No permanent home theme or 20-stock cap.
- Added a scanner validator and proposed-diff function that never writes membership.
  Exact private v2 source validation matches the committed identifier manifest.
- Added offline checks, isolated vNext bootstrap and safe inspection generation.
  Inspection rejects .env files, secret patterns, SQLite databases, provider payloads,
  personal absolute paths, symlinks and unrelated destination files.
- Replaced legacy test provider payloads with deterministic synthetic equivalents
  for inspection ZIP safety. Existing import/publication tests still pass.
  Original payloads remain in pre-migration Git history; genuine runtime history
  and legacy production code are unchanged.

## Approved timing clarification — do not change

Old membership earns the entire close-to-close return ending on approval session t.
Rebalance at t close. New membership first earns the next US trading session's
return. `effective_from` is that next session; `effective_to` is exclusive.

The user has not selected launch session L. Keep all launch dates pending. When L
is explicitly approved, old membership owns L's return, rebalance at L close, and
new membership first earns the next US session's return. Never infer L from the
November 5 export filename or splice legacy ETF returns into a vNext series.

The methodology is amended. Phase 1 tests prove old/new membership assignment
across a Friday approval and Monday effective session. **Phase 3 still must add
the numerical synthetic-index rebalance-boundary test** showing old holdings earn
t and new holdings earn t+1. Bootstrap initializes indicators only and must never
produce apparent live signal history.

## Production blockers (not Gate A implementation blockers)

- 335 primary-source refresh relationships remain pending, preserved in status
  and in a sanitized review queue.
- Four additional AMZN/GOOGL cloud-platforms/internet-commerce relationships point
  to repository records explicitly labeled Unresolved. They need relationship-
  specific resolution; a cited URL alone is not evidence approval.
- The 318 industry-rule-accepted declarations need links to documented approved
  deterministic rules/explicit exceptions before final evidence clearance. Do not
  invent rules or relabel these declarations as primary-source verification.
- Launch rebalance session/effective dates are not approved. Production is off.
- Live SIP success and Windows-native launch validation remain later local checks.
- Actual dated SPY/QQQ rosters remain a later manual import requirement.

Common-stock status is user-attested from the scanner setup; the CSV has no
security-type column. Source SHA256:
`e2b271c54bde7498ff1d9712452b18977cf4321f8e755ec67ca0efbc64a9e374`.
The 151-row delta is not the authoritative review universe.

## Validation and safety

Unchanged-main baseline: 207 unittest cases, one Windows-only skip; JS checks,
compilation and clean-install/browser smoke passed. Phase 0: 209 cases, same skip.
Phase 1's final test report is in `inspection/test-report.txt`.

Tests use fixtures/mocks. Linux smoke checks cover clean setup, two sessions,
failure preservation, older replay, HTTP previews/downloads, all 64 Market Matrix
cases and light/dark browser layouts. Native CMD/Windows locked-file semantics
were not executed here. Local HTTP tests require loopback socket access.

Legacy identifiers remain `manual-csv-2`, `manual-csv-1`,
`themescope-ranking-history-1`, `tradingview-daily-price-ema21-ema50-1`,
`ema-score-priority-2`. New config has schema 1 / `themescope-vnext-1` methodology;
the runtime SQLite schema is not implemented yet.

Only source and synthetic inspection artifacts may be pushed to the implementation
and prescribed checkpoint branches. No main merge, deployment, trading endpoint,
live Alpaca credentials, IEX fallback or runtime DB is part of this gate.

## Remaining handoff sequence

1. Phase 2: pure 21/63-session returns, member medians/coverage, tied percentiles,
   60/40 score, LOO W and SQLite storage; boundary/missing/corporate-action tests.
2. Phase 3: chain-linked drifting index, approved timing, explicit bootstrap and
   compatible adjacent-session history.
3. Phase 4: daily liquidity, independent qualifying relationships and deterministic
   combined placement; safe fixture report and **Gate B**.
4. Phase 5: FixtureProvider/Alpaca SIP adapters; paging, retries, auth/subscription
   failures, split/spin-off handling and local access PoC; **Gate C**. Live SIP may
   remain a local user validation item.
5. Phases 6–8: unchanged Market Matrix, dated manual rosters, optional earnings,
   loopback FastAPI/atomic refresh, Windows launcher/UI; **Gate D**.
6. Phase 9: retire legacy default calculations only when A–D and evidence/activation
   requirements permit cutover; retain legacy history readers.
7. Phase 10: independent review passes, E2E/failure/replay/corporate-action/provider
   tests, secret/data scan; **Gate E**, then PR to main. No self-merge/deployment.
