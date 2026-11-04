# Daily Stock scanner and CSV policy v2

Base: authoritative main `234c462`, merged by the owner through PR #5. This
changes Daily Stock liquidity only. No memberships, anchors, identifiers, stock
slots, ETF liquidity rules, Theme Score/Market Matrix/EMA-priority rules or
historical membership reviews are changed.

## Three independent layers

1. **Configured membership:** the existing curated company/theme relationships,
   including their original maintenance facts and old liquidity proxy. No daily
   reselection, refill, removal or ordering change occurs.
2. **Current Daily Stock eligibility:** BOTH one-day turnover **>= $10,000,000
   USD** and 10-day average volume **> 500,000 shares per trading session**.
   Exactly $10M passes; exactly 500,000 shares fails. Other approved scanner
   settings stay unchanged; this module adds no new price/cap/instrument rules.
3. **Daily Primary stock qualification:** membership in a Primary theme,
   verified current eligibility and the unchanged 60%/40% excess-return sign.
   Long requires W > 0, short W < 0; zero/missing returns cannot qualify.

The shared configuration is `config/manual_csv.json:daily_stock_policy`; parsing,
exports and public-site checks use `daily_stock_policy.py`. ETF anchors always
remain independent of these stock liquidity gates.

## Columns, units and native-header evidence

Add **Average volume, 10 days / Average Volume 10D** to the TradingView export.
It is shares per trading session, not money. Keep **Price × volume (turnover),
1 day**, in USD. Remove **Price × average volume, 30 days** if no longer needed.
The old field may be read optionally but never affects the current policy.

The supplied `Daily_Stock_2026-10-31.csv` and `Daily_Stock_2026-11-03.csv` contain
the old 30-day dollar-volume field and no 10-day share-volume header. Therefore
an actual new native header is not sample-verified. The explicit accepted,
case-insensitive contract is:

- `Average volume, 10 days`
- `Average Volume 10D` (deliberate alias)
- `average_volume_10d_shares` (deliberate normalized alias)

A missing column lists these accepted names. Today's volume, relative volume,
30-day average volume and dollar volume cannot substitute; no 10-day value is
derived from turnover/price or any other column. Actual new TradingView import or
scanner UI behavior is not claimed.

All unrelated required fields stay required. Blank, malformed, non-finite or
negative liquidity inputs fail with the role/line/field and preserve the previous
successful output. Zero is a valid measurement that fails the filters, not a
missing value. Known non-USD turnover currency is rejected; no FX conversion is
performed. Shares cannot be supplied as dollars or percentages.

## Stored state and exports

Normalized measurements are `turnover_1d_usd` and
`average_volume_10d_shares`. A separate `daily_stock_eligibility` object records
status, nullable eligibility, reasons, check results, policy version and input
schema. Valid performance stays measurable even when daily eligibility fails.
An absent configured stock remains in its slot with unavailable current values;
its scanner-exclusion cause is unknown. Extra CSV rows never become members.

The Watchlist retains its existing columns. The existing ticker information
tooltip describes daily eligibility; CSV downloads and audits expose its separate
fields/version. The visible vs ETF filter uses W alone and can include a measured
ineligible outperformer. It never becomes a hidden liquidity filter.

Primary stock exports re-evaluate measured eligibility through the shared policy;
a stale `eligible=true` flag cannot override failed measurements. Anchor-first
grouping, score/identifier order and deduplication are unchanged. Ordinary full
individual and complete collection TXT tokens remain unchanged. No reimport of
existing TradingView individual watchlists is required.

Theme breadth keeps the full configured coverage denominator. Missing members
are not counted as below an EMA. Both EMA breadth horizons share the valid set,
including present ineligible rows with valid EMA measurements. Minimum eight and
80% coverage stay unchanged. Index breadth still uses separate unfiltered CSVs.
Build success, configured row completeness and liquidity eligibility are distinct.

## Explicit compatibility

- Output schema: `manual-csv-2`; current stock CSV: `daily-stock-csv-2`;
  liquidity policy: `daily-stock-liquidity-2`; sanitized site: `themescope-site-4`.
- Default `--stock-csv-schema current-v2` requires the new column. Missing 10D
  volume is never silently treated as passing.
- Explicit `--stock-csv-schema legacy-v1` reads the old schema, labels it
  `daily-stock-csv-1` and sets present stock eligibility to `legacy_unverified`.
  Measured historical values remain usable; no stocks enter a newly generated
  current-policy Primary list. Qualifying themes can still export their anchors.
- Existing saved HTML/history remains readable and is never edited in place.
  A new site requires an explicitly refreshed, versioned source run; old site
  schemas may be replaced transactionally but cannot be silently relabelled.
- ETF ranking methodology stays `manual-csv-1`, separately from CSV schema and
  stock policy. No stock policy field enters the Theme Score/rank/EMA-history
  fingerprint. Genuine compatible history remains compatible.

## Validation and handoff

Focused tests cover exact boundaries/AND behavior, invalid and zero values, units,
accepted/missing/decoy headers, optional 30-day independence, ETF/index scope,
legacy uncertainty, stock exclusion versus retained breadth/membership, ordinary
ordering, per-anchor weighted sign and theme-history compatibility. Site tests
recompute eligibility and Primary contents, even after a manifest is resealed.

Clean end-to-end tests use temporary synthetic current-schema CSVs, including a
measured ineligible outperformer, absent members, required-column failures and
legacy replay. Browser checks exercise the unchanged 14-column Watchlist in both
modes, demonstrate that vs ETF still includes that ineligible outperformer, and
compare local/public eligibility. Genuine user history is never overwritten.

The available real old CSVs can test only explicit legacy compatibility. A real
current-policy run still needs the user's new 10-day volume export; no values are
fabricated. Tests and CI results are reported in the associated PR/handoff.

Main is the normal branch. Old audit/download/provider branches are optional
references and are not deleted. The formerly local documentation `696e2d7` is
superseded by updated main-status notes here and in README/audit history; it held
no missing runtime fixes. The owner reports removing the obsolete Cloudflare
Workers trigger. No deployment command or data-bearing push is part of this work.
