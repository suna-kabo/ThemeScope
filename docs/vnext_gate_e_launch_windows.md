# Gate E: launch-close research and Windows evidence integrity

These are two separate corrections after the completed Lunar Lounge checkpoint.
The UI is unchanged. Gate E remains open pending native Windows validation.

## Launch-close research

The previous engine selected effective accounting members for research on L, while
all approved launch intervals start on the next earned session. This created an
artificial empty research universe even though official initialization succeeded.

`calculate_session()` now accepts an independent `research_members_for` resolver.
The runtime selects approved first-earned-session Core+Enabler intervals on the
approved launch close, after configuration and both roster gates pass. This resolver
feeds unchanged medians, Score, LOO W, eligibility, breadth, Primary and exports.
Official index construction, history compatibility and signal eligibility retain
existing accounting rules. Membership objects and effective intervals are untouched.

| Completed session | Research | Official history |
|---|---|---|
| 2026-11-05 | Pre-launch bootstrap research | No official earned history |
| 2026-11-06 close | Launch-close research from approved Nov 9 membership | Initialize at exactly 100; no earned symbols/return; signal_eligible false; transitions unavailable |
| 2026-11-09 | Normal effective-member research | First genuine Nov 6–Nov 9 return; transitions unavailable |
| 2026-11-10 | Normal effective-member research | Second earned observation; first possible compatible adjacent-live transition |

Research membership timing differs from return-accounting effectivity on the launch
close only. It is not backdated membership. Launch-close metadata separately records
`research_membership_basis=approved_launch_membership` and basis session 2026-11-09;
`theme_layer.state` remains `initialized`. Pre-launch bootstrap research is never
inserted as official live history. Existing indicator-only initialization seeds
remain supported and do not earn returns.

A deterministic synthetic fixture produces launch-close Candidates. Real completed
market data may legitimately produce none under unchanged qualification rules.
Scores and relationship calculations must not disappear because of interval wiring.

## Windows evidence line endings

Git CRLF checkout conversion changed raw SHA-256 bytes without changing reviewed
JSON content. Four reviewed JSON files now have explicit `text eol=lf` attributes:
industry_rule_registry, primary_source_attachment_tasks, membership_master_review
and membership_review_provenance. Existing CMD CRLF handling remains intact.

`reviewed_json_sha256()` strictly decodes UTF-8 and replaces only CRLF pairs with LF
before hashing. No general JSON canonicalization, whitespace stripping, lone-CR
normalization, BOM removal or binary normalization occurs. Existing expected
provenance hashes and all reviewed JSON contents are unchanged. Content/formatting
edits still fail; registry, relationship, membership and provenance checks remain.

## Native Windows retest

From the existing repository checkout in PowerShell, close any running ThemeScope
server, then run:

```powershell
git switch refactor/themescope-vnext
git pull --ff-only
.\.venv-vnext\Scripts\python.exe scripts\validate_vnext_config.py
.\.venv-vnext\Scripts\python.exe scripts\validate_membership_evidence.py
.\.venv-vnext\Scripts\python.exe -m unittest discover -s tests -p "test_vnext_launch.py" -v
.\.venv-vnext\Scripts\python.exe -m unittest discover -s tests -p "test_vnext_prelaunch_research.py" -v
.\.venv-vnext\Scripts\python.exe -m unittest discover -s tests -p "test_vnext_membership_evidence.py" -v
.\ThemeScope.cmd
```

Use locally configured SIP environment credentials; do not paste them into reports.
Do not edit reviewed documents or expected hashes to repair checkout line endings.
The in-memory hash normalization also supports an existing CRLF working copy.

Manually Refresh Data for the safely completed 2026-11-06 US session. Confirm actual
refresh success, not merely that the previous dashboard still opens. Inspect both
`http://127.0.0.1:8766/api/status` and `/api/dashboard-data` locally if needed.

Expected: target/session Nov 6, initialized theme layer, 44 Active themes, available
Scores for valid themes, research relationships, W/eligibility, rule-based Candidates
and exports, index levels exactly 100, signal_eligible false and unavailable
transitions. Persisted non-bootstrap launch index points must have empty
`earned_symbols`; there is no earned Nov 6 return. The versioned Nov 9 memberships
remain formally inactive on Nov 6. No pre-launch research series supplies a live
transition. Do not require a nonempty real-market Candidate list.

Cloud fixtures validate these paths but cannot close native Windows validation.
Real Nov 9 and Nov 10 chronological production checks remain deferred until those
completed US sessions exist. No merge, branch deletion, deployment or Gate E closure.

## Cloud validation

- Stage 1 focused vNext suite: 115 run, 114 passed, one native-Windows skip.
- After both fixes: full suite 325 run, 323 passed, two native-Windows skips;
  focused vNext 118 run, 117 passed, one native-Windows skip.
- Launch 7, pre-launch research 9, evidence 10 and SQLite lifecycle 11 tests pass;
  engine/provider/cache/local API regressions and all 64 frozen Matrix cases pass.
- Configuration and membership-evidence validators, Python compilation, both
  JavaScript syntax checks and `node tests/test_dashboard.js` pass.
- Expected reviewed hashes and all configuration document contents remain unchanged.
  The registry normalized digest remains
  `e3c436863a9e1452a0067d6987db1af3eaa833e389a7efe53706d69e6b0f7581`.
- Existing Starlette TestClient/httpx deprecation warning remains; it does not fail
  tests and dependency migration is outside these two fixes.
- No live Alpaca calls or credentials were used. Native Windows and real later
  chronological sessions remain required; these Linux results do not close Gate E.
