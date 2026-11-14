# ThemeScope UI v3 — After Close

ThemeScope is an Operate surface for focused chart research after the US close.
The visual direction is a charcoal research ledger: warm paper text, quiet green
surfaces and a restrained amber selection accent. It replaces Tidal Vector's
electric selection planes and cut geometry. Color carries state or focus, never
decoration. Positive/negative values also retain words or signs.

## Information hierarchy

Overview starts with market direction and its change, then themes gaining or
losing strength, researchable themes and stocks worth reviewing. It does not
start with a grid of interchangeable KPI cards. Themes compares structural
strength with recent change. The Daily Research List is the chart queue.
Theme and stock inspectors preserve the underlying list; full Theme expands
context. Saved and Methodology remain secondary destinations.

The local/static application keeps modular vanilla JavaScript. `workspace.js`
owns presentation primitives and interruptible motion; `app.js` composes
committed snapshot fields and browser state. Native links, tables, details and
dialog retain platform behavior. A framework migration would add a build and
state migration without improving these existing boundaries. Financial rules
are supplied by the backend, never reconstructed in the browser.

## Tokens and components

- Page #131615, rail #191d1b, surface #1c211e, raised surface #242b26.
- Text #f4f2e9, secondary #c8cec5, muted #a7b1a5; amber #e1c78b for focus/selection.
- Positive #9bcca9, negative #f2a6a0; warning shares amber with explicit wording.
- Existing self-hosted Inter remains the deliberate dense Operate face. It is
  pinned in static publication, requires no network and has tabular numerals.
- Body 14px, secondary 13px, captions 12px at default scale; page title 30px.
  Display text controls support 100–200% without hiding actions.
- Spacing follows 4/8/12/16/24/32/48px. Related rows are tight; headings separate
  work areas. Straight section rules replace nested panels.
- Controls use 4px corners; floating utilities and inspector use 8px. Rows and
  ordinary data do not acquire pill backgrounds or decorative shadows.

Tables retain real headers and numeric alignment on desktop. Theme state,
strength, five-session change, participation and researchability have distinct
roles. Research rows default to server priority; view sorting never changes
export priority. Related relationships are visible context, excluded from
calculations and the Daily Research List.

## Responsive behavior

Large desktop uses the persistent left navigation and dense aligned tables.
Tablet removes the rail in favor of a wrapping navigation row. At mobile widths
the five destinations become a reachable bottom bar, with safe-area padding.
The main content reserves space for that bar.

Research rows become a compact ticker/peer-strength line plus theme context,
with a separate Save action. Role and earnings move to inspection. Themes use
a deliberate compact state/strength/change hierarchy, rather than a miniature
desktop table. Full Theme member rows reflow independently. Filters wrap with
full-width search; inspectors fill the viewport with visible close actions.
320/360/390/430px, tablet, normal and large desktop are release checks.

## Language and accessibility

Use Market direction, Structural strength, Last five sessions, Participation,
Peer strength, Research list and Saved. W appears only in the exact methodology.
Internal lifecycle and provider details belong in Diagnostics. Countertrend,
snapback and setup predictions do not appear in the working experience.

All actions have accessible names, visible focus and native semantics. Inspectors
restore trigger focus; Back/Forward retain context. Reduced motion cancels
visual travel while preserving state. Readability, sample counts and non-color
state labels are release requirements. Mobile primary controls target 44px.

No gradients, blobs, glass, all-caps eyebrows, decorative charts, nested cards,
glows, repeated badges, technical-costume typography or marketing spacing.
The return map is retained because it compares actual supplied returns.

Impeccable is used in Operate mode. Its generic Inter saturation warning is a
contextual exception: the existing pinned offline face serves scanability and
publication integrity. Rendered QA and axe establish actual usability.
