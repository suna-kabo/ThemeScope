"""Active manual-CSV research policy. No signals, data access or execution."""
import math

PRIORITY_VERSION='ema-score-priority-2'
EMA_VERSION='tradingview-daily-price-ema21-ema50-1'
INPUT_SEMANTICS='tradingview-manual-us-session-performance-percent-1'
CURRENT_WEIGHT=0.60
MEDIUM_WEIGHT=0.40
SCORE_BOUNDARY=50
EMA_CLASSES=('Bullish','Mixed','Bearish')
BREADTH_CLASSES=('Positive','Mixed','Negative')
PRIORITY_LABELS=('Primary long','Watch','Primary short')
ACTION_SENTENCES={
    'Long bias':'Prioritise long-side theme research. Evaluate charts and setups separately.',
    'Selective long':'Prioritise selective long-side theme research. Evaluate charts and setups separately.',
    'Short bias':'Prioritise short-side theme research. Evaluate charts and setups separately.',
    'Selective short':'Prioritise selective short-side theme research. Evaluate charts and setups separately.',
    'Neutral':'No directional Primary research list. Keep chart/setup evaluation separate.',
    'Unclassified':'Required Market evidence is unavailable. No directional Primary research list.',
}


def number(value):
    return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)


def ema_classification(price,ema21,ema50):
    if not all(number(v) and v>0 for v in (price,ema21,ema50)):return None
    if price>ema21 and price>ema50:return 'Bullish'
    if price<ema21 and price<ema50:return 'Bearish'
    return 'Mixed'


def ema_relationship(price,average):
    if not all(number(v) and v>0 for v in (price,average)):return 'N/A'
    return 'Above' if price>average else 'Below' if price<average else 'At'


def breadth_classification(a,b):
    if not all(number(v) and 0<=v<=100 for v in (a,b)):return None
    return 'Positive' if a>=50 and b>=50 else 'Negative' if a<50 and b<50 else 'Mixed'


def breadth_consensus(spy,qqq):
    if spy not in BREADTH_CLASSES or qqq not in BREADTH_CLASSES:return None
    return spy if spy==qqq and spy in ('Positive','Negative') else 'Mixed'


def market_rule(spy,qqq,consensus):
    qualifier=None
    if spy not in EMA_CLASSES or qqq not in EMA_CLASSES:
        direction,rule_id,explanation='Unclassified','price-unavailable','A required SPY/QQQ price classification is unavailable.'
    elif spy==qqq and spy in ('Bullish','Bearish'):
        long=spy=='Bullish';direction='Long bias' if long else 'Short bias';rule_id='unanimous-'+spy.lower()
        qualifier='N/A' if consensus not in BREADTH_CLASSES else 'Mixed' if consensus=='Mixed' else 'Confirming' if (consensus=='Positive')==long else 'Diverging'
        explanation=f'SPY and QQQ are both {spy}: {direction}. SPY/QQQ Breadth Consensus is {consensus or "Unavailable"} ({qualifier}); breadth does not overturn unanimous price direction.'
    elif consensus not in BREADTH_CLASSES:
        direction,rule_id,explanation='Unclassified','breadth-unavailable','SPY/QQQ Breadth Consensus is unavailable; the required non-unanimous Market cell cannot be resolved.'
    else:
        pair={spy,qqq}
        if pair=={'Bullish','Mixed'}:
            direction='Selective long' if consensus=='Positive' else 'Neutral';rule_id='bullish-mixed'
        elif pair=={'Bearish','Mixed'}:
            direction='Selective short' if consensus=='Negative' else 'Neutral';rule_id='bearish-mixed'
        else:
            direction={'Positive':'Selective long','Negative':'Selective short','Mixed':'Neutral'}[consensus]
            rule_id='opposed-prices' if spy!=qqq else 'both-mixed'
        explanation=f'SPY is {spy}, QQQ is {qqq}, and SPY/QQQ Breadth Consensus is {consensus}: {direction}.'
    return {'direction':direction,'rule_id':rule_id,'reason':explanation,'breadth_qualifier':qualifier}


def market_direction(spy,qqq,consensus):return market_rule(spy,qqq,consensus)['direction']


def market_truth_table():
    return [{'spy':a,'qqq':b,'breadth':c,**market_rule(a,b,c)} for a in (*EMA_CLASSES,None) for b in (*EMA_CLASSES,None) for c in (*BREADTH_CLASSES,None)]


def market_side(direction):
    return 'long' if direction in ('Long bias','Selective long') else 'short' if direction in ('Short bias','Selective short') else None


def theme_priority(direction,score,classification,transition=None):
    side=market_side(direction);label='Watch';code='market_not_directional'
    if side:
        if not number(score) or not 0<=score<=100:code='score_unavailable'
        elif classification not in EMA_CLASSES:code='ema_unavailable'
        elif side=='long' and (score>=SCORE_BOUNDARY and classification in ('Bullish','Mixed') or classification=='Bullish' and transition=='newly_bullish'):
            label='Primary long';code='newly_bullish' if score<SCORE_BOUNDARY else 'score_ema_long'
        elif side=='short' and (score<SCORE_BOUNDARY and classification in ('Bearish','Mixed') or classification=='Bearish' and transition=='newly_bearish'):
            label='Primary short';code='newly_bearish' if score>=SCORE_BOUNDARY else 'score_ema_short'
        else:code='not_aligned'
    primary=label!='Watch'
    return {'label':label,'category':'primary' if primary else 'watch','group':0 if primary else 1,'side':side if primary else None,'reason_code':code}


def priority_change(previous,current):
    if previous not in PRIORITY_LABELS:return 'N/A'
    if current==previous:return '—'
    if current=='Primary long':return 'New long'
    if current=='Primary short':return 'New short'
    return 'Removed'


def priority_sort_key(row):
    p=row.get('research_priority',{});score=row.get('theme_score')
    return (p.get('group',1),score if p.get('side')=='short' and number(score) else -score if number(score) else math.inf,row['id'])


def methodology():
    return {'priority_version':PRIORITY_VERSION,'ema_version':EMA_VERSION,'input_semantics':INPUT_SEMANTICS,'score_boundary':SCORE_BOUNDARY,'weights':{'current':CURRENT_WEIGHT,'medium':MEDIUM_WEIGHT},
            'long_rule':f'Valid Score ≥ {SCORE_BOUNDARY} with a Bullish or Mixed ETF, or a valid Newly bullish transition. Valid Score and current EMA inputs are always required.',
            'short_rule':f'Valid Score < {SCORE_BOUNDARY} with a Bearish or Mixed ETF, or a valid Newly bearish transition. Valid Score and current EMA inputs are always required.',
            'transition_rule':'Only a valid non-Bullish-to-Bullish or non-Bearish-to-Bearish EMA transition from the immediately preceding US session, with the same anchor identity and compatible EMA/input methodology. No prior comparison means no exception.',
            'stock_rule':f'Weighted Excess Return = {CURRENT_WEIGHT:.0%} × (Stock 1M − ETF 1M) + {MEDIUM_WEIGHT:.0%} × (Stock 3M − ETF 3M), in percentage points. Long > 0; short < 0; zero and unavailable inputs excluded.',
            'note':'Configured research policies, not validated trading signals. Theme breadth does not determine Score or Priority.'}


def canonical_decision(session,generated_hkt,contexts,themes):
    indices={r['ticker']:r for r in contexts};spy=indices.get('SPY',{});qqq=indices.get('QQQ',{});iwm=indices.get('IWM',{})
    consensus=breadth_consensus(spy.get('breadth_state'),qqq.get('breadth_state'))
    matched=market_rule(spy.get('price_state'),qqq.get('price_state'),consensus)
    groups={'new':[],'continuing':[],'unavailable':[]}
    for theme in sorted(themes,key=priority_sort_key):
        if theme['research_priority']['category']!='primary':continue
        change=theme.get('priority_change','N/A')
        groups['new' if change in ('New long','New short') else 'continuing' if change=='—' else 'unavailable'].append(theme['id'])
    return {'session_date':session,'generated_at_hkt':generated_hkt,'market_classification':matched['direction'],'action_sentence':ACTION_SENTENCES[matched['direction']],
            'matrix_rule_id':matched['rule_id'],'reason':matched['reason'],'breadth_qualifier':matched['breadth_qualifier'],
            'spy_price_state':spy.get('price_state'),'qqq_price_state':qqq.get('price_state'),'iwm_price_state':iwm.get('price_state'),
            'spy_breadth_state':spy.get('breadth_state'),'qqq_breadth_state':qqq.get('breadth_state'),'breadth_consensus':consensus,'russell_2000_breadth_state':iwm.get('breadth_state'),
            'primary_groups':groups,'market_matrix':market_truth_table(),'priority_policy':methodology()}


def apply_policy(snapshot,previous=None,previous_session=None):
    """Recompute final priorities using only genuine adjacent-session metadata."""
    contexts=snapshot.get('context',[]);indices={r['ticker']:r for r in contexts}
    consensus=breadth_consensus(indices.get('SPY',{}).get('breadth_state'),indices.get('QQQ',{}).get('breadth_state'))
    direction=market_direction(indices.get('SPY',{}).get('price_state'),indices.get('QQQ',{}).get('price_state'),consensus)
    if previous and (not previous_session or previous.get('session_date')!=previous_session):previous=None
    metadata=(previous or {}).get('research_history',{})
    if not isinstance(metadata,dict):metadata={}
    ema_compatible=metadata.get('ema_methodology')==EMA_VERSION and metadata.get('input_semantics')==INPUT_SEMANTICS
    priority_compatible=ema_compatible and metadata.get('priority_methodology')==PRIORITY_VERSION
    previous_rows={r['id']:r for r in (previous or {}).get('themes',[])}
    for theme in snapshot['themes']:
        classification=ema_classification(theme.get('price_close'),theme.get('ema21'),theme.get('ema50'))
        old=previous_rows.get(theme['id'],{})
        same_anchor=old.get('anchor')==theme['anchor'] and bool(theme.get('tradingview_symbol')) and old.get('tradingview_symbol')==theme.get('tradingview_symbol')
        old_classification=ema_classification(old.get('price_close'),old.get('ema21'),old.get('ema50')) if ema_compatible and same_anchor else None
        transition='newly_bullish' if old_classification in EMA_CLASSES and old_classification!='Bullish' and classification=='Bullish' else 'newly_bearish' if old_classification in EMA_CLASSES and old_classification!='Bearish' and classification=='Bearish' else None
        theme.pop('theme_state',None)
        theme['etf_ema_classification']=classification;theme['ema_transition']=transition
        theme['ema_comparison_reason']='compatible' if old_classification in EMA_CLASSES else 'previous_ema_unavailable_or_incompatible'
        theme['research_priority']=theme_priority(direction,theme.get('theme_score'),classification,transition)
        comparable=priority_compatible and same_anchor and old_classification in EMA_CLASSES and number(old.get('theme_score')) and 0<=old['theme_score']<=100
        prior_label=old.get('priority_label') if comparable else None
        theme['priority_change']=priority_change(prior_label,theme['research_priority']['label'])
        theme['priority_comparison_session']=previous_session if theme['priority_change']!='N/A' else None
    decision=canonical_decision(snapshot['session_date'],snapshot.get('dashboard_generated_at_hkt') or snapshot.get('generated_at'),contexts,snapshot['themes'])
    snapshot['decision']=decision;snapshot['research_methodology']=methodology()
    snapshot['market_classification']={'direction':direction,'breadth_consensus':consensus,'breadth_qualifier':decision['breadth_qualifier'],'reason':decision['reason'],'action_summary':decision['action_sentence']}
    audit=snapshot.setdefault('manual_csv_audit',{})
    audit['market_classification']=direction
    audit['priority_methodology']=PRIORITY_VERSION
    audit['priority_counts']={label:sum(t['research_priority']['label']==label for t in snapshot['themes']) for label in PRIORITY_LABELS}
    return snapshot
