# ThemeScope v5 Implementation Change Brief

**Purpose:** Give Codex a complete, implementation-oriented description of the changes required to the latest `dashboard(1).html` and `Theme_and_Stock_Watchlist_Specification_v4(1).md`.

**Status:** Approved product direction. Implement only after inspecting the supplied v4 specification, latest HTML, and any generator/source scripts in the workspace.

**Primary user horizon:** US swing trading, normally less than one month.

## 1. Required product outcome

ThemeScope is an on-demand, end-of-day, offline selection dashboard with three sections:

1. **Market:** describe broad market price condition and internal participation.
2. **Themes:** rank tradeable sector, industry, and theme ETFs by relative performance and constituent participation.
3. **Watchlist:** show a manageable set of liquid stocks associated with the selected theme and describe whether each stock is outperforming or underperforming its related ETF.

ThemeScope is a **selection and organization system**, not a technical-entry scanner or complete trading strategy.

It must help the user answer:

1. What is the current SPY and QQQ market condition?
2. Is index movement broadly supported by constituents or narrowly driven?
3. Which tradeable sector, industry, or theme ETFs are relatively strongest and weakest?
4. Is an ETF's performance broadly supported by its own holdings?
5. Within a chosen theme, which selected stocks are outperforming or underperforming the anchor ETF?
6. Which charts should the user inspect manually in TradingView?

The system must **not** detect pullback entries, issue buy/short instructions, calculate stops, size positions, allocate a portfolio, or execute trades.

## 2. Preserve the deployment and operating model

Retain these v4 requirements:

- On-demand generation using the latest verified completed common US session.
- Self-contained static HTML with embedded snapshot data.
- No database, persistent backend, account system, scheduler, or unattended refresh requirement.
- The opened HTML must make no automatic external requests.
- Chart links may open externally only after an explicit user click.
- Provide downloadable local CSV and TradingView-compatible text exports.
- Display data-session date, collection time, source status, and unavailable reasons.
- Preserve the last successful dashboard when a refresh fails.
- Generate into temporary outputs, validate them, and replace the last successful outputs only after all mandatory validation passes.
- A failed refresh must create a separate run report and must not overwrite the last valid dashboard with partial or empty data.
- Never replace unavailable values with zero or silently mix incompatible price-adjustment conventions.

If generator scripts exist, update the scripts and regenerate the HTML. Do not patch only the generated snapshot while leaving its generator inconsistent. If only the HTML and specification exist, identify the missing generator dependency instead of pretending that live collection has been implemented.

## 3. Scope decisions approved after v4

### 3.1 Primary hierarchy

The implementation priority is:

1. Market condition.
2. Sector, industry, and theme ETF performance.
3. ETF constituent breadth.
4. Stock relative strength within the selected theme.
5. Optional research details.

Membership-research workflow must not dominate the default interface or block valid ETF-level calculations.

### 3.2 Tradeable ETF themes remain valid without stock drilldowns

A valid liquid anchor ETF is sufficient for a sector, industry, or theme to appear in the primary ranking.

- A theme with no curated stock list remains fully rankable and directly tradeable through its ETF.
- `ETF-only` means there is no curated stock drilldown. It does not mean that ETF return, ETF breadth, theme score, or market comparison is unavailable.
- Biotechnology may remain ETF-only while its ETF is still included in theme ranking and breadth.
- Do not exclude a valid ETF-level theme because individual-company classification is incomplete.
- Do not treat a target number such as 400 themes as a quality objective.
- A primary row still requires a suitable tradeable anchor ETF. A narrow concept without one remains a secondary stock tag.

### 3.3 Theme taxonomy

Each primary registry record should include a stable ID and a visible `level`:

- `Sector`
- `Industry`
- `Theme`

Use one primary anchor ETF for each economic exposure. Alternative ETFs may be shown in details but must not create duplicate primary rows for the same exposure.

Keep valid weak exposures visible. Do not add, remove, or switch anchors because of recent performance.

## 4. Market section

### 4.1 Required market instruments

Display SPY and QQQ separately.

- SPY is the general US large-cap market benchmark.
- QQQ is growth-heavy context and is especially relevant to technology-related themes.
- QQQ is not a universal gate for unrelated themes.
- Do not average SPY and QQQ into one market score.

### 4.2 Add true index breadth

Calculate index breadth from official or reproducibly sourced constituent universes:

- SPY context uses S&P 500 constituents.
- QQQ context uses Nasdaq-100 constituents.
- Use one company/security once within each index universe after verified mapping.
- Exclude cash, derivatives, funds, and other non-common-equity holdings from the breadth denominator.
- Keep the two universes separate because they overlap.

For index \(i\):

```text
IndexBreadth21_i = 100 * count(valid constituents with P > EMA21)
                   / ValidEMA21Count_i

IndexBreadth50_i = 100 * count(valid constituents with P > EMA50)
                   / ValidEMA50Count_i

Coverage21_i = ValidEMA21Count_i / EligibleConstituentCount_i
Coverage50_i = ValidEMA50Count_i / EligibleConstituentCount_i
```

Use split-adjusted closing prices for EMA calculations and the v4 session-alignment and missing-data rules.

### 4.3 Market-condition classifications

Do not compress market condition into an opaque composite score. Show a short-term and medium-term condition separately for SPY and QQQ.

For the short-term condition:

```text
PriceStrong21 = IndexClose > IndexEMA21
BreadthStrong21 = IndexBreadth21 >= 50
```

| PriceStrong21 | BreadthStrong21 | Short-term condition |
|---|---|---|
| True | True | Broad short-term strength |
| True | False | Narrow short-term strength |
| False | True | Internal strength, index below EMA21 |
| False | False | Broad short-term weakness |

For the medium-term condition, apply the same exhaustive logic using close versus EMA50 and IndexBreadth50:

| PriceStrong50 | BreadthStrong50 | Medium-term condition |
|---|---|---|
| True | True | Broad medium-term strength |
| True | False | Narrow medium-term strength |
| False | True | Internal strength, index below EMA50 |
| False | False | Broad medium-term weakness |

Exact equality of price and EMA belongs to the `False` branch. Exact 50% breadth belongs to the `True` branch. Evaluate unrounded values.

If the breadth validity requirements fail, show the price fact and mark the combined market-condition label unavailable. Do not infer breadth from SPY or QQQ price alone.

### 4.4 Market fields

The default Market section should show:

- Price close.
- 5-, 21-, and 63-session adjusted returns.
- Close above/below EMA21.
- Close above/below EMA50.
- IndexBreadth21 with numerator and denominator.
- IndexBreadth50 with numerator and denominator.
- Short-term market condition.
- Medium-term market condition.
- Session date and data warnings.

RSP/SPY and IWM may remain optional context. A falling RSP/SPY ratio is not itself true market breadth and must not replace constituent breadth.

## 5. Anchor-ETF breadth

### 5.1 Purpose

ETF breadth describes how many holdings participate in the anchor ETF's move. It is supporting evidence for theme strength, not a technical entry signal.

Breadth must not depend on business-relevance or SEC-filing review. Use the anchor ETF's complete official equity holdings universe after deterministic security mapping.

### 5.2 ETF breadth calculations

For theme \(t\):

```text
ETFBreadth21_t = 100 * count(valid equity holdings with P > EMA21)
                 / ValidEMA21Count_t

ETFBreadth50_t = 100 * count(valid equity holdings with P > EMA50)
                 / ValidEMA50Count_t

Coverage21_t = ValidEMA21Count_t / EligibleEquityHoldingCount_t
Coverage50_t = ValidEMA50Count_t / EligibleEquityHoldingCount_t
```

Rules:

- Equal-weight company participation. Do not weight the breadth percentage by ETF portfolio weight.
- Count a company once after verified share-class mapping.
- Exclude cash, derivatives, bonds, funds, and unresolved non-equity rows from the eligible breadth universe and report their counts separately.
- Do not require the holding to pass the curated stock-watchlist filters.
- Do not require a filing or company-level evidence review.
- Display numerator, denominator, percentage, holdings as-of date, and metric coverage.
- Do not call this whole-industry breadth. Label it `Anchor ETF holdings breadth`.

### 5.3 Breadth validity

A breadth measure is valid for scoring only when:

- The official holdings snapshot is no more than 35 calendar days old.
- At least eight companies are valid for that measure.
- At least 80% of eligible equity holdings have valid data for that measure.

Raw fractions may still be displayed with a warning when the sample or coverage requirement fails, but they must not enter a score.

This `coverage` means price-data completeness only. Remove membership-evidence coverage from the primary user workflow.

## 6. Theme relative performance and scores

### 6.1 Preserve adjusted return and excess-return definitions

Retain v4's adjusted-return, common-session, missing-endpoint, and percentage-point rules.

```text
Excess21_t = ThemeETFReturn21_t - SPYReturn21
Excess63_t = ThemeETFReturn63_t - SPYReturn63
```

Use SPY consistently so primary theme comparisons remain comparable. QQQ may be displayed as additional context but must not replace SPY within the primary score for technology themes.

### 6.2 Cross-sectional percentile ranks

For each valid primary ETF, convert Excess21 and Excess63 into separate 0-to-100 cross-sectional percentile ranks within the dated primary ETF ranking universe:

```text
r = ascending rank with average ranks for exact ties
Percentile = 100 * (r - 1) / (N - 1)
```

Require at least ten valid peer ETFs for a percentile. Display the peer count and ranking-universe date. Keep unrounded values for calculations.

### 6.3 Current Strength Score

```text
CurrentStrength_t = 0.70 * PercentileExcess21_t
                    + 0.30 * ETFBreadth21_t
```

This score represents approximately one-month relative performance plus short-term constituent participation.

### 6.4 Medium Strength Score

```text
MediumStrength_t = 0.70 * PercentileExcess63_t
                   + 0.30 * ETFBreadth50_t
```

This score represents approximately three-month relative performance plus medium-term constituent participation.

### 6.5 Overall Theme Score

```text
ThemeScore_t = 0.60 * CurrentStrength_t
               + 0.40 * MediumStrength_t
```

Rationale:

- ETF price relative performance is the primary outcome and receives 70% within each horizon.
- Breadth is confirmation and receives 30%, so it influences but does not dominate ETF performance.
- Current strength receives 60% of the final score because the user's normal holding period is less than one month.
- These weights are fixed, documented conventions, not claimed optimal parameters.

Do not add further momentum, RSI, MACD, volatility, volume, sentiment, VIX, Fear and Greed, concentration, or market-breadth inputs to ThemeScore without a separate approved methodology change.

### 6.6 Five- and 126-session returns

- Display Return5 and Excess5 as recent context when valid.
- Do not include five-session performance in ThemeScore because it is noisy and can penalize a normal pullback.
- Return126 may remain an expanded background field when available.
- Do not include Return126 in ThemeScore.

### 6.7 Score availability

Do not impute missing breadth as 50 and do not silently reweight a score.

- If Excess21 percentile or ETFBreadth21 is invalid, CurrentStrength is unavailable.
- If Excess63 percentile or ETFBreadth50 is invalid, MediumStrength is unavailable.
- If either component score is unavailable, ThemeScore is unavailable.
- Valid ETF returns, raw excess returns, EMA facts, and price-only ranks remain visible independently.
- An unavailable ThemeScore does not remove the ETF from the table.

### 6.8 Four exhaustive theme states

Use the component scores, not rounded displayed values:

| CurrentStrength | MediumStrength | State |
|---|---|---|
| >= 50 | >= 50 | Leading |
| >= 50 | < 50 | Short-term strength only |
| < 50 | >= 50 | Medium-term strength only |
| < 50 | < 50 | Lagging |
| Either unavailable | Any | Unavailable |

Do not label the two cross-horizon states as proven `Improving`, `Fading`, `Recovery`, or `Rotation`. A current snapshot comparing nested 21- and 63-session windows does not establish a time-series transition.

`Leading` and `Lagging` are relative descriptions. They do not mean that the ETF price is rising or falling in absolute terms. Always display actual returns and independent EMA facts beside the state.

## 7. Stock membership and watchlists

### 7.1 Anchor holdings become a discovery source, not a formal gate

Revise v4's rule that formal membership requires current anchor-ETF membership.

A stock may enter a theme watchlist even when it is absent from the anchor ETF if:

- Its principal business or a material established business line directly matches the documented theme charter.
- It passes the existing stock eligibility and liquidity filters.
- A short inclusion rationale and reliable source are recorded.

ETF methodology, holdings, business descriptions, investor-relations material, annual reports, and segment disclosures may support classification. A 10-K or equivalent filing is not mandatory for every obvious case. Use deeper filing review only for ambiguous classifications.

Keep two simple visible membership tags:

- `Core`: the principal business directly matches the theme.
- `Related`: established material exposure exists, but the theme is not the company's principal business.

If relevance cannot be supported, keep the idea outside the current watchlist. Do not force a decision. Detailed unresolved and rejected records may remain in a research file but should not dominate the dashboard.

Allow the same company in multiple themes when each company-theme pair independently matches the relevant charter.

### 7.2 Preserve existing stock eligibility defaults unless separately changed

- Market capitalization at least USD 2 billion.
- Raw close at least USD 15.
- ADV$30 proxy at least USD 20 million.
- NYSE or Nasdaq listings.
- Eligible common shares, listed REIT common shares, and sponsored ADRs.
- Exclude OTC securities, preferred shares, warrants, units, and funds.
- Retain the current exclusion of individual biotechnology stocks unless explicitly revised later. Biotechnology ETFs remain valid theme instruments.

### 7.3 Preserve the existing 15/20 selection convention

- Candidate capacity remains 20 per theme.
- Default compact view shows the first 15.
- The user may expand to 20.
- Sorting and filtering must not change membership or refill the list.
- Preserve the existing transparent queue cycle: `Liquid, Liquid, Strong, Weak`.
- Preserve the existing queue definitions and deterministic tie-breakers unless required to support accepted non-anchor members.
- A non-anchor accepted member has no ETF portfolio weight. Treat the weight as unavailable, not zero.
- Do not force equal numbers of long and short candidates.
- Do not add an automated setup detector.

### 7.4 Preserve stock-versus-theme relative strength

For each accepted company-theme pair:

```text
StockExcess21 = StockReturn21 - AnchorETFReturn21
StockExcess63 = StockReturn63 - AnchorETFReturn63
```

Retain these as core stock-selection metrics. They answer whether the stock is outperforming or underperforming its related ETF.

Display:

- Return5, Return21, and Return63.
- StockExcess21 and StockExcess63.
- Above/below EMA21.
- Above/below EMA50.
- EMA21 slope as optional context.
- ADV$30.
- Membership tag and inclusion rationale.
- TradingView chart link.

Do not treat short-term stock weakness as an automatic exclusion. A leading stock can temporarily weaken during a pullback. ThemeScope describes the data and leaves setup interpretation to the user.

## 8. Remove or demote v4 complexity

Remove these from the default dashboard and from primary success criteria:

- Membership evidence coverage.
- Pending SEC-filing review counts.
- Extractor, challenger, judge, architect, curator, or other agent-role concepts.
- Requirement to read a filing for every obvious company-theme classification.
- ETF-weight coverage of the reviewed watchlist as a prominent field.
- Detailed unresolved/rejected evidence workflow on the main page.
- Any suggestion that incomplete stock classification invalidates ETF ranking or ETF breadth.

The following may remain in compact optional details:

- Largest holding weight.
- Top-five holding weight.
- Holdings as-of date.
- Alternative anchor ETFs.
- Theme overlap.
- Supporting membership sources.
- Registry/configuration version.

Concentration and overlap must not enter ThemeScore.

## 9. Dashboard interface requirements

### 9.1 Market section

Provide separate SPY and QQQ panels containing:

- Actual returns.
- EMA21 and EMA50 facts.
- Index breadth with counts.
- Short-term and medium-term market conditions.
- Data dates and warnings.

### 9.2 Themes section

Default sortable columns:

- Rank.
- Level.
- Theme name.
- Anchor ETF.
- ThemeScore.
- CurrentStrength.
- MediumStrength.
- Four-state label.
- Return5, Return21, Return63.
- Excess21 and Excess63 versus SPY.
- ETFBreadth21 with count.
- ETFBreadth50 with count.
- Close above/below EMA21.
- Close above/below EMA50.
- Data status.

Default sort should be ThemeScore descending, with unavailable scores placed last and a stable theme ID tie-breaker. Allow sorting by raw return, excess return, breadth, and component scores.

Allow filtering by `Sector`, `Industry`, and `Theme`. Sorting a filtered view must retain ranks from the declared ranking universe unless the UI explicitly labels a within-filter rerank.

### 9.3 Watchlist section

- Default to 15 selected stocks.
- Provide an explicit control to expand to 20.
- Preserve search, numeric sorting, trend/EMA filters, relative-performance filters, CSV export, TradingView export, and chart links.
- Show the selected theme's ETF score, component scores, breadth, state, and returns above its stock table.
- Stock ranking is within the selected theme universe, not across unrelated themes.

### 9.4 Progressive disclosure

The default screen should prioritize decision-relevant fields. Put methodology, source details, concentration, membership rationale, and diagnostics behind expandable details. Do not display research-pipeline complexity before market and theme information.

## 10. Exports and embedded data contract

Add the following fields where applicable to embedded JSON and CSV exports:

### Market/index fields

- `index_constituent_asof`
- `index_eligible_count`
- `index_valid_ema21_count`
- `index_valid_ema50_count`
- `index_breadth21_pct`
- `index_breadth50_pct`
- `index_coverage21_pct`
- `index_coverage50_pct`
- `market_condition21`
- `market_condition50`

### Theme fields

- `level`
- `holdings_asof`
- `breadth_eligible_equity_count`
- `breadth_valid_ema21_count`
- `breadth_valid_ema50_count`
- `etf_breadth21_pct`
- `etf_breadth50_pct`
- `breadth_coverage21_pct`
- `breadth_coverage50_pct`
- `percentile_excess21`
- `percentile_excess63`
- `current_strength_score`
- `medium_strength_score`
- `theme_score`
- `theme_state`
- Per-field status and unavailable reason.

### Stock membership fields

- `membership_tag` with `Core` or `Related`.
- `membership_source`
- `membership_rationale`
- `is_anchor_holding`

Retain separate raw values, statuses, reasons, observation counts, dates, and input versions. Do not encode unavailable numeric values as zero.

## 11. Validation and acceptance tests

### 11.1 Calculation tests

- Verify adjusted 5-, 21-, and 63-session return endpoints on common sessions.
- Verify excess returns are percentage-point subtraction, not return ratios.
- Verify percentile endpoints, exact ties, and minimum peer counts.
- Verify CurrentStrength, MediumStrength, and ThemeScore using hand-calculated fixtures.
- Verify a missing score input makes the dependent score unavailable without suppressing unrelated metrics.
- Verify ThemeScore uses no 5-session or 126-session input.
- Verify ThemeScore uses no index breadth, concentration, overlap, VIX, or sentiment input.
- Verify EMA equality uses the specified false branch for market price strength.
- Verify breadth equality at exactly 50% uses the specified true branch.
- Verify zero denominators return unavailable.
- Verify eight valid of ten eligible meets 80%; eight of eleven does not.
- Verify missing constituents are excluded from the metric denominator and reported, not counted as below EMA.
- Verify multiple share classes do not double-count a company.

### 11.2 State tests

- Current >= 50 and Medium >= 50 gives `Leading`.
- Current >= 50 and Medium < 50 gives `Short-term strength only`.
- Current < 50 and Medium >= 50 gives `Medium-term strength only`.
- Current < 50 and Medium < 50 gives `Lagging`.
- Any missing component gives `Unavailable`.
- Theme relative state must not be described as a proven rotation or reversal.

### 11.3 Market-condition tests

Test all four combinations of price-above-EMA and breadth-at-least-50 for EMA21 and EMA50, for both SPY and QQQ.

### 11.4 UI and export tests

- Default stock view contains no more than 15 rows.
- Expanding shows no more than 20 rows.
- Sorting and filtering do not change selected membership.
- Missing ThemeScore rows sort after valid rows.
- Table values and exports use the same underlying numbers and dates.
- A stock accepted in multiple themes exports separately for each company-theme pair where theme sections are supported.
- The core HTML remains usable offline and makes no automatic external request.
- A failed generation leaves the previous valid HTML and exports untouched.

## 12. Implementation order

Implement in this sequence:

1. Refactor the data model so ETF-level metrics do not depend on curated stock membership.
2. Add S&P 500 and Nasdaq-100 constituent collection and index breadth.
3. Add complete anchor-ETF holdings breadth.
4. Add excess-return percentiles and the three documented theme scores.
5. Add the four exhaustive theme states.
6. Update Market and Themes UI.
7. Revise company-theme membership so non-anchor companies can be accepted as `Core` or `Related`.
8. Preserve and adapt the existing 15-default/20-expanded stock-selection logic.
9. Update exports, diagnostics, run reports, and offline failure behavior.
10. Run deterministic calculation, UI, export, and failure-preservation tests.

Do not start by adding more indicators, agents, themes, or entry rules.

## 13. Required implementation report

After implementation, report:

1. Files changed.
2. Source/generator architecture discovered.
3. Data sources used for index constituents, ETF holdings, adjusted prices, and market capitalization.
4. Which registry themes were successfully generated.
5. Themes with unavailable breadth or score and exact reasons.
6. Formula tests and UI tests run with results.
7. Whether refresh-failure preservation was tested.
8. Known limitations and any decisions that still require user approval.

Do not claim that the score predicts returns or improves profitability without prospective evidence. Its approved purpose is consistent ranking and prioritization for manual swing-trading review.
