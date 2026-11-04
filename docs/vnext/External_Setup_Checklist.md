# ThemeScope vNext: What the user needs to do outside ChatGPT/Codex

## Required now or before live-provider testing

### 1. Create a free Alpaca Paper Only account
Use Alpaca only as a market-data credential for ThemeScope.

You do NOT need to:
- fund an Alpaca brokerage account;
- transfer your trading from IBKR;
- give ThemeScope trading permission;
- use Alpaca order endpoints.

Generate API keys from the Alpaca dashboard.

Never paste the key or secret into:
- ChatGPT;
- a Codex prompt;
- GitHub;
- an inspection branch;
- screenshots.

The implementation should read local environment variables:
- APCA_API_KEY_ID
- APCA_API_SECRET_KEY

Codex Cloud must use fixtures and mocks, not your live keys.

### 2. Run the local Alpaca SIP PoC after Codex adds it
Run the supplied local script after a US session is at least 15 minutes old.

Expected test:
- historical 1Day bars;
- feed=sip;
- end timestamp older than 15 minutes;
- multiple NYSE/NASDAQ symbols;
- volume present;
- pagination works;
- adjustment=split,spin-off works.

If Alpaca returns a subscription error for historical SIP:
STOP.
Do not accept an automatic IEX fallback.
Do not pay for a plan until we compare alternatives.

### 3. Keep SPY / QQQ constituent rosters manual initially
Once a month, or whenever you know an index constituent change occurred:
- export full SPY constituent scanner, no filters;
- export full QQQ constituent scanner, no filters;
- import them into ThemeScope's roster-update workflow.

The new app should store the effective date and warn when a roster is old.
It should not block ordinary daily price refresh merely because a roster is old.

No IWM constituent export is needed in vNext.
No ETF scanner export is needed in vNext.

### 4. Quarterly Stock membership review
At the quarterly review, export the Stock scanner with:

- Market Cap >= USD 2B
- Price >= USD 5
- Security Type = Common Stock
- Exchange = NYSE or NASDAQ
- Avg Volume 10D > 500K
- 1D Turnover >= USD 10M

Do not include NYSE Arca.

Import that CSV into the vNext membership-review tool.
The tool must create a proposed diff only. Review/approve before membership config changes.

### 5. Back up your current ThemeScope installation before switching
Back up at least:
- config/
- inputs/
- output/
- downloads/
- reports/
- site/ if you still need it

Keep the current main version usable until vNext is accepted.

## Optional

### Alpha Vantage earnings key
If you want Upcoming Earnings restored automatically, obtain a free Alpha Vantage key.

ThemeScope should use the EARNINGS_CALENDAR endpoint.
If no key exists, the dashboard should simply show earnings as Unavailable.

Suggested local variable:
ALPHAVANTAGE_API_KEY

This is optional and must not block the market refresh.

## GitHub inspection/download workflow

Because Codex workspace files are awkward to download directly, use GitHub
inspection branches as explicit checkpoints.

Implementation branch:
refactor/themescope-vnext

Checkpoint branches:
inspection/vnext-a-domain
inspection/vnext-b-engine
inspection/vnext-c-provider
inspection/vnext-d-ui
inspection/vnext-e-final

At a checkpoint Codex should:
1. make sure tests pass;
2. generate a safe inspection/ folder;
3. ensure it contains no credentials, runtime database, raw licensed market data or personal paths;
4. push that checkpoint branch;
5. report its commit SHA.

You can then open that branch in GitHub and use:
Code -> Download ZIP

Do not merge an inspection branch to main.
Final source merge comes from refactor/themescope-vnext after review.
