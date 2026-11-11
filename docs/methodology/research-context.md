# Extension, ranks and research lenses

The additive contract is `themescope-research-1`; policy/version hashes come from
[research_context.json](../../config/vnext/research_context.json). It leaves the
Market Matrix, Strength, W, Directional qualification and official history unchanged.

## Market Extension

For SPY and QQQ separately, use `(adjusted close − EMA21) / Wilder ATR20`.
True Range is `max(H−L, |H−previous close|, |L−previous close|)` in split/spin-off-adjusted
units. Seed ATR with 20 True Ranges (21 closes), then use
`(19 × previous ATR + current TR) / 20`. Missing/interrupted inputs or zero ATR are
unavailable; no close-range substitution. Snapshot metadata records the history start.

Absolute distance <1 is Normal; [1,1.5) Stretched; ≥1.5 Extended. Sign determines
Upside/Downside. Exact thresholds apply before display rounding. Aggregate requires
both benchmarks on the same side and at least Stretched: both Extended gives Extended;
Stretched/Extended or both Stretched gives Stretched. Normal involved or opposing
sides gives Normal; either unavailable gives Unavailable. IWM, breadth, EMA50,
VIX and theme metrics do not enter Extension.

Short Bias with Downside extension adds Countertrend Watch/Highlighted; Long Bias
mirrors with Upside extension and Pullback-Risk Watch/Highlighted. Opposite-side
extension does not change focus. Non-directional Bias remains Observe. The initial
preferred lens applies once per page load; manual selection survives polling.

## Canonical rank and changes

Valid Active Strength scores rank descending with competition ties `1,2,2,4`.
Theme ID breaks display ordering only, not tied economic rank. Filters do not rerank.
Rank Change is previous rank minus current rank from one compatible adjacent-session
successful run. Missing/new score, changed ranked universe, incompatible series or
missing prior earned history gives an explicit unavailable comparison. EMA transitions
follow the same adjacent-session/earned-history guard; equality means reaching an EMA.

## Countertrend

Use supplied Active Core/Enabler relationships with passing existing liquidity and
finite nonzero W. There are no extra earnings or Newly Bullish/Bearish exceptions.

| Market side | Theme filter | W >0 bucket | W <0 bucket |
| --- | --- | --- | --- |
| Short | Strength <50; Bearish or Mixed | Peer outperformers | Weak-theme laggards |
| Long | Strength ≥50; Bullish or Mixed | Strong Leaders / Pullback Watch | Relative Weakness |
| Non-directional | No inferred universe | Unavailable | Unavailable |

Positive buckets order W descending, score descending, ticker alphabetically;
negative buckets order W ascending, score ascending, ticker alphabetically.
Theme ID is the final stable tie-breaker. These are research organization rules,
not reversal signals. **Positive W does not predict a pullback.**

Stocks view selects supplied representative relationships; a ticker can appear
in both buckets through different themes. Global stock counts deduplicate;
relationship counts do not. Grouped view retains every relationship. A Theme filter
shows that relationship's Role/W and passes it to inspection, while unfiltered
representatives and published export placement stay unchanged.

Directional files remain unchanged. Countertrend publishes All Countertrend and
the two side-specific bucket TXT lists, plus per-theme counterparts through existing
verified mappings. Visible filters do not reduce the full published-lens download.
Original enums/routes/filenames and `themescope-vnext-watchlist` remain compatible.
See [workflow](../getting-started/research-workflow.md) for navigation and Saved.
