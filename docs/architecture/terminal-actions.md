# Approved terminal corporate actions

This is a generic, explicit-approval framework, not automatic event detection or a
ticker-specific exception. Approved records in
[corporate_actions.json](../../config/vnext/corporate_actions.json) bind event terms,
source/approval metadata, valuation session and effective lifecycle. Supported models
cover cash-only, stock-only and cash-plus-stock acquisitions, merger termination,
successor/security conversion and an explicitly known terminal delisting cash value.
Existing split/spin-off bar adjustment remains unchanged.

When an original target-session trading bar is missing, only a matching supported
approved event can supply deterministic value for **existing-holding/index accounting**.
Cash plus stock uses approved cash/ratio and actual usable successor close; the
original last close must also be genuine. Raw economic units are kept separate
from adjusted price units. Missing successor data, unknown events, ambiguous terms
or a record used as a later-session waiver fail closed.

No OHLCV or volume is fabricated. Without its own trading bar, the original ticker
has unavailable stock research/liquidity/W and cannot qualify as a candidate.
After the final return, removal/replacement follows approved first-earned-session
intervals with exclusive `effective_to`. No event is inferred merely from a missing bar.
Sanitized diagnostics identify missing symbols for deliberate review.

## ROKU: first approved real event

The configured merger consideration is **USD 95.30 + 0.9799 FOXA shares**.
The approved terminal valuation is Nov 9, 2026; exclusive removal is Nov 10.
This accounts for the final economic holding return without making ROKU tradeable,
preserves Nov 6 initialization/history, and removes it from later current relations.

The user-confirmed [Nov 10 closure record](../operations/gate-e-closure.md) reports
898 required/valid/trading target inputs, zero terminal target inputs, one historical
input and zero current ROKU relations. These supplied counters do not imply any
unprovided prices or realized economic values.

## Provenance and failure safety

No new schema beyond version 2 is needed. The transaction pins actual observations,
approved terms, valuation proof and input versions. The index verifies economic
terms; storage independently recomputes proof before publication. An audit JSON
object alone cannot waive an unknown missing symbol. Failure rolls back with the
prior dashboard and TXT intact; replay cannot replace a newer publication.

Tests use independent rational oracles with manufactured tickers/prices. Their
numerical values are test evidence, not real merger prices or live chronology.
Original incident analysis/retest instructions are preserved as
[historical provenance](../archive/migration/vnext_terminal_actions.md), not current
instructions to force or relabel an old target session.
