# ThemeScope v7 run report

Market session: 2026-10-23

Dashboard generated: 2026-10-24T23:28:18+00:00

Workflow: offline import / rerender

## Ranking and state

Current is the percentile rank of 21-session ETF excess return versus SPY. Medium is the 63-session percentile. Theme Score remains `0.60 × Current + 0.40 × Medium`, with the configured 50 state threshold. Theme and index breadth do not affect score, state, or rank.

## Watchlist migration

- Active anchors: 53; inactive registry records: 12.
- Configured lists: 16; active exposures awaiting stock-universe input: 37.
- Configured memberships: 265; unique stocks: 257; overlapping stocks: 8 (8 additional memberships).
- Populated lists: Communication Services (18), Consumer Discretionary (20), Consumer Staples (20), Energy (20), Financials (20), Health Care (20), Industrials (20), Information Technology (20), Materials (20), Real Estate (20), Utilities (20), Semiconductors (13), Cloud Computing (10), Cybersecurity (10), Aerospace & Defense (10), Clean Energy (4).
- Missing lists: Software (theme-software), Internet (theme-internet), Artificial Intelligence & Big Data (theme-artificial-intelligence), Robotics & Automation (theme-robotics-automation), Quantum Computing (theme-quantum-computing), Blockchain & Digital-Asset Companies (theme-blockchain), Autonomous & Electric Vehicles (theme-autonomous-electric-vehicles), Biotechnology (theme-biotechnology), Pharmaceuticals (theme-pharmaceuticals), Medical Devices (theme-medical-devices), Healthcare Providers (theme-healthcare-providers), Genomics (theme-genomics), Space Economy (theme-space), US Infrastructure (theme-us-infrastructure), Transportation (theme-transportation), Airlines (theme-airlines), Agribusiness (theme-agribusiness), Oil & Gas Exploration & Production (theme-oil-gas-exploration), Oil Services (theme-oil-services), Midstream & MLP Infrastructure (theme-midstream), Natural Gas Companies (theme-natural-gas-equities), Solar (theme-solar), Uranium Miners (theme-uranium-miners), Nuclear Energy (theme-nuclear-energy), Lithium & Battery Technology (theme-lithium-batteries), Copper Miners (theme-copper-miners), Rare Earth & Strategic Materials (theme-rare-earths), Gold Miners (theme-gold-miners), Silver Miners (theme-silver-miners), Diversified Metals & Mining (theme-metals-mining), Regional Banks (theme-regional-banks), Insurance (theme-insurance), Broker-Dealers & Capital Markets (theme-capital-markets), Homebuilders (theme-homebuilders), Retail (theme-retail), Residential Real Estate (theme-residential-real-estate), Mortgage REITs (theme-mortgage-reits).
- Missing lists remain explicitly unconfigured until the intended TradingView scanner CSV is supplied and the proposed membership changes are reviewed.

## Cache and requests

- Offline bundle: 2,852 saved price histories reused; no cache fetches were attempted.
- Source requests by category: price histories 0; index universes 0; filings 0; company quotes 0; theme holdings 0; AUM/spread 0.
- A rerender/import uses no network requests. Request totals shown here count actual collector fetches, not cache hits.

## Breadth and limits

- Theme breadth uses the fixed configured list and displays above/valid counts. Validity requires at least 8 observations and at least 80% of configured members. A missing ticker stays in the configured denominator.
- Five-session breadth change uses the same current membership at both dates; it is not a historical point-in-time universe.
- Index breadth remains separate: SPY uses observed S&P 500 constituents, QQQ uses Nasdaq-100, and IWM uses current holdings as a practical Russell 2000 proxy.
- The initial 16 lists are carried forward from the saved v6.2 run. The remaining 37 require scanner input for curation; no companies were invented to fill them.
- No SEC filing retrieval, company research, ETF holdings breadth, AUM, spread, or daily market-cap request is part of normal refresh.

## Files

The run bundle includes the dashboard, compact snapshot and CSVs, configuration, and compressed price sidecars. Run `python3 scripts/generate_dashboard.py --import-run output` to rerender without network access.
