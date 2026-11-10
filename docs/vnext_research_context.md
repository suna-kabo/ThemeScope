# Completed-session research context

User-approved research expansion, 10 November 2026. Implementation remains on
`refactor/themescope-vnext`. Gate E is **open**: manufactured browser/numerical
fixtures do not supply live validation evidence. User reports Nov 6 and Nov 9 PASS;
Nov 10 adjacent-live validation remains PENDING.
No deployment, main merge, membership amendment or financial-core rewrite.

## Additive contract and price inputs

`src/themescope/research/context.py` attaches `research`, schema
`themescope-research-1`, after the existing market, theme, Directional and export
calculations. Its policy is versioned separately in
`config/vnext/research_context.json`; snapshot fields record policy version/hash.
All original financial fields, original methodology/series IDs and exports remain
identical. Older snapshots without this contract display unavailable context;
the browser never derives business rules from the visible table.

New fields:

- `extension`: aggregate state, SPY/QQQ ATR20, signed distance, side/magnitude,
  period and history start. IWM is deliberately absent.
- `focus`: label and initial preferred Candidate lens.
- `ema_transitions`: SPY/QQQ/IWM, separately EMA21/EMA50: current/previous relation,
  changed (nullable), explicit dated message and previous session.
- `ranks`: competition method, entire Active universe, valid-scored count and
  per-theme rank, prior rank, nullable change, reason and comparison date.
- `countertrend`: side/availability, ordered relationship pointers and stock-view
  representatives for each sign bucket, stock/relationship counts and ordering note.
- `companies`: supplied approved configuration company names only; no new provider.

Alpaca already returns adjusted daily high/low; these are retained as optional
`Bar.adjusted_high/adjusted_low`. ATR uses the same split/spin-off-adjusted price
units for high, low, close and previous close. Raw close/volume remain the unchanged
liquidity and terminal-action inputs. No requests, feed, provider identity, symbol
mapping, terminal-action handling or trading endpoint were added.

Old close-only cached observations deserialize unchanged. A first refresh fills
missing high/low history **for SPY/QQQ only**; normal refresh remains the existing
missing-session + bounded repair window + adjustment-anchor scheme. Adding optional
fields alone is not treated as an adjustment revision of the whole universe.
Invalid/missing high/low makes Extension unavailable; no close-range fallback or
fabricated OHLCV. Old observations and their run references remain immutable.
Absent high/low keys are omitted when serializing old Bars, retaining their original
canonical bytes and observation IDs. JSON payloads already support optional fields:
SQLite remains schema v2, with no DDL migration or historical rewrite.

## Exact Extension rule

For each benchmark: `(completed adjusted close − EMA21) / Wilder ATR20`.
Each True Range is `max(H−L, |H−previous C|, |L−previous C|)`.
The first ATR is the arithmetic mean of 20 True Ranges, requiring 21 closes;
subsequent ATR = `(19 × previous ATR + current TR) / 20`. The supplied history
begins at the service's deterministic completed-session lookback (recorded in the
snapshot). Missing/interrupted history, invalid high/low, or zero ATR is unavailable.
A legacy scanner's imported ATR14 column is not a versioned vNext ATR convention.
Decimal precision/rounding use the same deterministic 34-digit context as vNext.

Per-index absolute distance: `<1` Normal; `[1,1.5)` Stretched; `>=1.5` Extended.
Positive/negative supplies Upside/Downside. Exact threshold comparisons precede
formatting; a rounded visual distance never determines the state.

| SPY / QQQ relationship | Aggregate |
| --- | --- |
| Either unavailable | Unavailable |
| Both Extended, same side | That side Extended |
| Stretched + Stretched, same side | That side Stretched |
| Stretched + Extended, same side (either order) | That side Stretched |
| Normal involved, or opposing sides | Normal |

This explicitly resolves the brief's “at least directionally stretched enough”
wording conservatively: both must reach 1 ATR on the same side. No hidden 0.99
support threshold. EMA50, breadth, IWM, VIX and theme metrics are excluded.

Short Bias: Directional normally; Downside Stretched adds Countertrend Watch;
Downside Extended highlights/defaults Countertrend. Long Bias mirrors with Upside
and Pullback-Risk Watch/Highlighted. Opposite-side extension does not change focus.
Non-directional Bias remains Observe. Extension never modifies Matrix output,
qualification or underlying candidate universes. Manual lens selection survives
polling; initial preferred mode is applied once per page load.

## Canonical ranks and history

Rank every valid score from 0 through 100 in the complete Active universe, descending.
Competition ties are `1,2,2,4`: rank = 1 + count of strictly higher scores.
Theme ID is stable display order only, with no economic advantage among ties.
Search, filters, sorting and Untracked view do not recalculate ranks.

Rank Change = previous rank − current rank, compared with the adjacent completed
session from one successful stored run. Missing score, newly active theme, newly
available score, changed Active/scored universe, incompatible per-theme series or
missing compatible prior history yields no change, with a supplied reason. The
history query reads all themes and market from one run, never mixing per-theme
revisions. It is read-only. EMA transitions use the same completed-session guard.

Launch initializes exactly 100 on Nov 6, with no earned return. Nov 9 cannot use
launch initialization or indicator-only history as an earned comparison. Nov 10 is
the first possible adjacent-live comparison, conditional on successful compatible
data. Above/Below/At changes show explicit dated text; unchanged or missing states
produce no invented crossing. Equality is described as reaching the EMA.

## Countertrend: an independent lens

Use only supplied Active Core/Enabler relationships with available, passing existing
liquidity eligibility and finite nonzero W. Earnings never enter eligibility.
No Newly-bullish/bearish exception is added to Countertrend.

| Bias | Theme filter | Positive W | Negative W |
| --- | --- | --- | --- |
| Short | Score <50; Bearish or Mixed | Resilient: strength within weakness | Snapback: potential rebound from weakness |
| Long | Score >=50; Bullish or Mixed | Strong Leaders / Pullback Watch | Relative Weakness |
| Non-directional | None inferred | Unavailable | Unavailable |

Positive buckets order W descending, score descending, ticker alphabetical;
negative buckets order W ascending, score ascending, ticker alphabetical. Theme ID
is the final stable display tie-breaker. No Countertrend score or extra threshold.
These rows remain inspectable in Normal conditions. Long-side Pullback Watch is a
market-extension warning against chasing; **W does not predict a pullback**.
Neither bucket confirms reversal, entry or best trade. Chart work remains manual.

Stocks view selects the first relationship per ticker in each bucket's supplied
W order. A ticker may appear in both buckets through different themes. Global
stock counts deduplicate across both; relationship counts remain separate.
Grouped by theme retains every relationship, ordered within theme using that same
supplied order. Group order follows first appearance in bucket order. Without a Theme filter, Stocks view retains its representative relationship. With
a Theme filter, the displayed Theme/Role/W and initial ticker inspection use that
selected relationship. Countertrend never changes Directional TXT files.

## Presentation and navigation

Candidates contains Directional/Countertrend; stored `Primary` enum values/routes
and export filenames stay compatible. Strength Score/Rank are distinct from
Research Priority. W is percentage points versus named theme peers; stock research
uses no invented returns. Core/Enabler labels explain business roles. Earnings
remain optional and the prior global-unavailable presentation stays intact.
Overview separates Bias, Extension and Focus, keeps bias guidance visible, and
labels preview ordering. IWM remains small-cap context, never breadth or decisions.
Untracked Concepts omit empty Active metrics/controls and reset irrelevant filters.
Saved retains `themescope-vnext-watchlist` exactly, with browser-only wording and
explicit theme context for W. Public mode says Market data fixed and remains secure,
interactive static content with no API/credential/database exposure.

Nested inspectors push history entries. Back returns to the previous sheet with
search/filter/sort, sheet scroll and trigger focus restored. Escape/Close dismiss the
owned sheet chain to the research page. Direct deep links close in place. Polling
retains the current sheet and state; one native dialog remains open. Context/price
input and financial calculation changes are not performed by browser code.

## Validation

See `tests/test_vnext_research_context.py` for independent ATR/threshold, tie/history,
Countertrend, old cache serialization and static allowlist regressions.
`tests/smoke_research_context_ui.py` exercises new context, bucket order/counts,
Directionals exports, stable ranks, nested/direct navigation, Untracked states and
1440/1024/768/480/320px at 100/200% text in both densities, with high contrast,
reduced motion and axe. The existing five browser suites remain in place with
updated terminology and nine-column geometry expectations. Screenshots and reports
are external review artifacts; no new binary assets or real market inputs are
committed. Linux Chromium results do not claim native Windows/live SIP validation.


Final acceptance: 377 full Python tests (375 passed, two existing Windows skips),
150 focused vNext tests (149 passed, one skip), including 19 new research tests.
All six browser programs pass; 57 axe audits report zero WCAG violations. Twenty
viewport/text/density combinations pass, including both inspector sheets and both
Candidate lenses. At 1440p, 31 Theme and 25 Directional rows remain visible. Both
static modes make zero API/external requests. Configuration/evidence validation,
compilation, JavaScript syntax/helpers and diff checks pass. No new runtime package.
Automated Chromium/axe does not substitute for native Windows or manual screen-reader
review. The user reports Nov 9 PASS; Nov 10 adjacent-live evidence remains outstanding.

## Professional workspace and additive downloads

See [professional workspace](vnext_professional_workspace.md) for selected-theme
Role/W presentation, contextual inspection, descriptive operational bucket labels
and the additive Countertrend TXT contract. Qualification/ordering here and the
existing Directional exports remain unchanged.
