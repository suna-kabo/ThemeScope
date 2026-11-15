# ThemeScope UI redesign exploration

**Design exploration only. Prepared 6 November 2026, Hong Kong.**

Functional checkpoint: `ed12ba49e4ea6ce3cfb1998ae6bdc72d11fe0324` on
`refactor/themescope-vnext`. Current remote `main` was checked at
`cf4fdb1e4784ff6fbc7183d5e709ffae044ec2fe`.

**Recommendation: Lunar Lounge.** It combines a welcoming dark identity with a
serious theme-to-member research workflow. Signal Atlas is the density-first
alternative; Comet Club is the more expressive, candidate-first alternative.
These are exactly three concepts, not three skins of the same layout.

No product source, API, calculation, configuration, persistence or export was
changed. No implementation, commit, push, merge or deployment is authorized by
this document. Existing `DESIGN.md` is audit evidence, not a constraint preserving
the rejected identity; the user's new brief governs this exploration. Gate E's
functional/native-Windows review remains separate and open.

## 1. Evidence and audit method

### Files inspected

| Area | Files / evidence | Purpose |
|---|---|---|
| Main UI | `static/dashboard_template.html`, `static/dashboard.css`, `static/dashboard.js` | Navigation, table controls, detail flow, typography, responsive behavior |
| vNext UI | `static/vnext/index.html`, `static/vnext/app.css`, `static/vnext/app.js` | Current page, displayed fields, state handling, Save and downloads |
| Product constraints | `AGENTS.md`, `GOALS.md`, `PLANS.md`, `PRODUCT.md`, `DESIGN.md`, approved vNext methodology | Frozen scope and semantics |
| Read-only contract check | `src/themescope/research/engine.py`, `src/themescope/local/app.py`, existing fixture helpers | Distinguish available UI data from desired-but-unexposed fields |
| Render evidence | Unchanged application surfaces with temporary deterministic fixtures | Confirm density, navigation, focus and overflow observations |

The three legacy UI files were compared against the checked `main` ref and have
identical SHA256 hashes. The local copies therefore represent current main's UI,
not an assumed old screenshot. The vNext render used the real approved 44-theme
configuration with manufactured prices/volumes, not real account or market data.
Optional external earnings were mocked. All databases and generated HTML stayed
in temporary directories. Screenshots have an audit watermark added only to the
temporary browser DOM; they are not redesign implementations.

Browser inspection used Chromium at 1440×1000, with vNext width checks at 1600 and
1920, plus a 390×844 mobile check. No page errors occurred. This is a visual and
interaction audit, not a complete accessibility conformance test. Native Windows,
screen readers, real browser 200% zoom, 320px and RTL were **not verified** here.
Concepts below include explicit requirements for those later checks.

### Evidence files

- [Legacy theme research, dark, 1440px](assets/legacy-main-themes-1440.png)
- [Legacy member drilldown, 1440px](assets/legacy-main-members-1440.png)
- [Current vNext entry view, 1440px](assets/vnext-overview-1440.png)
- [Current vNext themes, 1440px](assets/vnext-themes-1440.png)
- [Current vNext themes, 390px](assets/vnext-themes-390.png)
- [Measured observations](assets/audit-observations.json)

These images document the existing UIs with **deterministic test data**. Their
returns, scores, priorities, counts of qualifying stocks and dates are not a live
research recommendation. The 44 Active / eight Watch-only configuration is real;
the displayed financial measurements are not.

## 2. Current UI audit

### Legacy/main: retain the behavior, replace the presentation

The legacy UI is an actual multi-page application surface. Its useful behaviors
include sortable tables, combined search/filtering, a theme-to-member route,
previous/next theme browsing, browser/application Back, restored view state,
explicit export links, tooltips and a working dark/light toggle. These are worth
retaining as interaction principles. Its ETF-era models, values and state formats
must not be carried into vNext.

| Severity | Location | Before: verified evidence | Proposed direction, not an applied fix | Why |
|---|---|---|---|---|
| Medium | `static/dashboard.js:1216` | Theme table has **15 columns**; 53 legacy exposures in the fixture | Keep score, returns, trend, breadth and priority in a deliberately grouped research table | Equal visual weight makes the important comparison expensive |
| Medium | `static/dashboard.js:1288` | Member table has **14 columns**, including ETF-relative fields | Lead with ticker, role, peer W and eligibility; disclose supporting metrics | A user should find the research reason before auditing every input |
| Medium | `static/dashboard.css:10` | Theme table has a 1422px minimum width; measured container is 1328px at 1440 | Plan column budgets and a real narrow-screen layout | The primary desktop viewport already needs horizontal travel |
| Medium | `static/dashboard.css:39` | 1200–1599px collapses navigation to icons and clips the wordmark | Keep legible navigation labels or an explicit intentional compact rail | Density should not make product identity/navigation cryptic |
| Medium | `static/dashboard.css:5` and `:10` | Controls, header labels and numeric tables rely heavily on small monospace | Sans-serif interface and tabular figures; reserve monospace for technical identifiers, if any | Financial precision does not require a terminal appearance |
| Medium | `static/dashboard.js:957` | Toolbar exposes search, type, priority, sort and direction at once; headers add tools | One concise toolbar, active-filter summary and contextual help | Controls compete with the research hierarchy |
| Medium | `static/dashboard_template.html:56` | “Watchlist” means a configured theme-member surface | Use Theme Detail / Members; reserve **Saved** for manual bookmarks | The same word currently describes different mental models |

Legacy details such as ETF anchors, stock-versus-ETF comparisons, maintenance caps,
manual daily collection exports and its old breadth thresholds are historical
compatibility only. None is a redesign feature or a vNext formula reference.

### Current vNext: clearer semantics, insufficient research workspace

| Severity | Location | Before: verified evidence | Proposed direction, not an applied fix | Why |
|---|---|---|---|---|
| High | `static/vnext/app.js:29` polling / `render()` | Focused Save button for AVAV became **BODY** after the next polling render | Keep interactive nodes/focus stable across unchanged snapshot polling | Keyboard users can lose their current task without acting |
| Medium | `static/vnext/index.html:3` | Market, plan, candidates, themes and Saved are one scrolling document | Separate Overview, Themes, Candidates and Saved views | An application needs clear task locations, not just anchor jumps |
| Medium | `static/vnext/app.js:18` | Fixture renders **187 candidate rows** before Themes; Themes starts around **13,531px**, document height **18,322px** | Overview previews a bounded useful subset; full results live in dedicated pages | Large valid result sets should not bury another core surface |
| Medium | `static/vnext/app.css:1` | Pine navigation, green actions, large white surfaces and generous section spacing | Replace the identity with dark neutral layers and an independent navigation accent | The sustainability/SaaS association conflicts with the brief |
| Medium | `static/vnext/app.js:20` | Themes has six columns and **zero search, sort or filter controls** | A 44-theme research table with explicit query, sort, family and priority controls | Simplification removed the tools needed to inspect the universe |
| Medium | `static/vnext/app.js:20` | Family leads in large text; theme name is smaller; rows follow theme ID order | Theme name leads; family is metadata; ordering is clearly stated | The thing being compared should be the strongest row anchor |
| Medium | `static/vnext/app.js:18` | Only qualifying stocks are shown; no Theme Detail or all-member view | Open the theme's existing eligible member relationships, including nonqualifiers | Users cannot explain a theme or investigate why another member did not qualify |
| Medium | `static/vnext/app.js:19` | Candidate table has eight flat columns, repeats multi-theme relationships, and exposes long IDs | Provide explicit relationship and unique-ticker views, with assignment details | Deduplication is an export rule, not proof a stock belongs to only one theme |
| Medium | `static/vnext/app.js:7` | “Watchlist” is a browser-local ticker bookmark array | Rename visible UI to **Saved**, preserving existing stored bookmarks | Bookmarking must not imply configured membership or qualification |
| Medium | `static/vnext/app.css:1` | At 390px the themes table scrolls 690px inside a 350px content area | Recompose theme rows for mobile; preserve secondary facts in labeled disclosure | Shrinking the same desktop table conceals the important trend/priority fields |
| Low | `static/vnext/app.js:27` | Full raw ISO refresh timestamp dominates operational metadata | Separate “Completed US session” from human-readable refresh time | Freshness is essential, but should be easy to parse |

At 1920px vNext caps the main element at 1540px while retaining its sidebar. The
proposal uses wider desktop space deliberately for research, not additional blank
marketing space. Actual row counts vary with the session; the long-page finding
is evidence from one valid stress fixture, not a prediction of live counts.

**Layout audit disposition: Block production design sign-off.** The observed
focus loss needs a later authorized implementation fix. The exploration itself
is complete without modifying it. This disposition does not close or replace Gate E.

## 3. UI Skills discovery and selection

Discovery was performed on the current registry, rather than guessed from old
skill names. `ui-skills` CLI version **0.2.4** returned **638 skills / 27 categories**.

```text
npx ui-skills start
npx ui-skills categories
npx ui-skills list --category visual
npx ui-skills list --category systems
npx ui-skills list --category interaction
npx ui-skills list --category motion
```

Categories discovered: accessibility, motion, systems, visual, interaction,
performance, craft, taste, typography, color, 3d, frontend, architecture, testing,
debugging, code-quality, tooling, video, nextjs, nuxt, vue, react-native, threejs,
remotion, swiftui, frameworks, shadcn-ui-development.

The inspected category lists contained 349 visual, 130 systems, 105 interaction
and 117 motion entries; skills can belong to more than one category. The first
CLI request failed to reach the registry. Retrying with Node's environment-proxy
support succeeded. Commands used a temporary working directory/npm cache outside
the repository; no skill installer or repository configuration hook was run.

`ui-skills-root` was read as the routing protocol, **not a fourth active design
skill**. This broad, multi-surface redesign justifies its maximum of three.
The selected contexts were fetched with:

```text
npx ui-skills get anthropics/frontend-design
npx ui-skills get jakubkrehel/better-layout
npx ui-skills get wshobson/interaction-design
```

Only the following three skill bodies were loaded:

| Selected skill | Exact context retrieved | Why it earns a slot | How used here |
|---|---|---|---|
| **anthropics/frontend-design** | [Registry skill](https://www.ui-skills.com/skills/anthropics/frontend-design), [source](https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md) | Distinct visual direction instead of a familiar dashboard kit | Three different compositions, deliberate typography and a single memorable identity gesture per concept |
| **jakubkrehel/better-layout** | [Registry skill](https://www.ui-skills.com/skills/jakubkrehel/better-layout), [source](https://github.com/jakubkrehel/skills/blob/main/skills/better-layout/SKILL.md) | Directly addresses grouping, reading order, progressive disclosure and adaptive layout | Metric grouping, control zones, content-based collapse and preserving research context |
| **wshobson/interaction-design** | [Registry skill](https://www.ui-skills.com/skills/wshobson/interaction-design), [source](https://github.com/wshobson/agents/blob/main/plugins/ui-design/skills/interaction-design/SKILL.md) | Complements visual/layout work with feedback, continuity and reduced-motion behavior | Specific action-driven microinteractions, honest refresh states and stable selection |

The two `better-layout` reference files, `grouping-and-alignment.md` and
`spacing-and-adaptivity.md`, were also read. References are part of that skill,
not additional selected skills. Framework examples in skills are not stack
requirements. Instructions to build or fix are superseded here by the user's
**exploration-only** scope. No React, Tailwind, animation library or font package
is introduced.

Candidates considered from registry descriptions, but **not loaded**:

| Candidate | Rejected for this task because… |
|---|---|
| `ibelick/baseline-ui` | A cleanup pass is too narrow for intentional identity and architecture replacement; no Tailwind migration is needed |
| `ibelick/improve-ui` | Its evidence-first audit is useful, but overlaps our source/browser audit and selected layout angle; identity preservation is not this brief |
| `dammyjay93/interface-design` | Useful consistency guidance, but less direct than the selected layout skill and overlaps the visual slot; not rejected merely for its SaaS examples |
| `0xdesign/design-lab` | Broad variant workflow overlaps the requested three concepts; no interview or runnable variant implementation is needed now |
| `nextlevelbuilder/ui-ux-pro-max` | Broad style/stack catalog adds more context than needed for this precise product brief |
| `pbakaus/impeccable` | Strong craft coverage, but largely duplicates the chosen visual/layout contexts |
| `emilkowalski/improve-animations` | Best for auditing an existing motion system; this work needs a new restrained interaction vocabulary |
| `raphaelsalaja/12-principles-of-animation` | Rich animation vocabulary is less useful than direct feedback/orientation for a data-heavy daily tool |
| `emilkowalski/prototype` | Its in-page variants would require implementation expressly excluded from this phase |
| `jakubkrehel/better-ui` | Broad polish overlaps both visual and interaction slots; the more specific layout skill addresses the largest verified structural failures |

## 4. Reference study: inspiration is not a layout to copy

| Public reference inspected | Observed principle | Proposed ThemeScope decision | Explicitly not borrowed |
|---|---|---|---|
| [Alpaca public homepage and product image](https://alpaca.markets/) | Distinctive product identity can coexist with readable financial information | Compact market context, clear action hierarchy and identifiable navigation | Brokerage actions, portfolio P/L, charts or Alpaca assets; no authenticated account UI was accessed |
| [osu! documented client interface](https://osu.ppy.sh/wiki/en/Client/Interface) | Selection, search/grouping and clear return paths can make a large collection inviting | Recognizable selected state and a satisfying list-to-detail relationship | Audio, pulsing, rhythm effects, competitive rewards or its artwork; this is a documented interface reference, not a claim about the latest lazer client |
| [Valve's Steam Library presentation](https://store.steampowered.com/libraryupdate/?l=english) | A compact home and dedicated detail destinations support returning to an item | Overview as a daily entry point; detail as a real destination; Saved as a quiet personal shelf | Storefront promotion, game cover art, feeds, social systems or custom collections requiring new persistence |

These are public reference observations and our design interpretation, not copied
layouts. No external artwork, logos, character illustrations or visual assets are
included in the proposal. The old Steam announcement is a documented pattern
reference, not an assertion about the current installed client.

## 5. Shared product and design principles

1. **A research app before a brand showcase.** First screen answers market direction,
   today's research focus, relevant themes and candidate stocks. No hero banner.
2. **Overview replaces the separate Daily Plan destination.** Keep the plan sentence
   and decision-path explanation on Overview. The next click enters research, not
   another summary page.
3. **Make the Theme → Member step real.** Dedicated Themes and Theme Detail surfaces
   show why stocks qualify or do not. Detail remains reachable without a mouse.
4. **Retain information through disclosure.** Main rows support comparison; detail
   exposes breadth validity, eligibility inputs/reasons, peer medians and earnings.
5. **Separate accent from financial meaning.** Navigation/selection uses lavender,
   ice blue or peach. Positive/negative data gets semantic color plus text/sign.
   A high Score is not automatically green or a long recommendation.
6. **Keep backend meaning intact.** Show returned Priority and qualification flags.
   Do not infer a new trading signal from rounded W, a score, or an animation.
7. **One visible view action.** Refresh is a stable global utility; the research
   surface's main action is its existing Primary export or Open detail. Related
   utilities stay secondary, not a row of competing bright buttons.
8. **Use the desktop canvas.** Target 1440, 1600 and 1920; keep a coherent column
   budget. Avoid a narrow centered marketing container and giant per-metric cards.
9. **Name bookmarks Saved.** This is manual browser-local state, not a portfolio,
   configured universe, eligibility list or new membership record.
10. **Comfort through finish.** Soft corners, good type, stable focus and precise
    feedback provide personality. No XP, streaks, urgency countdowns, confetti,
    flashing prices, loot-box language or trade gamification.

### Frozen field/interaction contract

The concepts are compatible with the current local HTML/CSS/JS stack. They are
not authorization to add fields or endpoints. Symbols/numbers shown in wireframes
are illustrative layout placeholders, not published research results.

| Information / action | Available today | Proposal treatment without changing the contract |
|---|---|---|
| Completed session, refresh progress, last success, completeness, provider and blockers | Status/snapshot metadata | Compact persistent session strip; diagnostics on demand |
| Pre-launch vs initialized/live state | `theme_layer` | Keep a compact explicit research-history label; pre-launch is not a failure or fictional-data state |
| Theme name/family/status, Score, median 1M/3M, trend, breadth/coverage, Priority, transitions | Theme snapshot | Expose useful existing data instead of leaving it hidden in the payload |
| Stock ticker, theme, Core/Enabler role, peer medians, ERs, W, eligibility inputs/reasons, qualification, assignment and other qualifications | Relationship snapshot | Use in Theme Detail and Candidates, including nonqualifying eligible members |
| Raw stock 1M/3M returns, company name, verified chart URL | **Not direct relationship fields** in this checkpoint | Reserve secondary detail positions; show “Not supplied” or omit only these unprovided values. Do not reconstruct returns, guess venues, scrape or add API fields in this phase |
| Numerical canonical theme rank | Not a separate vNext snapshot field | Use Score sort and a clearly labeled **list position (#)**, mark equal scores; do not invent a canonical ranking/tie formula |
| Full chart/index history vectors | Not in the dashboard contract | No invented sparkline or performance chart |
| Individual TXT | Existing individual **Primary** output where present | Label “Theme Primary TXT”; unavailable when the server has none. Do not promise a full configured-membership export |
| Combined TXT | Existing canonical Primary output | Label “Export all Primary”; search, grouping and visible-row selection never alter it |
| Saved | Existing browser-local ticker array | Keep its key/format and existing bookmarks; no notes, tags, timestamps, cloud sync or Saved export added |
| Related members / Watch-only concepts | Related is excluded from calculation rows; eight Watch-only themes are present | Keep Watch-only accessible separately; do not fabricate Related member rows that are not exposed |

Company-search and direct chart-link enhancements are recorded as data-contract
questions for a later explicitly authorized task. The chosen concept must still
work without them. Theme/member links, peer W, eligibility, available returns and
existing TXT/manual chart inspection form a complete core workflow now.

### Shared display rules

- Default Themes view shows **44 Active**; eight Watch-only concepts remain one
  explicit filter/tab away. Do not silently mix unavailable concepts into ranking.
- “Top” on Overview means relevant returned Primary themes/candidates, not always
  the highest Score. Short research may emphasize weaker themes; Neutral or
  Unclassified must not manufacture directional Primary results.
- Missing is `—` / Unavailable, never zero. Every 1M/3M/W label has clear units.
- View filters affect browsing only. Combined placement and individual output
  remain exactly as published; grouping does not change Assigned section.
- Show multi-theme membership as relationships. A stock's assigned export section
  is placement, never its permanent home theme. A unique-ticker view must label
  which relationship supplies its W (normally the already assigned section);
  it must not compute an overall multi-theme W.
- Remember search/filter/scroll on Back within the current session. A new snapshot
  must not restore old-session financial values or lose keyboard focus on polling.
- Status copy distinguishes completed US session from local refresh time. Do not
  call yesterday's completed bars “live,” or ordinary pre-launch research “stale.”

## 6. Concept one — Lunar Lounge

### A–B. Name and thesis

**Lunar Lounge** is a quiet research desk with a cool night palette, a soft
navigation rail and a restrained “selected orbit” motif. It feels personal and
slightly game-like while the data behaves like a precise research instrument.
The memorable element is the desk's selected navigation/row treatment, not a
wall of cards or decorative space art.

### C. Visual language

| Token / quality | Proposed treatment |
|---|---|
| Background | Night ink `#171923` |
| Main surfaces | Slate `#222533`; raised focus surface `#2B3040` |
| Text | Soft white `#F1F0F7`; secondary `#B9BDCF` |
| Navigation/action accent | Moon lavender `#B7A5FF`; dark text on filled accent buttons |
| Semantic colors | Shared green/red/amber system in section 9; not the navigation palette |
| Typography | Manrope candidate for interface and headings; 14px table text, 15px body, 24–28px page titles; tabular figures, no all-monospace table |
| Radii | 18px desk surfaces, 10px controls, 6px selected-row corners; hierarchy rather than one radius everywhere |
| Depth | Matte tonal layers, one soft shadow for a floating inspector/menu; no glass or glow |
| Icons | Consistent rounded outline geometry; small original broken-orbit brand mark; text labels remain visible |
| Density | 44–48px theme rows; compact toolbar; 6-theme/8-stock previews on Overview |
| Motion | Short eased responses, almost still at rest; no animated market numbers |

Typeface choice is provisional. A later implementation must verify local font
licensing, tabular figures and Windows rendering; no remote font dependency is
part of this proposal.

### D. Information architecture

```text
Persistent labeled rail (about 184px)
  Overview       Market + today's plan + bounded research previews
  Themes         All Active; family/search/priority/trend controls
    Theme Detail Same view at wide widths; full route when space is tight
  Candidates     Qualifying relationships or unique tickers
    Stock context / theme links
  Saved          Manual bookmarks only
  Methodology    Secondary position near rail footer
```

### E. Overview wireframe

```text
┌──────────────┬──────────────────────────────────────────────────────────┐
│ ThemeScope   │ Overview   Completed US session: Nov 5      [Refresh]     │
│              │ Pre-launch research • Official history starts Nov 6     │
│ ● Overview   ├──────────────────────────────────────────────────────────┤
│   Themes     │ Market: Long bias          [Why this direction]          │
│   Candidates │ SPY ↑ Bullish / breadth+  QQQ ↑ Bullish / breadth+        │
│   Saved      │ IWM ↑ Bullish • context only                             │
│              │ Focus: returned daily research-plan sentence             │
│              ├────────────────────────────┬─────────────────────────────┤
│              │ Relevant themes     [All] │ Primary candidates    [All]  │
│              │ Theme          Score Pri │ Stock  Theme    W     Saved  │
│              │ Semiconductors   82  Long │ TICK   Semi     +…    [Save] │
│              │ ... 6 compact rows       │ ... 8 compact rows           │
│              ├────────────────────────────┴─────────────────────────────┤
│ Methodology  │ Data complete • SIP • last success      [Export all     │
│ Appearance   │ Details on demand                        Primary]       │
└──────────────┴──────────────────────────────────────────────────────────┘
```

The diagram's Long example is illustrative. Market color/plan/qualifiers always
come from the snapshot. The pre-launch strip is quiet informational chrome, not
a full-width warning competing with the market result.

### F. Themes wireframe

```text
Themes                                      Active 44 | Watch-only 8
[Search themes] [Family: All] [Priority: All] [Trend: All]  [Reset filters]
Sort: Score high → low   Showing 44 Active   [Display / supporting columns]
┌────┬────────────────────────┬───────┬──────┬──────┬─────────┬──────────┬─────────┬───────────┐
│ #¹ │ Theme / family         │ Score │ 1M % │ 3M % │ Trend   │ >21/>50 │ Priority│ Comparison│
├────┼────────────────────────┼───────┼──────┼──────┼─────────┼──────────┼─────────┼───────────┤
│ 01 │ Semiconductors         │ 82.4  │ +…   │ +…   │ ↑ Bull. │ …% / …% │ Long    │ —         │
│    │ Technology & Digital   │       │      │      │         │          │         │           │
│ 02 │ Aerospace & Defense    │ 79.1  │ +…   │ +…   │ ↑ Bull. │ …% / …% │ Long    │ —         │
│ .. │ Remaining Active themes; return values are median member returns                         │
└────┴────────────────────────┴───────┴──────┴──────┴─────────┴──────────┴─────────┴───────────┘
Select theme → detail; keyboard link works independently of whole-row pointer target.
¹ # means list position, not a newly invented canonical rank. Equal scores are marked.
```

All decision metrics remain scannable. Comparison is present, but its unavailable
state is short in the row and fully explained on focus/detail. Family is secondary
to the actual theme name. The two breadth values share one labeled column group.

### G. Theme Detail wireframe

```text
[Back to Themes • restores search / position]     [Theme Primary TXT²]
Semiconductors                                  Technology & Digital
Score 82.4   Median 1M +…   Median 3M +…   Priority: Primary long
Pre-launch research trend: ↑ Bullish     >EMA21 …%   >EMA50 …%
Comparison unavailable • no compatible prior live session

Members (Core + Enabler)        [Ticker search] [Role] [Eligibility] [W sort]
┌────────┬─────────┬────────────┬──────────┬─────────────┬──────────┬──────┐
│ Ticker │ Role    │ 1M / 3M³  │ W peers% │ Eligibility │ Earnings │ Save │
├────────┼─────────┼────────────┼──────────┼─────────────┼──────────┼──────┤
│ TICK   │ Core    │ — / —     │ +…       │ Eligible    │ date / — │ [☆]  │
│ OTHER  │ Enabler │ — / —     │ −…       │ Ineligible ⓘ│ —        │ [☆]  │
└────────┴─────────┴────────────┴──────────┴─────────────┴──────────┴──────┘
Expand member: peer medians, ER1M/ER3M, eligibility inputs/reasons,
qualification, Assigned section and every Also qualifies in relationship.
² Enabled only for an existing published individual Primary export.
³ Desired supporting slots; direct stock returns are not supplied by current API.
```

At 1920px, an optional ~400px inspector can sit beside a table retaining at least
its usable column budget. At 1440/1600px, open a full Theme Detail route instead
of squeezing both panes or silently hiding metrics. An Expand detail action is
always available; no tiny nested table inside an undersized drawer.

### H. Candidates wireframe

```text
Candidates          [Search tickers / themes] [Theme] [Role] [W sort]
View: [Relationships] [Unique tickers]             [Export all Primary]
187 qualifying relationships / U unique tickers  ← counts are session data

Semiconductors • Priority: Primary long                  [Theme Primary TXT]
  TICK   Core     W +…%   Eligible   Earnings —    [Save] [Open theme]
  NEXT   Enabler  W +…%   Eligible   Earnings date [Save] [Open theme]
  [Other qualifications]  Assigned: Semiconductors; Also qualifies in: ...
Next Primary theme ...
```

Default grouping supports the Theme → Stock sequence. Unique-ticker mode reduces
visual repetition while exposing all qualifying relationships in disclosure.
Neither mode changes the combined export or the independently qualifying lists.

### I. Saved

A quiet full-page list of ticker bookmarks with current relationship context,
current qualification or “No current Primary qualification,” and Remove. No
invented saved date, notes, tags or automatic removal. The empty state uses a
small outlined orbit plus “Save a stock from Themes or Candidates.” Existing
browser bookmarks survive the visible naming change.

### J. Responsive philosophy

At 1440 use the full research table; at 1600 expand the name/metadata breathing
room; at 1920 optionally show the inspector. A useful table budget is roughly
1140px including padding: position 40, theme 258, Score 82, returns 156, trend
126, paired breadth 128, Priority 142 and comparison 110. Exact widths are design
hypotheses, not implementation constants.

When that budget no longer fits, switch to a readable list, not a shrunken table:
name/Score/Priority first line, 1M/3M/trend second, breadth/comparison in a labeled
expandable section. Mobile Theme Detail is a route with metric pairs and member
rows; four main destinations use a compact nav, Methodology sits in More. Touch
controls are at least 44px; no inspector overlay competes with the keyboard.

### K. Six interaction examples

| Action | Feedback / motion | Keyboard and reduced-motion behavior |
|---|---|---|
| Choose navigation | One lavender selected shape settles in 140ms | Same visible state on focus; immediate change when motion reduced |
| Hover/select theme | Tonal row change, no row movement; selected marker persists | Enter opens its link; selection is text/shape, not color alone |
| Open detail | 180ms short opacity/position transition for the inspector | Full-route heading receives focus; Back/Close restores originating row |
| Refresh | Stage text updates in a reserved strip; prior committed data remains | No fake percent complete or endless pulse; announce changed stages only |
| Save | Bookmark fills once, label becomes Saved, small confirmation | `aria-pressed` state; Undo uses the existing remove action; no confetti |
| Change filters | Results update without animated row reordering; count announced | Focus stays on the control; clear-filter action is easy to reach |

### L. Risks

It could become another soft SaaS kit if every metric gets a rounded card. Keep
one desk surface with dense rows. Lavender could feel generic if the brand rests
on color alone; the stable desk/selection behavior must carry identity. The wide
inspector adds state complexity, so full-route detail is the reliable fallback.

## 7. Concept two — Signal Atlas

### A–B. Name and thesis

**Signal Atlas** treats the research universe like an organized field guide.
Horizontal application navigation and a broad, aligned data canvas put comparison
first. Its cool observatory character comes from structured typography and a small
original compass-like locator, not a terminal, graph wallpaper or a banking grid.
It is the most restrained and information-dense option.

### C. Visual language

| Token / quality | Proposed treatment |
|---|---|
| Background | Blue charcoal `#151C25` |
| Surfaces | Instrument slate `#1D2936`; raised `#283747` |
| Text | Mist white `#EDF3F8`; secondary `#B3C2CF` |
| Navigation/action accent | Ice blue `#8DCEFA` |
| Semantic colors | Shared direction colors; high/low Score itself remains neutral |
| Typography | IBM Plex Sans candidate; 13.5–14px research rows, 15px body, 24px headings; tabular numerals, no mono controls |
| Radii | 14–16px primary work surfaces; 10px search/filter controls |
| Depth | Mostly tonal separation and selective fine rules; menus get restrained elevation |
| Icons | Fine rounded locator/bracket symbols with labels; no chart icon for every theme |
| Density | 38–40px table rows; a single stable toolbar; broad full-page detail |
| Motion | Nearly still, crisp 100–160ms state changes; no animated data rearrangement |

### D. Information architecture

```text
Top bar: ThemeScope | Overview | Themes | Candidates | Saved | More
More: Methodology, Appearance, operational detail
Themes → full Theme Detail route → full member context disclosure
Candidates → theme-group or ticker-group browsing → Theme Detail
Back restores query, sort, family expansion and scroll.
```

Unlike Lunar Lounge, this concept does not reserve a permanent navigation rail
or split the main comparison table with an inspector.

### E. Overview wireframe

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ ThemeScope   Overview   Themes   Candidates   Saved          More   Refresh  │
├──────────────────────────────────────────────────────────────────────────────┤
│ Completed US session Nov 5       Pre-launch research       Data complete ⓘ  │
│ Market: Long bias   [Decision path]     SPY ↑ / QQQ ↑ / IWM context ↑         │
│ Today's focus: returned research-plan sentence                               │
├─────────────────────────────────────┬────────────────────────────────────────┤
│ Primary themes                      │ Stocks for chart inspection            │
│ # Theme             Score  Priority │ Ticker  Theme    W%   Earnings   Save   │
│ 1 ...               ...    Long     │ ...     ...      +…   —          ☆      │
│ ... compact 8-row research index    │ ... compact 8-row candidate preview    │
├─────────────────────────────────────┴────────────────────────────────────────┤
│ [Browse all 44 Active themes]                       [Export all Primary]     │
└──────────────────────────────────────────────────────────────────────────────┘
```

Market/plan occupies a compact shared band. No large cards are needed to repeat
SPY/QQQ status. Decision path stays directly accessible rather than disappearing.

### F. Themes wireframe

```text
Themes          [Search themes] [Family] [Priority] [Trend] [Reset]
[Global list] [Family groups]     Active 44 | Watch-only 8     Sort: Score ↓
┌────┬──────────────────────┬───────┬──────┬──────┬──────────┬──────┬──────┬─────────┬────────┐
│ #¹ │ Theme                │ Score │ 1M%  │ 3M%  │ Trend    │ >21% │ >50% │ Priority│ Compare│
├────┼──────────────────────┼───────┼──────┼──────┼──────────┼──────┼──────┼─────────┼────────┤
│ 01 │ Semiconductors       │ 82.4  │ +…   │ +…   │ ↑ Bullish│ …    │ …    │ Long    │ —      │
│ 02 │ ...                  │ ...   │ ...  │ ...  │ ...      │ ...  │ ...  │ ...     │ ...    │
└────┴──────────────────────┴───────┴──────┴──────┴──────────┴──────┴──────┴─────────┴────────┘
Family mode: expandable labeled family sections; count and every field retained.
Global positions remain identifiable; changing grouping does not imply a new rank.
```

Family mode is optional; default global Score ordering supports cross-family
comparison. One header sort affordance replaces duplicated sort controls and
repeated info icons. Column explanations sit in a concise keyboard-accessible
legend. Use normal table semantics, not a custom spreadsheet keyboard model.

### G. Theme Detail wireframe

```text
Themes / Semiconductors                         [Back to results] [Theme Primary TXT]
Semiconductors                                       Technology & Digital
Score 82.4 | median 1M +… | median 3M +… | ↑ research trend | Primary long
Breadth: >21 …% / >50 …%   [Validity/coverage]   Comparison unavailable

[Members]   Search ticker    Role: All    Eligibility: All    Sort: W ↓
Ticker | Role | 1M³ | 3M³ | W peers% | Eligible? | Earnings | Qualification | Save
TICK   | Core | —   | —   | +…       | Yes       | —        | Primary long  | ☆
OTHER  | ...  | ... | ... | ...      | No ⓘ      | ...      | Not qualified | ☆
Expanded member: peer return medians, excess returns, raw eligibility facts,
Assigned section and all independently qualifying themes.
```

This is an explicit full destination, never a popup. Secondary facts expand inline
in the member row without removing the row's ticker, W or eligibility. Stock-return
slots follow the shared contract limitation; no frontend reconstruction.

### H. Candidates wireframe

```text
Candidates     [Ticker/theme search] [Theme] [Role] [Sort W]    [Export all Primary]
[Group by Theme] [Group by Ticker]     Qualifying relationships R • Unique U
┌────────────────────────────────────────────────────────────────────────────┐
│ Semiconductors • Primary long                    [Theme Primary TXT]       │
│ TICK | Core | W +… | Eligible | earnings — | Assigned: Semi | [Save]         │
│      [Show other qualifying relationships: 2]                               │
│ NEXT | ...                                                               │
├────────────────────────────────────────────────────────────────────────────┤
│ Next theme ...                                                           │
└────────────────────────────────────────────────────────────────────────────┘
```

Ticker grouping is a comparison aid, not a new combined-output placement rule.
There is no select-checkbox promise of a filtered export the current API cannot
produce. Existing published exports remain all-current-Primary outputs.

### I. Saved

A plain research index with ticker, current theme relationships, W where available,
current qualification and Remove. “No current Primary qualification” remains a
valid saved state, not a deletion condition. Search operates on available tickers
and theme names. Empty Saved provides direct links to Themes and Candidates.

### J. Responsive philosophy

At 1440 the top navigation leaves almost the full width for the table. At 1600
use the surplus for theme names/return columns; at 1920 maintain aligned readable
column widths rather than spreading a few values to screen corners. Table rows
can show about 18–20 themes in a 1000px-high viewport, depending on text growth.

Below the table's content budget, render a compact definition-list row: identity,
Score and Priority, then return/trend facts, then breadth/comparison disclosure.
On mobile, top navigation becomes a labeled compact menu, filters a single sheet,
and Theme Detail remains a route. The desktop table is not kept at 1422px and
pushed off the phone. Filter controls return focus to their opening button.

### K. Six interaction examples

| Action | Feedback / motion | Keyboard and reduced-motion behavior |
|---|---|---|
| Switch top destination | Underline/shape changes in 120ms; view content appears without a slide show | Current page announced; immediate under reduced motion |
| Sort a column | Direction icon and row count update; no rows fly between positions | Real header button and `aria-sort`; retain button focus |
| Expand a family | Section reveals without squeezing unrelated groups | Disclosure button exposes expanded state and count |
| Open member detail | Facts reveal directly below the originating row | Escape/Collapse returns to that row; no nested focus trap |
| Refresh completes | Session strip updates after committed publication; one brief confirmation | Do not replace focused controls or announce every poll |
| Save or remove | Icon and text change once; undoable confirmation | Same action available by keyboard; no motion needed to understand it |

### L. Risks

This can regress into an internal research/admin tool. Protect readable sans-serif
text, a calm content hierarchy and comfortable controls; do not add every old
column back. Its personality is quieter than the user's game references, and the
family/global presentation needs clear state labels to avoid confusing ordering.

## 8. Concept three — Comet Club

### A–B. Name and thesis

**Comet Club** is a personal research launcher with warm plum surfaces, a peach
accent and a small comet-shaped selection mark. It emphasizes choosing something
to investigate, then opening a focused research destination. Its theme collection
and candidate review arrangement differ materially from both table-first options.
The game influence belongs to navigation and feedback, never to rewards for risk.

### C. Visual language

| Token / quality | Proposed treatment |
|---|---|
| Background | Velvet charcoal `#211C29` |
| Surfaces | Plum slate `#2B2534`; raised `#393142` |
| Text | Pearl `#F7EFF7`; secondary `#D1BDCD` |
| Navigation/action accent | Soft peach `#F4B99B`; distinct from semantic red and amber |
| Semantic colors | Shared positive/negative/mixed text system with explicit labels |
| Typography | DM Sans body candidate; Outfit only for short page/brand headings; 14px data with tabular figures, no oversized display headlines |
| Radii | 20px outer panels, 12px controls, 10–12px collection rows |
| Depth | Gentle matte overlap at navigation/popovers; no translucent glass, no ambient gradient |
| Icons | Small rounded solid/outline family; one comet mark can later accommodate an optional mascot identity |
| Density | Compact two-lane theme units rather than hero cards; 44–48px candidate queue rows |
| Motion | Tactile one-shot feedback; slightly more expressive detail changes, still short and interruptible |

### D. Information architecture

```text
Rounded top dock: Overview | Themes | Candidates | Saved
Secondary: Methodology / Appearance / data detail
Themes → focused full-page Theme Detail → member context
Candidates → ticker review list + qualification inspector
Saved → personal research shelf (same ticker bookmark storage)
```

No permanent side navigation and no mandatory Theme-table inspector. The distinctive
structure is a collection-like Themes surface and a ticker-first Candidates review
layout. Manual review is not an additional trade/qualification state.

### E. Overview wireframe

```text
┌────────────────────────────────────────────────────────────────────────────┐
│ ThemeScope     ( Overview  Themes  Candidates  Saved )   More    Refresh    │
│ Completed US session Nov 5 • Pre-launch research • Details                 │
├────────────────────────────────────────────────────────────────────────────┤
│ Market: Long bias                         [Decision path]                  │
│ SPY ↑ Bullish / breadth+   QQQ ↑ Bullish / breadth+   IWM: context ↑         │
│ Today's research focus: returned plan sentence                              │
├──────────────────────────────────────────┬─────────────────────────────────┤
│ Relevant themes (compact collection)      │ Stocks to inspect               │
│ 01 Semiconductors   82.4    Primary long  │ TICK  W +…   theme ...  [Save]   │
│ 02 Aerospace       79.1    Primary long  │ NEXT  W +…   theme ...  [Save]   │
│ ... four to six complete summaries       │ ... six to eight rows           │
├──────────────────────────────────────────┴─────────────────────────────────┤
│ Saved: compact current-context preview  [Open Saved]   [Export all Primary] │
└────────────────────────────────────────────────────────────────────────────┘
```

Saved is a preview, not a second endless list. The market decision and research
results remain above it. No price chart, mascot hero, achievements or news feed.

### F. Themes wireframe

```text
Themes     [Search] [Family] [Priority] [Trend]     Active 44 | Watch-only 8
Score high → low • # is list position • select a theme to open research
┌───────────────────────────────────┬───────────────────────────────────────┐
│ 01 Semiconductors   Score 82.4     │ 02 Aerospace ...        Score 79.1    │
│ Technology & Digital              │ Industrials & Mobility                │
│ 1M +…  3M +…   ↑ Bullish          │ 1M +…  3M +…   ↑ Bullish              │
│ >21 …% / >50 …%   Primary long    │ >21 …% / >50 …%   Primary long        │
│ Comparison unavailable  [Open]    │ Comparison unavailable       [Open]    │
├───────────────────────────────────┼───────────────────────────────────────┤
│ 03 ... complete unit              │ 04 ... complete unit                  │
│ ...                               │ ...                                   │
└───────────────────────────────────┴───────────────────────────────────────┘
```

These are tightly stacked, complete research units, not giant cards. Read in
row-major order: 1/2, then 3/4. No metric is revealed only on hover. At 1440 two
lanes are allowed only if both retain their complete readable content; otherwise
collapse to one. All 44 remain accessible through one coherent collection.

### G. Theme Detail wireframe

```text
[Back to Themes]                       Semiconductors           [Theme Primary TXT]
Technology & Digital     Score 82.4     Primary long
Median 1M +… / 3M +…   ↑ Pre-launch research trend   >21 …% / >50 …%
Comparison unavailable

Members                        [Ticker] [Role] [Eligibility] [W sort]
Ticker | Core/Enabler | W peers% | Qualification | Earnings | Save | Expand
TICK   | Core        | +…       | Primary long  | —        | ☆    | >
Expanded facts: 1M³/3M³, peer medians/ERs, daily eligibility inputs and reasons,
Assigned section and every Also qualifies in theme.

[Previous theme]                     [Back to results]               [Next theme]
```

The focused page has ordinary navigation, not a swiping trading carousel. Previous/
Next follows the user's current visible theme ordering. Those controls are never
required to access a theme, and do not change the ranking, qualification or exports.
Supporting stock-return slots remain subject to the shared data-contract limit.

### H. Candidates wireframe

```text
Candidates [Search tickers/themes] [Role] [Theme] [Assigned W sort] [Export all Primary]
┌────────────────────────────────┬───────────────────────────────────────────┐
│ Tickers with qualifications    │ TICK • current research context           │
│ > TICK  Semi W +…  2 themes      │ Theme             Role    W%    Qualified │
│   NEXT  Semi W +…  1 theme       │ Semiconductors    Core    +…    Yes       │
│   OTHER Gold W +…  3 themes      │ Robotics          Enabler +…    Yes       │
│ ... compact sorted review list│ Assigned section: Semiconductors          │
│                                │ Also qualifies in: Robotics               │
│                                │ Eligibility facts • earnings date / —     │
│                                │ [Save stock] [Open theme]                 │
│                                │ [Theme Primary TXT, when available]       │
└────────────────────────────────┴───────────────────────────────────────────┘
```

The queue groups existing qualifying relationships by ticker. Its displayed/sorted
W belongs to the named already-assigned relationship, not an aggregate. It does not add a
persisted “reviewed” state, calculate an overall multi-theme W, or choose a home
theme. If a summary W is displayed, it must name its associated relationship;
otherwise show “2 qualifying themes” rather than invent an aggregate score.

### I. Saved

A compact personal shelf of saved **stocks**, with current qualifying-context
rows and a separate “Other saved stocks” section where applicable. All original
tickers remain until manually removed. No saved themes, custom collections, notes,
review-progress tracking or cross-device persistence is assumed. A small static
comet icon softens the empty state; its instruction is simply “Save a stock while
you research.”

### J. Responsive philosophy

The two-lane theme collection gives 1600/1920px a distinct launcher feel, with
complete units around 96–112px tall depending on wrapping. It is less efficient
for strict cross-row numeric comparison than Atlas, but puts each theme's context
together. A single lane replaces it when text needs more room; order never changes.

Candidates' two panes become list → full ticker context on mobile. Theme Detail
uses a vertical facts layout and expandable member rows. The dock becomes a simple
labeled compact navigation bar; no horizontal gesture is necessary. Keep lower
navigation clear of mobile safe areas and the on-screen keyboard.

### K. Seven interaction examples

| Action | Feedback / motion | Keyboard and reduced-motion behavior |
|---|---|---|
| Pick dock destination | Small comet-shaped selected marker moves once in 160ms | Text/current-page state always identifies destination; no travel under reduced motion |
| Select a theme unit | Tonal border/selection change, no card tilt or scale | Open link remains explicit; Enter does not trigger financial actions |
| Enter Theme Detail | Short 200ms transition, background stays still | Focus moves to the new heading; Back restores the selected unit |
| Select candidate ticker | Adjacent context changes in 120ms without disturbing list scroll | Ordinary links/buttons; no mandatory drag, swipe or global arrow-key interception |
| Save | One small icon state change and clear Saved feedback | Existing ticker array only; no reward sound/particle effect |
| Refresh | Static progress text/stage indicator; committed results stay usable | One completion announcement; no celebratory animation or invented ETA |
| Empty filter result | Clear query summary and Reset filters, small static symbol | Reset is reachable immediately; no animated “sad” illustration or layout jump |

### L. Risks

This is the easiest concept to make too cute. Avoid game covers, wallpaper, XP,
collection-management scope and an ambiguous portfolio feel. Two-lane comparison
and the candidate inspector increase cognitive/state complexity. Peach must remain
an action/navigation color, never an alternative bearish signal. If review finds
comparison slower or the personality distracting, prefer Lunar Lounge rather than
adding a separate table mode and doubling the interface's maintenance burden.

## 9. Accessibility pass after the concepts

The following is a **design-stage pass**, not a claim that unbuilt concepts are
WCAG compliant. Contrast values below were calculated using WCAG relative
luminance; all reported pairs use opaque colors, with no glass/gradient ambiguity.

Shared proposed semantic text: positive `#8DDBB9`, negative `#FFADB6`, mixed/watch
`#F1CF96`. Unavailable uses each concept's secondary text, with an explicit label.
Bullish/Bearish, Long/Short, eligibility and qualification always have words or
symbols plus words. A saved icon has a state label. Score is not a confidence bar.

| Concept | Text / raised | Secondary / raised | Accent / raised | Dark button text / accent | Lowest shared semantic text / raised |
|---|---:|---:|---:|---:|---:|
| Lunar Lounge | 11.60:1 | 7.03:1 | 6.15:1 | 8.20:1 | 7.44:1 |
| Signal Atlas | 10.87:1 | 6.68:1 | 7.14:1 | 10.08:1 | 6.89:1 |
| Comet Club | 11.02:1 | 7.02:1 | 7.25:1 | 9.71:1 | 7.04:1 |

These pairs exceed the [normal-text 4.5:1 contrast minimum](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html).
Every additional hover/disabled/error/light-mode pair still requires later testing.
A decorative panel edge may be subtle; necessary control boundaries and focus
indicators should meet at least 3:1 against adjacent colors and remain visible
independently of that decoration.

| Check | Lunar Lounge | Signal Atlas | Comet Club |
|---|---|---|---|
| Keyboard path | Rail → filters → native table links → detail; close restores row | Top nav → filters → sortable headers → full detail → Back | Dock → row-major units / ticker list → full context → Back |
| Main risk | Wide inspector focus/order and premature breakpoint squeeze | Dense controls/headers becoming undersized | Grid reading order, candidate-pane focus and overexpressive feedback |
| Mitigation | Full-route fallback; no nested focus trap; minimum usable table budget | 32px-or-larger desktop button targets, no overlapping header tools | DOM order equals visual order; no gesture-only action, no hover-only metric |
| Screen-reader structure | Native tables and named detail heading | Native tables with caption, header associations, `aria-sort` | Labeled list/definition groups for theme units; qualification table inside detail |
| Reduced motion | Immediate route/state changes; retain focus and confirmation | No animated reordering or scanning effects | Remove marker travel and page motion; preserve static selected state |
| Zoom/long text | Detail stacks before columns are squeezed | Toolbar wraps; noncritical actions disclose; data remain reachable | Units grow vertically; collapse to one lane; no fixed-height clipping |

Common requirements for the later implementation:

- Aim for 44px touch targets and comfortable 32–40px desktop control hit areas;
  never fall below the [24px target minimum](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html)
  without a valid spacing/equivalent-control exception. Dense visual icons are
  allowed only with adequate distinct hit areas.
- A visible focus outline survives every state. Focused controls are not replaced
  on unchanged polling updates, hidden under sticky chrome or scrolled out of context.
- Refresh progress is announced on meaningful stage changes, not every 1.5-second
  poll. Failure keeps the prior committed session visibly identified. First-use
  emptiness, no qualifiers, blocked activation and network failure are different states.
- “Comparison unavailable” is truthful for pre-launch/initialization/incompatible
  history; do not recast it as a bearish transition or broken Theme Score.
- No continuous animation. No table-number counting, auto-scrolling, pulsing
  cards, parallax, flashing arrows, skeleton shimmer or sound. Reduced motion
  removes spatial transitions; the same information remains immediately available.
- Use logical reading order/spacing and safe-area-aware actions. Check 320/390px,
  200% real browser zoom, long names and pseudolocalized strings, RTL mirroring,
  keyboard-only usage, high-contrast/forced-colors and screen readers after selection.
  These concept-runtime checks are **not yet verified**, because no concept is built.

## 10. Comparison

Qualitative design judgments, not measured usability scores. “Complexity” and
“risk” describe the relative burden; higher is not better for those rows.

| Criterion | Lunar Lounge | Signal Atlas | Comet Club |
|---|---|---|---|
| Aesthetic appeal for this brief | High: cozy, calm, modern | Medium–high: precise, composed | High: expressive, warmer, playful |
| Distinct ThemeScope identity | High: research desk / orbit selection | Medium–high: observatory / locator | High: personal research launcher |
| Information density | High, balanced | Highest | Medium–high; complete units take more room |
| Scanability | High across overview and table | Highest for numeric comparison | High within a unit; moderate across two lanes |
| Research workflow | Strongest overall Theme → Stock continuity | Very strong, clear full-page transitions | Strong ticker review; more context switching |
| Game/cozy personality | Subtle and controlled | Lightest of the three | Strongest; needs firm restraint |
| Implementation complexity | Medium: wide inspector plus full-route fallback | Low–medium: routes and native tables | Highest: collection layout plus ticker inspector |
| Accessibility risk | Moderate, manageable focus/pane concerns | Lowest if density targets are respected | Highest; reading order and animated identity need care |
| Long-term maintainability | High with one shared detail model | Highest; fewest layout modes | Moderate; avoid adding parallel table/deck modes |

## 11. Recommendation and self-critique

Choose **Lunar Lounge** as the direction to review next. It meets the user's cozy,
rounded, slightly game-like preference without turning ThemeScope into a game or
obscuring numeric research. The full Themes/Theme Detail/Candidates structure
recovers the useful legacy behaviors while avoiding its overload. A restrained
night palette, legible labels and bounded Overview are a more meaningful identity
change than replacing green with purple.

The recommendation is **not** a blend of all three. Keep Lounge's desk/navigation
and detail behavior; use the shared contract, state and accessibility requirements,
not Atlas's entire horizontal application or Club's two-lane collection. If the
user's priority proves to be maximum comparison speed, select Signal Atlas instead.
If personality is the dominant priority, Comet Club is a deliberate alternative,
with its additional density/accessibility tradeoffs made explicit.

Self-critique against the brief:

- A first pass could have become lavender cards. The proposed overview now uses
  one market band and bounded aligned research lists, not one card per metric.
- A dense alternative could have recreated the old terminal. Atlas keeps sans-serif
  controls, fewer default columns and a distinct full-detail destination.
- A launcher alternative could have depended on art or new collections. Club uses
  original small geometry, no character hero, and the unchanged Saved ticker model.
- The three concepts change layout, entry structure and detail behavior, not just
  palette. Each retains returns, breadth, priority, qualification and relationships.
- Missing data-contract fields remain explicitly missing. None of the concepts
  requires invented stock returns, chart data, export types or bookmark metadata.

For user review, compare the three **structures and personalities** first. After
selection, a separate authorized implementation plan can define the component/
state map and validate font/layout details against 1440/1600/1920 and mobile.
That next phase is not started here.

## 12. Completion boundary and provenance

Deliverables are this proposal, five existing-UI audit screenshots and the small
measurement JSON. No runnable concept frontend, product patch, dependency change,
new API, persistence change, export change or configuration edit was made.
Existing production source remains frozen at `ed12ba4`; no commit, push, merge,
deployment or inspection checkpoint move occurred. No live provider credentials
were used, and no runtime database or raw market-data payload is in this folder.

CLI content hashes identify the exact selected guidance read on the audit date:

| Skill | SHA256 of retrieved CLI markdown |
|---|---|
| anthropics/frontend-design | `d91970639e9f5c37682ac7ab60094d35f1c7c1f38d731bd56396563aee10c1d3` |
| jakubkrehel/better-layout | `4e7fd6880f41a87a21bb3be8e0b2bd7e7b8c561af5fb706ec0bb3e58877d60ec` |
| wshobson/interaction-design | `87f2765ed1deeef3f1c06f9e4338ff103c391c6c4adcdffc885f3516b7c34ff2` |

Registry provenance: [UI Skills repository](https://github.com/ibelick/ui-skills)
and [current registry manifest](https://www.ui-skills.com/skills/registry.json).
Only brief paraphrases are used; third-party skill bodies and reference assets
are not redistributed with this proposal.
