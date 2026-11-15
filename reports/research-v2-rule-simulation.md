# Research Logic v2 rule simulation

Read-only pinned successful snapshot: 2026-11-12; 194 offline sessions (2026-02-06–2026-11-12), 44 themes and 663 unique members.

The frozen current reviewed Core/Enabler selection is used retrospectively **only for diagnostics**. This has survivorship/look-ahead selection bias and is not a performance backtest, point-in-time membership reconstruction, or official launch history. Official snapshots and observations are never changed. No P&L, entries, or portfolio returns are optimized.

Inputs come from the active successful run’s immutable observation references, not mutable cache rows. The JSON records run ID, provider identity and observation digest; it contains aggregate diagnostics, not raw prices/volumes.

## Candidate theme models

All candidates preserve the existing 60/40 score and use an exact five-completed-session score comparison. Short transforms score to 100−score and reverses change, so the rules are symmetric. At directional strength ≥50: Leading, or Fading when change ≤−threshold. Below 50: Improving when change ≥threshold; otherwise Lagging. Leading, Improving and Fading are researchable. Missing score is Unavailable; missing prior score does not invent a change. Breadth-veto alternatives require directional participation ≥50%.

| Δ threshold | Breadth veto | Side | Themes min/mean/max | Stocks min/mean/max | Mean state changes/day | Mean improving | Structural retention |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 5 | False | long | 18/26.737/31 | 262/426.794/532 | 11.597 | 5.222 | 1.0 |
| 5 | False | short | 20/26.845/32 | 277/393.258/497 | 11.591 | 4.68 | 1.0 |
| 5 | True | long | 4/19.268/29 | 59/313.722/510 | 11.597 | 5.222 | 0.784 |
| 5 | True | short | 7/19.753/29 | 58/282.603/474 | 11.591 | 4.68 | 0.789 |
| 10 | False | long | 18/24.66/29 | 262/398.655/505 | 9.398 | 3.144 | 1.0 |
| 10 | False | short | 20/25.031/30 | 255/363.995/474 | 9.392 | 2.866 | 1.0 |
| 10 | True | long | 4/18.562/29 | 59/303.876/458 | 9.398 | 3.144 | 0.784 |
| 10 | True | short | 7/19.052/29 | 58/272.629/459 | 9.392 | 2.866 | 0.789 |
| 15 | False | long | 18/23.371/28 | 262/380.34/477 | 7.881 | 1.856 | 1.0 |
| 15 | False | short | 19/23.866/28 | 232/344.314/444 | 7.875 | 1.701 | 1.0 |
| 15 | True | long | 4/17.979/26 | 59/294.835/458 | 7.881 | 1.856 | 0.784 |
| 15 | True | short | 7/18.521/27 | 58/263.557/431 | 7.875 | 1.701 | 0.789 |

Five-session comparisons: 179 available of 189 eligible session pairs. Unavailable diagnostic dates: insufficient_completed_history=5, ranked_universe_changed=10.
The 1M, 3M and combined scored-theme populations must each match globally across t and t-5. Unavailable comparisons use structural Leading/Lagging fallback for product/list counts. They censor temporal episodes and are excluded from recent-state churn; availability changes are not counted as market-state changes. State churn uses adjacent dates with valid comparisons on both dates, and excludes missing-score theme pairs. JSON records the included session-pair count.

**Retention is a definition check, not independent evidence for the recent-change threshold.** Every structurally strong theme is Leading or Fading and both are researchable, so the no-veto model necessarily reports 1.0. The breadth-veto comparison measures how many of those deliberately retained themes that extra gate would remove; it does not validate ±10.

## Recent-state persistence and transitions

Rates below are observed fractions (0–1), not profit metrics. Persistence is the fraction of valid next-session pairs that remain Improving. Transition rates use completed episodes only; left-edge and right-edge/missing-data episodes are censored and reported separately in JSON (one episode may touch both edges). Time to Leading counts sessions to a direct Improving → Leading exit, rather than counting later recoveries after a different state. Fading exits separate loss of directional structure (Lagging) from recovery (Leading).

| Δ threshold | Side | Improving next-session persistence | Completed Improving episodes | Direct to Leading | Mean sessions to Leading | Fading to Lagging | Fading recovery to Leading | Near-threshold change rate |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 5 | long | 0.550201 | 429 | 0.321678 | 2.254 | 0.333333 | 0.666667 | 0.279196 |
| 5 | short | 0.567749 | 369 | 0.336043 | 2.282 | 0.320093 | 0.67757 | 0.279196 |
| 10 | long | 0.502488 | 290 | 0.351724 | 1.902 | 0.322097 | 0.677903 | 0.191804 |
| 10 | short | 0.49635 | 267 | 0.325843 | 2 | 0.349481 | 0.650519 | 0.191804 |
| 15 | long | 0.455056 | 191 | 0.298429 | 1.719 | 0.344086 | 0.655914 | 0.156381 |
| 15 | short | 0.41411 | 186 | 0.349462 | 1.692 | 0.294737 | 0.705263 | 0.156381 |

Near-threshold change rate counts state changes among pairs within two score-change points of either material-change boundary, while both dates stay in the same directional structural zone. It isolates material-change sensitivity from crossing structural score 50. These diagnostics distinguish temporal behavior without optimizing P&L or list size. The established ±10 rule is retained; the diagnostics do not establish predictive superiority.

Rank instability is measured independently: absolute daily competition-rank movement min/mean/max = 0/3.189/27. State changes above count changed theme labels, not stock churn or profitable trades.

## Daily liquidity candidates

Price must be **above $5**. Liquidity is the arithmetic mean of each completed session’s raw close × raw volume. Every session in the 10- or 20-session window must exist and be completed/regular. No one-day turnover or share-volume gate is added. Eligibility never edits membership.

| Sessions | Floor $M | Eligible min/mean/max | Daily eligibility changes min/mean/max | Latest eligible | Missing window |
| --- | --- | --- | --- | --- | --- |
| 10 | 5 | 649/658.263/663 | 0/0.446/3 | 662 | 0 |
| 10 | 10 | 645/655.469/663 | 0/0.736/4 | 662 | 0 |
| 10 | 20 | 629/646.082/658 | 0/1.591/5 | 656 | 0 |
| 10 | 30 | 608/630.108/652 | 0/3.295/10 | 646 | 0 |
| 20 | 5 | 650/657.902/663 | 0/0.44/3 | 662 | 0 |
| 20 | 10 | 646/655.082/663 | 0/0.58/5 | 662 | 0 |
| 20 | 20 | 632/646.923/658 | 0/0.912/4 | 653 | 0 |
| 20 | 30 | 615/631.742/649 | 0/1.902/6 | 648 | 0 |

## Selected model

- Keep the existing structural boundary at 50; use a 10-point five-session score move to identify meaningful improvement/deterioration.
- Include every daily-eligible Core/Enabler member of researchable themes. W orders peers only; opposite-sign and unavailable W remain visible.
- Use 20 completed sessions and $10M average dollar volume, with price >$5. Compare all eight liquidity candidates without targeting a stock count.
- Keep breadth entirely contextual for every sample size. Below 10 valid members, flag the small sample; show numerator/denominator. One member moves a five-member theme by 20 percentage points, versus 5 points at 20 members.
- Keep synthetic EMA trend visible as context. Do not gate on it: the inspected official snapshot has trend availability {'Unavailable': 7, 'Bearish': 18, 'Bullish': 16, 'Mixed': 3}; a trend veto would suppress otherwise valid research during warmup.

Rejected alternatives: the 5-point change model is more sensitive to modest cross-theme rotation; 15 points delays emerging-theme discovery. The middle 10-point candidate balances the measured churn and discovery counts above. A breadth veto loses established structural leaders during participation pullbacks; it also makes one stock disproportionately decisive in small themes. The $20M/$30M alternatives remove additional reviewed names without a demonstrated research need; $5M admits thinner names. On these inputs the $10M/20-session rule has mean eligibility churn 0.58 versus 0.736 changes/day for its 10-session counterpart, while retaining 9 more names than $20M at the latest snapshot. This supports a moderate floor without claiming an optimal liquidity rule.

## Pullbacks, retention and symmetry

Both SPY and QQQ declined across five sessions on 89 diagnostic sessions. Per-session researchable and state counts are in the JSON. By the explicit retention policy, structural leaders are retained at mean ratios Long=1.0 and Short=1.0 without the breadth veto. Fading is a label change, not deletion. Exact mirrored inputs are unit-tested for Long/Short symmetry; actual Long/Short counts differ because market behavior is not symmetric.

Small themes (<10 configured members): 13; their IDs and counts are in the JSON. They receive no breadth ranking weight, the same as larger themes. The state classifier takes no breadth input, so 0% and 100% breadth have identical state/ranking influence. The JSON measures actual one-member percentage-point sensitivity and observations within one member of a hypothetical 50% gate, separately for valid samples below 10 and samples of 10 or more.

## Reproduce

```powershell
.venv-vnext/Scripts/python.exe scripts/research_v2_simulation.py
.venv-vnext/Scripts/python.exe -m unittest discover -s tests -p test_research_v2_simulation.py -v
```

This workflow never calls a provider, changes membership, writes the runtime DB, or emits raw market data. New observations or memberships change results; the JSON pins the inspected inputs. Threshold selection is a transparent research policy choice, not predictive evidence. Production may calculate an explicitly labelled same-basis five-session research comparison from sufficient completed bars; that comparison never becomes or rewrites official accounting history.
