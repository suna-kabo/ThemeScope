# Final frontend rebuild

Branch: `feature/ui-ground-up`. Reviewed with synthetic data on 15 November 2026.

## Design

A charcoal research journal organised around Market → Themes → Primary. Ruled
surfaces, restrained state colour and Figtree replace the previous comparison
dashboard. Figtree, Nunito Sans and Inter were compared in the rendered queue.
Figtree retained the clearest small numbers with the desired softer character.
One 20,156-byte variable Latin WOFF2 serves weights 400–700, with tabular numerals,
local fallbacks and its SIL OFL 1.1 license. Current static builds include only
this font; historical Inter assets remain available to legacy output.

## Removed and rebuilt

- Removed Display and its preference handlers, equal-weight Saved navigation,
  duplicated Market research previews, the three-column dashboard composition,
  current theme/stock tables, and the old metric-card drilldown composition.
- Market puts Bias ahead of paired SPY/QQQ evidence and a subordinate IWM row.
- Themes leads with side-aware five-session gains/losses, then a complete ledger.
  Relative state, raw Theme Score, change and price direction are distinct fields.
- Primary is a sequence of theme chapters containing ordered stock queues.
  Explicit global sorts use a flat queue; relationship mode retains every peer
  relationship. Company search joins ticker/theme search.
- Full theme and inspector surfaces share a new relative/price evidence renderer.
  Members use responsive research rows. Provenance, eligibility and full exports
  remain accessible through the contextual workflows.
- Saved, Methodology and snapshot/refresh utilities are secondary. Native browser
  text sizing and system reduced motion replace application display controls.

## Browser review and revisions

Actual interaction and screenshot review led to: a shorter movement section;
theme-chapter stock queues; distinct relative/price evidence; correct breadth
tracks; narrower-screen popover anchoring; long-name wrapping; 200% text reflow;
zoom-correct navigation indicators; and recoverable first-connection errors.

All eight widths were visually reviewed: **1920, 1440, 1280, 768, 430, 390,
360, 320**. The browser gate captures all five destinations, full themes and
both inspectors. Its 106 captures also include Selective, Short, Neutral,
unavailable comparisons, loading, connection loss and empty states.

Direct use and automated checks cover search, company search, filters, reset,
sort, untracked concepts, full member filters, both inspector types, nested
Back/Forward, Enter/Tab/Shift+Tab/Escape, restored focus, Saved add/remove/reload,
actual full-list downloads, theme downloads, map selection/keyboard/drilldown,
row hover, large-list scrolling, resizing, refresh progression/failure, retained
snapshots, cold connection recovery and static read-only boundaries.

## Validation

| Check | Result |
| --- | --- |
| Current browser release gate | Pass: eight widths, six coherent Market states, authoritative order and exact export content |
| axe WCAG 2/2.1/2.2 A/AA | 18 gate audits plus expanded evidence: zero violations |
| Keyboard, focus containment/history | Pass |
| Skip navigation and system forced colours | Pass in direct Chromium review |
| 200% text, browser-layout reflow and CSS zoom | Pass |
| Mobile tested controls | None below 40px; principal inputs/buttons 44px |
| Reduced motion | No running animations; normal sheet motion 180ms |
| JS syntax, workspace and legacy helper tests | Pass |
| Python 3.12 full suite | 468 run: 465 passed, one skipped, two symlink-creation errors |
| Current local API tests | 14 passed, including font/license routes |
| Fresh Windows/Unix-style static asset checkouts | Two passed |
| Current frozen snapshot tests | 23 passed; one symlink-creation error |
| Current synthetic demo tests | Two passed; one symlink-creation error |

The full-suite errors are the existing symlink tests in `test_cloudflare_demo`
and `test_public_snapshot`. Windows returns WinError 1314 while creating their
test symlinks, before their safety assertions can run.

Local Chromium performance review with 435 synthetic stocks:

| Measurement | Observation |
| --- | --- |
| First contentful paint | 68ms |
| Navigation actions | 79–183ms |
| Filter | 24ms in the gate; 69ms in direct review |
| Sustained queue scrolling | 84 frames; median 16.7ms, p95 16.8ms; no long tasks |
| Initial cumulative layout shift | 0.0616 |
| Browser errors / external app requests | Zero |

## Capabilities used

- Ponytail skill: scope, reuse of research boundaries, removal of obsolete code.
- Plugin Management skill/plugin: discovery of available design capabilities.
  Product Design was discoverable but unconnected, so no design-tool usage is
  claimed.
- Computer Use skill and availability check: confirmed the native browser host
  was unavailable; it was not used to operate the app.
- Local Chromium/Playwright: direct rendered interaction, screenshots, responsive
  and performance review. axe-core: automated accessibility review.

## Representative local captures

- [Market](../../../runtime/final-rebuild-qa/final-market-1440.png)
- [Themes](../../../runtime/final-rebuild-qa/final-themes-1440.png)
- [Primary](../../../runtime/final-rebuild-qa/final-primary-1440.png)
- [Mobile Primary](../../../runtime/final-rebuild-qa/final-primary-390.png)
- [Mobile theme inspector](../../../runtime/final-rebuild-qa/final-theme-inspector-390.png)
- [Mobile stock inspector](../../../runtime/final-rebuild-qa/final-stock-inspector-390.png)
- [Full theme](../../../runtime/final-rebuild-qa/final-full-theme-1280.png)

[Browser results](final-frontend-browser.json) preserve the recorded coverage.
Screenshots remain local synthetic review artifacts.

Not checked: physical devices, other browser engines, an actual screen reader or
live-provider data. The two Windows symlink tests remain unresolved here.
