# ThemeScope focused scanning release — 3 November 2026 HKT

Baseline: a70ce91fac50f819b79f6abca9712aa1471b68ea. Existing unrelated dirty and untracked work is preserved. The latest supplied CSV fixture still describes US session **2026-10-30**; this release does not claim newer market data.

## Source changes

- `config/watchlist_exports.json`: versioned stable group assignments and the 1,000-instrument limit.
- `src/themescope/daily_lists.py`: canonical group manifests, stock-only deduplication, guarded Primary union, per-anchor RS browsing metadata and expected-earnings window.
- `src/themescope/manual_csv.py`: attaches derived lists; retains the existing five input roles. Market Cap header remains required, while blank/invalid/non-positive cap values display N/A; invalid values are recorded as input warnings. No membership filtering uses those values.
- `scripts/generate_dashboard.py`: writes all bounded files, split-Primary ZIP when needed, canonical Primary data and Market Cap/RS CSV fields. Replaced owned export parts are retired through the existing publication backup/rollback transaction.
- `static/dashboard.js`, `static/dashboard_template.html`, `static/dashboard.css`: Daily Plan candidate view and earnings section, Performance/Relative Strength views, Market Cap, context selectors, scoped filters/sorting and shared width/spacing tokens.
- `README.md`: documents the four input/export roles. Regression and integration checks added/updated in `tests/test_daily_lists.py`, `tests/test_manual_csv.py`, `tests/test_dashboard.js`, `tests/browser_check_scanning.py`, `tests/browser_check_manual.py` and `tests/check_scanning_exports.py`.
- Updated private download bundle. Raw CSV uploads are not committed.

## Group assignments and files

Every active theme is assigned exactly once. Assignments are explicit configuration, independent of daily Performance, State and Priority. Each section retains its name/anchor heading, anchor first and configured stock order. Counts include repeated stock occurrences and anchors, excluding headings.

| Group | Sections | Instruments | File |
|---|---:|---:|---|
| Core Sectors | 11 | 231 | tradingview_group_core-sectors.txt |
| Technology & Growth | 10 | 188 | tradingview_group_technology-growth.txt |
| Consumer & Financial | 7 | 128 | tradingview_group_consumer-financial.txt |
| Healthcare & Industries | 10 | 196 | tradingview_group_healthcare-industries.txt |
| Energy & Resources | 15 | 211 | tradingview_group_energy-resources.txt |

- **Core Sectors**: Communication Services, Consumer Discretionary, Consumer Staples, Energy, Financials, Health Care, Industrials, Information Technology, Materials, Real Estate, Utilities.
- **Technology & Growth**: Semiconductors, Software, Cloud Computing, Cybersecurity, Internet, Artificial Intelligence & Big Data, Robotics & Automation, Quantum Computing, Blockchain & Digital-Asset Companies, Autonomous & Electric Vehicles.
- **Consumer & Financial**: Regional Banks, Insurance, Broker-Dealers & Capital Markets, Homebuilders, Retail, Residential Real Estate, Mortgage REITs.
- **Healthcare & Industries**: Biotechnology, Pharmaceuticals, Medical Devices, Healthcare Providers, Genomics, Aerospace & Defense, Space Economy, US Infrastructure, Transportation, Airlines.
- **Energy & Resources**: Agribusiness, Oil & Gas Exploration & Production, Oil Services, Midstream & MLP Infrastructure, Natural Gas Companies, Clean Energy, Solar, Uranium Miners, Nuclear Energy, Lithium & Battery Technology, Copper Miners, Rare Earth & Strategic Materials, Gold Miners, Silver Miners, Diversified Metals & Mining.

Normal groups are all well below 1,000. Splits occur only at complete theme boundaries with deterministic numbered filenames. A section larger than the limit fails precisely rather than dropping symbols. Synthetic tests prove 50 sections × 21 instruments split into 987 and 63 occurrences; stock-only 1,001 identities split into 1,000 and 1. A temporary run of the real writer with a lower test limit verifies split files and complete Primary ZIP contents without changing real configuration/history.

The current bundle contains **9 top-level TXT files**: five navigation groups, `tradingview_configured_stocks.txt` (**563** unique stock identities), `tradingview_primary_stocks_2026-10-30.txt` (**187**), the optional legacy all-theme file (954 occurrences), and the existing ETF list (56). The optional individual archive retains all 53 theme TXT files. Canonical and individual data preserve every overlapping membership.

## Distinct roles and missing data

- Candidate screening CSV: optional maintenance/discovery input, never a sixth daily requirement.
- Configured-stock daily CSV: same existing Stock schema; updates all fixed members without screener filtering.
- Grouped thematic TXT: chart navigation.
- Daily Primary TXT: complete deduplicated current Primary stock universe, unaffected by visible UI filters or sorting.

Actual original Stock CSV: 1,535 rows. A second calculation using only the 554 configured stock rows present in that file also succeeds. Both retain all 901 membership rows and report 13 unmatched membership occurrences across nine symbols: AG, AYA, CDE, HL, IRDM, NHI, PLMR, SKWD and VC. Missing daily rows do not remove or refill memberships.

## Primary candidates, RS and Market Cap

Final canonical category `primary`, after the existing EMA50 guard, determines inclusion. The actual union is **187 unique stocks**, including six without daily data. Every qualifying Primary theme/anchor tag is retained. Theme tags open their Watchlist; an explicit selector chooses the anchor context for each overlapping stock. No averaging, entry qualification or additional scoring is introduced.

Performance view has 15 columns with Market Cap immediately after 1D. Relative Strength has 11 compact columns with selected ETF, Stock/ETF 1M and 3M Performance, the two percentage-point differences, EMA context and expected earnings. Separate sort state, selected theme, search and RS filter persist through view changes and browser navigation. Outperforming means both differences >0; Underperforming means both <0; equality and other valid combinations are Mixed. Missing is separate and retained under All. No 1W exclusion is applied.

RS reuses the existing canonical matching-horizon stock-minus-anchor calculation. Percentage-point conversion happens once in canonical browsing metadata. The actual export check independently compares every generated difference to 100 × (stock fraction − anchor fraction); the browser checks an overlapping stock under a different anchor and verifies its displayed result. CSV exports include Market Cap, selected anchor context and RS fields where applicable.

Market Cap comes only from the Stock CSV, with raw numeric sorting and compact M/B/T display. **181 of 187** Primary candidates have Market Cap; the other six show N/A. No ETF AUM fallback or external request is used.

## Expected earnings

The inclusive session-based window is **2026-10-30 through 2026-11-06**. There are **61** unique Primary stocks with supplied expected dates in that window, **6** unavailable dates, and **120** dates beyond it. No same-day event occurs in this real fixture. Synthetic tests cover same-day `Today; timing unverified`, weekends, year/month boundaries, missing/invalid dates and past-only dates. Missing does not mean no event. Dates remain expected and require verification; no timing, catalyst score or trading prohibition is invented.

The section is collapsed by default and bounded when expanded. Unknown/past-only dates are listed separately. Neither the computer clock nor a new external source determines the window.

## Verification and integrity

- Full Python suite: **156 tests passed**. The 20 focused parser/list tests passed again after final backend adjustments. Node helper tests, JavaScript syntax, Python compilation and diff whitespace checks pass.
- Real five-file production command: `python scripts/generate_dashboard.py --source tradingview-csv --as-of 2026-10-30 --stock-csv <supplied Stock> --etf-csv <supplied ETF> --spy-csv <supplied SPY> --qqq-csv <supplied QQQ> --iwm-csv <supplied IWM> --output-dir output/manual_csv`.
- Actual measured generator runtime: **0.475830 seconds**, separate from browser tests. Network-forbidden calculation passed. Invalid-file/header/symbol/number/anchor/session cases preserved seeded successful output; low Breadth coverage remained unavailable according to existing rules.
- `python tests/check_scanning_exports.py output/manual_csv`: all manifest counts, group section boundaries, anchor-first ordering, exact memberships, configured-stock and Primary deduplication, per-anchor arithmetic and bundle contents agree with canonical data.
- `python tests/check_history_publication.py output/manual_csv/latest_snapshot.json`: first run, synthetic two-session comparison and injected publication-failure rollback pass, including new outputs. Synthetic records stay in temporary storage.
- Previous release comparison: Score, State, canonical rank, final Priority, Market decision (apart from generation timestamp), memberships and rank-history fingerprint are unchanged. The real saved 2026-10-30 history record is byte-identical to the baseline. No fabricated prior session is embedded.
- `python tests/browser_check_scanning.py output/manual_csv/dashboard.html` and the existing manual browser suite pass. New feature checks cover complete Primary download despite search, all theme tags, selected-anchor switching, view/sort retention, Back/Forward, earnings, header/body geometry and no page-level overflow.
- **32 new feature screenshots** inspected in light/dark at 1920×1080, 1536×864, 1366×768 and 390×844, plus the existing 32-screenshot browser regression pass. Performance, Relative Strength and Primary tables fit at supported desktop sizes; header/body boundaries agree within 0.6px. Narrow tables scroll deliberately. Screenshots were inspected directly and through labeled contact sheets. New candidate and earnings containers are bounded, preserving predictable proximity and access to later sections.
- Zero JavaScript errors and zero automatic external requests. Existing shared tooltip, native selector weights, plain full priority labels, subtle row highlighting, fixed-width Type tags, Score/Breadth colors, focus and reduced-motion behavior remain intact. No new document-level listeners are added during rerender.

## Design guidance and limits

The requested third-party [apple-design guidance](https://github.com/emilkowalski/skills/blob/main/skills/apple-design/SKILL.md) was read. Only typography hierarchy, grouping/proximity, predictable navigation, consistent control feedback, readable contrast, focus, reduced motion and concise labels were applied. It is not treated as an official Apple specification. No new motion framework, glass, gesture physics, pointer-down actions or audio/haptics was added.

Actual TradingView account import, section acceptance and repeated-symbol behavior remain **unverified**. The existing validated identifier mapping is reused; no prefixes are guessed. Repeated occurrences are counted conservatively regardless of possible platform deduplication. Local outputs remain private; this fixture run is not newer-session collection, longitudinal evidence, profitability evidence or predictive validation.
