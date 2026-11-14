# Research Logic v2 rule simulation

Read-only pinned successful snapshot: 2026-11-12; 194 offline sessions (2026-02-06–2026-11-12), 44 themes and 663 unique members.

The frozen current reviewed Core/Enabler selection is used retrospectively **only for diagnostics**. This has survivorship/look-ahead selection bias and is not a performance backtest, point-in-time membership reconstruction, or official launch history. Official snapshots and observations are never changed. No P&L, entries, or portfolio returns are optimized.

Inputs come from the active successful run’s immutable observation references, not mutable cache rows. The JSON records run ID, provider identity and observation digest; it contains aggregate diagnostics, not raw prices/volumes.

## Candidate theme models

All candidates preserve the existing 60/40 score and use an exact five-completed-session score comparison. Short transforms score to 100−score and reverses change, so the rules are symmetric. At directional strength ≥50: Leading, or Fading when change ≤−threshold. Below 50: Improving when change ≥threshold; otherwise Lagging. Leading, Improving and Fading are researchable. Missing score is Unavailable; missing prior score does not invent a change. Breadth-veto alternatives require directional participation ≥50%.

| Δ threshold | Breadth veto | Side | Themes min/mean/max | Stocks min/mean/max | Mean state changes/day | Mean improving | Mean leader retention |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 5 | False | long | 21/27.015/31 | 312/431.304/532 | 11.358 | 5.5 | 1.0 |
| 5 | False | short | 20/27.015/32 | 277/395.722/497 | 11.352 | 4.851 | 1.0 |
| 5 | True | long | 4/19.289/29 | 59/313.99/510 | 11.358 | 5.5 | 0.784 |
| 5 | True | short | 7/19.861/29 | 58/283.979/474 | 11.352 | 4.851 | 0.789 |
| 10 | False | long | 19/24.84/29 | 297/401.763/505 | 9.187 | 3.325 | 1.0 |
| 10 | False | short | 20/25.113/30 | 255/364.928/474 | 9.181 | 2.948 | 1.0 |
| 10 | True | long | 4/18.582/29 | 59/304.082/458 | 9.187 | 3.325 | 0.784 |
| 10 | True | short | 7/19.129/29 | 58/273.402/459 | 9.181 | 2.948 | 0.789 |
| 15 | False | long | 18/23.479/28 | 279/382.278/477 | 7.689 | 1.964 | 1.0 |
| 15 | False | short | 19/23.918/28 | 232/344.83/444 | 7.684 | 1.753 | 1.0 |
| 15 | True | long | 4/17.99/26 | 59/294.985/458 | 7.689 | 1.964 | 0.784 |
| 15 | True | short | 7/18.572/27 | 58/264.072/431 | 7.684 | 1.753 | 0.789 |

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

Rejected alternatives: the 5-point change model is more sensitive to modest cross-theme rotation; 15 points delays emerging-theme discovery. The middle 10-point candidate balances the measured churn and discovery counts above. A breadth veto loses established structural leaders during participation pullbacks; it also makes one stock disproportionately decisive in small themes. The $20M/$30M alternatives remove additional reviewed names without a demonstrated research need; $5M admits thinner names. The 20-session window reduces dependence on short-lived activity. Measured eligibility churn is reported rather than assumed.

## Pullbacks, retention and symmetry

Both SPY and QQQ declined across five sessions on 89 diagnostic sessions. Per-session researchable and state counts are in the JSON. Structural leaders are retained at mean ratios Long=1.0 and Short=1.0 without the breadth veto. Fading is a label change, not deletion. Exact mirrored inputs are unit-tested for Long/Short symmetry; actual Long/Short counts differ because market behavior is not symmetric.

Small themes (<10 configured members): 13; their IDs and counts are in the JSON. They receive no breadth ranking weight, the same as larger themes. The state classifier takes no breadth input, so 0% and 100% breadth have identical state/ranking influence.

## Reproduce

```powershell
.venv-vnext/Scripts/python.exe scripts/research_v2_simulation.py
.venv-vnext/Scripts/python.exe -m unittest discover -s tests -p test_research_v2_simulation.py -v
```

This workflow never calls a provider, changes membership, writes the runtime DB, or emits raw market data. New observations or memberships change results; the JSON pins the inspected inputs. Threshold selection is a transparent research policy choice, not predictive evidence. Official v2 recent-change fields must wait for compatible five-session history rather than representing retrospective diagnostics as earned history.
