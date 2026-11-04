"""Independent boundaries for Daily Stock CSV v2 and unchanged membership/breadth."""
import copy
import csv
import io
import json
from pathlib import Path
import tempfile
import unittest

from src.themescope.daily_stock_policy import load_policy,evaluate,CURRENT_SCHEMA,LEGACY_SCHEMA
from src.themescope.manual_csv import parse_csv,CSVValidationError,breadth
from src.themescope.daily_lists import primary_research,build
from src.themescope.local_history import record,apply
from src.themescope.research_policy import apply_policy
from test_manual_csv import HEADER,ROW
from test_research_policy import snapshot

ROOT=Path(__file__).resolve().parents[1]


class DailyStockPolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.folder=Path(self.temp.name)
        self.policy=load_policy(ROOT)

    def csv(self,*,turnover='10000000',volume='500001',header='Average volume, 10 days',legacy=None):
        rows=list(csv.reader(io.StringIO(HEADER+ROW)));rows[0][15]=header;rows[1][14]=turnover;rows[1][15]=volume
        if legacy is not None:rows[0].append('Price × average volume, 30 days');rows[1].append(legacy)
        path=self.folder/'stock.csv'
        with path.open('w',encoding='utf-8',newline='') as handle:csv.writer(handle).writerows(rows)
        return path

    def eligibility(self,rows):
        row=rows[0];return evaluate({'turnover_1d_usd':row['turnover_1d'],'average_volume_10d_shares':row['average_volume_10d_shares']},self.policy)

    def test_new_csv_without_adv30_and_explicit_header_aliases(self):
        for header in ('Average volume, 10 days','Average Volume 10D','average_volume_10d_shares'):
            rows,audit=parse_csv(self.csv(header=header),'stock')
            self.assertEqual(rows[0]['average_volume_10d_shares'],500001)
            self.assertNotIn('adv30',rows[0]);self.assertTrue(self.eligibility(rows)['eligible'])
            self.assertEqual(audit['stock_csv_schema'],CURRENT_SCHEMA)

    def test_other_volume_fields_cannot_substitute_and_error_lists_contract(self):
        for header in ('Volume','Relative volume','Average volume, 30 days','Dollar volume','Price × average volume, 30 days'):
            with self.assertRaisesRegex(CSVValidationError,'accepted 10-day shares headers'):
                parse_csv(self.csv(header=header),'stock')

    def test_missing_invalid_negative_and_wrong_unit_values_fail_without_zero_fill(self):
        for field in ('turnover','volume'):
            for invalid in ('','bad','NaN','inf','-1','12%'):
                with self.subTest(field=field,value=invalid),self.assertRaisesRegex(CSVValidationError,'stock: line 2'):
                    parse_csv(self.csv(**{field:invalid}),'stock')
        with self.assertRaisesRegex(CSVValidationError,'shares per trading session'):
            parse_csv(self.csv(volume='$600000'),'stock')
        rows,_=parse_csv(self.csv(turnover='0',volume='0'),'stock')
        self.assertEqual(self.eligibility(rows)['status'],'ineligible')
        self.assertEqual((rows[0]['turnover_1d'],rows[0]['average_volume_10d_shares']),(0,0))

    def test_exact_and_boundaries_and_both_conditions_required(self):
        for turnover,volume,expected in [(9999999.99,500001,False),(10000000,500001,True),(10000000.01,500001,True),
                                         (10000001,499999,False),(10000001,500000,False),(10000001,500000.01,True),
                                         (0,600000,False),(20000000,0,False)]:
            with self.subTest(turnover=turnover,volume=volume):
                result=evaluate({'turnover_1d_usd':turnover,'average_volume_10d_shares':volume},self.policy)
                self.assertIs(result['eligible'],expected)
        for invalid in (None,True,-1,float('nan'),float('inf')):
            for field in ('turnover_1d_usd','average_volume_10d_shares'):
                values={'turnover_1d_usd':10000000,'average_volume_10d_shares':600000};values[field]=invalid
                result=evaluate(values,self.policy);self.assertIsNone(result['eligible']);self.assertEqual(result['status'],'unavailable')

    def test_optional_legacy_field_never_changes_current_eligibility(self):
        for legacy in ('0','-100','999999999999','not a number'):
            rows,_=parse_csv(self.csv(legacy=legacy),'stock');self.assertTrue(self.eligibility(rows)['eligible'])
            rows,_=parse_csv(self.csv(turnover='9999999',legacy=legacy),'stock');self.assertFalse(self.eligibility(rows)['eligible'])

    def test_legacy_is_explicit_unverified_and_never_inferred(self):
        path=self.csv(header='Price × average volume, 30 days',volume='30000000')
        with self.assertRaisesRegex(CSVValidationError,'average_volume_10d_shares'):parse_csv(path,'stock')
        rows,audit=parse_csv(path,'stock',stock_schema='legacy-v1');self.assertEqual(audit['stock_csv_schema'],LEGACY_SCHEMA)
        result=evaluate({'turnover_1d_usd':100000000,'average_volume_10d_shares':9000000},self.policy,schema=LEGACY_SCHEMA)
        self.assertEqual(result['status'],'legacy_unverified');self.assertIsNone(result['eligible'])

    def test_etf_and_breadth_requirements_unaffected(self):
        # This header is intentionally a decoy: no new shares column is required.
        rows,_=parse_csv(self.csv(header='Average volume, 30 days',volume='bad',turnover='1'),'etf')
        self.assertEqual(rows[0]['turnover_1d'],1)
        p=self.folder/'index.csv';p.write_text('Symbol,Price,EMA21,EMA50\nA,20,19,18\n',encoding='utf-8')
        for role in ('spy','qqq','iwm'):self.assertEqual(len(parse_csv(p,role)[0]),1)

    def test_explicit_turnover_currency_is_usd_without_conversion(self):
        path=self.csv()
        with path.open(encoding='utf-8',newline='') as handle:rows=list(csv.reader(handle))
        rows[0].append('Price × volume (turnover), 1 day - Currency');rows[1].append('EUR')
        with path.open('w',encoding='utf-8',newline='') as handle:csv.writer(handle).writerows(rows)
        with self.assertRaisesRegex(CSVValidationError,'expected USD'):parse_csv(path,'stock')
        self.assertEqual(len(parse_csv(path,'etf')[0]),1)

    def sample(self):
        s=snapshot();s['market_classification']={'direction':'Long bias'}
        t=s['themes'][0];t['research_priority']={'label':'Primary long','category':'primary','side':'long','group':0}
        def stock(ticker,turnover=10000000,volume=600000):
            return {'ticker':ticker,'tradingview_symbol':'NASDAQ:'+ticker,'metric_status':'available','price_close':110,'ema21':100,'ema50':90,
                    'turnover_1d_usd':turnover,'average_volume_10d_shares':volume,'returns':{'21':{'value':.3},'63':{'value':.4}}}
        t['selected']=[stock('PASS'),stock('FAIL_TURNOVER',9999999),stock('FAIL_VOLUME',10000000,500000),stock('UNKNOWN',None,None)]
        t['selected'][1]['daily_stock_eligibility']={'status':'eligible','eligible':True} # A stale flag is not evidence.
        return s

    def test_primary_requires_verified_liquidity_and_positive_or_negative_weight(self):
        s=self.sample();before=copy.deepcopy(s['themes']);files,_=primary_research(s,1000)
        self.assertEqual(s['themes'],before)
        self.assertEqual(files[s['daily_primary_research']['combined_file']].strip().split(','),['###ETF — Alpha','AMEX:ETF','NASDAQ:PASS'])
        evaluations=s['daily_primary_research']['evaluations'];self.assertTrue(all(r['weighted_excess_pp']>0 for r in evaluations))
        self.assertEqual([r['included'] for r in evaluations],[True,False,False,False])
        s['market_classification']['direction']='Short bias';s['themes'][0]['research_priority']['label']='Primary short'
        for stock in s['themes'][0]['selected']:stock['returns']={'21':{'value':-.3},'63':{'value':-.4}}
        files,_=primary_research(s,1000);self.assertEqual(files[s['daily_primary_research']['combined_file']].strip().split(',')[1:],['AMEX:ETF','NASDAQ:PASS'])

    def test_legacy_snapshot_and_legacy_import_export_anchor_only(self):
        for legacy_snapshot in (False,True):
            s=self.sample()
            if legacy_snapshot:s.pop('daily_stock_policy');s.pop('stock_csv_schema')
            else:s['stock_csv_schema']=LEGACY_SCHEMA
            files,_=primary_research(s,1000);tokens=files[s['daily_primary_research']['combined_file']].strip().split(',')
            self.assertEqual(tokens,['###ETF — Alpha','AMEX:ETF'])
            self.assertTrue(all(r['daily_eligibility_status']=='legacy_unverified' for r in s['daily_primary_research']['evaluations']))

    def test_complete_collection_and_ordinary_order_ignore_daily_eligibility(self):
        s=self.sample();t=s['themes'][0]
        for i,stock in enumerate(t['selected'],1):stock['selection_slot']=i
        order=[stock['tradingview_symbol'] for stock in t['selected']]
        files=build(s,{'schema_version':1,'instrument_limit':1000,'groups':[{'id':'all','name':'All','theme_ids':['a']}]})
        name=next(row['file'] for row in s['export_manifest'] if row['role']=='individual_research')
        self.assertEqual(files[name].strip().split(','),['AMEX:ETF',*order])
        self.assertEqual(files['tradingview_configured_stocks.txt'].strip().split(','),sorted(order))
        self.assertEqual([stock['selection_slot'] for stock in t['selected']],list(range(1,5)))
        t.update(turnover_1d_usd=0,average_volume_10d_shares=0);t['selected']=[]
        files,_=primary_research(s,1000)
        self.assertEqual(files[s['daily_primary_research']['combined_file']].strip().split(','),['###ETF — Alpha','AMEX:ETF'])

    def test_breadth_uses_metrics_including_ineligible_and_full_missing_denominator(self):
        # Eight valid above-EMA rows out of ten configured: exactly 80% coverage.
        rows=[{'symbol':str(i),'price':110,'ema21':100,'ema50':90,'turnover_1d':1} for i in range(8)]+[{'symbol':'missing1'},{'symbol':'missing2'}]
        result=breadth(rows,minimum=8,coverage_floor=.8)
        for period in ('21','50'):
            self.assertEqual((result[period]['valid_count'],result[period]['configured_count'],result[period]['value']),(8,10,100))
        rows[7]={'symbol':'missing3'};self.assertEqual(breadth(rows,minimum=8,coverage_floor=.8)['21']['status'],'unavailable')

    def test_stock_policy_change_does_not_invalidate_theme_score_history(self):
        s=snapshot('2026-07-02');apply_policy(s);old=record(s)
        changed=copy.deepcopy(s);changed['daily_stock_policy']['version']='another-stock-policy'
        self.assertEqual(record(changed),old)
        history=self.folder/'history';history.mkdir();(history/'2026-07-02.json').write_text(json.dumps(old))
        current=snapshot('2026-07-06');apply(current,history,ROOT/'config/calendars/xnys_2020_2035_v1.json')
        self.assertEqual(current['themes'][0]['rank_change_daily'],0)


if __name__=='__main__':unittest.main()
