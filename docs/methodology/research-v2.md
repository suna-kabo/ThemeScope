# Research Logic v2

Research v2 changes which charts receive attention. It does not detect setups,
predict reversals, or place trades. The deterministic backend owns the rules;
the UI presents its committed snapshot. The versioned selection policy is
[`research_v2.json`](../../config/vnext/research_v2.json).

## Universes

The manually maintained Base Market Universe is NASDAQ/NYSE common stock with
price >$5 and capitalization >$1B. The supplied November 14 export has 2,229
unique symbols. It is a maintenance input, never a daily dependency. SPY/QQQ
rosters support market context and breadth; they do not confer research membership.

Reviewed effective-dated relationships define the Theme Research Universe.
Core and Enabler enter calculations; Related remains visible context only.
Unmapped companies are valid. Scanner proposals never become memberships
automatically. The original launch package remains immutable; the reviewed
November 14 amendment adds seven issuer-verified relationships on November 16.
See the [coverage audit](../../reports/archive/research-v2/research-v2-universe-audit.md).

## Structure and recent change

All existing return and accounting formulas remain unchanged: theme 1M/3M are
the medians of valid Core/Enabler 21/63-session price returns; Theme Score is
60% of the cross-theme 1M percentile plus 40% of the 3M percentile. At least
five valid members and 80% coverage remain required for these calculations.
The chain-linked index and EMA21/50 trend remain context.

Recent change recalculates Theme Score at today and exactly five completed
sessions earlier using **today's reviewed Core/Enabler basket at both dates**.
This read-only current-basket research comparison does not depend on saved
refreshes. It is not the historical official Theme Score and never writes or
backdates accounting, index or membership records. Both dates use the same
methodology and membership basis. The 1M percentile population, 3M percentile
population and combined scored-theme population must each agree globally;
otherwise every recent comparison is unavailable. A per-theme fallback would
incorrectly ignore the effect of another theme on cross-theme percentiles.

Provenance identifies the basis session, exact comparison session, methodology,
reviewed-membership fingerprint and all score populations. The calculation also
checks that today's snapshot metrics and relationships match that basis. It
needs 63+5 elapsed sessions (69 endpoint observations), not five earlier app runs.
Fresh installation, skipped refresh days and a v1 upgrade can therefore show
Improving/Fading on the first refresh when sufficient valid bars exist. Index
warm-up does not block a cross-sectional score comparison.

On November 16 the seven approved additions enter today's basket. Their already
available historical prices may enter the reconstructed November 9 comparison,
explicitly labelled as the **November 16 basket**, without asserting November 9
membership or modifying its official results. If data change a percentile
population, the entire comparison remains unavailable; no one-week app warm-up
is imposed. Insufficient completed history, unavailable score, incompatible basis
and changed percentile population have distinct readable explanations.

## Themes landscape

Themes defaults to highest raw Theme Score first in every market environment.
The 5-session Change is the current score minus the score exactly five completed
sessions earlier. A plus sign means the score rose. A minus sign means it fell.

| Raw Theme Score | Raw 5-session Change | State |
| --- | --- | --- |
| ≥50 | ≤−10 points | Fading |
| ≥50 | All other cases, including unavailable | Strong |
| <50 | ≥+10 points | Improving |
| <50 | All other cases, including unavailable | Weak |
| Unavailable | Any | Unavailable |

The movement disclosure ranks the largest positive and negative raw changes and
reports unavailable comparisons. Full Theme and Quick View explain comparison
availability and keep price context separate from State.

## Primary directional theme selection

The thresholds below use the raw Theme Score and raw 5-session Change.

| Long condition | Short condition | State | Researchable |
| --- | --- | --- | --- |
| Score ≥50 and change ≤−10 points | Score ≤50 and change ≥+10 points | Fading | Yes |
| Score ≥50 in other cases | Score ≤50 in other cases | Leading | Yes |
| Score <50 and change ≥+10 points | Score >50 and change ≤−10 points | Improving | Yes |
| Score <50 in other cases | Score >50 in other cases | Lagging | No |
| Missing score | Missing score | Unavailable | No |

Exactly 50 is included at the structural boundary for either research side.
This inclusive midpoint tie policy preserves mirrored Long/Short semantics; it
does not imply either market bias. Only the actual market side selects a list.
Reasons describe raw weakness as support for Short research, and raw strength
as support for Long research. Falling Theme Score can support Short research.

Without a comparable five-session change, structural strength still distinguishes
Leading and Lagging, with an explicit comparison-unavailable explanation.
Fading leaders remain researchable during broad pullbacks. Synthetic Trend and
breadth never veto these states. Breadth displays the above-EMA numerator and
valid denominator; below ten valid members it carries a small-sample warning.
It has zero ranking weight at every size. Small samples remain context even
when the original breadth metric cannot meet its calculation coverage minimum.

The SPY/QQQ Market Matrix remains unchanged, including Neutral and Unclassified.
IWM remains context only. Selective Long/Short use the corresponding side's
selection rules; reduced conviction does not delete otherwise eligible research.
Full Bias orders Leading → Improving → Fading. Selective orders Leading → Fading
→ Improving, preferring established structural themes over below-boundary early
improvement. This changes priority, never the qualifying membership set. Short
mirrors Long. No cap or additional score is introduced.

Neutral/Unclassified have no current side or current directional theme state,
no researchability and no directional list/export. The Themes landscape uses the same raw ordering and states in these environments.

## Daily eligibility and order

Price must exceed $5. Average dollar volume must be at least $10M over the latest
20 completed regular sessions: arithmetic mean of each session's **raw close ×
raw volume**. A missing/incomplete session makes eligibility unavailable. There
is no latest-session turnover veto or raw share-volume gate. Liquidity never
changes stable theme membership or peer denominators.

Every eligible Core/Enabler member of a researchable theme enters the list.
The original leave-one-out peer medians and W = 60% ER1M + 40% ER3M remain
unchanged. W orders stocks, with higher first for Long and lower first for Short.
Zero, opposite-sign and unavailable W are retained; unavailable values sort last.
The UI calls this **Peer strength**, in percentage points.

Primary orders themes by the full/Selective state sequence above, then by the
Theme Score in the appropriate direction and by theme ID. Within each theme, peer strength and ticker break ties. There is
no stock-count cap. Multiple relationships remain visible; combined TradingView
TXT deduplicates at the highest-priority theme, preserving that same ordering.
Individual theme exports preserve their own complete member order. Visible UI
filters do not alter the full-session download.

## Evidence and boundaries

The [rule simulation](../../reports/archive/research-v2/research-v2-rule-simulation.md) compares
12 state candidates and eight liquidity candidates over 194 offline sessions.
It is a stability diagnostic with frozen-membership selection bias, not a profit
backtest. Lists can exceed 250 names; thresholds were not optimized to a count.

Contract revision 4 includes the market-independent `raw_state` field. The
existing `score_change` remains raw. Primary uses its existing directional states
and `research_order_index`. Older stored versions require a refresh to populate
the current Themes and Primary views.

Read-only query functions in `research/queries.py` expose market state/changes,
themes/history/members, stocks and the research list for future agents. They omit
legacy v1 priority/transition fields from current theme DTOs; older selection is
explicitly unavailable. `/api/themes/{theme_id}/history` returns separately labelled
official session observations, not reconstructed current-basket state. Unknown
theme-member requests return 404, while a known empty theme returns an empty list. Current
loopback API routes share one committed snapshot. A failed refresh preserves the
preceding successful snapshot and exports.
