# Workflow and interface verification — 2026-10-22

## Actual retrieved run

- Collected at 2026-10-22T22:04:15+00:00; completed market session 2026-10-22.
- 60 historical series, 204 Nasdaq summaries (including industry-only screening), 47 SEC annual-feed checks; no unrecovered retrieval errors.
- Six ETF themes have numerical return/excess rankings. SPY and QQQ have dated closes, daily changes, 5/21/63-session adjusted returns, split-adjusted close charts, EMA distances and trend context.
- Selected provisional stocks: SMH 13, CIBR 10, ICLN 4, XAR 10, SKYY 9, XBI 0. Total: 46 distinct tickers. Lists are not padded.
- XBI: 157 distinct mapped tickers received industry summaries; 150 biotechnology classifications are excluded under the existing rule. Seven other industries need business-evidence decisions; three identifiers (`-`, `2200963D`, `2200964D`) cannot be mapped to eligible listings. Those ten remain pending. This is not a completed eligible-universe review.

## Diagnosis and alternatives

The user's failed run reported 60 Yahoo HTTP 429 responses and a VanEck fund-page redirect loop. A separate single-request 200 response did not isolate the cause: the client, user agent and requested range differed. Pacing reduces bursts but does not guarantee access on another network.

- Yahoo query1 succeeded for all 60 series in this environment. Chart requests remain sequential with 1.5-second spacing.
- Query2 was separately tested on SPY and four varied anchors: SMH, CIBR, ICLN, XAR. Each anchor returned 501 daily observations and 501 adjusted closes for the two-year range probe, with dividend-event fields. The two hosts use the same Yahoo adjustment convention; this is a host fallback, not an independent data vendor.
- A host receiving HTTP 429 is disabled for the remainder of the process, without immediate retry. Other transient failures have bounded retries. A unit test confirms only two host calls across three symbols when both hosts are rate-limited.
- VanEck's official direct dataset returned dated holdings for SMH. Fund identity and dated/nonempty holdings are checked before parsing. This fallback avoids the failing fund-page discovery step without substituting unofficial holdings.
- Stooq's CSV endpoint returned an HTML browser challenge, not price data. Alpha Vantage's demo request returned an information message, not an adjusted series. Neither was used.
- A dated real run can be explicitly imported with `--import-run`; original collection time and data date are retained. No data is silently substituted during a live run.

## Publication and failure tests

22 Python tests cover existing calculations plus import/publication, empty-run rejection, last-success preservation, rollback on publication failure, preservation of unrelated files, misaligned metrics, and source fallbacks. Node checks cover filtering, stable full-universe ranks, ties, missing-last sorting in both directions, fixed selection pools and exports.

Before publication, core prices and returns are checked against the underlying retrieved observations and common session; excess returns must agree with SPY differences. No recovered fields from an old run are mixed into a new live snapshot. Files are staged; the HTML is replaced last. A failed refresh writes separate `refresh_status.json` and `failed_refresh.md`, returns exit code 1 and preserves the last successful files/date. An invalid preexisting HTML is archived as `rejected_dashboard.html` instead of being called successful.

## Browser and network checks

Actual Chromium checks exercised both sort directions, theme selection, search, trend/relative filters, 15/20/all-reviewed pools, CSV/TXT and complete run ZIP downloads, verified TradingView URL construction, dark/light mode and persistence after reload. A failed embedded snapshot rendered a concise cause and no ranked tables or Loading placeholders. No JavaScript exceptions occurred.

Chromium DevTools Protocol `Network.requestWillBeSent` (the Network panel's backend) recorded **zero automatic external requests** on opening/reloading the exported document, including after interactions. Opening and reloading requested only the HTML document itself; the explicit ZIP download additionally requested its local archive. The export embeds its JSON, CSS, JS and SVG charts; `connect-src 'none'` also prevents runtime data requests.

Environment limitation: managed Chromium blocks `file://` URLs by administrator policy. The exact exported bytes were therefore served over loopback for browser verification. Direct file-scheme opening was not verified here; it needs no application server in a normal desktop browser. No claim is made of manual inspection of the graphical DevTools panel. See `browser_network_verification.json` for the captured event summary.

## Remaining coverage limits

Business-evidence membership reviews remain incomplete across all six themes. The all-reviewed view is explicitly a subset, not a full eligible universe. Nasdaq does not publish the market-cap field timestamp; cap eligibility is provisional. Annual SEC freshness checks do not classify all subsequent material disclosures. Those limits are preserved in the diagnostic exports and contextual warning. Current data access succeeded here; access from the user's Windows network remains unverified.

The checked-in demonstration is a deliberate delivery snapshot. Normal user runs write only to their ignored local `output/` folder and never commit or push anything.
