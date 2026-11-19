"""Pure Market-side interpretation of Theme Score and its raw change.

Consumes supplied metrics and policy only; no prices, config files or provider IO.
"""
from decimal import Decimal,InvalidOperation,localcontext,Context,ROUND_HALF_EVEN


def _number(value):
    if value is None or isinstance(value,bool):return None
    try:
        result=Decimal(str(value))
        return result if result.is_finite() else None
    except (InvalidOperation,ValueError):return None


def state(score,change,direction,rules):
    if direction not in ('long','short'):return None
    score,change=_number(score),_number(change)
    if score is None or not 0<=score<=100:return 'Unavailable'
    with localcontext(Context(prec=34,rounding=ROUND_HALF_EVEN)):
        strength=score if direction=='long' else 100-score
        delta=change if direction=='long' or change is None else -change
        if strength>=Decimal(str(rules['structural_boundary'])):
            return 'Fading' if delta is not None and delta<=-Decimal(str(rules['material_score_change'])) else 'Leading'
        return 'Improving' if delta is not None and delta>=Decimal(str(rules['material_score_change'])) else 'Lagging'
