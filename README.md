# ThemeScope (WIP)

ThemeScope is an on-demand, end-of-day US equity sector and theme dashboard. It presents SPY, QQQ and IWM market context, ranks eligible ETF exposures by price-relative strength, and offers optional sourced stock drilldowns. It does not produce entries, trade recommendations, sizing, allocations, orders, or predictive claims.

## Generate a dashboard

Use Python 3.10 or newer. The regular pipeline uses only the Python standard library.

For an offline run from the versioned real-data fixture:

```sh
python3 scripts/generate_dashboard.py --import-run tests/fixtures/v1 --output-dir output
```

For a current source refresh, provide the configured network access and run:

```sh
python3 scripts/generate_dashboard.py --output-dir output
```

The command prints `SUCCESS` only after validating and publishing a dated run. It stages output and preserves the last successful dashboard if a refresh fails. Open `output/dashboard.html` locally; it embeds its required page assets and data and makes no automatic external requests. The complete run ZIP retains source inputs, histories, audits, and diagnostics that are excluded from the smaller dashboard payload.

The default artifact limits are 99,000,000 bytes for `raw_inputs.json`, 20,000,000 bytes for `dashboard.html`, and 95,000,000 bytes for `run_bundle.zip`. They are configurable in `config/themes.json`. Oversized output fails before publication with the artifact size and next step. IWM price histories stay in the compressed sidecar.

## Development checks

Run the required Python and JavaScript checks:

```sh
python3 -m unittest discover -s tests -v
python3 -m compileall -q src scripts tests
node --check static/dashboard.js
node tests/test_dashboard.js
```

The browser verification is optional for normal generation. Install its pinned development dependency and Chromium with:

```sh
python3 -m pip install -r requirements-dev.txt
python3 -m playwright install chromium
python3 scripts/generate_dashboard.py --import-run tests/fixtures/v1 --output-dir output
python3 tests/validate_output.py output
python3 tests/browser_check.py output/dashboard.html
```

CI runs the unit, syntax, export, generated-output, interaction, and offline-network checks. Browser checks need Chromium; generation does not need Playwright.

## Ranking and eligibility

The fixed score methodology is Current = 21-session ETF excess-return percentile versus SPY; Medium = 63-session ETF excess-return percentile; Theme Score = `0.60 × Current + 0.40 × Medium`. The four states compare Current and Medium with the configured 50 threshold. Breadth and stock availability do not affect score, state, or ETF eligibility. Themes remain ETF-only when no stock list qualifies, and invalid holdings breadth stays separate from price-based ranking.

Equal valid scores receive descending average ranks in both the current run and the five-session-prior recalculation. Rank change is `rank_t_minus_5 - rank_current`. Unavailable scores sort last and have no numeric rank. Display order inside a tie remains stable by registry ID.

The registry contains 65 exposures and 112 candidate ETFs. All candidates have a dated, candidate-specific issuer or filing review: 109 are compatible long-only equity exposures and three are explicitly rejected. MSOS uses total-return swaps for core exposure, URA permits physical-uranium trusts, and VPN has no verifiable current listing or issuer mandate. Rejected candidates remain in the audit but cannot be selected. Every selected anchor must also have a verified USD ETF instrument type, at least the configured minimum price history, and sufficient ADV30. Holdings adapters and breadth are not eligibility requirements.

The $10 million ADV30 floor is retained. Each generated report counts candidates that otherwise pass but fail only that floor; low-liquidity ETFs are not activated to increase coverage. Each of the 65 registry records ends as a selected anchor or an inactive record with its current specific eligibility failure. Use the generated registry audit to distinguish candidates blocked by price history, instrument metadata, liquidity, or an explicit mandate rejection.

## Exports and limitations

All user-facing CSV returns are percentage values named `return5_pct`, `return21_pct`, and `return63_pct`. Excess returns and breadth changes are percentage points named `excess*_pp` and `breadth*_change_5_pp`. Internal calculations retain decimal returns. Blank CSV cells mean unavailable.

ETF AUM and historical bid/ask spread sources are not configured. Yahoo adjusted prices are provider-defined. Holdings and index universes are current source snapshots, not historical point-in-time constituents. Nasdaq market-cap data lacks its own observation timestamp, so stock market-cap eligibility remains provisional. Sector stock drilldowns intersect the current S&P 500 sector classification with official sector ETF holdings; they do not represent every listed company in the sector.

Generated runs belong in ignored `output/` or `dist/` directories. They are not committed with source. Versioned historical input samples belong under `tests/fixtures/<schema-version>/`; production commands never read fixtures implicitly.

## Project files

- `config/themes.json`: exposure registry, candidate-specific mandate review state, eligibility settings, and score configuration.
- `config/sources.json`: price, holdings, universe, quote, and filing sources.
- `src/themescope/v5.py`: collection, score/state, breadth, and historical-rank calculations.
- `src/themescope/v6.py`: candidate eligibility, mandate audit, and registry selection.
- `src/themescope/ranking.py`: shared deterministic average-rank calculation.
- `scripts/generate_dashboard.py`: validation, exports, offline UI payload, size checks, staged publication, and rollback.
- `static/`: self-contained dashboard template, styles, JavaScript, and font.
- `tests/fixtures/`: versioned historical input fixtures.
