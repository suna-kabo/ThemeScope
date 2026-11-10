# ThemeScope: quiet personal research terminal

This document describes the implemented `static/vnext` workspace. The approved
professional-refinement brief governs this pass; financial and lifecycle rules
remain in their versioned methodology. Dark ThemeScope / Lunar Lounge identity is
preserved. There is no light mode, remote font, UI library or motion dependency.

## Page responsibilities

- **Overview:** Market Bias first, Extension/focus second, compact SPY/QQQ evidence
  plus lighter IWM context, then four-item research destinations. The Returns Map
  is available as a disclosure instead of dominating the first viewport.
- **Themes:** cross-theme comparison. Strength Rank is the supplied complete-universe
  rank; displayed Strength is separate from Research Priority. Filters do not rank.
- **Candidates:** one workspace with Directional/Countertrend tabs. Search and Theme
  lead the filter bar; Role/W/Earnings are in a secondary disclosure. View and sort
  are quieter utilities. Export is scoped to the published lens, not current filters.
- **Inspector:** current theme/ticker context, concise explanation and member preview.
  Full Theme owns the complete member/filter/measurement surface. Back returns through
  nested sheets with state, focus and scroll preserved.
- **Saved:** continuation of a chosen theme/lens, independent of present qualification.
- **Methodology:** meaning, interpretation, then exact rules in nested disclosures.

## Executable tokens

The single CSS foundation is `static/vnext/app.css`: tokens, components, responsive
rules and motion, in that order. Do not append a parallel late-override design.

| Foundation | Implemented choice |
| --- | --- |
| Desktop rail | `--rail-width:11.5rem` (184px at default text) |
| Desktop gutter | `--s6:24px`; narrow gutter 16px |
| Spacing | `--s1/2/3/4/6/8/12`: 4,8,12,16,24,32,48px |
| Controls | radius 4px, normally 32–36px; touch controls at least 44px high |
| Floating utilities | radius 8px, border plus a quiet elevation shadow |
| Research sections | flat; row/section dividers, no decorative card corners/shadows |
| Compact / Comfortable | table cell vertical padding 4 / 8px |
| Page / section title | 28 / 17px (24px page title below 520px); weight 600 |
| Body / supporting | 14 / 12–13px; normal weight 400 |
| Identity / labels | identity 600, labels 400–500; tabular numeric measurements |

Some dimensions are functional rather than spacing: 18px checkboxes, 24px desktop
help and table-link targets, a 28px compact save target, and SVG axis/hit geometry. Text scales from
100% to 200% using the existing Display preference; readable text is not shrunk to
force table fit. Default displayed precision: Strength one decimal, breadth whole
percent, W/returns two decimals, prices two decimals. Calculations keep full precision.

## Typography and assets

`@font-face` loads the existing `static/InterVariable.woff2` as **ThemeScope Inter**,
with a stable system sans-serif fallback. The existing SIL OFL 1.1 licence is shipped
alongside it. Local runtime and both static builders serve the same font. The public
builder pins font/licence SHA256 values and rejects replacements; this is not a new
binary upload or a remote font dependency. Source UI/behaviour remains ordinary
HTML/CSS/JavaScript. `workspace.js` supplies presentation/interaction helpers only.

## Colour and emphasis

Warm grounds: page `#191724`, rail `#1e1a2b`, sections `#24212f`; raised utility
`#2d293b`. Text `#f1ece9`, secondary `#c9c1d3`, muted `#b5abbf`. Lavender `#cebbff`
is for primary actions, selected tabs/views, focus and saved/selected entities.
Identity links normally use primary text and a fine underline; hover/focus strengthens
the affordance. Green/red carry defined financial positive/negative meanings only.

Navigation has one selected background. No skewed marks, asymmetric decorative
radii, hover lift, ambient effects or stacks of badges. Controls communicate their
job: underline tabs for lens, moving neutral selection for view segments, native
selects for filters, quiet links for secondary navigation. No ambiguous Candidates
sidebar count is displayed; Saved's count has one clear scope.

## Comparison and responsive strategy

Tables remain tables at default-text laptop/tablet widths, including 1024 and 768px.
Themes prioritises Rank, Theme, Strength, returns, Trend and Research. Rank Change
is deprioritised below 64rem available width; breadth below 55rem. Local horizontal
access is signposted only if needed. There is no bounded vertical results scroller.

Only below **36rem logical content width** do Theme rows become summaries prioritising
identity, Strength, Trend and Research. The same threshold provides Candidate reflow;
this is also appropriate when text is enlarged. Full details remain available through
research links. Benchmark evidence follows the same readable narrow-width principle.
The desktop rail moves above content at 800px. At 520px controls have touch-sized
hit areas; the header wraps without covering the brand or hiding the completed date.
Inspectors use a 38rem right sheet capped at viewport width, with content-based reflow.

## Interaction and motion

| Interaction | Purpose / timing |
| --- | --- |
| Lens tabs | sliding underline 240ms; explicit content switch fade 160ms |
| View segments | moving selected background 240ms |
| Metric help | focus/hover after 250ms; 160ms fade, 4px arrival; keyboard pin/escape |
| Methodology | native disclosure, 240ms smooth content/chevron where supported |
| Inspector | 200ms right-sheet appearance/disappearance; native dialog semantics |
| Saved/export feedback | non-blocking 160ms toast; never an unverified “download succeeded” claim |
| Text/control hover | 100–160ms colour/underline feedback, without movement |

These are native CSS/JS equivalents of the requested motion vocabulary. No library
code is copied. OS reduced-motion and Display Reduce Motion suppress transitions;
programmatic fades are guarded/cancelled too. Financial values and initial table rows
never animate. Older browsers fall back to immediate native disclosures.

The Returns Map keeps every valid observation and nice linear ticks. Hover/focus
inspects, click/Enter selects, and **Open theme** deliberately enters research.
Roving point focus makes this one Tab stop instead of dozens. Dropdown selection
remains available for keyboard and touch users.

## Accessibility and operational states

Semantic headings, table headers, native controls and text states stay explicit.
Help buttons have keyboard-accessible content and stable Methodology links; native
`title` may supplement, never replace, that help. Native inspector focus management
and nested Back are preserved. Contrast and forced-colour modes remain supported.
Loading precedes genuine empty results. A failed/disconnected refresh preserves the
committed snapshot and identifies its completed session. Missing comparisons remain
missing; unavailable, insufficient coverage and no active basket are distinct causes.

Browser fixtures/screenshots are review aids, never live chronological evidence.
Current user-reported validation: Nov 6 PASS; Nov 9 PASS; Nov 10 PENDING; Gate E OPEN.
No merge or deployment is authorised by this design document.
