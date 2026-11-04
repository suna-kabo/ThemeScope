"""One exact decimal weighted comparison for browsing and research exports."""
from decimal import Decimal,localcontext
from .research_policy import CURRENT_WEIGHT,MEDIUM_WEIGHT,number


def weighted_excess(stock,anchor):
    endpoints={name:row.get('returns',{}).get(period,{}).get('value') for name,row,period in
        [('stock_1m',stock,'21'),('stock_3m',stock,'63'),('etf_1m',anchor,'21'),('etf_3m',anchor,'63')]}
    invalid=[key for key,value in endpoints.items() if not number(value)]
    if invalid:return {**endpoints,'er1m_pp':None,'er3m_pp':None,'weighted_excess_pp':None,'weighted_vs_etf':'Unavailable','reason':'missing_or_invalid:'+','.join(invalid)}
    with localcontext() as context:
        context.prec=40
        values={key:Decimal(str(value)) for key,value in endpoints.items()}
        er1=100*(values['stock_1m']-values['etf_1m']);er3=100*(values['stock_3m']-values['etf_3m'])
        weighted=Decimal(str(CURRENT_WEIGHT))*er1+Decimal(str(MEDIUM_WEIGHT))*er3
    return {**endpoints,'er1m_pp':float(er1),'er3m_pp':float(er3),'weighted_excess_pp':float(weighted),
        'weighted_vs_etf':'Outperforming' if weighted>0 else 'Underperforming' if weighted<0 else 'Flat','reason':None}
