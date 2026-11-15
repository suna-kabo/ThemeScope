# ThemeScope UI v3 motion

Motion explains a state change already made. It never delays input or focus.
Native CSS and Web Animations API provide one coherent hierarchy; no animation
dependency or decorative looping effects are used.

| Interaction | Treatment |
| --- | --- |
| Top-level navigation | Immediate route and focus; brief 5px content resolve |
| Selected destination/view | Stable blue destination underline; quiet view-selection marker |
| Deeper/back research | 240ms ±14px inner content; opaque research sheet, brief exit |
| Disclosure, filtering and sorting | Short 160–200ms content replacement, no row stagger |
| Save, export and refresh completion | 140ms nonblocking confirmation |
| Buttons and links | 120ms color response and short press feedback |
| Map selection | One 180ms ring response and readout update |

Arrival uses cubic-bezier(.22,1,.36,1); exit (.4,0,1,1); selection travel
(.2,.8,.2,1). There are no bounce curves, hover-lift cards or entrance animations
on every section. Unchanged polling does not replay navigation effects.

`workspace.js` cancels the previous effect on an element before starting another.
Selection remains visible by position, text and focus even without motion.
The native inspector owns focus; closing returns to the correct trigger and
restores scroll. Nested Back returns through research context.

Loading skeletons preserve expected research geometry and use static surfaces.
Real refresh status uses actual backend messages; no invented percentage or
fake delay. Existing content remains during refresh and failures.

Both prefers-reduced-motion and the browser-local Display preference suppress
animation/transitions. Changing that preference cancels running effects. Reduced
motion retains all actions and state. Browser acceptance covers interruption,
Back/Forward, reduced motion and responsive inspector behavior.
