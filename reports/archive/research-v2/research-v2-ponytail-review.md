# Research v2 / UI v3 Ponytail review

What this change does: It separates theme structure from recent change and includes
every liquid Core/Enabler stock in researchable themes, ordered by peer strength.
It replaces the research interface while preserving effective-dated memberships,
launch accounting and atomic publication.

Reviewed for one local user with hundreds of displayed stock relationships. The
review followed the Ponytail review skill and traced the feature diff against
`main`, new production modules, their callers, tests and current specifications.

## Findings resolved

1. **A changed percentile population can look like theme improvement**
   (`src/themescope/research/v2.py`, `recent_change`)
   - **What this is:** Theme Score combines independently ranked 1M and 3M
     cross-theme percentiles. The five-session change drives Improving/Fading.
   - **Problem:** A theme losing a valid score or horizon changes those percentile
     populations. The code still reported another theme's score change as
     comparable, suppressing only its rank change. A fixture with one missing
     prior theme score reproduced Improving with `available=True` and a 10-point
     delta despite an incompatible scored universe.
   - **Fix:** Reject recent comparisons when the scored-theme population or either
     horizon's valid-theme population changes; add a regression for each case.
   - **If we skip it:** A data-availability change can put a stock into the daily
     list as an apparent improving theme.
   - **Resolution verified:** `recent_change` now rejects a changed combined
     scored population and either changed horizon population. The regression
     covers both a missing score and a changed horizon while the combined scored
     population stays unchanged. The targeted Python 3.12 v2 suite passed.

2. **An existing snapshot can be shown as a false empty research list**
   (`static/vnext/app.js`, `v2`, `renderOverview`, `renderCandidates`)
   - **What this is:** Existing installations retain a successful snapshot when
     the application updates or a later refresh fails.
   - **Problem:** A snapshot without `research_v2` defaults to empty maps/rows.
     Overview displays zero themes/stocks and Research says no eligible members
     exist, even though that retained snapshot has relationships and exports.
   - **Fix:** Show an explicit current-rules-unavailable/refresh-required state.
     Keep existing context and Saved, and clearly label any retained legacy
     export. Do not rebuild financial selection in the browser.
   - **If we skip it:** An upgrade or failed refresh misrepresents retained data
     as an economically empty research universe.
   - **Resolution verified:** Overview now returns an explicit unavailable state
     without zero counts; Research requests a refresh; retained exports say
     Previous rules. Existing theme/market context and Saved remain accessible.
     A manufactured older-snapshot browser regression was added; its final run is
     tracked by the release validation gate.

3. **New symbol mappings cite the old input file**
   (`src/themescope/research/membership_review.py`, `apply_review`;
   `src/themescope/research/exports.py`, `reviewed_mapping`)
   - **What this is:** The reviewed amendment adds seven instruments that were
     absent from the original 1,525-symbol review universe.
   - **Problem:** Their inferred verified export mapping inherited the original
     universe's source hash, identifying a file that did not contain them.
   - **Fix:** Preserve the amendment Base export hash per new instrument and
     prefer that hash when creating its mapping; assert provenance in a test.
   - **If we skip it:** Export identity remains correct but its evidence trail is
     factually wrong.
   - **Resolution verified:** New instruments retain the amendment's Base hash;
     `reviewed_mapping` prefers per-instrument provenance while retaining the
     original fallback. A regression checks all seven reviewed additions. The
     targeted Python 3.12 membership suite passed.

## Coverage and limits

Inspected retained Market Matrix/return boundaries, v2 direction symmetry,
liquidity units and completed-session windows, all-W inclusion and ordering,
multi-theme TXT placement, Related exclusions, immutable membership amendment
validation, public allowlisting/scanning, query copies and atomic refresh callers.
No additional concrete correctness/security finding was identified in those flows.
No speculative framework, abstraction or dependency changes are requested.

Verdict: Ship. All three review findings are resolved in the inspected source and
regression tests. Final browser/full-suite release gates remain separate evidence
in the release validation record.

Not checked: live provider credentials, publication to a public host, or physical
screen-reader hardware. Browser/visual/accessibility and full-suite results are
owned by the release validation report.
