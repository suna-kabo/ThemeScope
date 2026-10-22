# ThemeScope v5 implementation report

Data session: **2026-10-22**. The delivered export was regenerated offline from the complete freshly retrieved inputs, retaining their original data date and collection timestamps.

## Architecture and changes
The existing project uses Python standard-library source adapters, a core collection/eligibility module, pure calculation functions, a static template/JavaScript UI, and a generator that stages and validates local exports. No database or backend was added.

- Added `src/themescope/v5.py`: index universes, issuer mapping, independent holdings breadth, percentiles, scores and states.
- Updated `src/themescope/collect.py`, `presentation.py`, and `sources.py`: non-anchor membership, Core/Related metadata, explicit optional filing review, excluded-row diagnostics, core validation and bulk constituent retrieval.
- Updated `scripts/generate_dashboard.py`: v5 enrichment, market/theme CSVs, per-field statuses, ZIP imports, reporting and existing failure rollback.
- Updated `static/dashboard.js`, `.css`, and `_template.html`: market participation/conditions, level filters, approved score columns, raw metric sorting, coverage warnings, stock EMA facts and 3M excess.
- Updated `config/themes.json` and `config/evidence_reviews.json`; preserved six anchors and the selection queues. Existing supported principal-business classifications are Core; unsupported memberships were not manufactured.
- Added v5 formula/membership tests and expanded browser/export/failure checks. README and the supplied brief in `docs/` document operation.
- Current deliverables are in `dist/`, `exports/` and `reports/`. `data/` remains a labeled compact v4 regression fixture; v5 raw inputs are in the downloadable run ZIP.

## Actual sources
- S&P 500: reproducible current Wikipedia constituent table with retained rows and SHA-256 response hash; CIKs verify company deduplication. Date is observation at retrieval, not an official effective date.
- Nasdaq-100: official Nasdaq dated constituent list endpoint.
- Security mapping: SEC company_tickers_exchange.json; no guessed foreign ticker substitutions.
- ETF holdings: official VanEck, First Trust, iShares and State Street adapters. A separate same-date audit verified the equity rows and retained non-equity exclusions.
- Price histories: Yahoo daily chart endpoint, identical adjustment convention across both hosts; 60 core plus 727 additional unique histories retrieved, zero reported request errors. This controlled live probe used 0.5-second breadth spacing with circuit breakers; the user default remains 1.5 seconds.
- Market capitalization/industry/exchange: Nasdaq summaries; field timestamp for capitalization remains unavailable.
- Membership sources: recorded issuer/filing evidence and inclusion rationale; annual filings are mandatory only for explicitly ambiguous records. No agent roles are exposed.

## Market breadth
| Context | Eligible companies | EMA21 above/valid | EMA50 above/valid | Conditions |
|---|---:|---:|---:|---|
| SPY | 500 | 355/499 | 320/497 | Internal strength, index below EMA21; Internal strength, index below EMA50 |
| QQQ | 100 | 47/100 | 51/98 | Broad short-term weakness; Internal strength, index below EMA50 |

## Registry results
| Anchor | Level | EMA21 above/valid; eligible | EMA50 above/valid | Watchlist |
|---|---|---|---|---:|
| SMH | Industry | 0/23; 25 | 1/23 | 13 |
| CIBR | Theme | 21/41; 45 | 30/41 | 10 |
| ICLN | Theme | 2/14; 103 | 1/14 | 4 |
| XAR | Industry | 14/50; 50 | 8/46 | 10 |
| SKYY | Theme | 39/65; 65 | 45/65 | 10 |
| XBI | Industry | 56/157; 157 | 38/153 | 0 |

All six ETF return series were successfully generated. Both index breadth measures and both breadth measures for SMH/CIBR/XAR/SKYY/XBI satisfy the freshness, eight-company and 80% rules.

**ICLN breadth is unavailable for scoring:** 14/103 valid companies = 13.5922% price coverage. 89 equity rows have no verified foreign listing mapping in the current SEC-based adapter. Its observed fractions (2/14 above EMA21; 1/14 above EMA50) are displayed only with a warning. 34 cash/derivative/non-equity rows are excluded, not counted as missing equities.

**All six CurrentStrength, MediumStrength and ThemeScore values are unavailable:** six valid primary ETF peers are below the required ten. The exact percentile/tie/weight/state implementation is present and passes hand-calculated fixtures, including a full 11-peer fixture producing 74 Current, 49 Medium and 64 ThemeScore. No registry padding, missing-input imputation or reweighting was used.

XBI remains ETF-only but has valid holdings breadth across 157 eligible companies; curated biotechnology exclusions do not contaminate ETF breadth. Total stock selections are 47 across the five other themes. NET can enter under the supported Core classification because v5 no longer makes every obvious classification depend on an annual-filing freshness gate.

## Validation
- 34 Python tests passed: original return/session/split/liquidity rules; percentile endpoints, exact ties and minimum peers; approved formulas and excluded inputs; exhaustive theme/market states; equality rules; zero denominators; 8/10 versus 8/11 coverage; missing-price handling; verified share-class deduplication; non-anchor Related membership with no ETF weight; source requirements; import/CSV consistency; ETF-only validity; transport-failure abort versus explicitly missing symbols.
- Node checks passed: numeric sorting both directions, stable ID ties, missing scores last/no rank, fixed 15/20 nested pools, filters and export fields.
- Real Chromium checks passed: score default, raw-excess sorting, level/EMA filters, theme selection, 15/20/all-accepted controls, CSV/TXT/complete ZIP downloads, dark/light persistence, failed-snapshot state and zero JavaScript errors.
- Network instrumentation recorded zero automatic external requests on opening/reloading. Managed Chromium disallows file://, so exact exported bytes were served over loopback. This verifies the browser Network backend, not a manual graphical panel inspection.
- Refresh-failure preservation was tested: prior files/date preserved byte-for-byte, publication failure rollback, unrelated files retained, missing mandatory holdings rejected, invalid prior HTML not treated as a success.

## Remaining limits and decisions
- To obtain live scores, the primary registry needs at least ten deliberately selected, suitable ETFs. Expanding the economic coverage is a separate registry decision; no extra ETFs were added merely to force scores to appear.
- Improving ICLN participation requires verified foreign exchange/listing and company/share-class mappings. Unresolved equities remain in the coverage denominator; unknown company identities are not guessed.
- Wikipedia membership has observation-time provenance, not a historical effective-date guarantee. SEC issuer IDs identify companies, and deterministic primary share classes represent participation; unresolved mappings are disclosed separately.
- Scores are approved prioritization conventions, not demonstrated predictions, profitable strategies or entry instructions.
- Source availability on the user’s Windows network is unverified. The bundled dated real-data import is available if live access fails.
- No approval is needed to use the implemented features. No license, public visibility, extra indicators, execution rules or additional primary ETF exposures were introduced.
