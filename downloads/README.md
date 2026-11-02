# Current downloads

- [Latest complete ThemeScope bundle — US session 2 November 2026](ThemeScope_manual_csv_session_2026-11-02.zip): refreshed from the five supplied 3 November Hong Kong exports. Extract everything and open `dashboard.html`, retaining sibling files and `individual_watchlists/`.
- [All individual research watchlists](ThemeScope_individual_watchlists.zip): 53 ETF-first TXT files. Their contents are unchanged; no daily reimport is required.

The current run has all 53 anchors, 46/53 valid theme Breadth readings, and rank changes against the real 30 October session. Eleven configured stocks are absent from the Stock CSV; memberships remain intact. Read `REFRESH_AUDIT.md` and `run_audit.json` inside the ZIP, or `docs/refresh_2026-11-02.md`.

Both actual `local_history/2026-10-30.json` and `local_history/2026-11-02.json` are included. Preserve that folder for future runs. Daily data collection still uses **Daily Data Stocks — export CSV only** and the existing five-CSV command.

Actual TradingView import is not tested here. Managed Chromium blocks direct file:// testing; local HTTP tests pass. If needed, run `python -m http.server 8000` from the extracted folder and open `http://localhost:8000/dashboard.html`.

Latest bundle: 1,786,148 bytes. SHA-256 `dc7d7a33a83cdf48090110672c08500e5a20378457c7c7b829b73eb0a87fe0b7`.

Previous dated bundles are retained: [30 October 2026](ThemeScope_manual_csv_session_2026-10-30.zip) and the older v7.1 artifact. They are historical outputs.
