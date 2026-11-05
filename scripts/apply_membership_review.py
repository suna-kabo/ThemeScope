"""Idempotently apply supplied reviewed roles and explicit source-validation records.

No research/classification is performed here. Launch dates cannot be assigned.
"""
from pathlib import Path
import csv,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.themescope.membership_evidence import read_review,rule_coverage,key,unique,validate_evidence


def apply(root=ROOT):
    folder=Path(root)/'config/vnext'
    master,registry,evidence=read_review(root)
    with (folder/'memberships.csv').open(newline='',encoding='utf-8') as handle:old=list(csv.DictReader(handle))
    if any(r['effective_from'] or r['effective_to'] for r in old):raise ValueError('Cannot rewrite activated historical membership')
    covered=rule_coverage(master,registry)
    attachments=unique(evidence['attachments'],'attachments')
    rows=[];queue=[]
    for d in master['decisions']:
        if not d['final_role']:continue
        row={'ticker':d['ticker'],'company':d['company'],'theme_id':d['theme_id'],'role':d['final_role'],
             'effective_from':'','effective_to':'','review_snapshot':master['baseline_snapshot'],
             'evidence_status':d['target_evidence_status'],'evidence_url':d['evidence_url']}
        attachment=attachments.get(key(d))
        if attachment:
            if attachment['status']=='verified':row['evidence_url']=attachment['source_url']
            else:
                row['evidence_status']='primary_source_refresh_required'
                queue.append({k:row[k] for k in ('ticker','company','theme_id','role','review_snapshot')}|
                             {'required_action':attachment['required_fact']+'; '+attachment.get('unresolved_reason','Source validation unresolved')})
        rows.append(row)
    def write_csv(name,fields,records):
        with (folder/name).open('w',newline='',encoding='utf-8') as handle:
            writer=csv.DictWriter(handle,fieldnames=fields,lineterminator='\n');writer.writeheader();writer.writerows(records)
    write_csv('memberships.csv',list(rows[0]),rows)
    write_csv('evidence_review_queue.csv',['ticker','company','theme_id','role','review_snapshot','required_action'],queue)
    gate={'status':'cutover_blocked','membership_review_package':master['package_id'],'findings':[r for r in evidence['inherited_findings'] if r['status']!='verified'],
          'industry_rule_registry_status':'approved','industry_rule_covered_relationships':covered,'source_evidence_queue_count':len(queue),
          'baseline_evidence_queue_count':335,'launch_effective_dates':'pending','production_enabled':False}
    (folder/'evidence_gate.json').write_text(json.dumps(gate,indent=2)+'\n')
    from src.themescope.domain import load_configuration
    return validate_evidence(root,load_configuration(root))

if __name__=='__main__':print(json.dumps(apply(),indent=2))
