"""Offline coverage review; reads a manual CSV and never changes memberships.

Outputs derived coverage and review decisions only, never private market prices,
volumes, returns, or a copy of the TradingView export.
"""
import argparse
from collections import Counter, defaultdict
import csv
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.themescope.domain import iso_date, load_configuration


MISSING_AREAS = {
    'Restaurants': 'restaurants',
    'Major banks': 'money-center-and-diversified-banks',
    'Railroads': 'freight-and-logistics',
    'Trucking': 'freight-and-logistics',
    'Air freight/Couriers': 'freight-and-logistics',
    'Oil refining/Marketing': 'refining-and-fuel-marketing',
    'Containers/Packaging': 'packaging',
}
# These industries do not match a current written theme charter.
OUTSIDE_CHARTERS = {'Tobacco', 'Commercial printing/Forms',
                    'Publishing: newspapers', 'Publishing: books/magazines'}
REQUIRED = {'Symbol', 'Industry', 'Sector', 'Exchange', 'Price',
            'Price - Currency', 'Market capitalization',
            'Market capitalization - Currency'}


def read_base(path):
    """Reject duplicates and invalid quantitative scope rather than repair silently."""
    with Path(path).open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        if not REQUIRED.issubset(reader.fieldnames or ()):
            raise ValueError('Base CSV is missing required columns')
        rows = {}
        for row in reader:
            ticker = row['Symbol']
            if not re.fullmatch(r'[A-Z][A-Z0-9./-]*', ticker or ''):
                raise ValueError('Invalid Base CSV symbol')
            if ticker in rows:
                raise ValueError('Duplicate Base CSV symbol: ' + ticker)
            try:
                price = Decimal(row['Price'])
                cap = Decimal(row['Market capitalization'])
                valid = price.is_finite() and cap.is_finite() and price > 5 and cap > 1_000_000_000
            except InvalidOperation:
                valid = False
            if (not valid or row['Exchange'] not in ('NASDAQ', 'NYSE')
                    or row['Price - Currency'] != 'USD'
                    or row['Market capitalization - Currency'] != 'USD'):
                raise ValueError('Base CSV scope violation: ' + ticker)
            if not row['Industry'] or not row['Sector']:
                raise ValueError('Missing classification: ' + ticker)
            rows[ticker] = row
    if not rows:
        raise ValueError('Base CSV is empty')
    return rows


def matching_rules(ticker, industry, rules, active_ids):
    return [rule for rule in rules if rule['theme_id'] in active_ids
            and rule.get('decision') == 'keep' and rule['industry_snapshot'] == industry
            and (rule['type'] == 'exact_industry'
                 or rule['type'] == 'explicit_allowlist' and ticker in rule['tickers'])]


def audit(base, configuration, rules, as_of):
    if not iso_date(as_of):
        raise ValueError('Audit date required')
    themes = {theme.theme_id: theme for theme in configuration.themes}
    active_ids = {key for key, theme in themes.items() if theme.status == 'active'}
    effective = [m for m in configuration.memberships if m.active_on(as_of)]
    research = [m for m in effective if m.theme_id in active_ids and m.calculation_eligible]
    all_members = {m.ticker for m in effective}
    research_members = {m.ticker for m in research}
    memberships = defaultdict(list)
    for member in effective:
        memberships[member.ticker].append(member)
    existing = {(m.ticker, m.theme_id) for m in effective}
    candidates = []
    classifications = []
    for ticker, row in sorted(base.items()):
        matches = matching_rules(ticker, row['Industry'], rules, active_ids)
        for rule in matches:
            if (ticker, rule['theme_id']) not in existing:
                candidates.append({'ticker': ticker, 'theme_id': rule['theme_id'],
                                   'proposed_role': rule['role'], 'rule_id': rule['rule_id'],
                                   'decision': 'review_addition',
                                   'rationale': rule['rationale'],
                                   'effective_from': None,
                                   'effective_date_policy': 'next completed approval-session close + 1 XNYS session',
                                   'applied': False})
        if ticker in all_members:
            continue
        if matches:
            category = 'likely_existing_theme'
            basis = 'Exact industry / explicit allowlist matches a reviewed existing charter rule'
        elif row['Industry'] in MISSING_AREAS:
            category = 'potential_missing_theme'
            basis = MISSING_AREAS[row['Industry']]
        elif row['Industry'] in OUTSIDE_CHARTERS:
            category = 'outside_current_coverage'
            basis = 'No matching current charter; industry is not a supported thematic activity'
        else:
            category = 'ambiguous_insufficient_evidence'
            basis = 'Industry alone does not establish principal or material theme-specific business'
        classifications.append({'ticker': ticker, 'category': category, 'basis': basis,
                                'candidate_theme_ids': sorted({r['theme_id'] for r in matches})})

    def coverage(field):
        groups = defaultdict(set)
        for ticker, row in base.items():
            groups[row[field]].add(ticker)
        return [{'name': name, 'base': len(tickers),
                 'mapped': len(tickers & all_members),
                 'research_members': len(tickers & research_members),
                 'unmapped': len(tickers - all_members)}
                for name, tickers in sorted(groups.items())]

    by_theme = []
    for theme_id, theme in sorted(themes.items()):
        rows = [m for m in effective if m.theme_id == theme_id]
        tickers = {m.ticker for m in rows}
        by_theme.append({'theme_id': theme_id, 'name': theme.name, 'status': str(theme.status),
                         'roles': dict(sorted(Counter(str(m.role) for m in rows).items())),
                         'members': len(tickers), 'mapped_base': len(tickers & base.keys()),
                         'absent_base': len(tickers - base.keys()),
                         'calculation_members': sum(m.calculation_eligible for m in rows)})
    industry_reviews = []
    for member in effective:
        if member.evidence_status != 'industry_rule_accepted' or member.ticker not in base:
            continue
        industry = base[member.ticker]['Industry']
        matches = matching_rules(member.ticker, industry, rules, active_ids)
        if not any(r['theme_id'] == member.theme_id and r['role'] == str(member.role) for r in matches):
            industry_reviews.append({'ticker': member.ticker, 'theme_id': member.theme_id,
                                     'current_industry': industry,
                                     'decision': 'retain_pending_company_evidence_review',
                                     'reason': 'Current industry no longer matches the accepted rule; a label change alone does not justify removal'})
    return {
        'schema': 'themescope-research-v2-universe-audit-1', 'as_of': as_of,
        'counts': {'base': len(base), 'active_themes': len(active_ids),
                   'all_effective_theme_members': len(all_members),
                   'active_calculation_theme_members': len(research_members),
                   'effective_relationships': len(effective),
                   'active_calculation_relationships': len(research),
                   'mapped_base': len(base.keys() & all_members),
                   'research_mapped_base': len(base.keys() & research_members),
                   'unmapped_base': len(base.keys() - all_members),
                   'members_absent_base': len(all_members - base.keys()),
                   'multi_theme_stocks': sum(len({m.theme_id for m in rows}) > 1 for rows in memberships.values())},
        'roles': dict(sorted(Counter(str(m.role) for m in effective).items())),
        'evidence_statuses': dict(sorted(Counter(m.evidence_status for m in effective).items())),
        'mapped_base': sorted(base.keys() & all_members),
        'members_absent_base': sorted(all_members - base.keys()),
        'multi_theme_stocks': {ticker: sorted({m.theme_id for m in rows})
                               for ticker, rows in sorted(memberships.items())
                               if len({m.theme_id for m in rows}) > 1},
        'coverage_by_sector': coverage('Sector'), 'coverage_by_industry': coverage('Industry'),
        'coverage_by_theme': by_theme, 'unmapped_review': classifications,
        'unmapped_categories': dict(sorted(Counter(r['category'] for r in classifications).items())),
        'missing_area_candidates': dict(sorted(Counter(r['basis'] for r in classifications
                                            if r['category'] == 'potential_missing_theme').items())),
        'membership_review': candidates,
        'current_membership_industry_reviews': industry_reviews,
        'ended_relationships': [{'ticker': m.ticker, 'theme_id': m.theme_id,
                                 'effective_to': m.effective_to, 'decision': 'preserve_approved_end'}
                                for m in configuration.memberships
                                if m.effective_to and m.effective_to <= as_of],
        'safety': {'memberships_changed': False, 'historical_inputs_changed': False,
                   'prices_or_volumes_exported': False,
                   'security_type': 'Common Stock is exporter-supplied scope; CSV has no security-type column'},
    }


def review_completion(result, configuration, amendment):
    """Separate screening/charter triage from actual company-evidence decisions."""
    candidates = result['membership_review']
    groups = defaultdict(list)
    for row in candidates:
        groups[row['theme_id']].append(row)
    charters = {theme.theme_id: theme for theme in configuration.themes}
    decisions = [{'ticker': row['ticker'], 'theme_id': row['theme_id'],
                  'decision': 'approved_forward_amendment', 'reviewed_on': amendment['reviewed_on'],
                  'effective_from': amendment['effective_from'],
                  'source_url': row['evidence']['source_url'],
                  'rationale': row['evidence']['support_summary']} for row in amendment['additions']]
    decisions += [
        dict(ticker='FTDR', theme_id='homebuilders', decision='rejected_company_review',
             source_url='https://www.frontdoorhome.com/about/',
             rationale='Home-maintenance service plans do not establish principal residential construction'),
        dict(ticker='FSLR', theme_id='semiconductors', decision='rejected_company_review',
             source_url='https://www.firstsolar.com/en/About-Us/Overview',
             rationale='Solar manufacturing belongs to its supported Solar charter; a broad industry label does not establish this semiconductor relationship'),
        dict(ticker='CVCO', theme_id='homebuilders', decision='suitable_proposal_pending_separate_approval',
             reviewed_on='2026-11-15', source_url='https://investor.cavco.com/',
             rationale='Issuer describes principal manufactured/modular housing; a suitable charter fit, kept unapplied pending its own dated approval rather than backdating the existing amendment'),
        dict(ticker='LEN.B', theme_id='homebuilders', decision='deferred_share_class_policy',
             reviewed_on='2026-11-15',
             source_url='https://www.sec.gov/Archives/edgar/data/920760/000162828026003870/len-20251130.htm',
             rationale='Issuer confirms a second share class of already represented LEN; review duplicate-issuer treatment before adding another economically overlapping security')]
    candidate_pairs = {(row['ticker'], row['theme_id']) for row in candidates}
    decisions = [row for row in decisions if (row['ticker'], row['theme_id']) in candidate_pairs]
    cohorts = []
    evidence_gaps = {
        'regional-banks':'Establish actual regional banking operations and geography; distinguish bank operators from other financial issuers',
        'pharmaceuticals':'Establish principal drug-development/manufacturing exposure and distinguish distributors, service providers and mixed businesses',
        'capital-markets':'Establish the operating capital-markets business; distinguish managers/brokers/exchanges from investment vehicles and incidental holdings',
        'insurance':'Establish insurance underwriting, reinsurance or brokerage operations and the proposed Core/Enabler relationship',
        'retail':'Distinguish retail operators from brands, wholesalers and manufacturers; verify the principal customer-facing retail activity',
        'biotechnology':'Inspect current pipeline and operating activities; resolve biotech/pharma/platform overlap rather than relying on the industry tag',
        'construction-infrastructure':'Verify physical infrastructure exposure and charter exclusions, particularly pure homebuilding and generic industrial activity',
        'aerospace-defense':'Verify issuer aerospace/defense activity and segment materiality rather than inferring exposure from general component manufacturing',
        'leisure-entertainment':'Verify the actual leisure/entertainment operator and resolve media, platform and untracked gaming overlap',
        'healthcare-providers':'Establish care delivery or healthcare-service operations; distinguish drug/device businesses and incidental health exposure',
        'oil-gas-producers':'Verify upstream production exposure and distinguish producing operations from royalty, midstream and refining businesses',
        'marine-shipping':'Verify the commercial shipping business and distinguish operator, leasing, port and shipbuilding relationships',
        'agribusiness':'Verify principal agricultural/input operations and distinguish general food processing, retail and incidental commodity exposure',
        'semiconductors':'Verify chip design/fabrication/equipment activity; FSLR demonstrates that an industry label can otherwise admit solar manufacturing',
        'homebuilders':'Verify principal residential construction; FTDR fails that relationship, CVCO fits but awaits separate approval, LEN.B needs share-class review',
        'oil-services':'Verify drilling/oilfield-service activity and distinguish producers and general industrial suppliers',
        'airlines':'Verify airline transport operations and distinguish lessors, travel intermediaries and other transport businesses',
        'midstream-lng':'Verify pipeline, storage, processing or LNG infrastructure operations and distinguish upstream producers and incidental suppliers',
        'timber-forestry':'Verify principal forestry/timber activity and resolve packaging, pulp, general real-estate and mixed-business exposure',
        'water':'Verify principal/material water or wastewater operations; original three screened omissions have issuer-backed approvals in the amendment',
    }
    for theme_id, rows in sorted(groups.items()):
        charter = charters[theme_id]
        cohorts.append(dict(theme_id=theme_id, candidate_relationships=len(rows),
            rule_ids=sorted({row['rule_id'] for row in rows}),
            charter=charter.definition, exclusions=charter.excluded_activities,
            required_review=evidence_gaps.get(theme_id,'Verify issuer principal/material activities, charter exclusions, proposed role and current identity'),
            decision='defer_unreviewed_companies_without_auto_apply'))
    return dict(machine_candidates=len(candidates), cohort_triage=cohorts,
                company_decisions=decisions,
                not_company_evidence_reviewed=len(candidates)-len(decisions),
                exhaustive_company_review_complete=False,
                screening_never_applies_membership=True)


def markdown(result):
    counts = result['counts']
    lines = ['# Research Logic v2: universe and membership audit', '',
             f"As of {result['as_of']}. Offline manual-export comparison; no runtime history was changed.", '',
             '## Coverage', '', '| Measure | Count |', '| --- | ---: |']
    lines += [f'| {key.replace("_", " ")} | {value} |' for key, value in counts.items()]
    lines += ['', 'Mapped means any effective reviewed relationship, including Related and watch-only themes. '
              'Research membership means Core/Enabler in an Active theme. These are separate from the '
              'provider completeness union and SPY/QQQ context rosters.', '',
              'Roles: ' + ', '.join(f'{key} {value}' for key, value in result['roles'].items()) + '.', '',
              '## Review decisions', '',
              'The existing evidence-validated launch membership is the seed, not a coverage target. '
              'No relationship is deleted because its ticker is absent from the new export; price, cap, '
              'listing and timing changes do not disprove its business relationship.', '',
              f"{len(result['membership_review'])} missing relationships match an already reviewed exact-industry "
              'or explicit-allowlist rule. The JSON contains every proposed addition, role, rule, rationale '
              'and unapplied effective-date policy. Review candidates include both unmapped stocks and '
              'additional legitimate relationships for already mapped stocks. They are not automatically '
              'approved memberships. CSV industry labels are useful screening evidence, not proof of '
              'company-specific exposure, current listing identity or an approval date.', '',
              'Unmapped classifications: ' + ', '.join(f'{key}: {value}' for key, value in result['unmapped_categories'].items()) + '.', '',
              'Potential missing areas (unmapped stocks): ' + ', '.join(f'{key}: {value}' for key, value in result['missing_area_candidates'].items()) + '.', '',
              'These are investigation queues, not newly created themes. A coherent industry does not '
              'by itself establish that another theme improves research value; charter, overlap, durable '
              'constituent set and source review are required before activation. Ambiguous names remain '
              'unmapped rather than being forced into a theme.', '',
              f"{len(result['current_membership_industry_reviews'])} current industry-rule relationships no longer match "
              'the latest classification. The JSON flags each for company-evidence review; an industry-label '
              'change does not rewrite a reviewed business relationship.', '',
              'Approved terminal-event ends: ' + (', '.join(f"{r['ticker']} / {r['theme_id']} ends {r['effective_to']}"
                                                          for r in result['ended_relationships']) or 'none') + '.', '',
              'Evidence status counts: ' + ', '.join(f'{key}: {value}' for key, value in result['evidence_statuses'].items()) + '.', '',
              'The current loader validates reviewed roles, evidence provenance and effective intervals '
              'before this audit; its approved corporate-action overlay is included. Original launch '
              'CSV and archived review decisions remain intact. Future approved changes must be '
              'forward-dated to the next XNYS session after approval at close; never backdated.', '',
              '## Sector coverage', '', '| Sector | Base | Mapped | Research | Unmapped |', '| --- | ---: | ---: | ---: | ---: |']
    lines += [f"| {r['name']} | {r['base']} | {r['mapped']} | {r['research_members']} | {r['unmapped']} |"
              for r in result['coverage_by_sector']]
    lines += ['', '## Theme coverage', '', '| Theme | Status | Members | Base overlap | Absent Base | Core/Enabler |',
              '| --- | --- | ---: | ---: | ---: | ---: |']
    lines += [f"| {r['name']} | {r['status']} | {r['members']} | {r['mapped_base']} | {r['absent_base']} | {r['calculation_members']} |"
              for r in result['coverage_by_theme']]
    review = result.get('reviewed_amendment')
    if review:
        lines += ['', '## Evidence-reviewed forward additions', '',
                  f"Review {review['reviewed_on']}; first effective XNYS session {review['effective_from']}. "
                  'Seven company-specific Core additions expand existing charters. The launch CSV, original '
                  'evidence package and prior observations remain unchanged.', '',
                  '| Stock | Theme | Decision and issuer evidence |', '| --- | --- | --- |']
        lines += [f"| {r['ticker']} | {r['theme_id']} | Add Core: {r['evidence']['support_summary']} "
                  f"[Issuer source]({r['evidence']['source_url']}) |" for r in review['additions']]
        lines += ['', 'Every source fingerprint is SHA256 of the stored short UTF-8 supporting excerpt, '
                  'explicitly labeled as such; it is not a claimed full-page-body hash. The manual export '
                  'supplies sanitized symbol/venue/common-stock identity. No raw price or volume is included.', '',
                  '| Coverage | As-of audit | After forward additions |', '| --- | ---: | ---: |']
        lines += [f"| {key.replace('_', ' ')} | {counts[key]} | {value} |"
                  for key, value in review['effective_counts'].items()]
        lines += ['', 'No existing relationship was removed or reclassified. Broad scanner-rule matches '
                  'remain proposals; they are not part of this amendment. Frontdoor is rejected as a '
                  'Homebuilders addition: its issuer describes maintenance/service plans rather than '
                  'residential construction ([source](https://www.frontdoorhome.com/about/)). First Solar '
                  'remains a solar-manufacturing company; a generic semiconductor industry label is not '
                  'a reason to add it to Semiconductors ([source](https://www.firstsolar.com/en/About-Us/Overview)).', '',
                  '## Missing-theme investigation', '',
                  'Freight/logistics is the clearest coherent coverage gap: 26 unmapped rail, trucking '
                  'and courier names. Issuer profiles confirm substantial freight businesses at '
                  '[Union Pacific](https://www.up.com/about-us), '
                  '[UPS](https://about.ups.com/us/en/our-company.html) and '
                  '[Old Dominion](https://www.odfl.com/us/en/about.html). A candidate charter would '
                  'cover freight transport and logistics networks, excluding passenger airlines and marine '
                  'shipping already covered elsewhere. It spans materially different parcel, rail and '
                  'less-than-truckload businesses; activating a single broad basket before reviewing all '
                  '26 company relationships would obscure those differences. Decision: retain the named '
                  'investigation queue, create no theme in this amendment. This is a coverage decision, '
                  'not an assertion that these companies lack thematic value. Banks, packaging, refining '
                  'and restaurants similarly remain explicit unsupported-area queues rather than forced '
                  'members of unrelated current charters.', '']
    completion = result.get('review_completion')
    if completion:
        lines += ['', '## Review scope and deliberately deferred work', '',
                  f"Machine screening identified {completion['machine_candidates']} proposed relationships. "
                  f"All {len(completion['cohort_triage'])} theme cohorts received charter/evidence-gap triage; "
                  'this is not issuer review of every candidate. '
                  f"Company-evidence decisions cover {len(completion['company_decisions'])} candidate relationships: "
                  'seven approved forward additions, two rejected proposals, one suitable proposed addition '
                  'awaiting a separate approval artifact, and one share-class deferral. '
                  f"The remaining {completion['not_company_evidence_reviewed']} proposals have not received "
                  'company-level evidence review and remain explicitly deferred. No other approval is implied.', '',
                  '| Theme cohort | Machine candidates | Further evidence required |', '| --- | ---: | --- |']
        lines += [f"| {row['theme_id']} | {row['candidate_relationships']} | {row['required_review']} |"
                  for row in completion['cohort_triage']]
        lines += ['', 'The complete-coverage audit and cohort triage are finished; an exhaustive '
                  'company-by-company review of all 560 proposals is **not** finished and is not claimed. '
                  'The release checklist wording “Missing/misaligned memberships reviewed” refers only '
                  'to the documented scope above, not blanket company approval.', '',
                  'Additional issuer checks: [Cavco](https://investor.cavco.com/) describes a principal '
                  'manufactured/modular housing business, making CVCO a suitable Homebuilders proposal. '
                  'It remains unapplied until a separate dated approval artifact; it is not appended '
                  'retroactively to the November 14 amendment. '
                  '[Lennar’s issuer filing](https://www.sec.gov/Archives/edgar/data/920760/000162828026003870/len-20251130.htm) '
                  'identifies LEN.B as another share class of the issuer already represented by LEN. '
                  'Adding that security is deferred until an explicit duplicate-issuer/share-class '
                  'policy is reviewed; no new weighting formula is invented here.', '']
    lines += ['', 'Full industry coverage, unmapped classifications, absent members, multi-theme '
              'relationships and proposed additions are in `research-v2-universe-audit.json`.', '',
              '## Reproduce and limits', '',
              '```powershell',
              '.venv-vnext/Scripts/python.exe scripts/research_v2_universe_audit.py --input "Daily_Stock_2026-11-14 (1).csv" --as-of 2026-11-14',
              '```', '',
              'NASDAQ/NYSE, USD price > $5 and market cap > $1B are validated for every input row; '
              'duplicate, missing and invalid rows fail visibly. Common-stock status is supplied by '
              'the manual export settings because the CSV does not contain a security-type field. '
              'No daily-volume or turnover screen is applied to Base membership. This is not a daily '
              'provider dependency. Source hashes identify local inputs without publishing raw private '
              'prices/volumes/returns or personal absolute paths.', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--as-of', required=True)
    parser.add_argument('--output', type=Path, default=ROOT / 'reports')
    args = parser.parse_args()
    configuration = load_configuration(ROOT)
    registry = ROOT / 'config/vnext/industry_rule_registry.json'
    rules = json.loads(registry.read_text(encoding='utf-8'))['registry']['rules']
    base = read_base(args.input)
    result = audit(base, configuration, rules, args.as_of)
    review_path = ROOT / 'config/vnext/research_v2_membership_review.json'
    if review_path.exists():
        from src.themescope.research.membership_review import apply_review
        review = json.loads(review_path.read_text(encoding='utf-8'))
        if sha256(args.input.read_bytes()).hexdigest() != review['base_universe_source']['sha256']:
            raise ValueError('Reviewed amendment belongs to a different Base export')
        for row in review['additions']:
            if row['ticker'] not in base or base[row['ticker']]['Exchange'] != row['instrument']['exchange']:
                raise ValueError('Reviewed addition does not match Base instrument')
        sessions = json.loads((ROOT / 'config/calendars/xnys_2020_2035_v1.json').read_text(encoding='utf-8'))['sessions']
        days = [row['session'] for row in sessions]
        # The loader may already have applied the validated overlay; do not apply twice.
        amended = configuration if configuration.universe.get('research_v2_review') else apply_review(configuration, review, days)
        result['reviewed_amendment'] = dict(review, effective_counts=audit(base, amended, rules, review['effective_from'])['counts'])
        result['review_completion'] = review_completion(result, configuration, review)
    sources = [args.input, registry, ROOT / 'config/vnext/memberships.csv',
               ROOT / 'config/vnext/themes.csv', ROOT / 'config/vnext/corporate_actions.json',
               ROOT / 'config/vnext/membership_master_review.json',
               ROOT / 'config/vnext/primary_source_attachments.json']
    if review_path.exists():
        sources.append(review_path)
    result['sources'] = {path.name: sha256(path.read_bytes()).hexdigest() for path in sources}
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'research-v2-universe-audit.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
    (args.output / 'research-v2-universe-audit.md').write_text(markdown(result), encoding='utf-8', newline='\n')
    print(json.dumps(result['counts'], indent=2))


if __name__ == '__main__':
    main()
