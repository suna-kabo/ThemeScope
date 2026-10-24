# ThemeScope v6.2 corrections

## Current generated run

The [dashboard](../output/dashboard.html), [run report](../output/latest_run.md), and [registry audit](../output/registry_audit.csv) were regenerated on 24 October 2026 from an explicitly imported real-data run dated 23 October 2026. This refresh recalculates the full eligible registry from the imported source histories; it did not perform a new live market-data collection.

The run publishes 53 of 65 exposures. All 53 have a valid Theme Score, state, and current rank; 16 have curated stock drilldowns with 265 selected stocks, while 37 are ETF-only. Breadth is unavailable for 37 exposures and does not affect their price-based scores. Twelve records are inactive for specific current eligibility failures; none is inactive because its mandate review is pending.

The generated dashboard is 3,142,423 bytes, `raw_inputs.json` is 98,267,830 bytes, and the run bundle is 22,740,877 bytes. Each stays below its configured limit of 20,000,000, 99,000,000, and 95,000,000 bytes, respectively.

## Corrections delivered

- Current and five-session-prior rankings use the same deterministic average-rank method for ties. Unavailable scores sort after valid scores and have no numeric rank. Rank change remains prior rank minus current rank.
- Python and browser CSV exports use percentage-valued `return5_pct`, `return21_pct`, and `return63_pct` fields, plus percentage-point `excess*_pp` fields. Ambiguous decimal return columns and duplicate period aliases were removed from user-facing exports.
- All 112 configured candidate ETFs have dated, candidate-specific review outcomes: 109 compatible long-only equity exposures and three rejected products. MSOS uses total-return swaps for core exposure; URA permits physical-uranium investment trusts; VPN has no verifiable current listing or issuer mandate. Rejected candidates remain auditable and cannot be selected.
- Candidate selection now materializes price metrics for every runtime-selected anchor before calculating relative-strength percentiles. This also covers themes that switch to an eligible alternate candidate when an older imported run contains only its previous anchor.
- The $10 million ADV30 floor is retained. The latest run identifies 33 otherwise-eligible candidate ETFs that fail only this floor; low-liquidity candidates are not activated to increase coverage.
- XBI and ICLN regression tests protect ETF-only scoring and scoring with unavailable breadth.
- The selected-theme heading omits “Watchlist ·”. Back, Previous, and Next are text-only controls with their existing IDs and accessible labels. The full run ZIP is available from the always-visible dashboard footer, including when an ETF-only theme is selected.
- The dashboard embeds a smaller UI projection. Raw input, dashboard, and run-bundle sizes have configurable pre-publication limits. The IWM compressed sidecar and staged rollback remain in place.
- Generated runs are ignored instead of tracked. Historical JSON samples are under `tests/fixtures/v1/`, and old reports are in versioned archive folders.
- Added pinned Playwright development requirements, an output consistency validator, and CI for Python tests, JavaScript checks, dashboard generation, browser interactions, and offline-network behavior.

## Verification

- `python3 -m unittest discover -s tests -v`: 63 tests passed.
- `python3 -m compileall -q src scripts tests`, `node --check static/dashboard.js`, `node tests/test_dashboard.js`, and `git diff --check` passed.
- `python3 tests/validate_output.py output` passed for the generated 53-exposure run and 112 candidate audit rows.
- Chromium 154 passed browser interactions on the generated dashboard. Opening and reloading made zero external requests; JavaScript errors were zero. The check covered theme search and sorting, navigation, CSV and ZIP downloads, light/dark mode, text-only controls, and mobile visibility.

## Remaining limits

The last market session in this generated run is 23 October 2026; the run is an imported dated data bundle, not a same-day live refresh. The VPN candidate remains rejected until a current product listing and issuer mandate can be verified. ETF AUM and historical bid/ask spread sources are not configured, so ADV30 is the current liquidity screen. Yahoo adjusted-price conventions are provider-defined, current holdings are not historical point-in-time constituents, and sector stock drilldowns cover the sourced S&P 500/ETF-holdings intersection rather than every listed company in each sector. Windows Chrome rendering was not tested.
