import copy
import csv
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import re

from src.themescope.site_output import prepare_site,public_payload,seal_site,validate_site,placeholder_site

ROOT=Path(__file__).resolve().parents[1]
CANARY='PRIVATE_INPUT_HISTORY_REVIEW_CANARY'


def sample():
    stock={'ticker':'NVDA','company':'NVIDIA','tradingview_symbol':'NASDAQ:NVDA','price_close':100,'ema21':90,'ema50':80,'daily_change':.01,'returns':{'21':{'value':.1,'status':'valid'}},'selection_slot':1,'metric_status':'available','membership_rationale':CANARY,'maintenance':{'private':CANARY},'source_url':CANARY,'excess21_pp':3}
    theme={'id':'theme-semiconductors','name':'Semiconductors','anchor':'SMH','tradingview_symbol':'NASDAQ:SMH','theme_score':50,'global_rank':1,'rank_current':1,'rank_change_daily':0,'rank_comparison_session':'2026-10-30','returns':{'21':{'value':.07,'status':'valid'}},'selected':[stock],'research_priority':{'category':'watch','label':'Watch'},'private_review':CANARY}
    snapshot={'session_date':'2026-11-02','generated_at':'2026-11-03T00:00:00+00:00','dashboard_generated_at':'2026-11-03T00:00:00+00:00','dashboard_generated_at_hkt_display':'3 Nov 2026, 08:00 AM HKT','run_kind':'manual_csv','manual_csv_audit':{'publication_pass':True,'inputs':{'stock':{'path':CANARY}}},'raw_inputs':CANARY,'local_history':{'comparison_session':'2026-10-30','fingerprint':CANARY,'status':CANARY},'score_methodology':{'theme_score_weights':{'current_strength':.6,'medium_strength':.4}},'ui_configuration':{'score_bands':[]},'context':[],'themes':[theme],'decision':{},'market_classification':{},'expected_earnings':{'as_of':'2026-11-02','through':'2026-11-09','later_count':0,'upcoming':[],'unknown':[]},'export_manifest':[{'file':'individual_watchlists/SMH_Semiconductors.txt','role':'individual_research','theme_id':theme['id'],'anchor':'SMH','instrument_count':2,'stock_count':1,'section_count':0}]}
    snapshot['export_configuration']={'instrument_limit':1000}
    from src.themescope.daily_lists import primary_research
    primary_research(snapshot,1000)
    return snapshot



class SiteBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name).resolve();self.source=self.base/'private-run';self.source.mkdir();self.destination=self.base/'site'
        self.snapshot=sample();(self.source/'latest_snapshot.json').write_text(json.dumps(self.snapshot))
        (self.source/'individual_watchlists').mkdir()
        (self.source/'individual_watchlists/SMH_Semiconductors.txt').write_text('NASDAQ:SMH,NASDAQ:NVDA\n')
        for name in ('themes.csv','theme_stocks.csv'):
            with (self.source/name).open('w',newline='') as f:
                writer=csv.DictWriter(f,fieldnames=['theme_id','ticker','price','membership_reason']);writer.writeheader();writer.writerow({'theme_id':'theme-semiconductors','ticker':'NVDA','price':100,'membership_reason':CANARY})
        (self.source/'raw_inputs.json').write_text(CANARY)
        (self.source/'run_audit.json').write_text(CANARY)
        (self.source/'local_history').mkdir();(self.source/'local_history/2026-10-30.json').write_text(CANARY)

    def build(self):return prepare_site(ROOT,self.source,self.destination,'2026-11-02')

    def test_daily_primary_site_parity_filtered_exports_and_empty_replacement(self):
        from src.themescope.daily_lists import primary_research
        snapshot=self.snapshot;theme=snapshot['themes'][0]
        snapshot['market_classification']={'direction':'Long bias'}
        theme['research_priority']={'category':'primary','label':'Primary long','side':'long','group':0}
        theme['returns']['63']={'value':.1};theme['selected'][0]['returns']['63']={'value':.2}
        files,manifest=primary_research(snapshot,1000)
        snapshot['export_manifest']+=manifest
        for name,content in files.items():
            path=self.source/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(content.replace('\n','\r\n').encode('utf-8'))
        def save(): (self.source/'latest_snapshot.json').write_text(json.dumps(snapshot))
        save();self.build()
        research=snapshot['daily_primary_research']
        for name,content in files.items():
            self.assertEqual((self.destination/name).read_text(encoding='utf-8'),content)
            self.assertEqual((self.destination/name).read_bytes(),(self.source/name).read_bytes())
        self.assertTrue((self.destination/research['relationships_file']).is_file())
        self.assertFalse((self.destination/'daily_primary_audit.json').exists())
        # Same instrument universe/count cannot disguise wrong order or qualification.
        name=research['combined_file'];original=(self.source/name).read_text(encoding='utf-8')
        (self.source/name).write_text(','.join(reversed(original.strip().split(',')))+'\n',encoding='utf-8')
        before=(self.destination/'index.html').read_bytes()
        with self.assertRaisesRegex(ValueError,'weighted per-anchor'):
            self.build()
        self.assertEqual((self.destination/'index.html').read_bytes(),before)
        (self.source/name).write_text(original,encoding='utf-8')
        snapshot['market_classification']['direction']='Neutral';theme['research_priority']={'category':'watch','label':'Watch'}
        snapshot['export_manifest']=[r for r in snapshot['export_manifest'] if r['role']=='individual_research']
        primary_research(snapshot,1000);save();self.build()
        self.assertFalse((self.destination/name).exists())
        self.assertFalse(list(self.destination.glob('daily_primary_*')))


    def test_allowlist_embedded_payload_downloads_and_private_canaries(self):
        manifest=self.build()
        self.assertEqual(manifest['session_date'],'2026-11-02')
        for file in self.destination.rglob('*'):
            if file.is_file():self.assertNotIn(CANARY.encode(),file.read_bytes())
        self.assertFalse((self.destination/'local_history').exists())
        self.assertFalse((self.destination/'run_audit.json').exists())
        self.assertFalse((self.destination/'run_bundle.zip').exists())
        payload=public_payload(self.snapshot,ROOT)
        self.assertEqual(payload['themes'][0]['theme_score'],50)
        self.assertEqual(payload['themes'][0]['selected'][0]['excess21_pp'],3)
        self.assertEqual(payload['themes'][0]['rank_change_daily'],0)
        with zipfile.ZipFile(self.destination/'individual_theme_watchlists.zip') as z:
            self.assertEqual(z.namelist(),['SMH_Semiconductors.txt'])
            self.assertEqual(z.read('SMH_Semiconductors.txt'),(self.source/'individual_watchlists/SMH_Semiconductors.txt').read_bytes())

    def test_invalid_session_or_export_preserves_previous_site(self):
        self.build();before={p.relative_to(self.destination):p.read_bytes() for p in self.destination.rglob('*') if p.is_file()}
        with self.assertRaisesRegex(ValueError,'session'):prepare_site(ROOT,self.source,self.destination,'2026-11-03')
        (self.source/'individual_watchlists/SMH_Semiconductors.txt').unlink()
        with self.assertRaises(OSError):self.build()
        self.assertEqual(before,{p.relative_to(self.destination):p.read_bytes() for p in self.destination.rglob('*') if p.is_file()})

    def test_replacement_failure_rolls_back(self):
        self.build();before=(self.destination/'index.html').read_bytes()
        from src.themescope import site_output
        real=site_output.os.replace
        def fail(src,dst):
            if Path(src)!=self.destination and Path(src).name=='site' and Path(dst)==self.destination:raise OSError('injected replacement failure')
            return real(src,dst)
        with patch.object(site_output.os,'replace',side_effect=fail):
            with self.assertRaisesRegex(OSError,'injected'):self.build()
        self.assertEqual(before,(self.destination/'index.html').read_bytes());validate_site(self.destination)

    def test_unlisted_and_modified_assets_stop_cloud_build(self):
        self.build();extra=self.destination/'run_audit.json';extra.write_text(CANARY)
        with self.assertRaisesRegex(ValueError,'unlisted'):validate_site(self.destination)
        extra.unlink();(self.destination/'themes.csv').write_text('changed')
        with self.assertRaisesRegex(ValueError,'changed'):validate_site(self.destination)

    def test_identifier_mismatch_fails_instead_of_guessing(self):
        self.snapshot['themes'][0]['tradingview_symbol']='NYSE:SMH'
        with self.assertRaisesRegex(ValueError,'Identifier/config changed'):public_payload(self.snapshot,ROOT)

    def test_replaced_txt_cannot_smuggle_private_text_into_site(self):
        (self.source/'individual_watchlists/SMH_Semiconductors.txt').write_text(CANARY)
        with self.assertRaisesRegex(ValueError,'unexpected instruments'):self.build()

    def test_both_breadth_horizons_and_safe_embedded_strings_are_preserved(self):
        self.snapshot['context']=[{'ticker':'SPY','tradingview_symbol':'AMEX:SPY','index_breadth':{'21':{'value':75,'status':'valid'},'50':{'value':60,'status':'valid'}}}]
        self.snapshot['themes'][0]['theme_watchlist_breadth']={'21':{'value':80,'status':'valid'},'50':{'value':65,'status':'valid'}}
        company='NVIDIA </script><img src=x> \u2028 text'
        self.snapshot['themes'][0]['selected'][0]['company']=company
        (self.source/'latest_snapshot.json').write_text(json.dumps(self.snapshot))
        self.build()
        text=(self.destination/'index.html').read_text(encoding='utf-8')
        payload=json.loads(re.search(r'<script id="snapshot-data"[^>]*>(.*?)</script>',text,re.S)[1])
        self.assertEqual(payload['context'][0]['index_breadth']['50']['value'],60)
        self.assertEqual(payload['themes'][0]['theme_watchlist_breadth']['50']['value'],65)
        self.assertEqual(payload['themes'][0]['selected'][0]['company'],company)

    def test_placeholder_contains_no_market_snapshot(self):
        result=placeholder_site(self.destination)
        self.assertEqual(result['kind'],'placeholder')
        self.assertIsNone(result['session_date'])
        self.assertEqual(set(result['files']),{'index.html','_headers'})

    def test_private_payload_key_even_in_a_resealed_site_is_rejected(self):
        self.build();path=self.destination/'index.html';text=path.read_text(encoding='utf-8');text=text.replace('"schema_version":"themescope-site-2"','"manual_csv_audit":{},"schema_version":"themescope-site-2"');path.write_text(text,encoding='utf-8')
        seal_site(self.destination,'snapshot','2026-11-02')
        with self.assertRaisesRegex(ValueError,'Private metadata'):validate_site(self.destination)
