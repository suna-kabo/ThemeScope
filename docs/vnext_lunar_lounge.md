# Lunar Lounge UI implementation

6 November 2026. Functional parent: `ed12ba49e4ea6ce3cfb1998ae6bdc72d11fe0324`.
Implementation branch: `refactor/themescope-vnext`. One design direction, no framework
migration, no deployment. This implements the user's later UI brief; the exploration
in `design-plans/themescope-ui-redesign-exploration.md` records the earlier decision.
The new navigation supersedes the old UI naming in specification section 24 only.
The financial methodology specification is unchanged.

## Product surfaces

- **Overview**: returned Market Matrix direction and explanation, SPY/QQQ price and
  roster breadth, secondary IWM context, six relevant returned Primary themes and
  eight unique candidate previews. Short focus sorts returned Primary themes in the
  weaker-score direction; it never creates qualification. Status is compact, with
  refresh/recovery diagnostics disclosed on demand.
- **Themes**: 44 Active themes by default; eight Watch-only concepts separately
  accessible. Search, family/priority/trend filters, numeric sorting, list positions
  and equal-Score labels, sticky headers and a bounded results scroller. Theme names
  lead family metadata. Mobile reflows the same rows into labeled research units.
- **Theme Detail**: a full research route at every width rather than squeezing a
  member table into a narrow inspector. Back restores the originating destination,
  theme filters, scroll and theme-link focus; browser Back/Forward work. Shows
  supplied Score, median returns, index/EMA/trend, breadth validity, Priority and
  compatible comparison state. Member search, role/eligibility filtering, W sorting,
  qualification, earnings, Save, research disclosure and published Theme Primary TXT.
- **Candidates**: default unique tickers using the server's assigned relationship
  for W; an independent By theme view preserves all qualifying relationships.
  Search, theme/role/W/earnings filters and sorting. Assigned section and Also
  qualifies in remain explicit. Filtering never changes either TXT export.
- **Saved**: retained `themescope-vnext-watchlist` ticker-array key and format.
  Current qualification, earnings and every supplied relationship provide context.
  Remove is available; missing current relationships never delete a bookmark.
  Blocked browser storage falls back to this visit with an explicit confirmation.
- **Methodology**: eight native disclosures cover Market Matrix, Score, synthetic
  trend, breadth, peer W, eligibility/Primary, multi-theme placement, and launch.
  Configuration/activation blockers remain available in a separate disclosure.

No direct stock 1M/3M return or verified chart URL exists in the frozen relationship
contract. Detail says stock returns are not supplied, and shows the supplied peer
medians, excess returns and W. It does not reconstruct returns or guess chart venues.
Related members are absent from calculation rows and are not fabricated. An
individual TXT link is offered only when the snapshot has that published Primary
output. No new export, API field, endpoint, backend calculation or persistence was
introduced.

## Visual system and interaction

Night-ink page `#171923`, matte slate surfaces `#222633` / `#2c3142`, lavender accent
`#bcadff`, soft-white primary text, and separate green/red/amber market semantics.
CSS variables define surfaces, borders, text, semantic colors, radii, spacing,
shadow, timing and type roles. Rounded panels and controls have distinct radius
levels; numbers use tabular figures. A local system sans stack prefers Inter where
installed and Segoe UI on Windows; there is no remote font or new font route.
Original rounded outline SVG icons avoid platform-dependent arrow glyphs.

Navigation and hover have short tonal feedback; last-opened theme has a persistent
edge marker; Save updates in place with pressed state and confirmation. Route
entrance is 180ms; press response is 150ms; routine tonal transitions are 140ms.
There are no loops, animated backgrounds, bouncing numbers or decorative spinners.
Reduced motion disables movement and transitions. Native disclosures need no custom
widget keyboard model or focus trap.

Polling updates operational status without rebuilding identical research content.
A changed snapshot preserves keyed focus and current filters. Saved controls are
updated in place. Refresh failure keeps the prior snapshot visible; the backend's
atomic snapshot/export publication remains completely unchanged.

## Specialist passes actually used

1. [jakubkrehel/better-ui](https://github.com/jakubkrehel/skills/blob/main/skills/better-ui/SKILL.md):
   deliberate surface/radius hierarchy, original consistent icons, press/hover
   feedback, named transitions, reduced motion and no continuous decoration.
2. [jakubkrehel/better-typography](https://github.com/jakubkrehel/skills/blob/main/skills/better-typography/SKILL.md):
   readable application scale, rem type roles, tabular figures, wrapping, mobile
   16px inputs, unitless line height and a local fallback stack.
3. [jakubkrehel/better-accessibility](https://github.com/jakubkrehel/skills/blob/main/skills/better-accessibility/SKILL.md):
   dedicated post-implementation keyboard, label/name, semantics, target size,
   contrast, reduced-motion and resize pass.

Skills were used sequentially, not installed into the application. The earlier
three exploration skills remain provenance for the proposal, not three additional
implementation passes. Inspected the public `educlopez/ui-craft` tooling and
`ihlamury/design-skills` catalogs. UI Craft's installer/hooks/MCP gates were not
needed beyond the concrete browser, contrast and axe checks used here. No brand
skill was loaded or mixed into the identity; no framework/dependency was added.

## Review findings and fixes

| Severity | Location | Before | After | Why |
|---|---|---|---|---|
| High | `static/vnext/app.js` render/poll | Identical snapshots replaced focused Save controls every poll | Skip identical snapshot renders; update Save controls in place | Preserve keyboard task continuity |
| Medium | `static/vnext/app.js` navigation | Native fragment scrolling could bypass route context; skip link could change route | Explicit app routing, native modifier-click links, focus/title/scroll restoration; independent skip action | Predictable navigation and focus, WCAG 2.4.3 |
| Medium | `static/vnext/app.css` theme-link | Candidate links near adjacent disclosures failed axe target-size | Minimum 24px link targets without overlapping expansion | WCAG 2.5.8 |
| Medium | `static/vnext/app.css` narrow theme rows | Paired breadth values crowded Priority at small widths | Breadth spans two cells; Priority/change use a separate row | Readable 320px reflow, WCAG 1.4.10 |
| Medium | `static/vnext/app.js` icons | Direction arrows could render as missing glyph boxes | Original inline SVG outline set | Meaning survives platform font differences |
| Medium | `static/vnext/app.css` typography | Initial implementation used undersized table/caption text | 14px research values, 12–13px supporting text, rem sizing | Research density without shrinking essential values |
| Low | `static/vnext/app.js` Save | Pressed label and accessible name could disagree | “Saved TICKER; remove from Saved” includes visible label | WCAG 2.5.3 |

Accessibility review outcome: **Approve for the inspected Chromium scope**; no
remaining High findings there. This is not a claim of full platform conformance.
Axe-core 4.11.0 reported zero A/AA violations on Overview, Themes, Candidates,
empty Saved, Methodology, Theme Detail, populated Saved and 320px Theme Detail.
Its `color-contrast` incomplete items were separately checked against the actual
solid color tokens. Lowest text contrasts over the used surface levels:

| Text role | Minimum contrast |
|---|---:|
| Primary | 10.41:1 |
| Secondary | 6.78:1 |
| Muted | 5.39:1 |
| Accent | 5.93:1 |
| Positive / negative | 7.57:1 / 6.70:1 |
| Warning / info | 7.92:1 / 7.18:1 |
| Focus perimeter | 7.36:1 |
| Input boundary | 3.20:1 |
| Filled accent button text | 8.32:1 |

Verified keyboard navigation, Enter/Space disclosure/Save, route-heading focus,
Back focus restoration, skip link, labelled filters, native table headings/captions,
polite changed-status feedback, persistent error alert and reduced-motion behavior.
Financial states also have text and direction symbols, never color alone. Forced
colors has system-color focus and explicit boundaries. Actual screen-reader
speech, native Windows rendering/high-contrast behavior, Safari/Firefox and native
browser zoom are **not verified**. 200% root text resize and 320px reflow were
verified; they are not described as native browser zoom.

## Validation

All tests use mocks/deterministic fixtures; no real provider credentials or market
calls. Real configuration is used for the 44-theme browser fixture. Additional
presentation states are explicitly mocked API snapshots, not financial-engine
assertions or published recommendations.

| Check | Result |
|---|---|
| Full unittest suite | 321 run; 319 passed, 2 native-Windows-only skips |
| Focused vNext unittest suite | 114 run; 113 passed, 1 native-Windows-only skip |
| Pre-launch / launch / SQLite lifecycle within those suites | 8 / 7 / 11 passed |
| Frozen Market Matrix | All 64 cases passed |
| `tests/smoke_vnext_ui.py` | Refresh, canonical combined TXT, Saved, mobile and original static inspection preview passed |
| `tests/smoke_prelaunch_ui.py` | Research banner/trend/Primary TXT, Save and automatic launch initialization passed |
| `tests/smoke_lunar_ui.py` | All six surfaces, controls, context, state coverage and accessibility checks passed |
| JavaScript syntax, Python compilation, whitespace | Passed |
| Configuration validation | Valid, zero configuration blockers |

Desktop: **1440, 1600, 1920px**. Theme table width/scroll width respectively
1166/1166, 1326/1326, 1606/1606: no desktop horizontal travel. Narrow layouts:
800, 390, 320px; all six surfaces have no document overflow. Genuine member and
candidate research tables retain a labelled, local horizontal scroller. Themes
reflow into labeled units. 200% root text resize preserves five destinations.

State coverage: initial/no prior snapshot, refresh running/success/failure with
prior data retained, real pre-launch research, initialized launch, live-history
label, long/neutral/short/Unclassified market displays, no Primary themes, no
candidates, available candidates, short qualification and supplied earnings date,
unavailable metrics, empty/populated Saved and retained older bookmark. Financial
rules themselves are covered by the unchanged engine tests. Browser runs had
**zero page errors and zero external requests**.

Run with the existing browser-test environment (Playwright + Chromium):

```text
python -m unittest discover -s tests -v
python -m unittest discover -s tests -p "test_vnext*.py" -v
python tests/smoke_vnext_ui.py
python tests/smoke_prelaunch_ui.py
python tests/smoke_lunar_ui.py
node --check static/vnext/app.js
python -m compileall -q src scripts tests
```

Optional environment variables for the new smoke: `THEMESCOPE_AXE_SCRIPT` points to
an already available local axe-core script; `THEMESCOPE_UI_ARTIFACTS` is a temporary
screenshot/report destination. Neither is needed at runtime. No npm package or
browser-CDN dependency was added to ThemeScope. Screenshots linked below are
labelled **deterministic test data, not live** and contain no raw provider payload.

[Overview](../design-plans/lunar-lounge/overview-1440.png) ·
[Themes](../design-plans/lunar-lounge/themes-1920.png) ·
[Theme Detail](../design-plans/lunar-lounge/theme-detail-1440.png) ·
[Candidates](../design-plans/lunar-lounge/candidates-1440.png) ·
[Saved](../design-plans/lunar-lounge/saved-populated-1440.png) ·
[Narrow Theme Detail](../design-plans/lunar-lounge/theme-detail-320.png) ·
[Machine-readable browser results](../design-plans/lunar-lounge/results.json).

## Frozen boundary and remaining review

`src/`, `config/`, runtime/provider/storage logic, calculation engine, Matrix,
memberships, evidence, exports and official launch history have no diff from the
functional parent. Launch remains **2026-11-06 close**, first earned session
**2026-11-09**. All original inspection refs are preserved. `main` remains
`cf4fdb1e4784ff6fbc7183d5e709ffae044ec2fe`; no merge or deployment.

Gate E's native Windows functional retest remains open independently. This UI
checkpoint does not close it. No unresolved UI choice blocks this implementation;
the finished single direction is stopped for user visual review. Any later direct
stock-return/chart-link enhancement requires a separately approved data contract.
