# ThemeScope v6.2 implementation report

## Delivered files

The reusable changes are in `src/themescope/v5.py`, `src/themescope/v6.py`, `src/themescope/presentation.py`, `src/themescope/cache.py`, `scripts/generate_dashboard.py`, `config/themes.json`, `static/dashboard_template.html`, `static/dashboard.css`, and `static/dashboard.js`. Tests were added or updated in `tests/test_v62.py`, `tests/test_v5.py`, `tests/test_v6.py`, `tests/test_presentation_v61.py`, `tests/test_dashboard.js`, and `tests/browser_check.py`.

The generated deliverables are in `dist/`: self-contained dashboard HTML, dated JSON snapshot and source inputs, compressed IWM price sidecar, market/theme/watchlist CSVs, source and registry audits, TradingView symbol lists, font license, run report, and complete run ZIP. `reports/latest_run.md` and `reports/browser_network_verification.json` provide readable run and browser records.

## Typography and interface

The dashboard embeds the Inter Variable WOFF2 from [the Inter project](https://github.com/rsms/inter), under the SIL Open Font License 1.1 copied to `static/Inter-LICENSE.txt` and `dist/Inter-LICENSE.txt`. The generator inserts the font as a data URL; the content security policy permits that embedded font source with `font-src data:`. Chromium confirmed the font loads without a network request. Windows Chrome itself was not available in this Linux environment, so Windows-specific rendering remains unverified.

Market cards now separate market/holdings breadth from index/ETF price versus EMA trend, identify constituents or holdings explicitly, and show price-to-EMA distance only in the trend section. The UI retains the three left navigation pages, internal Back history, searchable Sector/Theme selector, Previous/Next controls, and compact sort utilities. Dark and light modes use flatter surfaces, short labels, consistent controls, and configured score chips.

Score bands use configured thresholds: 0–<25 muted red, 25–<50 muted amber, 50–<75 muted blue, 75–100 muted green, and unavailable neutral gray. Classes use the unrounded value; state remains based on Current and Medium relative to 50. Score text/background contrast was calculated at 5.58:1 or higher in both themes. No gradients, glow, or card stripes remain.

The default UI no longer includes the brief's filler sentences or a redundant Watchlist back button. Technical collection errors and coverage reasons live in the run report, source matrix, snapshot, and diagnostics. The top bar shows the snapshot's actual market date and generation time.

## IWM data collection and current result

The v6.1 pipeline did not put the IWM holdings ticker set into the price-download universe and required SEC listing matches for many IWM price symbols. That left about 180 valid EMA21 observations out of 1,964 holdings. v6.2 now classifies the issuer's official equity rows, normalizes direct iShares tickers, uses SEC CIKs for verification and deduplication where available, and downloads one year of history for the resulting symbols. The 80% breadth threshold is unchanged.

For the 23 Oct 2026 snapshot: iShares supplied 1,986 rows; 1,980 were labeled Equity; 11 descriptions identified non-common/contingent securities; 2 tickers could not be normalized; 19 rows were excluded in total. The remaining 1,967 equity rows mapped to 1,957 company records and 1,967 symbols. SEC matched 1,949 companies; 8 used direct issuer tickers.

Of 1,792 new chart requests, 1,788 returned Yahoo histories; 175 histories already retrieved elsewhere in the run were reused. There are 1,963 retained histories: 1,910 met the 205-session warm-up and 53 were shorter. Yahoo returned HTTP 404 for ADRO, PDLI, SBT, and THRD. EMA21 has 1,943/1,957 valid company observations (99.3%); 925 are above EMA21, for 47.6% breadth and a +18.0 percentage-point five-session change. EMA50 has 1,899/1,957 valid observations (97.0%); 775 are above EMA50, for 40.8% breadth and a +12.5 pp change. Both periods pass the configured completeness rule.

The IWM collection took about 25 minutes including the configured index constituent work. Keep the conservative Yahoo pacing; HTTP 429 opens a run-local circuit. The four 404s and the 53 shorter histories remain visible in diagnostics rather than being filled or treated as complete-year histories.

## Context calculations

The score method is still Current = 21-session ETF excess-return percentile versus SPY; Medium = 63-session ETF excess-return percentile; Theme Score = `0.60 × Current + 0.40 × Medium`. Breadth does not enter any score or state. The rank-change formula is `RankAtTMinus5 - CurrentRank`; the earlier rank recomputes the 21/63-session excess returns and cross-sectional percentiles over the same runtime-eligible peers, with average ties. All 17 eligible ETF anchors have valid historical ranks in this run.

Breadth change is `Breadth(t) - Breadth(t-5)` in percentage points, using the same current holdings universe at each date; if either observation fails the independent completeness rule the change stays unavailable. Tests cover unavailable inputs and changes. The selected-theme sparkline is the 63-session series of ETF adjusted close divided by SPY adjusted close; it is descriptive and does not produce a signal.

The generated VIX snapshot is level 19.45, +2.21% for the day, -2.70% over five sessions, +24.12% over 21 sessions, and at the 78.0th percentile of 252 sessions. Its text correctly says volatility direction is mixed across the periods. VIX is outside Theme Score and state.

## Verification and limitations

- `python -m unittest discover -s tests -v`: 55 tests passed, including refresh failure preservation, metric acceptance, IWM normalization/sidecar, historical rank ties, breadth changes, and score-band boundaries.
- `node --check static/dashboard.js`, `node tests/test_dashboard.js`, Python compilation checks, and `git diff --check` passed.
- Chromium 154 on Linux checked the generated HTML in dark and light modes, navigation, sorting, watchlist selection, CSV/TradingView downloads, ZIP contents, and failure display. Opening/reloading made zero external requests; the embedded WOFF2 loaded. Browser JavaScript errors: zero. Windows Chrome was unavailable for direct verification.
- Current additional source failures: four unavailable IWM charts above; one VPN chart returned Yahoo HTTP 404; 15 Nasdaq quote summaries were unavailable. These details remain in `dist/latest_run.md`, `dist/source_matrix.csv`, the raw input diagnostics, and the registry audit. The 17 eligible primary anchors and IWM breadth metrics remain populated.

These ranks, score colours, breadth changes, and ratio sparkline are descriptive tools for manual review. They are not predictions, trade signals, or allocation advice.

> Archive notice: this report predates the current ranking, export, registry-audit, and UI corrections. Its UI, formulas, counts, and page structure are historical and are not current ThemeScope behavior.
