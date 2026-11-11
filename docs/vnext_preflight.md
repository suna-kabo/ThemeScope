> **Historical checkpoint.** Status, counts and instructions below describe that
> checkpoint, not current operation. Gate E is now **CLOSED**; Nov 6, Nov 9 and
> Nov 10 live validation passed per the user. See the [closure record](operations/gate-e-closure.md)
> and [current documentation](README.md).

> Historical gate report. Launch/evidence status below describes that gate.
> Current approved activation and Phase 9: [vnext_launch.md](archive/migration/vnext_launch.md).

# vNext preflight — 5 November 2026 (Hong Kong)

**Update after the initial comparison:** bundle v2 supplies the full 1,525-row
universe. All proposed launch/Watch-only symbols are present and all measurable
scanner policy checks pass. Common-stock status is user-attested because there
is no security-type column. The user also resolved rebalance timing: old members
earn t, rebalance at t close, effective_from is t+1 (next trading session).
Launch dates remain pending. See PLANS.md and the amended methodology. The
original findings below preserve the pre-edit audit record; items 2 and the
timing portion of 3 are now resolved. Evidence findings remain open.

Compared every file in ThemeScope_vNext_Handoff_Bundle.zip with GitHub main at
`cf4fdb1e4784ff6fbc7183d5e709ffae044ec2fe`. The user's request governs this task;
the methodology and handoff are the requested migration specification, while
drafts/checklists do not establish that memberships, accounts or live tests have
already been approved/completed. No deployment is authorized.

## Blocking findings and scope

1. **Inherited evidence is not uniformly cleared.** Four proposed Core relations
   (AMZN and GOOGL in each of cloud-platforms and internet-commerce) have
   `existing_repo_primary_source_evidence`. The cited ticker/URL records exist on
   main, but explicitly say `Unresolved` and that cloud exposure was not screened.
   They do not establish accepted classifications under the new charters, or an
   Internet Commerce review. See ledger lines 574, 577, 658, 665 and main's
   `config/evidence_reviews.json:1067,1085`. This does not prove those memberships
   are wrong; it prevents declaring them cleared from existing records alone.
   Resolve them alongside the supplied 335 pending relationships. Preserve the
   original ledger and evidence statuses; never invent verification.

2. **The full November 5 review universe is missing.** The supplied delta has
   151 tickers, only 75 of which are active launch tickers. The other 596 of 671
   launch tickers cannot be checked against a full source universe available in
   this workspace. The ledger also lacks 10-day volume, turnover and security-type
   facts for independent validation of the complete scanner policy. Price, market
   cap and exchange checks pass, but are insufficient. Older configurations and
   October scanner files cannot establish November 5 eligibility. This blocks
   Phase 1's production universe-validation claim/Gate A, not provisional models
   or fixture work. Required: the full source CSV/location and filter metadata.

3. **Activation dates and rebalance timing are unresolved.** All 729 proposed
   effective dates are blank. A review snapshot date is not approval of the first
   live US session. Leave production activation pending. The spec also does not
   define whether new holdings earn the effective session's return using
   prior-close rebalance prices, or old holdings earn that return and rebalance
   at the effective session's close. This changes synthetic index/EMA results.
   Pause that specific calculation until clarified; current main has no custom
   theme index that resolves it. Bootstrap must never become apparent live history.

4. **Accepted industry rules need traceability.** 318 relations have
   `industry_rule_accepted`, but the bundle has no separate versioned rule IDs,
   predicates or approval records. Charters and scanner industry labels are not
   enough to reproduce all assignments (RUN's scanner industry is Semiconductors,
   but its assignment is Solar). Preserve the supplied declaration without
   pretending it is primary-source verification. Link the intended approved rules
   and explicit exceptions before final evidence clearance. Do not invent rules.

Findings 1, 2 and 4 concern validation/production cutover. They do not prohibit
implementation using explicitly provisional configuration and synthetic fixtures.
Finding 3 pauses the effective-session index rule and production activation.
The methodology's explicit evidence gate takes precedence over the README's
broader wording suggesting a refresh for all non-verified rows.

## Current main and intentional migration differences

The original clean `work` checkout at `1e46d6a` is behind main. GitHub's live main
was checked through the connector and agrees with local origin/main at `cf4fdb1`.
An isolated checkout of that exact commit was used. PR #7's blank-unused-stock
metric fix must be retained. Main has no root AGENTS.md or GOALS.md.

| Area | Current main | Required vNext |
| --- | --- | --- |
| Universe | 53 anchor-backed rows; 901 relations, 563 stocks | 44 Active, 8 Watch-only; proposed 729 relations, 671 stocks |
| Membership | 20-member capacity; importer slices rows | Effective dates, Core/Enabler/Related; no 20 cap |
| Breadth | Minimum 8 valid, 80% coverage | Minimum 5, 80% coverage; context only |
| Theme score | ETF returns; global 80% score-universe floor | Member medians, 21/63 sessions; valid Active-theme percentiles; 60/40; no undocumented global floor |
| Theme trend | ETF close vs imported EMA21/50 | Chain-linked synthetic index; drifting holdings; split/spin-off price adjustments |
| Stock W | Stock vs ETF | Leave-One-Out medians; >=4 other peers, >=80% peer coverage |
| Liquidity | Turnover >= $10M; AvgVol10 >500K | Preserve boundaries; add explicit close >=$5; derive from completed daily bars |
| Exports | Independent per-theme qualification already exists; combined first-theme wins and reserves anchors | Retain all qualifying relations; combined Core before Enabler, directional W, then lexical theme ID; remove thematic anchors |
| Market | Pure 64-case SPY/QQQ matrix; IWM has no vote | Preserve matrix and priority exceptions; dated manual rosters and provider bars |
| Completeness | Missing configured stocks can publish with data_complete=false | Missing required current-session data preserves previous active snapshot |
| History | JSON records, journaled file publication | Separate SQLite vNext series; legacy records remain readable and unchanged |
| Runtime | Five CSV roles and static preview | Loopback FastAPI refresh; no daily CSV; optional earnings |
| Publication | Legacy site allowlist and separate preparation | No provider-data deployment; fixture-only inspection outputs |

Source locations: `manual_csv.py:197,217,290`, `daily_lists.py:35`,
`research_policy.py:49,83`, `local_history.py:8`, `local_publication.py:119`,
`generate_dashboard.py:1296`, `config/manual_csv.json:24`.

Legacy identifiers: snapshot `manual-csv-2`, methodology `manual-csv-1`, history
`themescope-ranking-history-1`, EMA `tradingview-daily-price-ema21-ema50-1`, priority
`ema-score-priority-2`. Never relabel them as vNext. Existing priority exceptions
already require adjacent, compatible prior-session history.

## Bundle checks

All 14 documents/data files were read; all CSV rows were parsed and checked.

- 52 taxonomy rows: 44 Active, 8 Watch-only.
- 729 launch relations: 659 Core, 70 Enabler; 671 tickers; 57 multi-theme tickers.
- 21 Watch-only candidate relations in seven themes; Cannabis has none.
- Evidence declarations: 335 refresh required, 318 industry-rule accepted,
  65 inherited repository evidence, 11 newly verified. This audit did not perform
  fresh SEC/IR verification.
- No duplicate relationship keys or unknown launch theme IDs; all Active proposed
  counts are >=5. All price/cap/exchange snapshots pass the corresponding filters.
- Charter counts, member-count table and ledger agree. All 25 overlap rows match
  recomputed intersections/Jaccard/containment, with no missing overlapping pairs.
- The 335 queue keys and shared field values exactly match pending ledger rows.
- All 65 inherited ticker/URL references exist in repository evidence; matching
  URLs does not establish new-charter qualification.
- Removing all pending rows would put 17 Active themes below five members; this
  is not a valid shortcut to declaring the proposed taxonomy launch-ready.
- All 729 effective dates are blank. The 151-row delta is not the full universe.

## Baseline on unchanged main

Python 3.12.14; Node 24.19.0.

| Command | Result |
| --- | --- |
| python -m unittest discover -s tests -v | 207 run; 206 passed; 1 Windows-only skip |
| python -m compileall -q src scripts tests | Passed |
| node --check static/dashboard.js | Passed |
| node tests/test_dashboard.js | Passed |
| python tests/smoke_local_install.py --browser | Passed on Linux |

An initial sandboxed unit run had 12 socket-permission errors in local-server
tests. The unchanged suite passed with local socket access. Native Windows CMD
and Windows locked-file semantics were not tested locally.

The existing smoke test passed clean setup, two-session history, failure
preservation, older replay, HTTP preview/downloads, and browser navigation,
methodology, all 64 matrix cases, weighted stock filters and light/dark layouts.
Reported browser checks had zero JavaScript errors or automatic external requests.

No complete real November 4 input set is available. The saved repository fixture
is October 22. A separately labeled synthetic January 3, 2024 baseline captures
all 53 anchor rankings, the Market decision, Primary exports and history. It uses
563 synthetic stock rows and 500/100/2000 synthetic breadth rows; it is not a
reconstructed November 4 result or genuine user history.

## Implementation sequencing

The comparison and blockers were reported before migration code edits. Record
Phase 0 on `refactor/themescope-vnext`, based on the audited main. Keep legacy
runtime and history unchanged. Do not claim Gate A while the source-universe
validation cannot be completed. Record the rebalance decision in PLANS.md before
implementing its dependent calculation.

Production cutover additionally needs resolved evidence, approved activation
dates, dated SPY/QQQ roster inputs and the user's local live-SIP test. Live SIP
may remain pending through fixture Gate C, as the handoff explicitly permits.
Do not request keys for cloud work. No source push, merge or deployment was made
during the preflight audit.
