# ThemeScope motion grammar

Motion explains a change already made; it never delays input, focus or research.
Native CSS plus Web Animations API, no animation library. Visual identity:
Tidal Vector's selected plane and a consistent rightward research hierarchy.

| Family | Meaning | Implementation |
| --- | --- | --- |
| Shift · 180ms | top-level workspace change | 5px vertical resolve + opacity, only explicit navigation |
| Slide · 240ms | deeper/back research | nested content/title ±14px; outer right sheet 24px; 180ms exit |
| Sweep · 200ms | research mode/view change | travelling selection plane plus 8px content resolve |
| Reveal · 160ms | expose secondary information | menus/filters/help; native Methodology disclosure where supported |
| Confirm · 140ms | action applied/initiated | small non-blocking feedback, never a modal |
| Lock · persistent | current research object | cyan rail, selected navy plane, primary identity; no looping animation |

Map selection adds a single 180ms ring response and readout confirmation; it does
not alter returns, domains or keyboard selection semantics. A changed published
Market Bias may Sweep its context plane; unchanged polls do not replay effects.

Arrival: `cubic-bezier(.22,1,.36,1)`. Departure: `cubic-bezier(.4,0,1,1)`.
Selection travel: `cubic-bezier(.2,.8,.2,1)`. No default-ease/bounce/elastic motion.

## Interruption and performance

`workspace.js` owns the named timings, one running effect per element and selection
geometry. New intent cancels the previous effect. The navigation plane starts from
its currently rendered rectangle; resize/observer passes do not interrupt an
unchanged target. Geometry is set once, then transform/opacity animate; there is no
continuous width/height/position loop. No per-row animation on large data tables.
Native disclosure interpolation is bounded to opening/closing, with immediate
fallback where unsupported. Native dialog semantics and the backdrop remain intact.

No focus delay, decorative pointer follower, ambient loop, number tween, scroll
choreography, particles or external runtime assets. A hidden document has no
indefinite work to stop.

## Reduced motion

Both OS `prefers-reduced-motion` and ThemeScope Reduce Motion remove spatial
movement, rather than merely accelerating it. CSS transitions are disabled and
programmatic effects are skipped/cancelled. Selection, focus, disclosure, status
and action feedback remain immediately visible. Tests exercise a preference change
while effects are running, keyboard tab travel, rapid navigation reversal and
nested Back restoration.

## References

- [Impeccable](https://github.com/pbakaus/impeccable): authored focal state, hierarchy,
  browser verification, no animation debt.
- [Codex frontend-design](https://github.com/dobromirdikov/codex-frontend-design-skill):
  committed visual world, dense operational ergonomics, rendered QA.
- [Motion Prompt](https://github.com/showheyohtaki/motion-prompt) and its
  [gallery](https://showheyohtaki.github.io/motion-prompt/): tabs, selection,
  reveals and feedback vocabulary, not copied runtime code.
- [Motion Director](https://github.com/frankxai/awesome-motion-design-agent-skills/blob/main/skills/motion-director/SKILL.md):
  lightest stack, interruption/reversal, reduced motion, observed evidence.

The public guidance was read directly; no global settings/hooks were installed.
Target-browser timing, state, keyboard and rendering are tested. Native Windows
smoothness and manual assistive-technology review are not claimed from Chromium
cloud evidence.
