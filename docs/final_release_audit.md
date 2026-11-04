> Historical record. Current setup and audit: [README](../README.md) and [repository audit](repository_audit.md). Bundle paths below refer to retained local files or historical Git commits, not current source downloads.

# ThemeScope final release audit — 31 October 2026 (HKT)

## A. Verdict

Ready with documented limitations for local manual-CSV dashboard use. TradingView platform-import acceptance remains open. Public publication and automated live collection are outside this verdict. Baseline: dc5060364d64fa9a686d5d78efef1d701812dce9, download branch. Existing dirty and untracked earlier work was preserved; this is a bounded production-path review, not proof that every legacy tool is defect-free.

## B. Confirmed findings and fixes

| Severity | Source | Evidence and correction |
|---|---|---|
| High | scripts/generate_dashboard.py, static/dashboard.js | startsWith(NYSE) converted NYSE Arca ETFs to NYSE identifiers. Forty ETF identifiers corrected using instrument-specific public TradingView metadata; ordinary NYSE stocks retain NYSE. |
| High | src/themescope/manual_csv.py | Missing daily rows were omitted before Theme Breadth denominator construction. Missing configured members now remain denominator placeholders. Silver retains denominator 6, including four missing rows. |
| Medium | generator and dashboard exports | Theme exports omitted anchors; browser export depended on visible sorting/filtering. All manual exports now insert the resolved anchor before stable configured stocks. |
| Medium | manual_csv.py | Matching-horizon stock-versus-anchor differences were absent. Canonical per-membership excess_returns now hold stock minus that selected anchor for each matching horizon; CSV helpers convert fractions to percentage points. |
| Medium | approved_rules.py | Mixed/Mixed prices plus missing Breadth produced an inadequate explanation. Unavailable required Breadth is named, with Unclassified consequence. Empty priority groups retain their matrix state rule. |
| Medium | generator template integration | Run report and legacy audit links pointed to absent manual artifacts. Generated report, run_audit.json and theme_stocks.csv now back the links. |
| Low | dashboard.js/CSS | Reinitialization could add duplicate global listeners/tooltip portals. Initialization is idempotent; unused locals and unreachable exchange-guess/omission branches removed. Essential table values enlarged; light State contrast and narrow sticky cells improved. |
| Low | generator audit | Generator recorded browser network count as if measured. It now identifies that measurement as belonging to the separate browser audit. |

## C. Regressions

New test_manual_release_audit.py covers instrument-specific AMEX/NYSE/NASDAQ/CBOE mapping, unknown-identity rejection, explicit punctuation exceptions, chart/export consistency, anchor plus 20 stocks, ETF-only export, configured denominator coverage and missing-Breadth explanation. Node regressions require unresolved exports to throw. Browser checks download the real generated Watchlist TXT and compare every token to canonical configured membership. Existing score, threshold, tooltip, colspan, matrix and failure-preservation tests retained.

## D. Cleanup and retained tools

Removed obsolete manual prefix inference helper, duplicate frontend prefix inference, unused score-weight locals, unused unavailable-cell diagnostics locals. Historical live-provider collectors, SEC/roster tooling, old exporter and optional v5/v6 imports remain because existing CLI/tests still use them; they are not invoked by the manual branch. Their legacy exchange assumptions are not accepted evidence for the current manual release. No dependency was removed merely because manual mode does not use it. No unrelated user changes were discarded.

## E. Production workflow and execution

scripts/generate_dashboard.py --source tradingview-csv selects _run_manual_csv before live preflight. build_release parses/normalizes/validates five explicit roles; computes shared-cohort percentiles, Price States, Breadth, Market, priorities and canonical decision; attaches offline identifiers; _manual_csv_outputs renders reusable templates and writes exports to staging. Final audit/runtime is re-embedded, ZIP assembled, and outputs published with rollback/preservation behavior. No credentials, SEC data, licensed roster fetch or live collector is executed by this path. US session is explicit, not inferred from Hong Kong filenames. Local-only scope, inline assets and connect-src none remain.

Commands run: python -m unittest discover -s tests -p 'test_*.py' (141 passed); python -m compileall -q src scripts tests (passed); node --check static/dashboard.js (passed); node tests/test_dashboard.js (passed); python tests/browser_check_manual.py output/manual_csv/dashboard.html (passed). Ruff is not installed; no lint/type-clean claim is made.

Real command (input files supplied locally):

```sh
python scripts/generate_dashboard.py --source tradingview-csv --as-of 2026-10-30 --stock-csv Daily_Stock_2026-10-31.csv --etf-csv Daily_ETF_2026-10-31.csv --spy-csv SPY_2026-10-31.csv --qqq-csv QQQ_2026-10-31.csv --iwm-csv IWM_2026-10-31.csv --output-dir output/manual_csv
```

The executed command used the corresponding absolute attachment paths. A real build_release run with socket.connect forbidden passed. Independent direct CSV checks recomputed all 53 ascending average-rank percentiles and 60/40 scores and agreed within 1e-10. Ranking, State, strict Price/EMA comparisons, inclusive score/Breadth boundaries and shared valid Breadth sets preserve approved methodology. Calendar-period Performance remains labeled TradingView 1W/1M/3M; no exact-session return claim or five-session Breadth change enters manual outputs.

## F. End-to-end results

Session 2026-10-30. Input rows/unique symbols: Stock 1535/1535, ETF 56/56, SPY 503/503, QQQ 101/101, Russell 1921/1921. All 53 anchors plus SPY/QQQ/IWM present. No silent substitution. 901 configured stock membership rows remain, 888 matched and 13 missing rows (9 unique symbols); membership does not depend on daily turnover or missing CSV rows. Breadth valid for 46/53 themes under minimum-eight and 80% configured coverage. Market Short bias; State counts 21 Leading, 6 Improving, 6 Fading, 20 Lagging. Priority counts 20/5/6/22 reconcile to 53. Runtime 0.391931 seconds for the actual command through generator's measured stages; browser tests are separate. This is one offline fixture run, not live-session or longitudinal reliability evidence.

Missing file/header, duplicate symbol, NaN required number, absent configured anchor and invalid Saturday session were each tested through the real CLI in isolated temporary output. All rejected and preserved a seeded prior successful dashboard/date. Below-80% SPY coverage remained an accepted import with unavailable SPY Breadth and unanimous Bearish price Short bias, as required.

## G. TradingView export audit

Root cause: treating source exchange labels as TradingView namespaces. Evidence reviewed 2026-10-31: each public instrument page's primary resolved_symbol metadata, title and URL. config/tradingview_symbols.json stores all 619 distinct instrument identities and evidence. This number describes static manual identities, not any automated full-roster fetch workload. Zero unresolved mappings in this fixture; future unknowns fail publication explicitly, preserving the prior success.

Corrected identifiers:

```
NYSE:XLC → AMEX:XLC
NYSE:XLY → AMEX:XLY
NYSE:XLP → AMEX:XLP
NYSE:XLE → AMEX:XLE
NYSE:XLF → AMEX:XLF
NYSE:XLV → AMEX:XLV
NYSE:XLI → AMEX:XLI
NYSE:XLK → AMEX:XLK
NYSE:XLB → AMEX:XLB
NYSE:XLRE → AMEX:XLRE
NYSE:XLU → AMEX:XLU
NYSE:FDN → AMEX:FDN
NYSE:BLOK → AMEX:BLOK
NYSE:IDRV → AMEX:IDRV
NYSE:XBI → AMEX:XBI
NYSE:XPH → AMEX:XPH
NYSE:IHI → AMEX:IHI
NYSE:IHF → AMEX:IHF
NYSE:XAR → AMEX:XAR
NYSE:JETS → AMEX:JETS
NYSE:MOO → AMEX:MOO
NYSE:XOP → AMEX:XOP
NYSE:OIH → AMEX:OIH
NYSE:AMLP → AMEX:AMLP
NYSE:FCG → AMEX:FCG
NYSE:TAN → AMEX:TAN
NYSE:URNM → AMEX:URNM
NYSE:NLR → AMEX:NLR
NYSE:LIT → AMEX:LIT
NYSE:COPX → AMEX:COPX
NYSE:REMX → AMEX:REMX
NYSE:GDX → AMEX:GDX
NYSE:SIL → AMEX:SIL
NYSE:KRE → AMEX:KRE
NYSE:KIE → AMEX:KIE
NYSE:IAI → AMEX:IAI
NYSE:XRT → AMEX:XRT
NYSE:REZ → AMEX:REZ
NYSE:SPY → AMEX:SPY
NYSE:IWM → AMEX:IWM
```

NASDAQ and CBOE ETFs are validated individually; ARKG remains CBOE:ARKG. Punctuation exceptions are explicit mapping values, never a global rewrite. Chart links, grouped ETF TXT, grouped theme TXT, individual ZIP/JSON and UI Watchlist TXT use the same attached resolved identifiers.

ETF TXT: 56 instruments. Theme exports: 53 sections/files, 901 stock membership occurrences plus 53 anchors = 954 instrument occurrences. Individual files preserve all cross-theme overlaps, up to 21 instruments. Header token is ###Theme name (ETF), followed by anchor then stable configured stock order. ETF-only behavior is tested synthetically because current themes all have configured members.

Static comma-delimited token/order/ZIP checks pass. TradingView platform import was NOT performed: there is no authorized authenticated platform session available. Section-header acceptance and repeated-symbol behavior across grouped sections are untested; no claim of deduplication or preserved cross-section duplicates is made. Complete membership is retained in canonical JSON and individual files. Instrument metadata verification is separate from account watchlist import. Published import-format reference: https://www.tradingview.com/support/solutions/43000487233-how-to-import-or-export-a-watchlist/ . It does not establish our grouped-section/duplicate behavior.

Smallest remaining platform action: import tradingview_sector_theme_etfs.txt and one TXT from individual_theme_watchlists.zip into a temporary watchlist; verify each exchange/ticker and intended instrument, heading, anchor first and configured stock order. Then import two overlapping grouped sections and record whether duplicates are retained, moved or deduplicated. No credentials should be shared in chat.

## H. Browser and visual checks

Chromium: four pages, Daily Plan links, browser Back/filter/sort restoration, one tooltip portal, focus/touch/Escape/navigation close, reduced motion and real TXT download checks pass. Zero console errors and zero automatic external requests across the tested interactions. 16 screenshots captured; Sectors & Themes screenshots inspected in both modes at 1920x1080, 1536x864, 1366x768 and 390x844. Required desktop sizes fit 14 columns without horizontal scroll; measured header/body x and width differ by less than 0.6px. N/A single-line, row height stable and colorized numeric chips visible. At 1366 some long priority labels wrap to two lines; mobile intentionally scrolls the table. Score header labels ellipsize at the smaller desktop width but keep full accessible sort labels/tooltips. No formal screen-reader or automated WCAG contrast certification is claimed.

## I. Remaining limitations

Actual TradingView import, section syntax and duplicate behavior remain external acceptance checks. Identifier evidence is a dated public-page observation, not a guarantee against future venue/ticker changes. No future live run, public redistribution authorization, or longitudinal screening was performed. Legacy optional paths were retained and not certified as production alternatives. Existing configuration/review, current metric availability, measured offline runtime, local publication checks and post-implementation reliability remain distinct results.
