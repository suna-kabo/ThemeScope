# Ground-up research workspace

## Direction and boundaries

Replace After Close with a cool, light research workspace under a dark horizontal
masthead. The desktop composition is a working comparison surface: market evidence
at the left, theme leadership and stock research alongside it. The navigation
expresses Market → Themes → Primary; Saved and Methodology are secondary tasks.
No hero, decorative chart, metric-card grid, or permanent left navigation.

Scope: `static/vnext/index.html`, `app.css`, and presentation rendering in `app.js`;
design/motion documentation; browser and source tests that freeze presentation.
Preserve workspace state helpers, backend calculations, snapshot schema, export
contents/order, effective memberships, local-only operation, Saved keys, routes,
inspectors, refresh transactions and all financial semantics.

## System

- Canvas ice #edf1f5, working surface white #ffffff, masthead ink #17283f,
  body ink #203047, secondary slate #526176, selection blue #174ac7.
- Positive teal #167052, negative red #b32d49. Strength is blue/neutral;
  financial signs and named states remain explicit.
- Pinned offline Inter for data and controls, native Segoe UI for navigation;
  tabular figures, 14px body, 13px controls, 12px metadata, 24px page titles.
- 4/8/12/16/24/32 spacing, 36px desktop controls and 44px touch controls.
- Tables retain column semantics, aligned numerics and compact row rhythm.
  Theme identity and state lead; comparison metrics remain distinct.
- Inspectors use an opaque white working sheet with a dark title bar, preserving
  the originating selection and natural history. Display controls stay secondary.
- Desktop uses all available width. At tablet, market evidence spans the page;
  mobile uses compact labeled rows and a four-destination bottom navigation,
  with Methodology in the masthead. No horizontal research-table dependence.
- Motion only for selection and opening/closing inspection. Reduced motion is
  immediate. Avoid page entrances, sweeping highlights and ornamental hover motion.

## Review baseline

Personally inspected current Market, Themes, Primary, theme inspector, stock
inspector and mobile Market using local Chromium with synthetic full-universe data.
Saved and Methodology captures retained for comparison; remaining pre-change
surfaces and interactions are inspected before implementation.

Observed weaknesses: market evidence behind duplicate disclosure layers; substantial
mobile chrome before research; low distinction between interactive rows and data;
repeated long theme labels in the stock list; undifferentiated dark surfaces;
large one-dimensional overview and unnecessarily repeated helper copy.

## Validation

Keep before/after synthetic captures locally in runtime. Review all major surfaces
at 1920/1440/1280/768/430/390/360/320, including actual screenshots, separately
recording functional and visual judgments. Exercise filtering, sorting, inspection,
Saved, exports, history, display, keyboard, loading/error/empty, reduced motion and
200% text/reflow. Run existing current browser gates, axe, JS and full Python suite.
Document obsolete presentation assertions changed, without weakening behavior.
Do not publish or merge main. Finish bounded changes with checks and commits.
