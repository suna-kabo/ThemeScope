# ThemeScope methodology

Current chart selection follows [Research Logic v2](research-v2.md), which replaces
the former W-sign filter and daily liquidity. This guide also
records the retained return and accounting formulas.
Versioned constants remain in [methodology.json](../../config/vnext/methodology.json);
the full [approved specification](../vnext/ThemeScope_vNext_Product_and_Methodology_Spec.md)
retains its original inspection-compatible path and dated amendments. The
[Gate E closure](../operations/gate-e-closure.md) supersedes old validation blockers.

## Data and Market Bias

Use completed US sessions from the versioned XNYS calendar with a 20-minute safety
delay. Alpaca historical SIP supplies `1Day` bars adjusted for splits and spin-offs,
not dividends. Raw regular-session close/volume are separately retained for liquidity.
Thematic ETFs have no calculation role.

The frozen SPY/QQQ Market Matrix combines their price/EMA states and breadth consensus.
IWM supplies context only. SPY and QQQ each require an effective approved constituent
roster; missing either blocks theme activation/Directional outputs. Stale rosters
are advisory. Index breadth requires valid price/EMA data and at least 80% coverage;
IWM has no constituent roster or breadth vote. The 64 frozen Matrix cases remain
in [the regression suite](../../tests/test_research_policy.py).

## Theme Strength and breadth

Only effective **Core + Enabler** members enter calculations; Related is context
only. For each horizon independently, take the median valid member price return
from 21 or 63 sessions earlier. At least five valid members and 80% configured-member
coverage are required. Missing endpoints stay missing; dates are not compressed.

Across valid Active themes, each horizon uses average-rank percentiles:
`(average_rank − 1) / (N − 1) × 100`. Ties share average rank; one valid theme cannot
supply a percentile. Both horizons are required for:

`Theme Strength = 0.60 × percentile(1M) + 0.40 × percentile(3M)`.

Theme breadth measures the proportion of valid members above their corresponding
EMA21 or EMA50. Each metric requires five valid members and 80% coverage. Unavailable
is a dash, not zero. Breadth does not enter Strength or Directional qualification.

## Synthetic index, Trend and history

The chain-linked price index begins at 100 and equal-weights Core/Enabler holdings
at initialization and approved rebalances. Weights drift naturally between rebalances.
Old holdings earn approval session t; rebalance at t close; new holdings first earn
the next trading session. `effective_from` names that first earned session;
`effective_to` is exclusive. No retrospective membership rewrite or daily re-equal-weighting.

Trend is Bullish when the index is strictly above both EMA21/EMA50, Bearish when
strictly below both, Mixed otherwise; invalid/missing is Unavailable. EMAs use the
approved contiguous SMA seed and alpha `2/(period+1)`.

Approved launch rebalance: **2026-11-06 close**. First earned session: **2026-11-09**.
Launch initializes official indices at exactly 100, without a launch-day return.
Approved launch-close research uses the first-earned membership independently.
Bootstrap history seeds indicators/current pre-launch research only; it never
becomes official earned history or a prior live transition. Nov 9 has no adjacent
earned-live transition; Nov 10 is the first possible compatible adjacent-live
comparison, subject to genuine compatible data. All three real chronological
checks now passed per the [closure record](../operations/gate-e-closure.md).

Comparisons require compatible methodology/series and adjacent completed sessions.
Legacy ETF-based history is a distinct series and is never spliced into this one.
Explicitly approved [terminal events](../architecture/terminal-actions.md) may value
existing holdings without fabricating OHLCV or tradeability.

## Peer strength and chart research

For each stock/theme relationship, exclude the stock and compute peer medians for
both horizons. At least four other valid peers and 80% coverage of the other
configured members are required. `ER = stock return − peer median return` and
`W = 0.60 × ER1M + 0.40 × ER3M`. The UI's **Peer strength (pp)** expresses W in percentage
points; it is not a return forecast.

Leading, Improving and Fading themes are researchable in the market direction.
Every daily-eligible Core/Enabler member enters the list; W orders peers without
excluding zero, opposite-sign or unavailable values. Short mirrors Long. Trend
and breadth remain context. See the v2 specification for exact state boundaries.

Daily eligibility uses raw close >$5 and average daily dollar volume **≥$10 million**
over 20 completed sessions, averaging each session's raw close × volume. Missing required
bars make eligibility unavailable. Membership, theme medians and peer denominators
do not change because a stock fails daily liquidity. Earnings are optional and
never affect qualification.

## Multiple themes and exports

A stock qualifies independently in each theme. Individual-theme exports retain
all qualifying relationships. Combined placement follows theme research priority,
directional peer strength, then ticker. Verified TradingView
identifiers are required; no exchange is guessed. Visible UI filters do not rewrite
current session exports.
