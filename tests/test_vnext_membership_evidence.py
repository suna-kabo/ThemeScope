from collections import Counter
from copy import deepcopy
from pathlib import Path
import csv,json,shutil,tempfile,unittest
from scripts.apply_membership_review import apply
from src.themescope.domain import load_configuration
from src.themescope.membership_evidence import validate_evidence,read_review,rule_coverage
ROOT=Path(__file__).resolve().parents[1]

class MembershipEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        shutil.copytree(ROOT/'config/vnext',self.root/'config/vnext')
    def test_authoritative_roles_removals_related_and_minimums(self):
        config=load_configuration(self.root);report=validate_evidence(self.root,config)
        self.assertEqual(report['relationships'],726)
        self.assertEqual(report['roles'],{'Core':659,'Enabler':62,'Related':5})
        self.assertEqual((report['verified_source_tasks'],report['supplemental_verified'],report['remaining_queue']),(167,1,0))
        rows={(m.ticker,m.theme_id):m for m in config.memberships}
        for k in [('EXC','nuclear-energy'),('ZG','internet-commerce'),('SMG','agribusiness')]:self.assertNotIn(k,rows)
        self.assertIn(('Z','internet-commerce'),rows)
        related={('AQN','clean-energy'),('TSLA','robotics-automation'),('F','ev-autonomy'),('GM','ev-autonomy'),('TTC','agribusiness')}
        self.assertEqual({k for k,m in rows.items() if m.role=='Related'},related)
        self.assertTrue(all(not rows[k].calculation_eligible for k in related))
        for k in [('AKAM','cybersecurity'),('ZETA','ai-applications'),('HOOD','fintech-payments')]:self.assertEqual(rows[k].role,'Core')
        self.assertTrue(all(n>=5 for n in report['per_theme_eligible'].values()))
        self.assertTrue(all(m.effective_from is None and m.effective_to is None for m in config.memberships))
        self.assertFalse(config.methodology['production_enabled'])
        self.assertIsNone(config.methodology['launch_rebalance_session'])
        self.assertEqual(len(config.production_blockers()),3)
    def test_industry_rules_cover_exact_tuples_and_explicit_allowlists_only(self):
        master,registry,_=read_review(self.root)
        self.assertEqual(rule_coverage(master,registry),451)
        self.assertEqual(len(registry['registry']['rules']),75)
        copied=deepcopy(master)
        row=next(d for d in copied['decisions'] if d['industry_rule_id'].startswith('EXC-'))
        row['ticker']='UNREVIEWED'
        with self.assertRaisesRegex(ValueError,'allowlist'):rule_coverage(copied,registry)
        copied=deepcopy(master)
        row=next(d for d in copied['decisions'] if d['industry_rule_id'])
        row['industry_snapshot']='Broader industry inference'
        with self.assertRaisesRegex(ValueError,'tuple mismatch'):rule_coverage(copied,registry)
    def test_reapply_is_byte_identical_including_food_and_removed_rows(self):
        folder=self.root/'config/vnext'
        names=('memberships.csv','evidence_review_queue.csv','evidence_gate.json')
        before={name:(folder/name).read_bytes() for name in names}
        apply(self.root);apply(self.root)
        self.assertEqual(before,{name:(folder/name).read_bytes() for name in names})
        self.assertEqual(sum(m.theme_id=='food-beverage' for m in load_configuration(self.root).memberships),23)
    def test_unsupported_source_stays_unresolved_and_queue_never_forced_to_zero(self):
        path=self.root/'config/vnext/primary_source_attachments.json'
        data=json.loads(path.read_text());data['attachments'][0].update(status='evidence_mismatch',unresolved_reason='Synthetic required fact not supported')
        path.write_text(json.dumps(data))
        report=apply(self.root)
        self.assertEqual(report['remaining_queue'],1)
        config=load_configuration(self.root)
        self.assertIn('1 primary-source reviews pending',config.production_blockers())
        with (self.root/'config/vnext/evidence_review_queue.csv').open() as f:queue=list(csv.DictReader(f))
        self.assertEqual(len(queue),1)
        self.assertEqual(queue[0]['ticker'],data['attachments'][0]['ticker'])
    def test_stale_gate_queue_or_undocumented_registry_fails_closed(self):
        folder=self.root/'config/vnext'
        p=folder/'evidence_gate.json';original=p.read_text();data=json.loads(original)
        data['source_evidence_queue_count']=335;p.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,'Stale'):load_configuration(self.root)
        p.write_text(original)
        p=folder/'industry_rule_registry.json';data=json.loads(p.read_text());data['registry']['rules'][0]['tickers'].append('UNREVIEWED');p.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,'Supplied review file changed'):load_configuration(self.root)
    def test_inherited_findings_and_task_source_records_are_complete(self):
        _,_,evidence=read_review(self.root)
        self.assertEqual(len(evidence['attachments']),168)
        self.assertEqual(len({r['source_url'] for r in evidence['attachments']}),158)
        self.assertTrue(all(r['status']=='verified' for r in evidence['attachments']))
        self.assertEqual({(r['ticker'],r['theme_id']) for r in evidence['inherited_findings']},
                         {(s,t) for s in ('AMZN','GOOGL') for t in ('cloud-platforms','internet-commerce')})
        self.assertTrue(all(r['status']=='verified' for r in evidence['inherited_findings']))
    def test_application_refuses_to_rewrite_activated_membership(self):
        path=self.root/'config/vnext/memberships.csv'
        with path.open(newline='') as f:reader=csv.DictReader(f);fields=reader.fieldnames;rows=list(reader)
        rows[0]['effective_from']='2026-11-09'
        with path.open('w',newline='') as f:writer=csv.DictWriter(f,fields);writer.writeheader();writer.writerows(rows)
        original=path.read_bytes()
        with self.assertRaisesRegex(ValueError,'activated historical'):apply(self.root)
        self.assertEqual(path.read_bytes(),original)
