# Independent UI acceptance review

Reviewed `3d767fc` on `feature/ui-ground-up`, 15 November 2026. The running
product was inspected before consulting the previous validation report.
All observations used isolated synthetic data. No live provider or publication.

## Corrections from rendered use

- Phone Primary filters opened outside the viewport; exports used the wrong edge.
- Selected segments were barely distinguishable; selected mobile rows broke into
  separate colored cells. Both now have deliberate, continuous selection states.
- Long lists lost desktop navigation. The masthead and table headings now remain
  accessible. Replaced tables receive fresh overflow measurements, preventing
  header overlap after filtering or resetting a list.
- Excessive preview/phone row spacing and repeated comparison/sample explanations
  reduced scanning density. Reasons remain available to assistive technology,
  hover, and inspectors; research values and meanings remain unchanged.
- Inspectors lacked a participation label and repeated stock identity copy.
  Empty relationship disclosures are hidden, and metric help stays with its label.
- Saved now explains its empty state; untracked concepts no longer show an
  unrelated active-theme research count.

## Direct review

Viewed Market, Themes, Primary, Saved, Methodology, full Theme, theme inspector
and stock inspector at 1920, 1440, 1280, 768, 430, 390, 360 and 320 CSS pixels.
Operated search, filters, sorting, grouping, exports/downloads, Saved/removal,
inspectors, nested Back/Forward, keyboard focus, hover, metric help, display
settings, map selection, loading, empty results and connection failure.
Revisited affected views after fixes. Compared archived screenshots, including
`runtime/redesign-before/`, after the independent first pass. The redesign has
substantially different navigation, composition, typography and visual identity.

Final local screenshots: `runtime/independent-final/` (64 surface captures,
eight review sheets, and focused interaction/state captures).
Browser regression artifacts: `runtime/independent-acceptance/`.
These are synthetic local review artifacts, not a publishing or inspection bundle.

## Final checks

- Current Chromium browser gate: pass, eight widths, 20 axe audits with zero
  violations; no page errors or external requests. Added assertions check actual
  filter options, disclosure bounds, selected controls and sticky header geometry.
- Local/static and prelaunch browser smoke: pass.
- JavaScript syntax and workspace/dashboard helper tests: pass.
- Python compilation, configuration and membership validators: pass.
- Full Python suite: 468 run; 465 passed, one skipped, two errors. The two errors
  are `test_output_symlink_rejected` and
  `test_tampered_output_symlinks_and_extra_files_rejected`: Windows denies test
  symlink creation with WinError 1314. No assertion was weakened or bypassed.

Remaining limits: Chromium emulation, no physical-device or screen-reader use,
and no live-provider testing. Backend, research formulas, exports, routing and
Saved persistence contracts were not changed.
