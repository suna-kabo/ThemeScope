# PR #10 fresh adversarial Ponytail review

What this change does: Research v2 retains every daily-eligible Core/Enabler member of a researchable theme and orders peers without a W sign gate. UI v3 presents explicit directional states and read-only current-basket comparisons while preserving official membership and accounting history.

Reviewed the current `feature/research-v2-ui-v3` working tree against `main`, including tracked changes and the new untracked production/test/document files. Expected load: one local researcher with hundreds of displayed relationships. This review used the master contract and approved rules as oracles, rather than treating agreement between implementation and its tests as proof.

## Findings resolved

1. **Simulation evidence includes comparisons production rejects** (`scripts/research_v2_simulation.py:182`)
   - **What this is:** The offline simulation supplies state counts, churn and temporal persistence evidence for the five-session rules.
   - **Problem:** It compares current and prior scores without checking the global 1M, 3M and combined scored populations. A read-only examination of the actual pinned run-8 observations found **10 of the 189 eligible five-session pairs** have different populations. Those pairs still drive Improving/Fading and persistence metrics, whereas production `reconstruct` deliberately makes their changes unavailable.
   - **Fix:** Retain both horizon populations and combined scored population per diagnostic date. When any differs at t and t-5, withhold recent change globally, retaining structural Leading/Lagging fallback, and exclude unavailable changes from completed recent-state episodes. Regenerate aggregate evidence and add a changed-population oracle.
   - **If we skip it:** The reported temporal evidence describes a different comparison policy from the shipped research model.
   - **Resolution verified:** The simulator now checks all three populations, uses structural fallback for product counts, censors recent-state episodes and excludes unavailable comparisons from churn. Eight focused tests passed, including a real-bar horizon-population counterexample and mixed available/unavailable adjacent dates. The pinned rerun reports 179 comparable / 189 eligible pairs, 10 population mismatches, five initial unavailable dates and 176 valid adjacent churn pairs. Both reports were regenerated; the database file hash and pinned observation digest stayed unchanged.

   Reproduction: call `load_inputs(ROOT, ROOT/'runtime/vnext/runtime.sqlite')` in read-only mode; for every date in `sessions[63:]`, use `benchmarks(..., members_for=lambda key: members.get(key, ()))`; record the theme-ID sets whose first return metric, second return metric and score are non-null. Comparing those triples five dates apart yields 10 unequal pairs. No raw market values or database writes are needed.

2. **The public validator accepts contradictory research semantics** (`scripts/research_v2_projection.py:27`)
   - **What this is:** Public projection claims to verify the supplied normalized research contract and exports before freezing it.
   - **Problem:** It checks allowed state names and the currently selected state, but never derives both directional states from structural score, recent change and policy. In `demo_snapshot()`, alpha has score 100, Long Leading and Short Lagging. Replacing only `short_state` with `Leading` is accepted by `project_snapshot`. The same boundary only checks the membership fingerprint format, not its agreement with relationships, and does not cross-check relationship assignment metadata with export assignments.
   - **Fix:** Check both supplied states against the declared rule, recompute the membership fingerprint from the supplied calculation relationships, and compare relationship assignment metadata with the validated export assignments. Add independent tampering regressions for these cases.
   - **If we skip it:** A snapshot can publish false opposite-side states, basis provenance or placement metadata while claiming validated consistency. This is an integrity issue; this review found no credential leak.
   - **Resolution verified:** Inspected the shared pure state rule and current validator. Direct independent probes now reject the opposite-side-state example, a forged fingerprint, changed relationship placement and a below-floor close with stale eligible=true. An unchanged synthetic public source still projects successfully.

   Pre-correction reproduction: obtain `s=demo_snapshot()`, set `s['synthetic_fixture']=False` and `s['provider_health']={'status':'Healthy'}`, then set `s['research_v2']['themes']['alpha']['short_state']='Leading'`. Before correction, `project_snapshot(s,s['session'])` accepted and retained the false state; the final validator rejects it.

## Coverage

- Traced production refresh, current-basket reconstruction, membership signatures, population guards, state selection, liquidity, exports, queries, storage/history and frontend presentation callers.
- Checked all changed production/config/CI/UI paths, affected test and fixture changes, documentation and generated report structures. For large generated JSON artifacts, checked all parsed collections, aggregate scope/counts, source hashes and generator provenance rather than treating thousands of generated lines as extra research evidence.
- Checked the fourteen prior hypotheses against actual source. Normalized revision-2 fields, explicit Neutral/Unclassified no-side behavior, selective same-set/different-order behavior, Short directional rank ties, first-refresh comparison, forward-only seven-member overlay and truthful 560-proposal scope are present.
- Retained 21/63-session medians, 60/40 score and peer weights, structural boundary 50, exact five-session comparison, 20-session raw-dollar liquidity, price >5 and ADTV >=10M. No breadth/trend veto, stock cap, W sign gate or Countertrend selection was introduced.
- Reviewed the old-snapshot path, Saved context preservation, read-only official history route, public field allowlist, failure-preservation caller and immutable launch records. No further concrete production calculation, data-loss or credential-exposure bug was established.
- Parsed the current universe artifact: 2,229 Base symbols; 560 machine proposals; 11 explicit company decisions; 549 not company-reviewed. Every available committed-input fingerprint matched its current local source. Pinned simulation remains run 8 / 194 sessions / 663 members with unchanged observation digest.

Verdict: Ship, conditional on the parent release gates passing against the final tree. Both concrete findings are resolved in inspected source and focused checks. No further concrete correctness finding was established; prior green tests alone were not used to reach this verdict.

Not checked: no duplicate full-suite/browser run, no live provider, no merge/deploy, no physical device or screen-reader test. Parent release gates own final test and browser evidence. After reporting findings, the parent explicitly delegated the simulator correction: this review changed only that script, its focused tests, regenerated simulation reports and this report. The parent owns the public-boundary correction, full validation, final commit and release handoff.
