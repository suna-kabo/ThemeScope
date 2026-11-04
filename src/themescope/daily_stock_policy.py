"""Daily scanner liquidity, separate from curated membership and ETF scoring."""
import copy
import json
from pathlib import Path
from .research_policy import number

CURRENT_SCHEMA='daily-stock-csv-2'
LEGACY_SCHEMA='daily-stock-csv-1'
SCHEMA_MODES={'current-v2':CURRENT_SCHEMA,'legacy-v1':LEGACY_SCHEMA}


def load_policy(root):
    policy=json.loads((Path(root)/'config/manual_csv.json').read_text(encoding='utf-8'))['daily_stock_policy']
    if policy.get('csv_schema')!=CURRENT_SCHEMA or not policy.get('version'):raise ValueError('Invalid Daily Stock policy version/schema')
    for name,operator,unit in [('turnover_1d_usd','>=','USD'),('average_volume_10d_shares','>','shares per trading session')]:
        rule=policy[name]
        if rule.get('operator')!=operator or rule.get('unit')!=unit or not number(rule.get('threshold')) or rule['threshold']<0:
            raise ValueError('Invalid Daily Stock rule: '+name)
    return copy.deepcopy(policy)


def evaluate(row,policy,*,schema=CURRENT_SCHEMA,present=True):
    """Unknown eligibility never passes; valid zero is measured but ineligible."""
    result={'policy_version':policy['version'],'csv_schema':schema,'status':'unavailable','eligible':None,'reasons':[],'checks':{}}
    if not present:
        result['reasons']=['absent_from_daily_stock_csv; exclusion_cause_unknown'];return result
    if schema!=CURRENT_SCHEMA:
        result.update(status='legacy_unverified',reasons=['legacy_input_not_verified_under_current_daily_stock_policy']);return result
    for field in ('turnover_1d_usd','average_volume_10d_shares'):
        value=row.get(field);rule=policy[field]
        if not number(value) or value<0:
            result['checks'][field]=None;result['reasons'].append('missing_or_invalid:'+field)
        else:result['checks'][field]=value>=rule['threshold'] if rule['operator']=='>=' else value>rule['threshold']
    if any(value is None for value in result['checks'].values()):return result
    passed=all(result['checks'].values())
    result.update(status='eligible' if passed else 'ineligible',eligible=passed,
                  reasons=[field+':threshold_failed' for field,passed in result['checks'].items() if not passed])
    return result


def verified_eligibility(stock,policy,schema):
    """Re-evaluate measurements rather than trusting a supplied eligible flag."""
    if not policy:return {'status':'legacy_unverified','eligible':None,'policy_version':None,'csv_schema':None,'reasons':['snapshot_predates_daily_stock_policy'],'checks':{}}
    return evaluate(stock,policy,schema=schema,present=stock.get('metric_status')!='unavailable')
