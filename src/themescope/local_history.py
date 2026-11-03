"""Versioned local ranking history, published in the dashboard transaction."""
import copy
import hashlib
import json
import math
from pathlib import Path

SCHEMA = 'themescope-ranking-history-1'


def record(snapshot):
    themes = sorted(snapshot['themes'], key=lambda t: t['id'])
    # Old rank fingerprints included two retired presentation thresholds. Retain
    # their hash inputs privately so removing labels cannot invalidate Δ Rank.
    weights=copy.deepcopy(snapshot['score_methodology'])
    ranking=copy.deepcopy(snapshot.get('ranking_configuration'))
    if snapshot['methodology_version']=='manual-csv-1':
        weights.setdefault('state_threshold',50)
        if isinstance(ranking,dict):ranking.setdefault('state_boundary',50)
    config = {'methodology': snapshot['methodology_version'], 'weights': weights,
              'ranking_configuration': ranking,
              'percentile': snapshot['manual_csv_audit']['percentile_method'],
              'universe': [[t['id'], t['anchor']] for t in themes if t['theme_score'] is not None],
              'configured_universe': [[t['id'], t['anchor']] for t in themes]}
    fingerprint = hashlib.sha256(json.dumps(config, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    result = {'schema': SCHEMA, 'session_date': snapshot['session_date'], 'methodology_version': snapshot['methodology_version'],
            'ranking_configuration_fingerprint': fingerprint, 'eligible_universe': config['universe'],
            'themes': [{k: t.get(k) for k in ('id', 'anchor', 'current_strength_score', 'medium_strength_score', 'theme_score', 'global_rank')} |
                       {'performance_1m_pct': t['returns']['21']['value'] * 100 if t['returns']['21']['value'] is not None else None,
                        'performance_3m_pct': t['returns']['63']['value'] * 100 if t['returns']['63']['value'] is not None else None} for t in themes]}
    if snapshot.get('run_kind')=='manual_csv':
        from .research_policy import EMA_VERSION,PRIORITY_VERSION,INPUT_SEMANTICS
        result['research_history']={'ema_methodology':EMA_VERSION,'priority_methodology':PRIORITY_VERSION,'input_semantics':INPUT_SEMANTICS,
            'market_classification':snapshot['market_classification']['direction'],
            'market_inputs':[{k:r.get(k) for k in ('ticker','price_close','ema21','ema50','price_state','breadth_state','index_breadth')} for r in snapshot.get('context',[])]}
        by_id={t['id']:t for t in snapshot['themes']}
        for row in result['themes']:
            theme=by_id[row['id']]
            row.update({k:theme.get(k) for k in ('tradingview_symbol','price_close','ema21','ema50','etf_ema_classification','ema_transition','ema_comparison_reason','priority_change','priority_comparison_session')})
            row['priority_label']=theme.get('research_priority',{}).get('label')
            row['priority_reason_code']=theme.get('research_priority',{}).get('reason_code')
    return result



def validate_record(value, session):
    if not isinstance(value, dict) or value.get('schema') != SCHEMA or value.get('session_date') != session:
        raise ValueError('history schema/session mismatch')
    if not isinstance(value.get('ranking_configuration_fingerprint'), str) or len(value['ranking_configuration_fingerprint']) != 64:
        raise ValueError('invalid ranking fingerprint')
    universe = value['eligible_universe']
    identities = {row[0]: row[1] for row in universe}
    rows = value['themes']
    if len(identities) != len(universe) or len({row['id'] for row in rows}) != len(rows):
        raise ValueError('duplicate history identity')
    for row in rows:
        if row['id'] in identities:
            rank = row['global_rank']
            if row['anchor'] != identities[row['id']] or isinstance(rank, bool) or not isinstance(rank, (int,float)) or not math.isfinite(rank) or not 1 <= rank <= len(universe):
                raise ValueError('invalid history anchor/rank')
    if set(identities) - {row['id'] for row in rows}:
        raise ValueError('missing eligible history identity')


def apply(snapshot, history_dir: Path, calendar_path: Path):
    current = record(snapshot)
    validate_record(current, snapshot["session_date"])
    sessions = [r['session'] for r in json.loads(calendar_path.read_text(encoding='utf-8'))['sessions']]
    index = sessions.index(snapshot['session_date'])
    previous_date = sessions[index - 1] if index else None
    status = 'No snapshot for immediately preceding US trading session.'
    previous = None
    research_previous = None
    if previous_date:
        path = history_dir / (previous_date + '.json')
        if path.exists():
            try:
                candidate = json.loads(path.read_text(encoding='utf-8'))
                validate_record(candidate, previous_date)
                research_previous=candidate
                if candidate.get('methodology_version') != current['methodology_version'] or candidate.get('ranking_configuration_fingerprint') != current['ranking_configuration_fingerprint'] or candidate.get('eligible_universe') != current['eligible_universe']:
                    status = 'Previous session ranking configuration or eligible universe differs.'
                else:
                    rows = candidate['themes']
                    if len({r['id'] for r in rows}) != len(rows): raise ValueError('duplicate theme')
                    previous = {r['id']:r for r in rows}
                    for t in current['themes']:
                        old = previous[t['id']]
                        if old['anchor'] != t['anchor']: raise ValueError('anchor mismatch')
                        if t['global_rank'] is not None and (isinstance(old['global_rank'], bool) or not isinstance(old['global_rank'], (float,int)) or not math.isfinite(old['global_rank']) or not 1 <= old['global_rank'] <= len(current['eligible_universe'])):
                            raise ValueError('invalid rank')
                    status = 'Comparable immediately preceding US session.'
            except (ValueError, KeyError, TypeError, AttributeError, IndexError, OSError) as exc:
                previous = None
                research_previous = None
                status = 'Malformed previous-session history: ' + str(exc)
    # Refuse to silently destroy an existing malformed same-session record.
    target = history_dir / (snapshot['session_date'] + '.json')
    if target.exists():
        try:
            existing = json.loads(target.read_text(encoding='utf-8'))
            validate_record(existing, snapshot['session_date'])
        except (ValueError, OSError, AttributeError, KeyError, TypeError, IndexError) as exc:
            raise ValueError('Existing same-session history is malformed; preserve and repair it explicitly: ' + str(exc)) from exc
    for t in snapshot['themes']:
        old = previous.get(t['id']) if previous else None
        t['rank_change_daily'] = old['global_rank'] - t['global_rank'] if old and t['global_rank'] is not None else None
        t['rank_comparison_session'] = previous_date
        t['rank_change_reason'] = status
    snapshot['local_history'] = {'schema':SCHEMA, 'comparison_session':previous_date, 'status':status,
                                 'fingerprint':current['ranking_configuration_fingerprint']}
    snapshot['manual_csv_audit']['local_history'] = snapshot['local_history']
    if snapshot.get('run_kind')=='manual_csv':
        from .research_policy import apply_policy
        apply_policy(snapshot,research_previous,previous_date)
        current=record(snapshot)
    return current
