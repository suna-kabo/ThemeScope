# ThemeScope design

The approved frontend is a charcoal research journal built around **Market ?
Themes → Primary**. Saved and Methodology are utilities. Snapshot details and
local refresh share a disclosure.

Market puts Bias before paired SPY/QQQ evidence and a secondary IWM context row.
Its continuation leads to theme research. The returns landscape is optional.
Themes leads with Research Priority, State, raw 5-session Change and returns.
Primary uses theme chapters and ordered stock queues; explicit global sorts offer
a flat queue. Filters affect the view, while exports retain the full session list.

Theme names open Full Theme. Quick View is an explicit secondary action. Stock
inspectors preserve the originating theme context. Back/Forward restores focus and
Full Theme keeps per-theme filters. Saved persists in local app state. Price context
is a secondary disclosure inside the theme. Financial color is accompanied by text and signs.

The shared CSS tokens in `static/vnext/app.css` define the current system:
charcoal canvas `#191b1d`, light text `#eceeeb`, restrained semantic color,
ruled rows and aligned tabular numbers. Self-hosted Figtree is bundled as
`Research.woff2` with its pinned SIL OFL license. Historical Inter belongs to the
separate legacy dashboard.

Desktop width supports comparison; mobile uses labeled research rows, wrapping
navigation and deliberate filter disclosures. Browser text sizing, forced colors
and system reduced motion supply accessibility preferences. Do not redesign this approved UI during maintenance.

The [release gate](tests/smoke_research_v2_ui.py) covers eight widths, inspectors,
keyboard/history, Saved, exports, refresh recovery, 200% text/reflow and accessibility.
Earlier designs and review captures are [archived](docs/archive/ui/design-plans/README.md).
