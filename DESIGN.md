# ThemeScope — Tidal Vector

ThemeScope is a completed-session personal equity-research terminal. This visual
world replaces the warm Lunar Lounge palette at `ee6a7aa`; it preserves the
research architecture and financial rules. Midnight surfaces, electric selection
and precise data columns give it a recognisable identity across sizes.

## Design thesis

The market is context; the selected research object is the user's working focus.
A **cut selection plane** carries that focus through navigation, research lens,
selected rows and relationship inspection. The same 12px diagonal means active
context. Neutral data keeps straight geometry. Cyan is selection/focus, never a
new financial signal. Green/red retain positive/negative financial meaning.

Two browser-rendered internal studies informed the choice: Tidal Vector's compact
vertical working frame and Blue Hour Ledger's broader editorial composition.
Tidal Vector won on repeated research navigation, table space and cross-surface
continuity. The larger editorial headline/bright banner was rejected. Concepts and
screenshots remain external, not production code or repository binaries.

## Tokens and typography

| Role | Token/value |
| --- | --- |
| Page / rail | `--page:#07111f`, `--rail:#0b192b` |
| Section / focused sheet | `--surface:#0d2033`, `--surface-raised:#10283e` |
| Selected context | `--selected:#123653` |
| Electric / ice | `--electric:#3ea6ff`, `--accent:#65e3ff` |
| Primary / secondary | `--text:#f3f7fb`, `--secondary:#afc3d5` |
| Metadata / unavailable | `--muted:#8ba5bc`, `--unavailable:#8aa0b3` |
| Positive / negative | `--positive:#65d6a4`, `--negative:#ff919c` |
| Dividers / input border | `--rule:#203a52`, `--input-border:#718ba1` |
| Spacing | 4, 8, 12, 16, 24, 32, 48px |
| Geometry | 4px controls, 8px floating utilities; 12px context cut, 8px narrow |
| Desktop rail / gutters | 192px / 24px; rail 160px at 801–1100px; narrow gutter 16px |

The existing local **Inter Variable** is the only font, with system fallback and
its existing SIL OFL 1.1 license. No remote font or added UI dependency.

Page titles: 30px/660 with −.035em tracking (24px narrow). Market Bias: 44px/740,
uppercase as a compact directional identity, 32px narrow. Inspector identity:
28px/700. Section titles: 17px/600. Research text: 14px; metadata 12–13px.
Table identity: Theme 550/secondary, ticker 650/primary; selected Theme is primary.
Ordinary numbers are secondary and use tabular lining numerals. Headers and labels
are quieter; unavailable values remain readable and explicitly missing.

Text hierarchy relies on tone/weight/position, not tiny fonts. All four text tokens
meet normal-text contrast against the page, raised and selected surfaces. Disabled
controls are distinctly disabled; readable unavailable information is not treated
as disabled. High contrast and native forced colours have explicit equivalents.
Selection, caret, scrollbars, input affordances and visible focus use the same palette.

## Page composition

- **Overview:** the compact Market Direction Plane connects Bias → Extension →
  Market focus. It does not imply an entry signal. SPY/QQQ evidence stays compact;
  IWM remains lighter non-voting small-cap context with equal ticker/price type.
  Four-item destinations follow; the Returns Map opens on demand.
- **Themes:** comparison stays table-first. Complete-universe Strength Rank never
  changes with sorting/filtering. Research Priority remains separate from Strength.
- **Candidates:** Market and Market focus are explicitly labelled context. The
  separate Research lens control identifies Directional or Countertrend. Search /
  Theme lead; secondary filters are disclosed, view/sort quieter, exports scoped.
  Peer delta (pp) is the short label for unchanged theme-specific W.
- **Grouped Candidates:** Theme is established by the group heading. Child tables
  omit repeated Theme cells; their ticker/Save actions still carry that exact theme
  and lens. Counts, relationships, qualification and export membership are unchanged.
- **Full Theme:** Strength, Rank, Research Priority and Trend lead. Returns/breadth
  are secondary; raw index/EMA values and comparisons are tertiary. No metric cards.
- **Inspector:** a raised right sheet, cyan leading edge and selected relationship
  plane. Summary first, secondary relationships expandable. A nested Back control
  returns to the previous object with search/View/scroll/focus restored.
- **Saved:** browser-local continuity, never a portfolio/trade journal. Original
  `themescope-vnext-watchlist` array and companion context key are preserved.
- **Methodology:** quiet reading surface; selected anchors, disclosures and metric
  help carry the new language without decorating formulas.

## Table ownership

Research tables use semantic `<colgroup>` definitions, shared header/body column
classes and stable rem widths. They do not rely on nth-child percentage guesses.

Themes: Rank 5rem; Theme flexible; Strength 7.5rem; Rank Δ/1M/3M each 5.5rem;
Trend 6rem; breadth 8.5rem; Research 8.75rem. Theme names wrap within their own
column. Numeric fields align right; descriptive identities, Trend and Research
align left. Header help precedes right-aligned numeric headings, preserving their
anchor. Save is centred. Horizontal padding is 12px, not column-specific nudges.

Candidates: Ticker 7rem; Theme flexible; Role 10.5rem; Peer delta 10rem; Save
3.5rem; optional earnings 8rem. Grouped tables give the remaining space to Role.
Compact/Comfortable retain 4/8px vertical padding and shared optical centring.
Selected rows keep their plane even on hover. No hover lift or initial row animation.

At default-text 1024/768px, Themes remains a reduced-column table. Rank Change,
breadth and longer-horizon returns are progressively deprioritised at logical
container widths. Local horizontal access is signposted where needed. Headers
stick to the page when the table fits; horizontal-scroll tables keep local access.
Only below 36rem logical content width do rows become labelled compact summaries.
Column widths no longer constrain those reflowed cells. There is no bounded
vertical research-results scroller. Text is not shrunk to force a fit.

## Motion and state

See [MOTION.md](MOTION.md) for the implemented grammar. Selection travels with one
transform-based plane; workspace changes Shift, hierarchy Slide, modes Sweep,
secondary information Reveal, actions Confirm. Lock is persistent state, not a
loop. Map selection has one short ring response and linked readout; every valid
point/outlier is retained and one roving Tab stop avoids dozens of Tab presses.

State and focus update immediately. Transitions are interruptible and settle to
the latest intent. Polling does not replay entrances. Both OS and user Reduce
Motion remove positional travel and cancel work already in flight. No continuous
animation, dramatic loading sequence, canvas decoration or motion dependency.

## Responsive and operational durability

The rail becomes compact navigation above content below 800px. At 520px, geometry
simplifies and controls are at least 44px high. At 200% text, controls wrap and
metrics stack; long identities remain readable. Grouped mode and Full Theme are
explicitly covered in addition to the ordinary five destinations and sheets.

Loading, empty results, unavailable history/comparisons, untracked concepts and
connection loss retain their existing distinctions. Disconnection keeps useful
research and names the completed session. Earnings behavior, exports and all
financial/lifecycle/provider/storage rules remain unchanged.

## Asset integrity and scope

`.gitattributes` pins the license to LF and WOFF2 to binary. Static HTML/CSS/JS are
also LF because builders copy their bytes verbatim. Fresh simulated Windows/Unix
checkouts produce identical public output and clean trees. Hash verification stays
strict with the original pinned font/license SHA256 values; no new binary asset.

User-reported Nov 6 and Nov 9 validation PASS; Nov 10 PENDING; Gate E OPEN.
Browser fixtures, screenshots and motion recordings are not real market evidence.
No merge, deployment or new live credentials are part of this design pass.
