# ThemeScope v7 availability

Market session: 23 October 2026. The dashboard contains all 53 active anchor ETFs and 12 inactive registry entries remain inactive. ETF returns, Theme Score, state, and rank do not depend on stock-list availability.

| Data | Available | Explanation |
| --- | ---: | --- |
| SPY, QQQ, IWM index breadth | 3/3 | EMA21 and EMA50 breadth are valid. IWM holdings are a practical Russell 2000 proxy. |
| Theme-watchlist breadth, EMA21 | 15/53 | Fifteen lists meet the sample and 80% completeness rules. |
| Theme-watchlist breadth, EMA50 | 15/53 | Same configured members and completeness rule. |
| Configured theme watchlists | 16/53 | 265 memberships, 257 unique stocks, 8 overlapping tickers. |

Thirty-seven active exposures have no watchlist and report “Theme watchlist not configured.” Their anchors still appear in the theme table with their price-based scores and ranks. Clean Energy (ICLN) is configured with four stocks, but breadth is unavailable because fewer than eight members have valid histories. The other 15 configured lists currently pass the breadth validity rule.

## Awaiting stock-universe input

The following 37 active exposures remain explicitly unconfigured. They were not filled with guessed companies because no TradingView scanner CSV or intended stock universe was included in the supplied inputs.

- Software
- Internet
- Artificial Intelligence & Big Data
- Robotics & Automation
- Quantum Computing
- Blockchain & Digital-Asset Companies
- Autonomous & Electric Vehicles
- Biotechnology
- Pharmaceuticals
- Medical Devices
- Healthcare Providers
- Genomics
- Space Economy
- US Infrastructure
- Transportation
- Airlines
- Agribusiness
- Oil & Gas Exploration & Production
- Oil Services
- Midstream & MLP Infrastructure
- Natural Gas Companies
- Solar
- Uranium Miners
- Nuclear Energy
- Lithium & Battery Technology
- Copper Miners
- Rare Earth & Strategic Materials
- Gold Miners
- Silver Miners
- Diversified Metals & Mining
- Regional Banks
- Insurance
- Broker-Dealers & Capital Markets
- Homebuilders
- Retail
- Residential Real Estate
- Mortgage REITs

Download the [TradingView importer source](https://github.com/suna-kabo/ThemeScope/blob/codex/themescope-v6.2-fix/scripts/maintain_watchlists.py) or read the [full migration report](v7_migration_report.md). The importer creates a review proposal and diff; it leaves the approved configuration unchanged.
