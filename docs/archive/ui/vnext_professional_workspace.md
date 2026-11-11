> **Historical checkpoint.** Status, counts and instructions below describe that
> checkpoint, not current operation. Gate E is now **CLOSED**; Nov 6, Nov 9 and
> Nov 10 live validation passed per the user. See the [closure record](../../operations/gate-e-closure.md)
> and [current documentation](../../README.md).

# Professional research workspace — 10 November 2026

Historical checkpoint: visual identity is superseded by [Tidal Vector](vnext_tidal_vector.md);
its financial/export contracts below remain current.

Continues `967dab6` on `refactor/themescope-vnext`. This is a presentation
refinement plus additive Countertrend TXT publication. Existing financial formulas,
qualification, history, launch lifecycle, corporate actions, provider/cache, schema
and Directional export semantics remain unchanged.

## Composition and context

Overview now starts with Market Bias, supporting Extension/focus and a compact
benchmark evidence table. SPY/QQQ vote; IWM is lighter non-voting small-cap context.
Four-item theme/stock destinations appear sooner; the map opens on demand.
Candidates has one dominant Directional/Countertrend tab pair, Search/Theme toolbar,
secondary filter disclosure, quiet view/sort utilities and one scoped Export menu.
No ambiguous sidebar Candidate count is shown. Detailed explanations live in
keyboard-accessible help and Methodology, whose stable anchors open the right rule.

No Theme filter preserves supplied stock representatives. With a Theme filter,
the display selects the qualifying relationship for that theme **before** sorting:
Theme, Role, W and initial ticker inspection all use that relationship. Neither
qualification nor export assignment changes. Both research lenses are covered.

Theme sheets provide quick metrics, concise context and a six-member preview with
Search/View, with Open full theme for complete research. Ticker sheets lead with
the selected relationship and its Role/W/status/liquidity; other relationships and
peer returns are secondary disclosures. Nested Back preserves the parent sheet,
search, View, scroll and focus. Polling preserves context. Saved retains the original
`themescope-vnext-watchlist` ticker-array contract; an optional separate
`themescope-vnext-saved-context` key records the chosen theme/lens. Missing or
unqualified bookmarks are retained.

Operational Countertrend labels are observations: Short uses Peer outperformers /
Weak-theme laggards; Long uses Strong leaders / Underperforming theme peers.
Internal bucket IDs and approved filters/order remain unchanged. W predicts neither
reversal, rebound, pullback nor success. The optional earnings presentation remains
hidden when the existing snapshot only reports global unavailability.

## Additive Countertrend export contract

`research.countertrend.exports` is attached before transactional publication using
published bucket pointers and the existing verified TradingView resolver. No new
qualification or exchange inference occurs. Unknown/unverified identifiers abort
publication, preserving the previous snapshot and downloads. Bucket files deduplicate
by ticker in supplied W order; combined files contain the sorted unique union.
The existing top-level Directional `exports` object is unchanged.

| Published side | Download filenames |
| --- | --- |
| Short | `Countertrend.txt`, `Resilient.txt`, `Snapback.txt` |
| Long | `Countertrend.txt`, `Strong-Leaders.txt`, `Relative-Weakness.txt` |
| Unavailable/empty | no invented download |

Local routes: `GET /api/exports/countertrend/{filename}` with a fixed filename
allowlist and one committed snapshot read per request. Existing Directional routes
`/api/exports/combined.txt` and `/api/exports/{theme_id}.txt` retain their behavior.
Static modes download literal supplied TXT as Blobs, never deriving membership in
JavaScript. The visible scope note says exports use the full published lens, not
current filters. The menu closes after choosing a download; feedback says Preparing,
not an unverified download-success claim.

Public projection validates exact side/filenames/sets/order against published
bucket pointers and verified identifiers, strips the internal symbol lookup, and
retains only `available`, `side`, `files`. Older snapshots without this child remain
readable with unavailable CT exports. Fixed static output allowlists and secret/path
scans remain; no SQLite, private runtime state, credentials or provider access is
exposed. Tests use manufactured source contracts, not a real public publication.

## Design system and interactions

`DESIGN.md` now describes the implementation. CSS is consolidated into tokens,
components, responsive rules and motion rather than another override layer. Warm
dark grounds, flat research sections, shared dividers, 4px controls / 8px overlays,
quiet underlined identities and restrained lavender selection/focus/actions replace
competing treatments. Existing local Inter and its SIL OFL 1.1 license are served
in local/static modes. SHA256-pinned assets cannot be swapped for arbitrary binary
payloads. No new font binary, remote asset or runtime dependency is introduced.

Tabs use a 240ms underline and 160ms explicit content switch; view segments move
selection in 240ms. Help has a 250ms delay / 160ms arrival; disclosures use native
240ms content/chevron motion where supported; sheets 200ms and small toasts 160ms.
No initial row/page animation, hover lift or decorative motion. Both OS and user
reduced-motion settings suppress/cancel motion. Keyboard tabs support arrows/Home/End;
help supports pin, Escape, focus return and Methodology navigation.

Tables stay tables at default-text 1440/1024/768px. Rank Change and breadth are
deprioritised before narrow reflow; local horizontal access is signposted where
needed. Summary rows start only below 36rem logical content width. Enlarged text
reflows without shrinking data. Compact/Comfortable remain 4/8px cell padding;
24px desktop identity/state targets and 44px narrow controls preserve useful density.
The map keeps all observations, nice ticks and one roving Tab stop; selection is
separate from the deliberate Open theme action.

Initial loading differs from genuine empty results. Supplied missing-comparison
reasons stay available, breadth remains a compact dash with known coverage/member
reasons, and untracked concepts explicitly have no calculation basket. Connection
loss keeps the committed data and says `Connection lost · showing completed session
YYYY-MM-DD`.

## Acceptance and review

- Full Python: 389 run, 387 passed, two existing native-Windows skips.
- Focused vNext: 160 run, 159 passed, one existing native-Windows skip.
- New Countertrend export tests: 10 passed; public snapshot tests: 19 passed.
- JavaScript syntax/helpers, compilation, configuration/evidence validators and
  whitespace checks pass. No financial, Matrix, lifecycle or corporate-action
  regression test was changed.
- All seven browser programs pass. The primary suites have 78 axe audits with
  zero violations (21 professional, 27 context, 14 Lunar, 8 static, 8 public).
  Known incomplete checks remain visible in reports; automated results do not
  substitute for manual assistive-technology review.
- Both professional/context matrices pass 20 width/text/density combinations,
  plus high contrast/reduced motion and keyboard checks. All requested surfaces,
  both lenses and sheets fit. Desktop density: 32 Theme / 26 Candidate rows at
  2560×1440. Static modes make zero API requests; no UI introduces external calls.
  The existing local favicon 404 is separately recorded, not a new failure.
- External screenshot gallery/report: `/workspace/artifacts/themescope-professional-workspace/`;
  ZIP: `/workspace/artifacts/ThemeScope_Professional_Workspace_Review.zip`.
  No screenshot binaries are committed. Before/after images illustrate structure,
  with different labeled deterministic sessions; they do not compare real returns.

Real launch Nov 6: **PASS**, first earned-session chronology Nov 9: **PASS**, both
user-reported. Adjacent-live Nov 10: **PENDING**. Gate E stays **OPEN**. No Nov 9 live
rerun/reclassification, real credentials, merge or deployment occurred. Native
Windows and manual assistive-technology review of this UI remain unclaimed followups.
