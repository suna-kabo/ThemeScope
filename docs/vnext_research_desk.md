# ThemeScope Research Desk

7 November 2026. Functional parent: `946259b`. This UI supersedes the earlier
[Lunar Lounge presentation](vnext_lunar_lounge.md), whose implementation record
and screenshots remain historical. The financial/runtime contract is unchanged.

## Visual system and information architecture

One original design: warm ink/navy, blue-violet surfaces, lavender interaction,
soft cyan context, mint positive, coral negative and amber Mixed. Watch and zero
are neutral. Text and signs accompany semantic color. No borrowed Persona assets,
remote requests, framework or runtime UI dependencies.

Overview emphasizes returned Market Matrix direction, prominent SPY/QQQ price
and trend, then a secondary IWM line. Compact Primary themes/stocks use separators.
Themes is a dense list; Primary is a daily research sheet; Saved is a compact
bookmark list; Methodology retains the actual eight calculation disclosures.
Decorative slogans/eyebrows and report-like introductions are removed.

Navigation is Overview, Themes, Primary, Saved and Methodology. Primary's heading
is **Primary Watchlist**; its counts come from supplied qualifying relationships.
The legacy `#candidates` fragment still resolves to Primary. It is a navigation
alias, not an export or qualification change. Unique rows continue to select the
server-assigned relationship before view filtering; exports remain canonical.

Research tables use document vertical scrolling, no bounded vertical pane.
Headers stick on desktop. Narrow genuinely wide research tables may scroll
horizontally; Themes reflows to labelled rows. Values use 14px base text, supporting
labels 12–13px, rem units and tabular numbers. Comfortable density adds row space.

## Browser-local preferences

Saved preserves `themescope-vnext-watchlist`, a JSON ticker array. Bookmarks remain
through refresh, application close/reopen and normal reboot in that browser profile,
including when a ticker leaves Primary or has no current supplied relationship.
They are not synchronized; clearing site data removes them. No SQLite persistence.

Display uses the separate `themescope-vnext-display` key: Compact/Comfortable,
100–200% text size in 25% steps, Reduce motion, High contrast. Invalid stored choices
fall back safely. OS reduced motion is always honored; the UI switch can additionally
reduce motion. Blocked storage applies changes for this visit and reports that limit.

Buttons respond in 80–90ms; Save has a persistent star/pressed state. No animated
numbers, floating cards or background motion. Semantic colors are not optional.

## Implementation checkpoints

1. Visual system, density, navigation, quiet diagnostics and Display controls.
   Full regression: 327 cases, 325 pass / two existing native-Windows skips.
   Browser refresh/export/Saved and pre-launch/launch cutover smokes pass.
   Visual and keyboard/accessibility review continues through the Inspector and
   visualization commits; final evidence is recorded below when complete.

Gate E remains open for real completed Nov 9/10 checks. Native Nov 6 launch
validation already passed. No live API call, merge, deployment, launch/configuration,
financial/provider/storage/cache/schema or official-history change in this work.

Stage 1 browser acceptance completed: all three existing UI smokes pass, zero
page errors/external requests. Axe A/AA has zero violations on the five destinations,
Theme Detail, populated Saved, Display high contrast and 320px Theme Detail.
Its incomplete contrast items were checked against solid tokens: minimum text
5.86:1, input boundary 3.17:1, filled accent-button text 8.24:1. Native screen-reader
speech and other browser engines are not verified. Chromium widths 1440/1600/1920,
800/390/320 and 200% root text resizing pass. Page-wheel scrolling and no nested
vertical table pane are verified. Review fixed the root Display selector, contained
screen-reader-only content within horizontal tables, and made the sidebar/text
reflow responsive to enlarged text. JavaScript, validators, compilation and whitespace
checks pass. Deterministic review captures remain local; no binary payload is pushed.

## Research Inspector

Theme and ticker links show a persistent underline and cyan chevron, with hover,
keyboard focus and native link semantics. Modified clicks retain normal link
behavior. The optional full Theme Detail route remains available. Repeated row
`Research details` disclosures are replaced by a single native modal dialog,
roughly 42% of desktop width and a full-width mobile sheet. The desk remains
visible behind it; its controls are inert while the inspector is open.

Opening adds a hash/history entry. Moving from a member to its ticker or another
theme replaces that inspector entry, so there is no modal stack. Escape, Close or
browser Back dismiss it; Forward restores it. Direct inspector URLs also work.
Filters, page scroll and source focus survive closure. A changed snapshot updates
inspector data while preserving member search, selection, sort, focus and scroll.
The inspector reports refresh failure and retains the last published research.

Theme view shows supplied Score/Priority/trend/returns, index/EMAs, breadth,
comparison availability and Core/Enabler member research. All/Primary/Eligible/
Core/Enabler are view filters only. Ticker view shows current Primary state,
server assignment, other qualifying themes and each supplied relationship's
role/W/eligibility/excess returns/peer medians. Where no assigned relationship
exists, multiple W/role values are explicitly **Per theme**. No standalone stock
returns, guessed chart URLs or fabricated Related rows. Supplied liquidity inputs
remain available in a single disclosure.

Stage 2 visual review fixed mobile dialog positioning against the reserved
scrollbar gutter and added explicit forced-colors system tokens. Full regression
remains 327 cases (325 pass/two existing Windows skips). Refresh/export/Saved and
pre-launch/launch cutover browser smokes pass. Final inspector browser acceptance
and screenshots are recorded with the completed redesign below.

Stage 2 acceptance complete: all three browser scripts pass. Axe A/AA reports zero
violations, including both inspectors, 320px ticker Inspector and forced colors.
Browser Back/Forward, Escape, source focus/scroll restoration, member filters,
changed-snapshot focus/search retention, failure preservation and absent Saved
symbols pass. No page errors/external requests. At 2560×1440, 30 complete theme rows
and 24 Primary rows are visible at default text/density. The retained tables and
inspector use values supplied by the same snapshot; no financial assertions changed.
