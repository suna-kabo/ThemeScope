# Ground-up frontend redesign validation

Completed locally on `feature/ui-ground-up`, 15 November 2026. Data in browser
reviews was synthetic. No provider call, production refresh, publication or
merge was performed. Main and the historical inspection checkpoints are unchanged.

## Result and scope

Research desk replaces After Close's sidebar, dark canvas and vertically stacked
Market composition with a horizontal task path, light comparison workspace,
side-by-side market evidence/theme leadership/Primary research, and contextual
opaque inspectors. Mobile has its own rows, four research destinations, expandable
filters and compact benchmark observations. Full Theme, Saved and Methodology
share the same type, control, selection and surface system.

Source changes are confined to the three current frontend files, the current
browser gate, and design/validation documentation. Backend, research policy,
methodology constants, eligibility, state calculation, authoritative peer order,
exports, persistence keys, effective memberships and providers were not edited.
No frontend dependency was added. Existing vanilla research/state primitives and
native table/dialog/details semantics were retained where useful.

## Independent critique and corrections

| Finding from rendered use | Correction verified in browser |
| --- | --- |
| Market evidence buried under separate disclosures | Visible desktop evidence alongside research; compact three-benchmark mobile summary |
| Mobile header and filters delay useful results | Horizontal utilities, compact task titles, expandable filters with active counts |
| Theme state separated from theme identity | State follows the name; score bars compare supplied strength without financial color |
| Tickers harder to identify and long relationship labels repeat | Desktop company names; explicit Stocks / By theme presentation remains available |
| First-pass benchmark column too tall | Compact benchmark composition; leadership changes use the area below research previews |
| Tablet rows squeeze names and conceal Save | Deliberate tablet column budgets and no required horizontal travel in normal research tables |
| Muted IWM opacity reduces contrast | Remove opacity; retain explicit context label |
| 200% text overlaps fixed navigation | Wrapping masthead utilities and two-row bottom navigation at enlarged text |
| CSS zoom makes refresh overflow | Container-based operational-header reflow |
| Display sheet inherits white masthead text | Explicit working-surface colors; normal and high-contrast axe coverage |
| Inspector explanation consumes member space | State rationale disclosed; full Theme rationale joins state/trend evidence |
| Alternating row styles can obscure selection | Explicit selection override for every row parity |

These were multiple implement/render/critique/fix cycles, not conclusions inferred
from test counts. Before captures are retained in `runtime/redesign-before/`;
final full-universe captures and review sheets are in `runtime/redesign-qa/`.
They remain local and are not a new inspection bundle.

## Visual and functional judgments

All eight surfaces were actually viewed: Market, Themes, Primary, Saved,
Methodology, full Theme, theme inspector and stock inspector. Final rendered
captures were reviewed together at each width, followed by focused interaction
and enlargement checks. The functional and visual judgments are separate.

| Width | Functional | Visual/UX judgment after refinement |
| --- | --- | --- |
| 1920 | Pass | Wide comparison workspace; dense lists, visible task path, no artificial centered gutter |
| 1440 | Pass | Evidence and research coexist; leadership changes occupy available lower workspace |
| 1280 | Pass | Names remain readable and controls remain distinct; selected rows clear |
| 768 | Pass | Full-width market evidence and tighter table budgets; Save remains reachable |
| 430 | Pass | Compact research rows, readable values and distinct navigation/inspection surfaces |
| 390 | Pass | Expandable filters preserve result space; full workflow remains understandable |
| 360 | Pass | Sort wraps deliberately; titles, selectors and inspector actions remain usable |
| 320 | Pass | Full-width sort/theme controls; long names wrap; no compressed desktop table |

Direct use included navigation, scrolling, search, filters, sort, untracked
concepts, theme and stock inspectors, keyboard Enter/Tab/Escape and restored
focus, Back/Forward, Saved/add/remove, a real download, density, high contrast,
text size, reduced motion, returns-map selection, loading, filter-empty,
Neutral-empty, and connection failure retaining the prior successful results.
Automated checks additionally verify both research sides, all six Market states,
exact export ordering/deduplication, opposite-sign peers, refresh progression and
static/read-only boundaries. No claim of physical-device or screen-reader use.

## Checks

| Check | Result |
| --- | --- |
| Current browser release gate, Python 3.12 + Chromium | Pass, eight widths and all eight surfaces |
| axe WCAG 2 A/AA, 2.1 AA, 2.2 AA | 20 audits; zero violations, including Display and high contrast |
| Keyboard/history/focus, touch targets, 200% text/reflow/zoom | Pass; no visible tested control below 40px; primary mobile controls 44px |
| Normal/reduced motion | Pass; no JavaScript errors or external requests |
| Local refresh/static browser smoke | Pass |
| Pre-launch / launch browser smoke | Pass |
| JS syntax, workspace and legacy JS helpers | Pass |
| Python compileall, source/scripts/tests | Pass |
| Config and original membership evidence validators | Pass; no production blockers |
| Complete Python 3.12 suite with UTF-8 enabled | 468 run: 465 passed, 1 skipped, 2 environment errors |

The two full-suite errors are unchanged symlink safety tests:
`test_cloudflare_demo.CloudflareDemoTests.test_output_symlink_rejected` and
`test_public_snapshot.PublicSnapshotTests.test_tampered_output_symlinks_and_extra_files_rejected`.
Windows denied creation of their test symlinks with WinError 1314 before the
assertions ran. Neither test nor the guarded production code was modified or
skipped to produce a green count. The first run also exposed CP950 decoding in
legacy tests; rerunning with `PYTHONUTF8=1` removed those locale errors.
This is an explicit validation limitation, not a complete-suite pass.

[Machine-readable browser results](ground-up-ui-browser.json) record workflows,
widths, audit findings, screenshot names and observed filter time. Full suite
output remains local in `runtime/redesign-python-tests-utf8.txt`.

## Tests and contract audit

No obsolete presentation assertions needed removal or relaxation. The existing
current browser gate was extended to exercise mobile filters/count/reset, visible
benchmark summaries, separated enlarged-text navigation targets, and Display
contrast. Genuine behavioral, semantic, data-integrity and accessibility checks
were retained. Historical smoke programs and inspection assets were not rewritten.

The final diff does not touch calculation or selection modules. SPY/QQQ and IWM
roles, median member returns, theme scoring, Leave-One-Out peer comparisons,
W ordering, Research v2 eligibility/state meanings, failed-refresh preservation,
Saved keys, hash routes and export contents/order remain protected by existing
unit and browser checks. Only view composition, labels and bounded previews changed.

Remaining limits: Chromium viewport emulation rather than physical phones;
no live-provider test; two symlink tests require a Windows privilege unavailable
in this environment. No publication or production cutover is part of this task.
