# ThemeScope motion

Motion explains completed state changes without delaying input or focus. Native
CSS and Web Animations API provide finite effects; system reduced motion cancels
running effects and retains all actions.

| Interaction | Current treatment |
| --- | --- |
| Navigation | Immediate route/focus with a brief 5px resolve |
| Selection | Restrained destination underline |
| Inspector | Short lateral reveal/exit; native dialog focus restoration |
| Filtering/disclosure | 160-200ms replacement without stagger |
| Save/export/refresh | Brief nonblocking confirmation |
| Map selection | 180ms ring/readout response |

`static/vnext/workspace.js` centralizes durations and cancels superseded effects.
CSS handles responsive surfaces and native dialog transitions. Unchanged polling
does not replay navigation. Loading uses static skeletons; refresh reports actual
backend progress and retains the committed snapshot on failure.

Browser acceptance covers interruption, nested Back/Forward, reduced motion and
responsive inspectors. Browser text sizing supplies accessibility preferences.
