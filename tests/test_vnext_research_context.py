"""Independent numerical oracles and additive-contract regression tests."""
from copy import deepcopy
from dataclasses import asdict, replace
from decimal import Decimal as D, localcontext
from pathlib import Path
import tempfile
import unittest
from src.themescope.research.context import (
    wilder_atr, extension_state, aggregate_extension, market_extension,
    research_focus, ema_transitions, canonical_ranks, rank_changes, countertrend, enrich)
from src.themescope.themes.calculations import Bar
from src.themescope.themes.history import ThemeHistory
from src.themescope.storage import Store, canonical, SCHEMA_VERSION
from test_vnext_calculations import SESSIONS

DAYS=('2026-11-06','2026-11-09','2026-11-10')


def theme(key,score,session=DAYS[-1],**overrides):
    row=dict(theme_id=key,status='active',score=score,index={'trend':'Bearish'},
        history=asdict(ThemeHistory(session,key,'themescope-vnext-1',key+'-series','Bearish','Watch')))
    row.update(overrides)
    return row


def snapshot(session=DAYS[-1],scores=(90,70,70,40)):
    return dict(session=session,methodology='themescope-vnext-1',market_direction='Short bias',
        themes=[theme(chr(97+i),str(s),session) for i,s in enumerate(scores)],relationships=[],
        market={'context':{s:dict(close='100',ema21='99',ema50='101') for s in ('SPY','QQQ','IWM')}},theme_layer={'state':'live'})


def relationship(ticker,w,theme_id='a',**extra):
    row=dict(ticker=ticker,theme_id=theme_id,role='Core',relative={'w':str(w)},eligibility={'available':True,'eligible':True},qualifies=False)
    row.update(extra)
    return row


class ExtensionTests(unittest.TestCase):
    def bars(self,days=SESSIONS[:23]):
        return {(s,d):Bar(s,d,D(100),D(200),D(1_000_000),adjusted_high=D(101),adjusted_low=D(99)) for s in ('SPY','QQQ','IWM') for d in days}

    def test_wilder_numerical_seed_gaps_smoothing_and_decimal_context(self):
        days=SESSIONS[:23];bars=self.bars(days)
        self.assertEqual(wilder_atr(bars,'SPY',days[:21]),D(2))
        # TR21 includes an overnight gap: max(2,11,9)=11; next TR=11.
        bars['SPY',days[21]]=Bar('SPY',days[21],D(110),D(220),D(1000000),adjusted_high=D(111),adjusted_low=D(109))
        expected=(D(2)*19+11)/20
        self.assertEqual(wilder_atr(bars,'SPY',days[:22]),expected)
        self.assertEqual(wilder_atr(bars,'SPY',days),(expected*19+11)/20)
        with localcontext() as ctx:
            ctx.prec=6
            self.assertEqual(wilder_atr(bars,'SPY',days),D('2.8775'))
        self.assertIsNone(wilder_atr(bars,'SPY',days[:20]))
        del bars['SPY',days[9]]
        self.assertIsNone(wilder_atr(bars,'SPY',days))

    def test_all_extension_boundaries_and_explicit_aggregate_truth_table(self):
        for distance,state in [('0','Normal'),('.999999','Normal'),('1','Upside Stretched'),('1.49999','Upside Stretched'),('1.5','Upside Extended'),('-1','Downside Stretched'),('-1.5','Downside Extended')]:
            self.assertEqual(extension_state(distance)['state'],state)
        values=[None,D('0'),D('0.99'),D('1'),D('1.49'),D('1.5'),D('-1'),D('-1.5')]
        for a in values:
            for b in values:
                if a is None or b is None:expected='Unavailable'
                elif a*b>0 and min(abs(a),abs(b))>=1:
                    expected=('Upside' if a>0 else 'Downside')+(' Extended' if min(abs(a),abs(b))>=D('1.5') else ' Stretched')
                else:expected='Normal'
                self.assertEqual(aggregate_extension(a,b),expected,(a,b))

    def test_zero_invalid_or_missing_ohlc_unavailable_not_fabricated(self):
        days=SESSIONS[:23];bars=self.bars(days)
        for s,d in bars:bars[s,d]=replace(bars[s,d],adjusted_high=D(100),adjusted_low=D(100))
        self.assertIsNone(wilder_atr(bars,'SPY',days))
        bars=self.bars(days);bars['SPY',days[3]]=replace(bars['SPY',days[3]],adjusted_high=None,adjusted_low=None)
        self.assertIsNone(wilder_atr(bars,'SPY',days))
        row=Bar('A',days[0],D(100),D(200),D(1),adjusted_high=D(98),adjusted_low=D(102))
        self.assertIsNone(row.adjusted_high)
        self.assertEqual((row.adjusted_close,row.close,row.volume),(100,200,1))

    def test_only_spy_qqq_adjusted_units_not_raw_close_ema50_or_breadth(self):
        days=SESSIONS[:23];bars=self.bars(days)
        market={'context':{s:dict(close='100',ema21='103',ema50='1',breadth={'state':'Bullish'}) for s in ('SPY','QQQ','IWM')}}
        first=market_extension(market,bars,days)
        self.assertEqual(first['state'],'Downside Extended')
        self.assertEqual(first['indices']['SPY']['distance'],D('-1.5'))
        market['context']['IWM']={'close':'10000','ema21':'1'}
        for s in ('SPY','QQQ'):
            market['context'][s]['ema50']='999999';market['context'][s]['breadth']={}
        self.assertEqual(first,market_extension(market,bars,days))
        self.assertEqual(set(first['indices']),{'SPY','QQQ'})

    def test_focus_is_side_aware_and_never_changes_bias(self):
        for direction,prefix,caution in [('Short bias','Downside','Countertrend'),('Long bias','Upside','Pullback-Risk')]:
            self.assertEqual(research_focus(direction,'Normal')['label'],'Directional')
            self.assertEqual(research_focus(direction,prefix+' Stretched')['label'],'Directional + '+caution+' Watch')
            self.assertEqual(research_focus(direction,prefix+' Extended')['preferred_mode'],'countertrend')
            self.assertEqual(research_focus(direction,('Upside' if prefix=='Downside' else 'Downside')+' Extended')['label'],'Directional')
        self.assertEqual(research_focus('Observe','Downside Extended'),{'label':'Observe','preferred_mode':'directional'})


class ComparisonTests(unittest.TestCase):
    def test_ema_unchanged_crossed_at_and_missing(self):
        now=snapshot();prior=snapshot(DAYS[-2])
        for close,old,expected in [('100','100',None),('98','98',None),('98','100','Crossed below EMA21 on 2026-11-10'),('100','98','Crossed above EMA21 on 2026-11-10'),('99','100','Reached EMA21 on 2026-11-10'),('100','99','Crossed above EMA21 on 2026-11-10')]:
            now['market']['context']['SPY']['close']=close;prior['market']['context']['SPY']['close']=old
            self.assertEqual(ema_transitions(now,prior,DAYS)['SPY']['ema21']['message'],expected)
        self.assertIsNone(ema_transitions(now,None,DAYS)['SPY']['ema21']['changed'])
        prior['market']['context']['SPY']['ema21']=None
        self.assertIsNone(ema_transitions(now,prior,DAYS)['SPY']['ema21']['changed'])

    def test_launch_bootstrap_nonadjacent_and_wrong_methodology_never_transition(self):
        now=snapshot();prior=snapshot(DAYS[-2]);prior['market']['context']['SPY']['close']='98'
        for bad in ('bootstrap','initialization','not_adjacent','methodology'):
            previous=deepcopy(prior)
            if bad=='bootstrap':
                for t in previous['themes']:t['history']['bootstrap']=True
            if bad=='initialization':
                for t in previous['themes']:t['history']['signal_eligible']=False
            if bad=='not_adjacent':previous['session']=DAYS[0]
            if bad=='methodology':previous['methodology']='legacy'
            self.assertIsNone(ema_transitions(now,previous,DAYS)['SPY']['ema21']['changed'],bad)
            self.assertTrue(all(r['change'] is None for r in rank_changes(now,previous,DAYS)['themes'].values()))

    def test_competition_ties_filter_and_order_independent(self):
        rows=snapshot()['themes']+[theme('watch','100',status='watch_only'),theme('missing',None)]
        expected={'a':1,'b':2,'c':2,'d':4}
        self.assertEqual(canonical_ranks(rows),expected)
        self.assertEqual(canonical_ranks(list(reversed(rows))),expected)
        self.assertEqual(rank_changes(dict(snapshot(),themes=rows),None,DAYS)['themes']['d']['rank'],4)
        self.assertEqual(rows[3]['score'],'40') # no rewriting scores to ranks

    def test_comparable_rank_gain_loss_and_ties(self):
        now=snapshot(scores=(70,90,70,40));prior=snapshot(DAYS[-2])
        result=rank_changes(now,prior,DAYS)['themes']
        self.assertEqual(result['a']['change'],-1)
        self.assertEqual(result['b']['change'],1)
        self.assertEqual(result['c']['change'],0)
        self.assertEqual(result['a']['previous_session'],DAYS[-2])
        now['themes'][0]['history']['series_id']='new-series'
        self.assertIsNone(rank_changes(now,prior,DAYS)['themes']['a']['change'])

    def test_new_activation_missing_score_changed_universe_no_invented_change(self):
        now=snapshot();prior=snapshot(DAYS[-2])
        now['themes'].append(theme('new','80'))
        result=rank_changes(now,prior,DAYS)['themes']
        self.assertEqual(result['new']['reason'],'newly_active_theme')
        self.assertTrue(all(r['change'] is None for r in result.values()))
        now=snapshot();prior['themes'][1]['score']=None
        result=rank_changes(now,prior,DAYS)['themes']
        self.assertEqual(result['b']['reason'],'newly_available_score')
        self.assertTrue(all(r['change'] is None for r in result.values()))
        now['themes'][0]['score']=None
        self.assertEqual(rank_changes(now,prior,DAYS)['themes']['a']['reason'],'unavailable_score')


class CountertrendTests(unittest.TestCase):
    def setup_short(self):
        now=snapshot(scores=(40,30,60,20));now['themes'][3]['index']['trend']='Bullish'
        now['relationships']=[relationship('Z','.03'),relationship('A','.03'),relationship('B','.02','b'),relationship('C','-.03'),relationship('D','-.04','b'),relationship('ZERO',0),relationship('BAD','.9',eligibility={'available':True,'eligible':False}),relationship('REL','.9',role='Related'),relationship('STRONG','.9','c'),relationship('WRONG','.9','d')]
        return now

    def test_short_filters_zero_and_ordering_without_directional_mutation(self):
        now=self.setup_short();old=deepcopy(now);result=countertrend(now)
        self.assertEqual([r['ticker'] for r in result['buckets']['resilient']['rows']],['A','Z','B'])
        self.assertEqual([r['ticker'] for r in result['buckets']['snapback']['rows']],['D','C'])
        self.assertEqual((result['stock_count'],result['relationship_count']),(5,5))
        self.assertEqual(now,old)
        self.assertFalse(any(r['qualifies'] for r in now['relationships']))
        now['relationships'].append(relationship('MISSING','.9',eligibility={'available':False,'eligible':True}))
        self.assertEqual(countertrend(now),result)

    def test_ties_score_order_multitheme_dedup_and_extension_independence(self):
        now=self.setup_short();now['relationships']=[relationship('Z','.03','b'),relationship('A','.03'),relationship('A','.03','b'),relationship('Z','-.03'),relationship('A','-.03','b')]
        result=countertrend(now)
        self.assertEqual(result['buckets']['resilient']['rows'],[{'ticker':'A','theme_id':'a'},{'ticker':'A','theme_id':'b'},{'ticker':'Z','theme_id':'b'}])
        self.assertEqual(result['buckets']['snapback']['rows'][0]['theme_id'],'b')
        self.assertEqual(result['buckets']['resilient']['stock_count'],2)
        now['research']={'extension':{'state':'Normal'}}
        self.assertEqual(countertrend(now),result)
        now['research']['extension']['state']='Downside Extended'
        self.assertEqual(countertrend(now),result)

    def test_approved_long_symmetry_boundary_and_nondirectional_conservative(self):
        now=snapshot(scores=(50,75,49,90));now['market_direction']='Long bias'
        for t in now['themes']:t['index']['trend']='Bullish'
        now['themes'][3]['index']['trend']='Bearish'
        now['relationships']=[relationship('UP','.03'),relationship('UP2','.04','b'),relationship('DOWN','-.05'),relationship('WEAK','-.99','c'),relationship('BAD','.9','d')]
        result=countertrend(now)
        self.assertEqual(result['buckets']['resilient']['label'],'Strong Leaders / Pullback Watch')
        self.assertEqual(result['buckets']['snapback']['label'],'Relative Weakness')
        self.assertEqual([r['ticker'] for r in result['buckets']['resilient']['rows']],['UP2','UP'])
        self.assertEqual(result['buckets']['snapback']['rows'],[{'ticker':'DOWN','theme_id':'a'}])
        now['market_direction']='Observe'
        self.assertFalse(countertrend(now)['available'])
        self.assertEqual(countertrend(now)['relationship_count'],0)

    def test_enrichment_only_adds_research_does_not_mutate_core(self):
        now=self.setup_short();now['exports']={'combined':'NASDAQ:A\n'};old=deepcopy(now)
        enriched=enrich(now,{},DAYS,companies={'A':'Example Company'})
        self.assertEqual(now,old)
        self.assertEqual({k:v for k,v in enriched.items() if k!='research'},old)
        self.assertEqual(enriched['research']['companies'],{'A':'Example Company'})
        self.assertEqual(enriched['research']['extension']['state'],'Unavailable')


class IntegrationTests(unittest.TestCase):
    def test_optional_ohlc_preserves_existing_observation_payload_bytes(self):
        row=Bar('A',DAYS[0],D(10),D(20),D(1000))
        old=asdict(row);old.pop('adjusted_high');old.pop('adjusted_low')
        self.assertEqual(canonical(row),canonical(old))
        updated=replace(row,adjusted_high=D(11),adjusted_low=D(9))
        self.assertIn('adjusted_high',canonical(updated))

    def test_provider_uses_adjusted_ohlc_raw_liquidity_unchanged(self):
        from test_vnext_provider import schedule,DATES
        from src.themescope.providers.alpaca import AlpacaMarketDataProvider
        calls=[]
        def send(params,headers):
            calls.append(params)
            raw=params['adjustment']=='raw'
            return 200,{'bars':{'SPY':[{'t':DATES[-1]+'T05:00:00Z','c':100 if raw else 50,'h':104 if raw else 52,'l':96 if raw else 48,'v':1000000}]}},{}
        batch=AlpacaMarketDataProvider('fixture','fixture',schedule(),send=send).get_daily_bars(('SPY',),DATES[-1],DATES[-1])
        row=batch.bars[0]
        self.assertEqual((row.adjusted_high,row.adjusted_low,row.adjusted_close,row.close,row.volume),(52,48,50,100,1000000))
        self.assertTrue(all(p['feed']=='sip' and p['timeframe']=='1Day' for p in calls))

    def test_cache_enriches_only_benchmarks_then_bounded_warm_refresh(self):
        from test_vnext_provider import schedule,DATES
        from src.themescope.providers.base import FixtureProvider
        from src.themescope.providers.cache import prepare,publish_prepared
        rows=[Bar(s,d,D(100),D(100),D(1000000)) for s in ('SPY','QQQ','A') for d in DATES]
        with tempfile.TemporaryDirectory() as folder:
            store=Store(Path(folder)/'test.sqlite');self.addCleanup(store.close)
            provider=FixtureProvider(rows,schedule())
            def publish(plan):publish_prepared(store,plan,DATES[-1],'themescope-vnext-1','test',{'session':DATES[-1]},('SPY','QQQ','A'))
            publish(prepare(store,provider,('SPY','QQQ','A'),DATES))
            provider.bars=tuple(replace(b,adjusted_high=D(101),adjusted_low=D(99)) for b in rows)
            provider.calls.clear()
            publish(prepare(store,provider,('SPY','QQQ','A'),DATES,repair_sessions=1,ohlc_symbols=('SPY','QQQ')))
            self.assertIn((('QQQ','SPY'),DATES[0],DATES[-1]),provider.calls)
            self.assertNotIn((('A',),DATES[0],DATES[-1]),provider.calls)
            before=store.connection.execute('SELECT count(*) FROM observations').fetchone()[0]
            provider.calls.clear()
            publish(prepare(store,provider,('SPY','QQQ','A'),DATES,repair_sessions=1,ohlc_symbols=('SPY','QQQ')))
            self.assertTrue(all(start==end for names,start,end in provider.calls),provider.calls)
            self.assertEqual(store.connection.execute('SELECT count(*) FROM observations').fetchone()[0],before)
            self.assertEqual(store.connection.execute('PRAGMA user_version').fetchone()[0],SCHEMA_VERSION)

    def test_historical_context_is_one_run_and_read_only(self):
        with tempfile.TemporaryDirectory() as folder:
            store=Store(Path(folder)/'test.sqlite');self.addCleanup(store.close)
            for count,keys in enumerate((('a','b'),('a',))):
                with store.refresh(DAYS[-2],'themescope-vnext-1','test') as run:
                    run.bars([Bar('A',DAYS[-2],D(10),D(10),D(1000000))])
                    for key in keys:run.theme(key,theme(key,50,DAYS[-2]))
                    run.db.execute('INSERT INTO market_snapshot VALUES(?,?)',(run.run,canonical({'context':{'SPY':{'close':str(count)}}})))
                    run.publish({'session':DAYS[-2]},required_symbols=('A',))
            before=store.connection.total_changes
            result=store.research_at(DAYS[-2],'themescope-vnext-1')
            self.assertEqual([t['theme_id'] for t in result['themes']],['a'])
            self.assertEqual(result['market']['context']['SPY']['close'],'1')
            self.assertIsNone(store.research_at(DAYS[0],'themescope-vnext-1'))
            self.assertEqual(store.connection.total_changes,before)

    def test_public_contract_whitelists_research_and_rejects_bad_references(self):
        from scripts.build_cloudflare_demo import demo_snapshot
        from scripts.build_public_snapshot import project_snapshot,SnapshotError
        data=demo_snapshot();data['synthetic_fixture']=False
        data['provider_health']={'status':'Healthy'};data['refreshed_at']=data['session']+'T22:00:00+00:00'
        data['research']['private']='discard';data['research']['extension']['indices']['SPY']['secret']='discard'
        result=project_snapshot(data,data['session'])
        self.assertNotIn('private',result['research'])
        self.assertNotIn('secret',result['research']['extension']['indices']['SPY'])
        self.assertEqual(result['research']['ranks'],data['research']['ranks'])
        data['research']['countertrend']['buckets']['snapback']['rows'].append({'ticker':'UNKNOWN','theme_id':'missing'})
        with self.assertRaises(SnapshotError):project_snapshot(data,data['session'])
