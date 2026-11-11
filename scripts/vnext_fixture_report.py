"""Reproducible Gate B synthetic fixture. Never uses proposed launch prices/dates."""
from dataclasses import asdict
from datetime import date,timedelta
from decimal import Decimal as D
from pathlib import Path
import argparse
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.themescope.domain import Configuration,Theme,ThemeStatus,Membership,Role
from src.themescope.themes.calculations import POLICY,Bar,bar_map,deterministic
from src.themescope.themes.index import build_index
from src.themescope.research.engine import calculate_session
from src.themescope.storage import canonical


@deterministic
def fixture():
    # Weekdays here are an explicit synthetic calendar, not a live US calendar.
    sessions=tuple((date(2024,1,1)+timedelta(days=i)).isoformat() for i in range(96)
                   if (date(2024,1,1)+timedelta(days=i)).weekday()<5)
    groups={'alpha':('AAA','BBB','AAC','AAD','AAE'),
            'beta':('AAA','BBB','BBC','BBD','BBE'),
            'weak':('WWA','WWB','WWC','WWD','WWE')}
    rates=dict(zip(('AAA','BBB','AAC','AAD','AAE','BBC','BBD','BBE','WWA','WWB','WWC','WWD','WWE'),
                   (20,12,5,6,7,1,2,3,-20,-12,-5,-6,-7)))
    themes=tuple(Theme(t,'Synthetic '+t,'Fixture',ThemeStatus.ACTIVE,'Manufactured test only','Synthetic','Real companies') for t in groups)
    memberships=tuple(Membership(s,'Synthetic '+s,t,Role.ENABLER if (t,s) in {('beta','AAA'),('alpha','BBB')} else Role.CORE,
                                 sessions[1],None,sessions[0],'synthetic_fixture') for t,names in groups.items() for s in names)
    config=Configuration(themes,memberships,{'instruments':[]},dict(POLICY),{'industry_rule_registry_status':'pending_documented_rules'})
    # Exactly 63 elapsed sessions: prices 100 -> 100+rate. No market-data payload.
    data=bar_map(Bar(s,session,D(100)+D(rate)*i/63,D(100)+D(rate)*i/63,D(2000000))
                 for s,rate in rates.items() for i,session in enumerate(sessions))
    target=sessions[63]
    indices={t:build_index(config,t,data,sessions,sessions[0],target) for t in groups}
    mapping={s:{'status':'verified','symbol':'NASDAQ:'+s,'source':'synthetic fixture'} for s in rates}
    return config,data,sessions,target,indices,mapping


def snapshots():
    config,data,sessions,target,indices,mapping=fixture()
    result={}
    for direction in ('Long bias','Short bias'):
        snapshot=calculate_session(config,data,sessions,target,direction,indices,
                                   {t:'synthetic-'+t for t in indices},mapping)
        snapshot['synthetic_fixture']=True
        result[direction]=snapshot
    return result


def report():
    output={'synthetic_fixture':True,'purpose':'Gate B deterministic formula and multi-theme inspection; no live signals',
            'schema':'themescope-vnext-snapshot-1','sqlite_schema':1,
            'formulas':{'returns':'close[t]/close[t-21 or 63]-1; split/spin-off adjusted, no dividends',
                        'benchmark':'median; >=5 valid and >=80% configured coverage',
                        'score':'0.60 * average-rank percentile(1M) + 0.40 * average-rank percentile(3M)',
                        'relative':'0.60*(stock1M - LOO median1M) + 0.40*(stock3M - LOO median3M)',
                        'liquidity':'raw Close >=5; raw AvgVol10 >500000; raw Close*Volume >=10000000'},
            'rebalance_regression':{'old_earns_approval_session':110,'new_earns_next_session':132,'initial':100,
                                    'test':'test_numerical_rebalance_boundary_old_t_new_t_plus_one'},
            'scenarios':{}}
    for direction,snapshot in snapshots().items():
        output['scenarios'][direction]={
            'formula_checks':[{'theme_id':t['theme_id'],
                               'expected_score':{'alpha':100,'beta':50,'weak':0}[t['theme_id']],
                               'actual_score':t['score'],
                               'expected_3m':{'alpha':'.07','beta':'.03','weak':'-.07'}[t['theme_id']],
                               'actual_3m':t['returns'][1].value,
                               'passed':t['score']=={'alpha':100,'beta':50,'weak':0}[t['theme_id']] and t['returns'][1].value==D({'alpha':'.07','beta':'.03','weak':'-.07'}[t['theme_id']])}
                              for t in snapshot['themes']],
            'themes':[{'theme_id':t['theme_id'],'returns':t['returns'],'score':t['score'],
                       'trend':t['index']['trend'],'priority':t['priority'],'transition':t['transition']} for t in snapshot['themes']],
            'qualifying_relationships':[{'ticker':r['ticker'],'theme_id':r['theme_id'],'role':r['role'],
                                        'relative':r['relative'],'assigned_section':r['assigned_section'],
                                        'also_qualifies_in':r['also_qualifies_in']} for r in snapshot['relationships'] if r['qualifies']],
            'exports':snapshot['exports']}
    return json.loads(canonical(output))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    args.output.write_text(json.dumps(report(),indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print('Synthetic Gate B formula report generated.')
