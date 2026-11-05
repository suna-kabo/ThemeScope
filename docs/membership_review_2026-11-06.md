# Membership master review applied — 2026-11-06

The supplied package is authoritative for classification. No taxonomy or calculation formula was redesigned.
Its 729 baseline keys and original roles match commit 94050ac exactly. Reapplication is byte-identical, including the Food & Beverage batch.

## Result

- Retained relationships: 726 across 668 tickers; Core 659, Enabler 62, Related 5.
- Removed: EXC / nuclear-energy; ZG / internet-commerce (Z retained); SMG / agribusiness.
- All 167 source-attachment tasks verified; YOU / cybersecurity additionally attached because its master decision requests a source but it is absent from the task file.
- 168 attachment records reference 158 distinct inspected sources. Four inherited AMZN/GOOGL findings are separately verified against two annual filings.
- No evidence mismatches remain; queue is empty.
- Industry registry: 75 supplied rules, 451 covered relationships; exact tuples and explicit allowlists only. Registry status approved after validation.
- All launch effective_from/effective_to remain blank; launch session unset; production disabled.

## Evidence provenance and selection

Versioned configuration includes the normalized master decisions, unchanged supplied rule registry/task file, source-validation records and package/file hashes. Raw annual reports, quarterly filings and PDFs remain outside Git. The package scanner-volume note is excluded; no private market-data payload is committed.
primary_source_attachments.json records the exact source URL, source content SHA256, filing period/date where established, required fact, reviewed final role, review date and a short supporting paraphrase for each relationship. Source verification is human-reviewed input; the offline validator checks structural consistency rather than claiming to prove financial facts from keywords.
Most sources are latest suitable annual SEC filings identified from issuer submissions. Fervo and Gentex use SEC quarters: Fervo has no annual filing after its IPO; Gentex's later report directly documents DMS/ICMS commercial shipments. X-energy uses its official reactor product description; MDA uses its official 2025 annual report linked by issuer IR. Uber's official Autonomous Solutions release directly documents its commercialization offering more clearly than the annual risk discussion. These source choices do not change the supplied roles.
The 107 retained primary-evidence records outside these 168 attachments retain the supplied completed-review citations/statuses (including the provided Food & Beverage sources). They are distinguished from the new mechanical attachments; no independent reclassification or invented citation was used.
The four inherited findings retain the package's exact reviewed resolutions and annual-report URLs; all four supporting records are verified in primary_source_attachments.json. The industry registry is preserved verbatim, with source-hash checks preventing broader undocumented substitutions.

## Reproduce and validate

Run from repository root:

```sh
python scripts/apply_membership_review.py
python scripts/validate_membership_evidence.py
python scripts/validate_vnext_config.py
python -m unittest discover -s tests -v
```

Application regenerates the queue from unresolved attachments. An unsupported task stays primary_source_refresh_required with its exact required fact/source/reason available for review; it cannot be forced clear by an expected total. The script refuses to rewrite any activated membership. Runtime config loading validates master roles, rule coverage, task/queue/gate consistency and pending launch safety.

## Per-theme eligible Core + Enabler counts

| Theme ID | Eligible |
| --- | ---: |
| aerospace-defense | 21 |
| agribusiness | 12 |
| ai-applications | 6 |
| ai-infrastructure | 25 |
| airlines | 5 |
| biotechnology | 47 |
| capital-markets | 25 |
| clean-energy | 15 |
| cloud-platforms | 16 |
| construction-infrastructure | 21 |
| copper-miners | 5 |
| cybersecurity | 18 |
| data-centers | 6 |
| digital-assets | 13 |
| enterprise-software | 31 |
| ev-autonomy | 10 |
| fintech-payments | 20 |
| food-beverage | 23 |
| genomics | 16 |
| gold-miners | 13 |
| healthcare-providers | 26 |
| homebuilders | 7 |
| insurance | 27 |
| internet-commerce | 23 |
| leisure-entertainment | 15 |
| marine-shipping | 11 |
| medical-devices | 23 |
| midstream-lng | 17 |
| mortgage-reits | 5 |
| natural-gas-producers | 8 |
| nuclear-energy | 13 |
| oil-gas-producers | 23 |
| oil-services | 19 |
| pharmaceuticals | 17 |
| regional-banks | 24 |
| residential-reits | 9 |
| retail | 20 |
| robotics-automation | 9 |
| semiconductors | 40 |
| silver-miners | 7 |
| solar | 5 |
| space-economy | 12 |
| timber-forestry | 5 |
| water | 8 |

All 44 Active themes retain at least five eligible members. Related rows never enter calculations; removed rows are absent, and ZG no longer duplicates Z in internet-commerce.

## Remaining production blockers

Launch effective dates pending; launch rebalance session not approved; production cutover disabled. Runtime roster gating remains in force (approved SPY/QQQ rosters effective 2026-11-05). Native Windows/performance validation items remain separate. No Phase 9, main changes, formula changes, live Alpaca calls or deployment. Existing inspection checkpoints are preserved.

## Validation results

Full suite: 295 cases, 293 passed and two Windows-only skips. Focused vNext: 88
cases, 87 passed and one Windows-only skip; seven new evidence tests passed.
Configuration, count and rule validation, Python compilation, JavaScript checks
and safe inspection generation passed. Legacy/Market Matrix baselines unchanged.
