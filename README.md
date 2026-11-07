# ThemeScope vNext

Private, local, end-of-day US equity research. Custom equity themes drive Theme
Score, synthetic trend and stock-versus-peer Primary qualification. SPY/QQQ define
market context; IWM is context only. Thematic ETFs have no calculation role.

The implementation branch is `refactor/themescope-vnext`. Phase 9 is implemented;
Gate E non-live review is complete; the real native Windows Nov 6 launch refresh
has passed. Real Nov 9/10 chronological checks remain deferred. The existing `inspection/` directory
is the preserved historical Gate D fixture, not current launch status. Nothing
here deploys a public site.

## Local operation

Use Python 3.12 on Windows. From this branch's checkout:

```powershell
.\setup.cmd
$env:APCA_API_KEY_ID = '<your local market-data key>'
$env:APCA_API_SECRET_KEY = '<your local secret>'
.\ThemeScope.cmd
```

Keep credentials in your local environment, never in a file committed to Git.
The application binds `127.0.0.1:8766`; select **Refresh Data** to retrieve the
latest safely completed US session. `refresh.cmd` and `open-dashboard.cmd` both
open this same application. They no longer accept legacy CSV/session arguments.
No daily Stock or ETF CSV uploads are needed. First use seeds history; later
refreshes use the incremental SQLite cache with a bounded repair window.

Alpaca historical SIP is explicit: `1Day`, split/spin-off adjustment, separate
raw daily liquidity observations and complete pagination. No IEX fallback or
trading endpoints. See [provider validation](docs/vnext_provider.md) for local
account diagnostics. The optional `ALPHAVANTAGE_API_KEY` enables earnings dates;
missing earnings never fail refresh.

For fictional offline data in an isolated database:

```powershell
.\ThemeScope.cmd --fixture
```

On Linux/macOS: `python3 scripts/bootstrap_dev.py`, then
`.venv-vnext/bin/python scripts/run_vnext.py` (optionally `--fixture`).

## Approved launch and history

The launch rebalance is **November 6, 2026 at close**. All **726** retained
relationships are effective **November 9, 2026**, the next XNYS session. Roles
remain 659 Core, 62 Enabler and 5 Related; Related never enters calculations.
Evidence review is complete and the industry registry is approved.

Before November 6 completes, the latest safely completed session (normally the
previous US close) supports **pre-launch research** with the approved launch universe:
Theme Scores, bootstrap-derived current trends, priorities, stock peer W, Primary
candidates and TXT exports. Related stays context only. A compact banner identifies
the research session and the future official-history start. These are real research
calculations from Alpaca SIP, not fictional fixture results or backdated membership.

At the November 6 close every valid Active theme initializes its official index at
100 using November 9 Core+Enabler holdings, earning no launch-day return. Launch-close
research independently uses that approved universe for Scores, W, eligibility,
breadth, Primary candidates and exports. The first
genuine return is November 6 close to November 9 close. Pre-launch bootstrap series
are never stored as official index history and never supply transitions. The launch
initialization cannot provide a prior earned live signal; November 9 transitions
remain unavailable. November 10 is the first possible compatible adjacent-live
transition; real Nov 9/10 chronological checks remain deferred.
See [pre-launch research](docs/vnext_prelaunch_research.md) for the explicit distinction.

Effective SPY **501** / QQQ **101** constituent rosters dated November 5 remain
separate manually maintained universes. Missing either effective roster blocks
theme activation and Primary outputs; staleness is advisory. IWM needs no roster.
Only roster symbols are configured from those TradingView files; Alpaca supplies
all runtime prices/volumes and ThemeScope calculates its own EMAs/breadth.

Dashboard and TXT exports read one committed SQLite snapshot. Provider/calculation
failure preserves the previous successful snapshot. Operational status-file
failure is nonfatal. Back up `runtime/vnext/` while the app is stopped; fixture
storage is separate. Never delete a database or replace genuine history with a
fixture. There is no legacy-to-vNext series splice or automatic backfill of signals.

## Legacy compatibility

Existing manual-CSV historical snapshots and readers are preserved unchanged.
Use **`legacy-open-dashboard.cmd`** to view an existing legacy dashboard. Explicit
`legacy-setup.cmd` / `legacy-refresh.cmd` retain historical reproduction tools;
they are not the daily runtime. The old workflow is archived in
[legacy manual CSV documentation](docs/legacy_manual_csv.md). Old ETF history
remains a distinct incompatible series; it cannot initialize vNext transitions.
Do not overwrite legacy `output/manual_csv/local_history` during updates.

TXT identifiers use existing verified mappings, supplemented only by explicit
Symbol/Exchange identifiers in the validated user-supplied TradingView review
universe. No venue is guessed; unresolved identifiers still fail closed. Actual
TradingView TXT import and a separately measured cold/warm comparison remain local
checks. The user reports a successful native Windows Nov 6 SIP refresh: 899/899
symbols, 44 Active themes, available research outputs and initialized official
indices at 100, in approximately 52.5 seconds. The user reports SIP roster compatibility passed for November 5:
501 SPY, 101 QQQ, zero missing/unusable, 12 pages, adjusted plus raw requests.

## Developer checks

```sh
python -m unittest discover -s tests -v
python scripts/validate_vnext_config.py
python scripts/validate_membership_evidence.py
python -m compileall -q src scripts tests
node --check static/vnext/app.js
node --check static/dashboard.js
node tests/test_dashboard.js
```

Tests use fixtures/mocks, never account credentials. See
[Phase 9 details](docs/vnext_launch.md), [methodology](docs/vnext/ThemeScope_vNext_Product_and_Methodology_Spec.md)
and [PLANS.md](PLANS.md). Gate E, merge to main and deployment are not part of
this implementation.

Current review evidence and deferred checks: [Gate E review](docs/vnext_gate_e_review.md).
