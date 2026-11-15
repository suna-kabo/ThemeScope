# PR #10 adversarial correctness review

Baseline reviewed: `cfc1099`, against `main`, the master product contract and the
project owner's fourteen hypotheses. This is a second review, not a reaffirmation
of the earlier passing tests. A passing consistency test is not treated as proof
that a product requirement is satisfied.

## Verified findings and disposition

| Finding | Verification | Root cause / required correction | Regression evidence |
| --- | --- | --- | --- |
| 1. Non-directional leakage | Confirmed | Backend theme ordering and several UI fallbacks treated every non-Short state as Long. Neutral/Unclassified need explicit no-side semantics, alphabetical neutral order and no directional list. | Six-state backend, API, projection and real-browser fixtures; final release gate owns results |
| 2. Ambiguous v2 contract | Confirmed | `state` meant Long while adjacent reason/researchability meant current side; `liquidity` contained the whole policy and `theme_rank` was an order index. Explicit directional/current fields, policy naming and Strength Rank/order separation are required across callers. | Contract/projection/query tests and JS/browser consumers |
| 3. Short explanation/change wording | Confirmed | Raw structural-score change and Long-oriented reasons were reused for Short research improvement. Directional reasons/change labels must agree while raw changes remain clearly named. | Mirrored raw-input states and Short reason/sort/Overview assertions |
| 4. Selective ordering | Confirmed | Both full and Selective bias collapsed to a side, and a test asserted identical order. Selective must retain the same set but deprioritize marginal Improving states relative to structurally established Fading states. | Same-set/different-order mirrored fixtures and export ordering |
| 5. Refresh-cadence dependency | Confirmed | Exact stored t−5 lookup made current research depend on prior app usage. Same-current-reviewed-basis read-only reconstruction is appropriate when bars and comparable score populations exist; it must identify the reconstructed basis and never persist backdated accounting. | Fresh install, skipped refresh, upgrade, amendment, population and no-write tests |
| 6. Availability wording | Confirmed | Distinct failure conditions were reduced to “History building,” including membership changes or unavailable scores; zero-state counts were indistinguishable from missing comparisons. | Reason mapping and Overview/detail/inspector tests |
| 7. Mixed rank horizons | Confirmed | The five-session cell consumed legacy adjacent-session rank context. Its annotation and sorting must use the actual v2 five-session comparison. | Distinct one-session and five-session rank fixture |
| 8. Upgrade/amendment warm-up | Confirmed | Stored-schema/config/series guards suppressed comparisons even with sufficient market bars. A labelled current-basket comparison can operate on the first refreshed session; unavailable data must remain explicit. | v1 upgrade and Nov 16 effective-date transition cases |
| 9. Membership completion overclaim | Confirmed | 560 machine-screened candidates were not 560 company-evidence decisions. Revised artifacts distinguish 20 charter/evidence-gap cohorts, 11 company-specific decisions and 549 proposals not company-reviewed. Only the existing seven forward additions are approved. | `test_screening_and_cohort_triage_never_claim_company_review_for_every_candidate` |
| 10. Retention evidence | Confirmed | No-veto structural retention of 1.0 follows directly from Leading/Fading inclusion. It is now explicitly an invariant, complemented by censored episode persistence, direct transitions/time and threshold-neighborhood churn. ±10 is retained without P&L or stock-count optimization. | `test_temporal_diagnostics_measure_observed_episodes_and_censor_incomplete_edges`, missing-state/edge tests and pinned read-only rerun |
| 11. Permanent authorization / stale terms | Confirmed | The reviewed amendment cited an uncommitted local prompt. Its reference now points to a durable committed authorization record; current working copy must use current research vocabulary. | `test_permanent_membership_authorization_is_a_committed_document_reference`; UI copy gate |
| 12. Agent/API ambiguity | Confirmed | Legacy priority was returned next to current research and history lacked HTTP parity. Current query DTOs need explicit current selection and separately labelled historical observations. Unknown theme members should return not-found, not a valid empty list. | Query/HTTP historical/current and unknown-versus-empty tests |
| 13. Exact score 50 | Reject as an arithmetic bug | Inclusive 50 on mirrored directional strength is symmetric: an exact midpoint can meet either side's structural boundary, but only the actual market side selects a list. Retain and document the tie policy; do not adjust it to reduce list breadth. | Exact-boundary and Long/Short mirror tests |
| 14. Fresh whole-change review | Required release gate | Review must include callers, generated artifacts, fixture consistency, public validation and UI semantics; prior green CI alone is insufficient. | Updated final validation report, complete suite and both CI workflows |

Two additional API/public-boundary cases were identified independently: unknown
theme-member queries returned a misleading successful empty result, and public
projection checked list identities/counts without checking directional semantics
or row agreement. These belong in the same normalized read-only boundary fixes;
neither finding is a claim that raw data or credentials were exposed.

## Independent coverage

The review traced the PR's production refresh orchestration, retained calculation
helpers, storage/publication reads, reviewed membership overlay, export resolver
and ordering, read-only API queries, static demo and public projection. It inspected
the frontend presentation/state helpers and affected JS/browser fixtures for
non-directional fallbacks, horizon labels and legacy fields. The changed config,
CI/development commands, audit/simulation generators, reports and regression
assertions were checked against their stated evidence scope. Machine JSON outputs
were checked by schema, input fingerprints, counts and generator provenance;
their length does not constitute additional company review.

The original Market Matrix, price-return medians, 60/40 score, leave-one-out peers,
effective-dated launch package, chain-linked index and atomic failed-refresh
preservation are retained. No new trading/provider endpoint, market publication,
bulk membership application, cap, W sign filter or Countertrend lens is justified.

## Membership scope and simulation result

Company-specific evidence remains bounded: seven approved additions and two
rejections from the original review, plus a new issuer spot review of CVCO
(suitable proposed addition, unapplied pending a separate dated approval) and
LEN.B (another share class of already represented LEN, deferred pending explicit
duplicate-issuer methodology). These deferrals do not deny their business
relationships or redefine either charter. The original November 14 amendment is
not backdated or expanded during this correctness pass.

The pinned run-8 observation digest remains unchanged. The expanded diagnostic
rerun uses the same 194 sessions and 663 reviewed members. At ±10, Improving
next-session persistence is about 0.502 Long / 0.496 Short; completed Improving
episodes directly enter Leading at about 0.352 / 0.326, after mean 1.902 / 2.000
sessions for those direct transitions. Fading direct exits separately measure
loss of structure and recovery. These are descriptive, censor-aware observations,
not predictive validation or a reason to alter the approved threshold.

## Release status

The corrections passed the final local release gates documented in
[adversarial validation](research-v2-adversarial-validation.md): 468 Python tests,
JavaScript, native Windows first use, all three browser gates and 18 axe audits.
The independent [Ponytail review](research-v2-adversarial-ponytail.md) found two
additional integrity defects; both were corrected and independently rechecked.
The final commit's Linux and Windows CI results are recorded on PR #10.
No merge, deployment, official-history rewrite or bulk membership addition occurred.
