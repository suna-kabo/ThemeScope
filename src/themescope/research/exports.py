"""Deterministic individual and combined TXT without a permanent home theme."""
from dataclasses import dataclass
from decimal import Decimal
import re
from ..domain import Role
from ..themes.calculations import number, deterministic
from ..tradingview import resolve


@dataclass(frozen=True)
class Qualification:
    ticker: str
    theme_id: str
    role: Role
    w: Decimal


def reviewed_mapping(configuration, mapping):
    """Fill identifiers from explicit venues in the validated TradingView review.

    No provider inference or default exchange: existing verified records win.
    This adds no legacy anchor dependency and does not mutate legacy mappings.
    """
    result=dict(mapping)
    if not configuration.universe.get('quantitative_policy_validated') or not configuration.universe.get('source_sha256'):
        return result
    for row in configuration.universe.get('instruments',()):
        ticker=row['ticker'];venue=row['exchange']
        if venue in ('NYSE','NASDAQ') and result.get(ticker,{}).get('status')!='verified':
            result[ticker]={'status':'verified','symbol':venue+':'+ticker,
                            'evidence_kind':'User-supplied TradingView review Symbol/Exchange',
                            'source_sha256':configuration.universe['source_sha256']}
    return result


@deterministic
def exports(relationships, direction, mapping):
    if direction not in ('long','short'):
        if relationships:raise ValueError('Directional qualifiers required')
        return {'individual':{},'combined':'','assignments':{}}
    rows=tuple(relationships)
    if len({(r.ticker,r.theme_id) for r in rows})!=len(rows):
        raise ValueError('Duplicate qualifying relationship')
    for r in rows:
        if r.role not in (Role.CORE,Role.ENABLER) or number(r.w) is None or not (r.w>0 if direction=='long' else r.w<0):
            raise ValueError('Invalid role or directional W')
        if not re.fullmatch('[a-z0-9]+(?:-[a-z0-9]+)*',r.theme_id):
            raise ValueError('Unsafe theme section identifier')
    symbols={r.ticker:resolve(r.ticker,mapping) for r in rows}
    if any(not re.fullmatch('[A-Z0-9_]+:[A-Z0-9_.-]+',s) for s in symbols.values()):
        raise ValueError('Unsafe TradingView identifier')
    if len(set(symbols.values()))!=len(symbols):
        raise ValueError('Distinct tickers resolve to one TradingView identifier')
    individual={theme:'\n'.join(symbols[r.ticker] for r in sorted(rows,key=lambda r:r.ticker) if r.theme_id==theme)+'\n'
                for theme in sorted({r.theme_id for r in rows})}
    assignments={}
    for ticker in sorted(symbols):
        choices=[r for r in rows if r.ticker==ticker]
        chosen=min(choices,key=lambda r:(0 if r.role==Role.CORE else 1,-r.w if direction=='long' else r.w,r.theme_id))
        assignments[ticker]={'assigned_section':chosen.theme_id,
                             'also_qualifies_in':sorted(r.theme_id for r in choices if r.theme_id!=chosen.theme_id)}
    lines=[]
    for theme in sorted({a['assigned_section'] for a in assignments.values()}):
        lines.append('###'+theme)
        lines.extend(symbols[ticker] for ticker,a in assignments.items() if a['assigned_section']==theme)
    return {'individual':individual,'combined':'\n'.join(lines)+('\n' if lines else ''),'assignments':assignments}
