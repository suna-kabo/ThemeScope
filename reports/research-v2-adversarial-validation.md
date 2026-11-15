# PR #10 adversarial correction validation

This supersedes the initial `cfc1099` validation for current Research v2 semantics.
It covers the final correction tree on `feature/research-v2-ui-v3`. Final commit
identity and both platform CI runs are attached to draft PR #10. No merge or
deployment is part of this validation.

## Final local evidence

| Gate | Actual result |
| --- | --- |
| Python 3.12 complete suite | 468 tests passed in 86.364 seconds |
| JavaScript | Workspace and legacy dashboard tests passed; app/workspace syntax checks passed |
| Compile | `compileall` passed for src, scripts and tests |
| Native Windows first use | Clean temporary install, CMD launchers, non-ASCII path, refresh/publication, failed/stale-input preservation and two-session history passed; browser checks passed |
| Local vNext browser | Refresh, downloads, Saved, responsive layout and static loopback preview passed; zero page errors/external requests |
| Prelaunch browser | Research context, automatic official-launch boundary, exports and Saved passed; zero page errors/external requests |
| Complete Research v2 release browser | Passed all workflows in `tests/smoke_research_v2_ui.py` on real Playwright Chromium |
| Responsive widths | 1920 / 1440 / 1280 / 768 / 430 / 390 / 360 / 320 passed |
| Accessibility | 18 axe-core 4.14.0 audits: zero violations; no touch targets below 40 px |
| Interaction | Keyboard navigation and modal containment/return focus, nested Back/Forward, Saved persistence, full-session export, filters, reduced motion, 200% text and reflow passed |
| Failure and migration UI | Loading, connection error, preserved completed snapshot, previous-rules notice, explicit unavailable comparisons and non-directional empty list passed |
| Public boundary | Static/frozen modes made zero API requests; allowlist, semantic consistency, provenance, assignment and malformed-input regressions passed |
| Fresh visual critique | Inspected all eight major surfaces at 1440 and 390; additionally 320/430 and Short/Neutral/unavailable captures; no unresolved correctness or layout defect found |
| Impeccable rerun | Only generic overused-font warning for Inter; retained pinned local offline font, appropriate to existing dense research UI; no redesign warranted |
| Independent Ponytail | Both fresh integrity findings fixed and independently rechecked; conditional ship verdict satisfied by final release gates |

Browser evidence uses synthetic bars and coherent backend-generated six-state
fixtures, including selective and non-directional cases. It does not establish
live-provider correctness or production-market outcomes. Screenshots and raw logs
remain local in ignored runtime storage. The browser suite captures all eight
surfaces at every listed width; visual review is narrower than automatic geometry
coverage and is stated above. No physical-device or screen-reader trial is claimed.

## Correctness and evidence scope

The [finding review](research-v2-adversarial-review.md) records all fourteen
hypotheses and regression ownership. Exact score 50 remains an inclusive symmetric
tie; it was not an arithmetic defect. Approved thresholds and formulas remain
unchanged. Current-side state, canonical Strength Rank, research-order index and
raw/directional five-session changes now have separate explicit fields.

Read-only reconstruction compares the current reviewed basket at t and t-5 using
completed bars. It requires compatible global 1M, 3M and scored populations, states
its current-basket provenance and never inserts official history. Sufficient data
permits comparison on first install/upgrade and on the November 16 amendment's
first refresh; missing bars/populations retain explicit unavailability. All
relevant calculations, migration, no-write, selective ordering, mirrored Short,
multi-theme exports, query DTOs and publication tampering have regressions.

The pinned simulation now excludes ten population-incompatible pairs: 179 of 189
eligible comparisons remain. Structural retention 1.0 is explicitly a definition
check. Persistence, completed transitions/time, censoring and threshold churn are
descriptive diagnostics, not predictive validation. The threshold stays at ±10.

Membership completion means screening and cohort triage are complete, not that
every machine proposal received company evidence review. The latest Base export
contains 2,229 symbols and yields 560 machine candidates: 20 triaged cohorts,
11 company-specific decisions, 549 candidates without individual company review.
The existing seven forward-dated approvals remain the only applied additions.
CVCO remains an unapplied suitable proposal; LEN.B awaits duplicate-issuer policy.
The remaining candidate classes are deliberately deferred for charter/evidence
review, without inflating membership. Durable authorization replaces the local
task-prompt reference.

## Release boundary

Final staged changes are checked for whitespace, secrets and forbidden private
artifacts before commit. The working tree and remote feature head are checked
after push. Linux and Windows GitHub Actions provide actual platform verification;
local Windows execution alone is not described as Linux execution. CI links and
the final commit are recorded in PR #10 and the handoff. Main, historical tags,
official launch/accounting records, private runtime data and public deployment
remain untouched.
