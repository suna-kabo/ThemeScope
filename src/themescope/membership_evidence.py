"""Validate supplied membership judgments and evidence governance; never classify."""
from collections import Counter
from pathlib import Path
from hashlib import sha256
from urllib.parse import urlparse
import csv,json


def key(row):return row['ticker'],row['theme_id']


def unique(rows,label):
    result={key(r):r for r in rows}
    if len(result)!=len(rows):raise ValueError('Duplicate '+label)
    return result


def rule_coverage(master,registry):
    rules={r['rule_id']:r for r in registry['registry']['rules']}
    if len(rules)!=len(registry['registry']['rules']):raise ValueError('Duplicate industry rule')
    for rule in rules.values():
        if rule['type'] not in ('exact_industry','explicit_allowlist') or not rule.get('rationale'):
            raise ValueError('Undocumented industry rule')
        if rule['type']=='explicit_allowlist' and (not rule.get('tickers') or len(set(rule['tickers']))!=len(rule['tickers'])):
            raise ValueError('Invalid explicit allowlist')
    count=0
    for decision in master['decisions']:
        if decision['target_evidence_status']!='industry_rule_accepted':continue
        rule=rules.get(decision['industry_rule_id'])
        if rule is None or any(rule[field]!=decision[source] for field,source in
                (('theme_id','theme_id'),('role','final_role'),('industry_snapshot','industry_snapshot'))):
            raise ValueError('Industry rule tuple mismatch: '+str(key(decision)))
        if rule['type']=='explicit_allowlist' and decision['ticker'] not in rule['tickers']:
            raise ValueError('Ticker outside explicit allowlist: '+str(key(decision)))
        count+=1
    return count


def reviewed_json_sha256(path):
    """Hash reviewed UTF-8 JSON text, ignoring only checkout CRLF representation.

    Strict decoding and literal CRLF replacement preserve all other bytes/content,
    including whitespace, lone CR, BOM and JSON formatting. Never use for binaries.
    """
    text=Path(path).read_bytes().decode('utf-8')
    return sha256(text.replace('\r\n','\n').encode('utf-8')).hexdigest()


def validate_supplied_files(folder):
    audit=json.loads((folder/'membership_review_provenance.json').read_text(encoding='utf-8'))
    for name,expected in [('industry_rule_registry.json',audit['source_files_sha256']['themescope_industry_rule_registry_2026-11-06.json']),
                          ('primary_source_attachment_tasks.json',audit['source_files_sha256']['themescope_primary_source_attachment_tasks_2026-11-06.json'])]:
        if reviewed_json_sha256(folder/name)!=expected:raise ValueError('Supplied review file changed: '+name)
    if reviewed_json_sha256(folder/'membership_master_review.json')!=audit['normalized_master_sha256']:
        raise ValueError('Master decisions changed without reviewed provenance')


def read_review(root):
    folder=Path(root)/'config/vnext'
    validate_supplied_files(folder)
    read=lambda name:json.loads((folder/name).read_text(encoding='utf-8'))
    return read('membership_master_review.json'),read('industry_rule_registry.json'),read('primary_source_attachments.json')


def validate_evidence(root,configuration=None):
    folder=Path(root)/'config/vnext'
    master,registry,evidence=read_review(root)
    decisions=unique(master['decisions'],'master decision')
    if len(decisions)!=master['baseline_relationship_count']:raise ValueError('Master baseline count mismatch')
    covered=rule_coverage(master,registry)
    if covered!=master['summary']['target_industry_rule_accepted']:raise ValueError('Industry rule count mismatch')
    tasks=json.loads((folder/'primary_source_attachment_tasks.json').read_text(encoding='utf-8'))['tasks']
    attachments=unique(evidence['attachments'],'source attachment')
    required=unique(tasks,'source task')
    extra={k for k,r in decisions.items() if r['source_action']=='attach_latest_official_source'}-required.keys()
    if attachments.keys()!=required.keys()|extra:raise ValueError('Attachment task coverage mismatch')
    for k,record in attachments.items():
        if record['final_role']!=decisions[k]['final_role']:raise ValueError('Attachment role mismatch')
        if k in required and record['required_fact']!=required[k]['required_fact']:raise ValueError('Required fact changed')
        if record['status']=='verified':
            if (urlparse(record['source_url']).scheme!='https' or not record.get('support_summary')
                    or len(record.get('source_sha256',''))!=64):raise ValueError('Incomplete inspected source')
    with (folder/'memberships.csv').open(newline='',encoding='utf-8') as handle:rows=list(csv.DictReader(handle))
    memberships=unique(rows,'membership')
    retained={k:r for k,r in decisions.items() if r['final_role']}
    if memberships.keys()!=retained.keys():raise ValueError('Retained/removed membership mismatch')
    unresolved={k for k,r in attachments.items() if r['status']!='verified'}
    approval_path=folder/'launch_approval.json'
    approval=json.loads(approval_path.read_text()) if approval_path.exists() else None
    if approval:
        from .domain import iso_date
        if (approval.get('schema_version')!=1 or approval.get('retained_relationships')!=len(retained)
                or not iso_date(approval['launch_rebalance_session'])
                or not iso_date(approval['first_earned_session'])
                or approval['first_earned_session']<=approval['launch_rebalance_session']
                or not approval['approved_before_launch_session'] or not approval['production_enabled']):
            raise ValueError('Explicit launch approval required')
        schedule=Path(root)/'config/calendars/xnys_2020_2035_v1.json'
        if schedule.exists():
            from .domain import effective_session_after_close
            days=[r['session'] for r in json.loads(schedule.read_text())['sessions']]
            if effective_session_after_close(approval['launch_rebalance_session'],days)!=approval['first_earned_session']:
                raise ValueError('Approved effective date is not next XNYS session')
    for k,row in memberships.items():
        decision=retained[k]
        if row['role']!=decision['final_role']:raise ValueError('Reviewed role changed: '+str(k))
        if row['effective_to'] or row['effective_from']!=(approval['first_earned_session'] if approval else ''):
            raise ValueError('Membership date differs from explicit launch approval')
        expected='primary_source_refresh_required' if k in unresolved else decision['target_evidence_status']
        if row['evidence_status']!=expected:raise ValueError('Evidence status mismatch: '+str(k))
        if k in attachments and k not in unresolved and row['evidence_url']!=attachments[k]['source_url']:
            raise ValueError('Attachment URL mismatch')
        if expected!='industry_rule_accepted' and k not in unresolved and not row['evidence_url']:
            raise ValueError('Primary evidence URL absent')
    with (folder/'evidence_review_queue.csv').open(newline='',encoding='utf-8') as handle:queue=unique(list(csv.DictReader(handle)),'queue')
    if queue.keys()!=unresolved:raise ValueError('Queue must equal unresolved tasks')
    gate=json.loads((folder/'evidence_gate.json').read_text())
    if approval and any(gate.get(field)!=approval[field] for field in ('launch_rebalance_session','first_earned_session')):
        raise ValueError('Stale launch gate metadata')
    if gate['source_evidence_queue_count']!=len(unresolved):raise ValueError('Stale evidence gate count')
    if gate['industry_rule_registry_status']!='approved' or gate['industry_rule_covered_relationships']!=covered:
        raise ValueError('Industry rule gate mismatch')
    resolutions=unique(master['inherited_finding_resolutions'],'reviewed inherited resolution')
    findings=unique(evidence['inherited_findings'],'inherited source validation')
    if resolutions.keys()!=findings.keys():raise ValueError('Inherited finding coverage mismatch')
    for k,r in findings.items():
        if r['status']=='verified' and (r['evidence_url']!=resolutions[k]['evidence_url'] or not r.get('support_summary') or len(r.get('source_sha256',''))!=64):
            raise ValueError('Inherited evidence mismatch')
    if {key(r) for r in gate['findings']}!={k for k,r in findings.items() if r['status']!='verified'}:
        raise ValueError('Stale inherited findings')
    counts=Counter(r['role'] for r in rows)
    if counts!={'Core':master['summary']['final_core'],'Enabler':master['summary']['final_enabler'],'Related':master['summary']['final_related']}:
        raise ValueError('Reviewed role totals mismatch')
    per_theme={}
    for row in rows:
        if row['role'] in ('Core','Enabler'):per_theme[row['theme_id']]=per_theme.get(row['theme_id'],0)+1
    if per_theme!={k:r['eligible_total'] for k,r in master['final_theme_counts'].items()}:
        raise ValueError('Reviewed per-theme totals mismatch')
    if configuration is not None:
        if any(t.status=='active' and per_theme.get(t.theme_id,0)<5 for t in configuration.themes):raise ValueError('Active minimum violated')
        if configuration.methodology['production_enabled']!=bool(approval) or configuration.methodology['launch_rebalance_session']!=(approval['launch_rebalance_session'] if approval else None):
            raise ValueError('Production/launch differs from explicit approval')
        if gate['production_enabled']!=bool(approval) or gate['launch_effective_dates']!=('approved' if approval else 'pending'):
            raise ValueError('Stale launch gate metadata')
    return {'relationships':len(rows),'roles':dict(counts),'industry_rules':len(registry['registry']['rules']),
            'rule_covered_relationships':covered,'verified_source_tasks':sum(attachments[k]['status']=='verified' for k in required),
            'supplemental_verified':sum(attachments[k]['status']=='verified' for k in extra),
            'remaining_queue':len(unresolved),'inherited_findings_remaining':len(gate['findings']),'per_theme_eligible':per_theme}
