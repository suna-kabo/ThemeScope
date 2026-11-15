# ThemeScope design

The approved frontend is a charcoal research journal built around **Market ?
Themes → Primary**. Saved and Methodology are utilities. Snapshot details and
local refresh share a disclosure; public snapshots expose details only.

Market puts Bias before paired SPY/QQQ evidence and a secondary IWM context row.
Its continuation leads to theme research. The returns landscape is optional.
Themes leads with side-aware five-session movement and a complete sortable ledger.
Primary uses theme chapters and ordered stock queues; explicit global sorts offer
a flat queue. Filters affect the view, while exports retain the full session list.

Theme and stock inspectors preserve the originating research context. Full-theme
routes, nested Back/Forward, focus restoration, keyboard actions and browser-local
Saved retain their compatibility contracts. Relative state and price direction
stay distinct. Financial color is accompanied by text and signs.

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
