# First verified production publication from main

Verified on 15 November 2026 (Hong Kong). This records the first main publication
that passed live browser acceptance, rather than claiming that an upload alone
proved the application usable.

| Evidence | Verified result |
| --- | --- |
| Ground-up UI merge | PR #11, `6c538c0b2d35d08878001bf5dddd9da469d38b2e`, present in main |
| First accepted publication source | `08b47a0eb7bd2447fa9928a88f3dd17cf43df596` on clean main |
| Helper | Existing `update-public.cmd`, normal live SIP mode |
| Completed US session | `2026-11-13`, selected by ThemeScope |
| Completeness | 904 required / 904 valid; successful new local snapshot |
| Production deployment | `dac223c4-641a-477c-8f78-fde1d5d9e6fe`, branch main, matching source |
| Public domain | [ThemeScope](https://themescope.pages.dev) |
| Deployment permalink | [Verified deployment](https://dac223c4.themescope.pages.dev) |
| External configuration | GitHub default main; existing Pages production main; automatic production Git builds disabled |

Both required workflows passed before the prerequisite fixes were merged. PR #12
made the public validator use the existing 34-digit calculation context without
changing values or exact comparisons. PR #13 preserved the frozen status node and
made score-bar rendering compatible with the unchanged public CSP. Its expanded
browser gate checks actual security headers; the zoom assertion waits for layout
observers before inspecting overflow.

The approved helper confirmed Refresh PASS, Completeness PASS and Public
deployment CONFIRMED. Live browser checks then verified Market, Themes, Primary,
Saved, Methodology, both inspectors, navigation, filters, nested Back/Forward,
browser-local Saved persistence and TXT downloads at 1440px and 390px.

The domain's HTML, CSS, JS, snapshot and font matched the validated upload hashes.
Combined and every theme TXT matched the frozen snapshot, including full-session
combined export under empty view filters. Fourteen live WCAG audits found no
violations; console, HTTP, external and API request errors were absent. Refresh
was hidden and a programmatic click made no API request. The real session banner
was correct and the synthetic indicator was hidden. Rendered desktop/mobile
screenshots were inspected locally and remain ignored.

Only after these checks did the separately scoped cleanup branch begin. Its
frontend deletions require a subsequent main publication after merge. This is a
first-publication record, not a claim that its source SHA is every later deployment.
[Current workflow](public-snapshots.md) and [branch/tag retirement](../development/branch-checkpoints.md)
remain the operator references. Local SQLite history, provider cache, backups,
credentials and the user's browser Saved state were preserved.
