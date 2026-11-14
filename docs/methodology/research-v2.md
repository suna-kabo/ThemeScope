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
See the [coverage audit](../../reports/research-v2-universe-audit.md).

## Structure and recent change

All existing return and accounting formulas remain unchanged: theme 1M/3M are
the medians of valid Core/Enabler 21/63-session price returns; Theme Score is
60% of the cross-theme 1M percentile plus 40% of the 3M percentile. At least
five valid members and 80% coverage remain required for these calculations.
The chain-linked index and EMA21/50 trend remain context.

Recent change compares Theme Score with exactly five completed sessions earlier.
The theme universe, calculation membership, methodology and index series must
be comparable. Missing history stays unavailable; diagnostic pre-launch
reconstructions never become official change history. A changed score universe
invalidates comparisons. Rank change is prior competition rank minus current
rank; unavailable scores that change the ranked universe invalidate rank change.

For Long, directional strength is Score and change is current minus prior Score.
For Short, strength is 100−Score and change is the reverse. Both use:

| Condition | State | Researchable |
| --- | --- | --- |
| Strength ≥50 and change ≤−10 points | Fading | Yes |
| Strength ≥50, otherwise | Leading | Yes |
| Strength <50 and change ≥10 points | Improving | Yes |
| Strength <50, otherwise | Lagging | No |
| Missing structural score | Unavailable | No |

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
Neutral/Unclassified do not manufacture a directional list. All themes and
members remain inspectable.

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

Themes order Leading, Improving, Fading, then directional structural strength,
then theme ID. Within each theme, peer strength and ticker break ties. There is
no stock-count cap. Multiple relationships remain visible; combined TradingView
TXT deduplicates at the highest-priority theme, preserving that same ordering.
Individual theme exports preserve their own complete member order. Visible UI
filters do not alter the full-session download.

Countertrend and its reversal-like buckets are removed from current snapshots
and screens. Historical helpers and approved old fixtures remain provenance.

## Evidence and boundaries

The [rule simulation](../../reports/research-v2-rule-simulation.md) compares
12 state candidates and eight liquidity candidates over 194 offline sessions.
It is a stability diagnostic with frozen-membership selection bias, not a profit
backtest. Lists can exceed 250 names; thresholds were not optimized to a count.

Read-only query functions in `research/queries.py` expose market state/changes,
themes/history/members, stocks and the research list for future agents. Current
loopback API routes share one committed snapshot. Public projection explicitly
allowlists the v2 presentation contract; it cannot expose local history inputs,
provider credentials, runtime databases or unknown nested fields. Failed refresh
still preserves the preceding successful snapshot. No publication is authorized
by this development work.
