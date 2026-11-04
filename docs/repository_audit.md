# Repository consolidation audit — 4 November 2026 (Hong Kong)

Review branch: `review/final-repository-audit`, based on approved `download`
commit `f8b9a8a`. Previous `main` is `c415198` and remains an ancestor through
a normal merge into this review branch. Its WIP designation is retained.
The original checkout's unrelated changes, inputs and history are untouched.

## Removal plan (recorded before removal)

These files leave the **source index**, not local user storage. Copies remain
in the original checkout and the isolated review checkout. None is a CLI,
fixture, license, active configuration, build input or runtime dependency.
Historical audit references will be marked as historical local paths.

| Path | Reason |
|---|---|
| `downloads/ThemeScope_individual_watchlists.zip` | Generated archive; setup/refresh rebuilds ordinary files from unchanged configuration. |
| `downloads/ThemeScope_manual_csv_session_2026-10-30.zip` | Old generated dashboard, audit and history bundle; not source or a deployment asset. |
| `downloads/ThemeScope_manual_csv_session_2026-11-02.zip` | Generated dashboard, audit and history bundle; private local output. |
| `downloads/ThemeScope_v7.1_session_2026-10-23.zip` | Legacy generated run with normalized inputs; not a supported fresh-install input. |
| `output/review_handoff/source_readiness_review.zip` | Internal source/access review; belongs outside the source/deployment artifact. |
| `reports/latest_run.md` | Generated, obsolete run report; current reports are generated locally per successful run. |
| `reports/v7_browser_verification.json` | Generated browser diagnostics; reproducible in local test output. |

Deployment-only retirement: optional broad-scan TXT files, individual
Primary-filtered TXT files/ZIP, and qualifying-relationships CSVs have no
current website link. They remain available in the private local run output;
the site generator must exclude them and their internal relationship payload.
Ordinary individual TXT contents and complete collection lists stay unchanged.

No legacy collector module is deleted: tests, historical imports and diagnostic
entry points still depend on them. Live collection will be isolated behind an
explicit opt-in instead of being the generator's default.

## Findings and validation

This is a source/manual-CSV audit, not a claim about profitability, live API
feasibility, actual TradingView import or future-session reliability.

| Severity | Finding | Resolution/status |
|---|---|---|
| High | Repository is public despite documentation claiming private; tracked run ZIPs include normalized input, audit/history metadata and local paths. | Seven generated files removed from the new source index and ignored; local copies retained. Old Git history/other branches remain accessible. Visibility/history remediation needs an explicit owner decision. |
| High | Old website allowlist published unlinked optional scans, Primary individual files/ZIP and qualifying-relationships CSV. Internal relationship structures also entered the embedded public payload. | Site schema 3 admits only explicitly purposed public files; strips internal Primary metadata. Old schemas cannot deploy without re-preparation. Migration retires obsolete files transactionally. |
| Medium | Lower-level generator bypassed wrapper close-time and stale-input checks. Bare invocation selected legacy live collection. | Shared completed-session and input-reuse guards now cover both entry points. Manual CSV is the default; live collection needs explicit `--source live --legacy-live`. |
| Medium | Successful import hardcoded `data_complete=true`, including when configured stock rows were absent. | Build success remains separate. Completeness now reflects configured instrument rows and includes an explicit scope; it does not certify roster identity or quote timestamps. Missing metrics remain N/A. |
| Medium | Site staging lacked the publication locks used by refresh/preparation. A post-commit backup-cleanup failure could incorrectly report a completed publication as failed. | Staging locks source and destination; checks cleanliness and preserves the target on copy failure. Committed cleanup failures retain recovery metadata and report successful publication with cleanup pending. |
| Medium | Windows drive/alternate-stream names were not explicitly rejected by the generic publication-path helper. | Colon/drive paths rejected in publication and preview; regressions cover both. No identifier or data changes. |
| Low | README, delivery links and implementation reports described old branches, old bundles and unsupported setup paths as current. | Current workflow and safe updates documented; historical reports clearly labelled; normal target branch is main after the gated PR merges. |

The bounded credential-pattern scan covered 123 original tracked files and 237
ZIP members. It found no private-key, GitHub-token, AWS-key or long literal Bearer
patterns; 14 archived members contained internal metadata or local paths. This
is not exhaustive credential forensics. No secret values were reproduced.

## Review coverage and invariants

| Area | Review and evidence |
|---|---|
| CSV schemas and units | Native aliases, duplicate symbol handling, canonical header precedence/audit, finite/positive requirements, percent normalization and missing-market-cap handling reviewed; parser regressions retained. |
| Sessions and folders | One explicit folder/session, duplicate roles, suffixes, holiday/early-close/DST boundaries, future refusal and direct-call reuse refusal tested. CSV timestamp/constituent-identity limits remain explicit. |
| Classification and priorities | Shared 64-cell matrix and result grouping; score boundary, EMA equality/missing inputs, full/selective equivalence and immediately preceding compatible-session transition exceptions unchanged. |
| Score and breadth | Average-rank ETF percentiles, shared weights, minimum-eight/80% breadth rules and denominator treatment unchanged. Browser filters never recompute breadth or membership. |
| Stock research and exports | Shared Decimal weighted excess, opposite-sign horizons, exact zero and missing endpoints; own-anchor evaluation, deterministic ordering, reserved anchors and overlap deduplication retained. All ordinary configured TXT contents remain unchanged. |
| History | Rank and EMA/priority compatibility remain separate. Same-session reruns, earlier replay, malformed history, migration backups and interrupted publication covered. Original checkout history was never modified. |
| Navigation and presentation | Search, filters, configured slots, per-tab scroll, Back/Forward, deep-link focus, earnings countdown from snapshot date, light/dark column boundaries and empty Primary states checked. |
| Serialization and deployment | Script-closing/Unicode escaping, sanitized payload, private canaries, symlink/path guards, exact allowlist, hash seal, ZIP member/content parity and excluded HTTP paths covered. No automatic external requests observed. |
| Legacy/unused material | Provider/cache modules have real historical-import, test or maintenance dependencies and were retained. No tests/fixtures/licenses removed. The redundant date-only session helper was replaced by the shared close-time guard. The `site_output.os` binding is still used by fault-injection tests, so static unused-import output alone did not justify deletion. |

Configuration files, current JS/CSS/templates, memberships, anchors and identifiers
are unchanged from `f8b9a8a`. The original checkout's unrelated dirty/untracked
files remain there; they were not folded into this candidate.

## Preview diagnosis

The previously implemented fixes were reviewed and retested, rather than assuming
the original server opened browsers before binding (it already bound first).
An old project owning a port independently reproduced old HTTP HTML/metadata
despite newer files elsewhere. A legacy conditional server independently
reproduced a same-second 304. Neither proves the cause on the user's PC.

Current previews print absolute root/type/session/exact URL, bind loopback before
opening, use separate defaults/strict explicit ports, reject wrong-copy URLs,
disable stale conditional caching and block newer downloads from old tabs until
reload. Live regeneration, occupied ports, moved/Unicode paths and different CWDs
are tested. No process is killed and no polling/backend is added.

## Final website inventory, by purpose

The isolated available real session remains **2026-11-02**, not newer market data.
It produces **64 files including the manifest**, down from 96 in the preceding
prepared site. The only nested directory is `individual_watchlists/`.

| Files | Count | Public purpose |
|---|---:|---|
| `index.html` | 1 | Website; inline JS/CSS/font and sanitized display data. |
| `_headers` | 1 | Hosting security/cache controls. |
| `Inter-LICENSE.txt` | 1 | Bundled font license. |
| `themes.csv`, `theme_stocks.csv` | 2 | Existing visible ranking and configured-stock CSV downloads. |
| `snapshot_summary.json` | 1 | Visible summary links and preview session metadata. |
| `individual_watchlists/*.txt` | 53 | Full selected Watchlist downloads, anchor first. |
| `individual_theme_watchlists.zip` | 1 | Download Individual Watchlists; exactly the same 53 TXT contents. |
| `tradingview_configured_stocks.txt` | 1 | Download All Stocks, complete configured stock collection universe. |
| `tradingview_sector_theme_etfs.txt` | 1 | Download All Themes, complete anchors/context collection universe. |
| `tradingview_daily_primary_2026-11-02.txt` | 1 | Current grouped Primary download; omitted when no result. |
| `site_manifest.json` | 1 | Public asset checksums; no internal rank/history fingerprint. |

The 32 retired deployment files comprise six optional broad scans, 24 Primary
individual TXT files, one Primary archive and one relationships CSV. They remain
in local run output for diagnostics; their calculations are unchanged. Public
relationship/archive structures were removed from the payload. Private source,
raw CSVs, normalized payloads, audit files, absolute input paths, history records
and run bundles are excluded. Every website ZIP member and download is checked.

Private exact-path inventory/checksums are in local
`output/repository_audit/site_inventory.json`, outside `site/` and Git. The public
purpose contract is `public_artifact_purposes()` in `site_output.py`.

## Verification actually performed

- Linux full unit suite: **191 tests run, one Windows-only skip**; JS syntax/helper
  tests and Python compilation passed. The skipped open-file behavior is covered
  by the native Windows workflow, not claimed from Linux.
- Clean staged-tree setup/build with temporary synthetic January 3/4, 2024 folders:
  normal refresh, same-date reruns, incomplete newer folder, duplicate/malformed
  inputs, missing-stock completeness reporting, wrapper/direct stale refusal,
  older replay, later-history preservation and stale-download retirement passed.
- Actual running production previews fetched exact HTML, metadata and downloads
  while outputs changed. Wrong-copy/occupied-port, no stale 304, crash recovery,
  concurrent locks, rollback and committed-backup cleanup tests passed.
- Real-session isolated rebuild/preparation passed. **94 local CSV/TXT/history
  files** remained byte-identical; all calculated theme data, classification and
  Primary selection remained identical. Three genuine history files are retained.
  Completeness correctly reports the existing 11 absent stock identities; there
  is no fill, replacement member or false completeness claim.
- HTTP site checks verified every allowlisted asset/download and confirmed private
  and retired paths return 404. ZIP contents match ordinary downloads.
- Chromium checked local/dashboard and site, all 64 matrix cases, available/empty/
  Unclassified Primary states, focus and Back/Forward/scroll; light/dark layouts
  at 1366, 1440 and 1920px, 100% zoom, passed. No JS errors or automatic external
  requests were observed. Screenshot artifacts remain local.
- Fresh Linux and native Windows CI run on the consolidation PR. Their attached
  statuses are the authoritative final-commit results. CI performs no data
  collection or publication and uploads no market artifacts.

The available historical refresh completed in about 1.4 seconds on this Linux
runner (command's through-publication timer). This is not a Windows-PC, full live
API, fresh market-session, profitability or longitudinal reliability measurement.

## Branch, merge gate and handoff

The [review branch](https://github.com/suna-kabo/ThemeScope/tree/review/final-repository-audit)
is committed and source-only; the
[associated PR](https://github.com/suna-kabo/ThemeScope/pulls?q=is%3Apr+head%3Areview%2Ffinal-repository-audit)
targets `main`. Previous main `c415198` remains in normal ancestry. `download`,
`pages` and other branches are not deleted or force-pushed. No deployment setting
is changed; no market site is committed, pushed or deployed.

**Main is not authoritative until the PR is safely merged.** Merge remains gated
on confirming that `main` and review branches cannot trigger a public deployment.
The smallest external action is to confirm actual Cloudflare production and
preview branch settings (or disable automatic deployments) without sharing any
credentials. A repository owner must separately decide whether the currently
public repository/history exposure is intended; changing visibility or purging
history was not authorized as an automatic cleanup shortcut.

Actual TradingView imports, expanded native select popup appearance, the user's
own Windows PC, new-session observations, rights to publish data and future
reliability remain unverified. Passing tests does not establish those facts.

See README for safe Git and selective ZIP updates, backing up local inputs,
output/history and old delivery files before branch changes while keeping `.venv`
and personal configuration. **Existing TradingView individual watchlists do not
require reimporting.**

GitHub currently reports this repository as **public**. Removing tracked bundles
in a new commit does not remove their historical accessibility. No history is
rewritten and repository visibility is not changed by this audit.

No GitHub deployment/environment records or external checks were found for
`main`; GitHub Actions checks are present. Webhook inspection returned HTTP 403.
Cloudflare account branch/build settings remain unverified. Do not merge into
`main` until its deployment behavior is confirmed; no hosting settings are
silently changed here.
