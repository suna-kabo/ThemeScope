# Gate E: useful research before official launch

This separate fix follows SQLite lifecycle commit 0b51a0f. The user explicitly
approved a distinction between the universe available for current research and
membership that officially earns synthetic-index returns. Gate E remains open
pending native Windows validation of the new research path.

## Daily workflow and membership

Before the upcoming US open, normal operation uses the latest safely completed US
session. If target < approved launch close and all configuration plus runtime roster
gates pass, `approved_launch_universe()` selects the approved interval effective on
the first earned session after launch. This is a general calendar-based rule, not
a hardcoded November 5 exception.

The selection retains original Membership objects, roles, evidence and effective
intervals. Its explicit `members_for()` method supplies Core+Enabler research
inputs. It never replaces official `members_on()` or `active_on()` and never changes
any effective date. Related relationships remain context only. Blocked, unapproved
or post-launch selections cannot use this path. Both effective SPY/QQQ rosters are
still required; staleness remains advisory and IWM remains context only.

For the approved launch:

| Concept | Value |
|---|---|
| Latest completed research session | 2026-11-05 |
| Approved relationships | 726: 659 Core / 62 Enabler / 5 Related |
| Research calculation relationships | 721 Core+Enabler |
| Official launch rebalance | 2026-11-06 close |
| Every retained official effective_from | 2026-11-09 |
| Official membership earning November 5 | none |

## Calculations and current trend

The same pure calculations receive an explicit research-member selector. No frozen
formula/threshold changes: 21/63-session adjusted returns, member medians, minimum
five/80% coverage, average-tie percentile scores, 60/40 weights, LOO peers/minimum
four/80% coverage, W, daily raw liquidity, Theme Priority and deterministic exports.
Market context, roster breadth and the entire Market Matrix are unchanged.

A separate bootstrap-only series uses fixed approved Core+Enabler holdings and
historical bars ending at target. It calls unchanged `build_index()` with explicit
bootstrap symbols. It does not use future prices, legacy ETF history or daily equal
weighting. Current EMA21/EMA50 and frozen strict trend boundaries support normal
current research priority and Primary qualification. Missing data is never filled
and no holdings are silently dropped.

Pre-launch indicator inputs use the latest contiguous valid observations within
the existing historical lookback. The theme series requires every selected holding
at each included close; each stock's EMA requires its own contiguous closes. This
allows a recent listing with 64 completed observations to supply a 63-session return
and EMA50. A recent gap leaving insufficient observations keeps trend unavailable;
valid endpoint-based Theme Score/W need not become unavailable with it. Official
live-index/launch bootstrap semantics are unchanged.

## Persistence and transition isolation

Pre-launch dashboard, relationships and exports can be published transactionally
with metadata such as:

```json
{
  "state": "pre_launch_research",
  "research_session": "2026-11-05",
  "membership_basis": "approved_launch_membership",
  "membership_basis_session": "2026-11-09",
  "official_live_history": false
}
```

The research series ID contains `:pre-launch-research:` and the target date; it is
never the official live series ID. Every research ThemeHistory is `bootstrap=true`
and `signal_eligible=false`. All transition fields stay unavailable, including
Newly Bullish, Newly Bearish and Priority Change. Prior pre-launch snapshots are
not used as historical live signals. The engine rejects mixed research/live input.

Research series points are not passed to the `theme_index` writer at all. Only the
current research observation is retained in its explicitly labeled research snapshot.
No backdated official membership or return history is created. SQLite stays schema
2, with the existing eager initialization, five-second bounded busy handling,
read-only polling, committed-snapshot cache and atomic publication/rollback intact.

At November 6 close the research selection turns off automatically. The official
series initializes at exactly 100 with empty earned_symbols, under its original
series ID. Approved Core+Enabler holdings first earn the November 9 close-to-close
return from November 6. That first return cannot compare with pre-launch research
or launch initialization. Existing natural-drift and 100 -> 120 -> 160 boundary
regressions are preserved; no series splice occurs.

## UI and native validation

A compact **Pre-launch research** banner identifies completed research session and
future official-history start. Theme Research and Primary cards label **Pre-launch
research trend**. Scores are displayed normally; comparisons say Comparison
unavailable. Normal live operation does not label these real Alpaca/approved-universe
research values as fictional fixtures. Save-to-Watchlist and individual/combined
TXT use the existing flows. The offline fixture mode remains explicitly fictional.

Stop any old server, update the implementation branch, keep existing runtime data,
and run these in PowerShell:

```powershell
.\.venv-vnext\Scripts\python.exe -m unittest discover -s tests -p "test_vnext_prelaunch_research.py" -v
.\.venv-vnext\Scripts\python.exe -m unittest discover -s tests -p "test_vnext_launch.py" -v
.\.venv-vnext\Scripts\python.exe -m unittest discover -s tests -p "test_vnext_sqlite_lifecycle.py" -v
.\ThemeScope.cmd
```

With the already configured local SIP environment, Refresh Data should use the
latest safely completed session. If it precedes launch, verify scores, research
trends, priorities, peer W, candidates, Save and both TXT forms, plus no ASGI lock
errors. After launch, verify normal automatic official-history behavior. No database
reset or manual daily CSV upload is required. Account/full-universe timing and
native Windows execution are local checks; cloud tests use synthetic bars only.

## Regression evidence

- Actual approved 44-theme / 726-relationship configuration with deterministic
  synthetic bars produces 44 non-null Theme Scores, current trends, breadth,
  priorities, all 721 eligible W results and nonempty Primary/TXT output.
- Independent rational oracle verifies all 44 median returns, tied-percentile
  scores and a selected LOO W; Related is excluded and symbols deduplicate.
- Pre-launch publication writes zero theme_index rows, every official date remains
  November 9, research histories are bootstrap/ineligible, and transitions are N/A.
- Research automatically stops at launch. Official level=100/empty earned_symbols,
  first November 9 return and natural drift remain intact; no pre-launch live point.
- General future-date selection, config/each-roster fail-closed behavior, genuinely
  insufficient versus adequate contiguous indicators, unchanged liquidity exclusion
  and mixed-series rejection are covered.
- Real loopback browser checks banner, current research trend, Primary download,
  Save-to-Watchlist, absence of a fictional-fixture banner and automatic official
  launch cutover. Zero page errors/external requests; existing browser checks pass.

Validation: **321 full cases, 319 passed/two existing native-Windows skips**;
**114 focused vNext cases, 113 passed/one native-Windows skip**. All **8 pre-launch**,
**7 official-launch** and **11 SQLite lifecycle** regressions pass, including the
independent rational oracle. Compilation, JS, config/evidence, provider/cache/export,
all **64 frozen Market Matrix cells**, both browser checks and temporary safe
inspection/source scans pass. The user must still validate the native Windows
pre-launch research workflow; these automated results do not close Gate E. No live market credentials, raw provider
payloads or runtime databases are committed. No main/deployment/inspection-ref
changes and no Gate E closure.

## Launch-close research correction (Gate E remains open)

Research membership timing differs from return-accounting effectivity on the launch
close only. The engine accepts an independent `research_members_for` resolver.
`approved_launch_close_membership()` selects the approved next-earned-session
Core+Enabler intervals on L after configuration/roster gates pass. Official index
construction still uses effective-dated accounting membership, without alteration.
The pre-launch bootstrap selector still stops before L; L is never labelled pre-launch.

| Session | Research | Official accounting / transitions |
|---|---|---|
| Nov 5 | Approved launch members, bootstrap research trend | No official index or compatible transition |
| Nov 6 close | Approved launch members: Score, W, eligibility, breadth, Primary and exports | Official index exactly 100; earned_symbols empty; signal_eligible false; no earned return or transition |
| Nov 9 | Effective members, normal research | First genuine Nov 6–Nov 9 earned return; transition unavailable |
| Nov 10 | Effective members, normal research | Second earned observation; first possible adjacent-live transition |

The launch-close snapshot records `research_membership_basis=approved_launch_membership`
and its first-earned-session basis separately from initialized official history.
This is not backdated membership. No dates, formulas, index math, compatibility,
UI, provider or schema change. A deterministic fixture proves a launch-close
Candidate can qualify; actual market data may legitimately yield zero Candidates.
