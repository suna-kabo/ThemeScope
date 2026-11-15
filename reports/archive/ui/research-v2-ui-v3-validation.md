# Research Logic v2 / UI v3 release validation

This is the **initial `cfc1099` checkpoint record**, retained as historical
evidence. Its passing tests did not establish all product semantics: a subsequent
adversarial pass confirmed directional/default, Selective-ordering, comparison
cadence and evidence-scope defects. The current result is the
[adversarial correction validation](../research-v2/research-v2-adversarial-validation.md).
In particular, the membership audit did not individually review all 560 machine
proposals; the updated audit distinguishes cohort triage, company decisions and
explicit deferrals. Do not use the initial completion table as current proof.

Completed 2026-11-15 on `feature/research-v2-ui-v3`. This record evaluates the
Definition of Done in the supplied master contract. All market observations used
for browser testing were synthetic; this is not a new live-provider validation.

## Research and membership

- The [universe audit](../research-v2/research-v2-universe-audit.md) covers all 2,229 supplied
  Base symbols, sector/industry/theme coverage, effective memberships, unmapped
  classifications, overlaps, absent members and evidence-review proposals.
- The reviewed amendment adds CCS, GRBK, NVR and MHO to Homebuilders, and AWR,
  CWT and MSEX to Water, all Core, effective 2026-11-16. Current November 14
  membership remains 667 unique stocks / 725 relationships; after effectiveness
  it becomes 674 / 732. Original launch CSV, evidence package and history remain
  unchanged. Broad industry matches are proposals, not automatic assignments.
- The [simulation](../research-v2/research-v2-rule-simulation.md) compares 12 state models and
  eight liquidity models across 194 offline sessions. It documents frozen-member
  selection bias, pullbacks, leader retention, emerging themes, churn, symmetry,
  rank instability and small-sample breadth sensitivity. No P&L was optimized.
- The selected model uses structural score 50, exact five-session score change
  of ±10 points, and Leading / Improving / Fading / Lagging states. Trend and
  breadth remain context. Fading leaders remain researchable.
- Eligibility requires price >$5 and at least $10M average daily dollar volume
  over 20 completed regular sessions. Every eligible Core/Enabler member enters
  researchable themes; W orders peers and never excludes by sign. Missing W
  sorts last. No stock-count cap was introduced.
- [Canonical rules](../../../docs/methodology/research-v2.md) and versioned constants
  describe the complete current contract. Market Matrix, return/peer formulas,
  launch accounting and corporate-action handling remain protected by regression
  tests. Related relationships remain visible context and do not calculate.

## UI, interaction and visual verification

The [After Close design specification](../../../DESIGN.md), [product brief](../../../PRODUCT.md)
and [motion grammar](../../../MOTION.md) cover information architecture, vocabulary,
tokens, component hierarchy, mobile strategy, density and purposeful motion.
The existing vanilla presentation/state modules were reused: a framework build
would add operational cost without improving the native dialog, routing or static
snapshot boundary for this local application.

The working flow is Overview → Themes → Daily Research List → contextual theme
and stock inspection. Saved storage keys remain compatible. Countertrend controls
and W-sign filters are removed. The browser renders backend selection and order;
it does not reconstruct financial rules. Older committed snapshots explicitly
request a research refresh rather than showing false zero counts or silently
applying the previous sign gate. Prior-rules downloads are labelled accordingly.

The real-browser release gate passed on Chromium with Python 3.12 / Playwright:

- Widths: **1920, 1440, 1280, 768, 430, 390, 360 and 320 CSS pixels**.
- All eight major surfaces: Overview, Themes, research list, Saved, Methodology,
  full Theme Detail, theme inspector and stock inspector.
- Hundreds of rows, both research sides and all four theme states; exact export
  ordering/deduplication; search/filter/sort/grouping; opposite-sign peers retained.
- Keyboard opening, nested Back/Forward, dialog containment, Escape/return focus,
  Saved persistence, 200% text, 200% browser-layout reflow and CSS zoom.
- Loading geometry, empty state, connection failure preserving results, refresh
  progression and disabled refresh while running; normal/reduced motion.
- Frozen static public mode makes no API requests and hides refresh. Synthetic
  static demo replay also makes no API requests. No external browser requests or
  JavaScript page errors occurred.
- **18 axe audits: zero violations**, including contrast, dialogs, narrow views,
  enlarged text and empty state. Visible button/input/select targets checked at
  mobile size had no dimension below 40px; principal touch controls are 44px.
- Filtering the hundreds-row fixture took **66ms** in the final recorded run.
  This is an observed local interaction time, not a general hardware benchmark.

[Machine-readable results](research-v2-ui-v3-browser.json) record the passing gate,
widths, workflows, audit results and private screenshot names. Sixty-nine surface
and state captures plus the static-readonly capture are retained locally under
`runtime/ui-v3-qa/`; no private live market screenshots are committed.

The implementation agent actually inspected desktop and mobile captures of every
major surface. The deliberate critique/fix pass corrected modal focus wrapping,
the wrapped bottom-navigation label, excessive mobile filter height, narrow sort
clipping and a needlessly tall mobile theme inspector. A final capture/inspection
confirmed the fixes, including 320px and 200% reflow. Research remains compact
two-line rows on mobile rather than enlarged desktop cards.

## Automated checks and review

| Gate | Evidence / result |
| --- | --- |
| Full Python 3.12 suite | **447 tests passed**, native Windows, final process exit 0 |
| Current browser release gate | `tests/smoke_research_v2_ui.py`, passed, explicit `passed: true` |
| Local refresh/browser regression | `tests/smoke_vnext_ui.py`, passed, including original synthetic inspection preview |
| Pre-launch/launch browser regression | `tests/smoke_prelaunch_ui.py`, passed |
| JavaScript | Both current syntax checks, workspace tests and legacy dashboard tests passed |
| Configuration and original membership evidence | Both validators passed; no production blockers |
| Python compilation | `compileall` for source, scripts and tests passed |
| Impeccable | Deterministic source detector: only generic Inter-font warning; deliberately retained pinned local font for readable dense tables and offline integrity |
| Ponytail | [Final review](../research-v2/research-v2-ponytail-review.md), three concrete findings fixed and verified; Verdict: Ship |
| Public boundary | Explicit v2 field allowlist, nested unknown-field stripping, reference/count checks, safe static output and no provider/runtime payloads; regression suite passed |
| Release hygiene | Diff whitespace check; allowlisted source/docs/tests/config/reports; no raw CSV, DB, credentials, screenshots or plugin setup files staged |

The review fixes reject recent comparisons when either return horizon's
percentile population changes, explicitly handle pre-v2 saved snapshots, and
retain the correct Base-source hash on each newly reviewed instrument mapping.
Focused regression tests and the final full suite cover these cases. Windows
test portability fixes close SQLite handles before temporary-directory cleanup
and prevent doubled CSV newlines; no legacy formulas were relaxed.

Current CI runs the existing local/launch smokes and the new comprehensive
browser/accessibility gate with a locally installed axe script. Development
instructions name the supported current commands. Historical UI-specific smoke
programs remain provenance for their earlier interfaces.

## Definition of Done audit

| Requirement group | Completion evidence |
| --- | --- |
| Base and membership audit; missing/misaligned review | Full coverage JSON/Markdown, issuer-backed amendment, rejected broad-rule examples and missing-theme investigation |
| Rule simulation; deterministic states; liquidity | Candidate measurements, selected/rejected explanations, canonical policy and edge-case tests |
| No Countertrend; W priority; first-class Short; small breadth | Backend v2 contract, both-side unit/browser checks and context-only sample counts |
| Rebuilt research list and coherent UI architecture/copy | Authoritative ordered list, four-state surfaces, design/product/motion specs and copy review |
| Mobile, motion, loading, navigation, major interactions | Eight-width browser matrix, interaction assertions, captured visual critique/fix/confirmation |
| Desktop/mobile/keyboard/reduced-motion/zoom/accessibility | Passing browser gate and eighteen zero-violation axe audits |
| Full automated and browser tests | 447 passing Python tests; JS, current local and launch browser checks |
| Impeccable and Ponytail findings resolved | Detector contextual-font decision and resolved final review |
| Secure snapshots, no secrets, final feature commit | Publication regressions, exact staged-file review and Git feature-branch commit; main is not merged |

## Practical limits

No live provider call, public deployment or merge into main was performed. Live
Gate E closure remains the existing historical milestone. Physical-device and
screen-reader hardware were not used; responsive layouts and keyboard/accessibility
were exercised in a real desktop browser. Recent-change comparisons intentionally
remain unavailable until compatible five-session inputs exist. The simulation
is diagnostic evidence, not predictive trading evidence.
