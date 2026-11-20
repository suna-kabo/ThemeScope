"""Frozen Market Matrix and the historical ETF priority rule."""
import math

SCORE_BOUNDARY=50
EMA_CLASSES=('Bullish','Mixed','Bearish')
BREADTH_CLASSES=('Positive','Mixed','Negative')
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
