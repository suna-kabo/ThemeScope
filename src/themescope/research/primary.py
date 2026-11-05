"""Daily eligibility and independent theme relationships; no membership mutations."""
from dataclasses import dataclass
from decimal import Decimal as D
from ..themes.calculations import POLICY, calendar, deterministic, number, usable


@dataclass(frozen=True)
class Eligibility:
    available: bool
    eligible: bool
    close: D | None
    average_volume: D | None
    turnover: D | None
    reasons: tuple[str, ...]


@deterministic
def daily_eligibility(bars, ticker, sessions, target, policy=POLICY):
    sessions=calendar(sessions)
    index=sessions.index(target)
    count=policy['average_volume_sessions']
    if index+1<count:
        return Eligibility(False,False,None,None,None,('insufficient_volume_history',))
    rows=[bars.get((ticker,s)) for s in sessions[index-count+1:index+1]]
    if any(not usable(row) for row in rows):
        return Eligibility(False,False,None,None,None,('missing_completed_regular_session',))
    close=rows[-1].close
    average=sum(row.volume for row in rows)/count
    turnover=close*rows[-1].volume
    reasons=[]
    if close<D(str(policy['price_floor'])):reasons.append('price_below_floor')
    if average<=D(str(policy['average_volume_floor_exclusive'])):reasons.append('average_volume_not_above_floor')
    if turnover<D(str(policy['turnover_floor'])):reasons.append('turnover_below_floor')
    return Eligibility(True,not reasons,close,average,turnover,tuple(reasons))


def side(direction):
    # Actual unchanged Market Matrix output labels plus the spec's display names.
    if direction in ('Long bias','Long','Selective long','Selective Long'):return 'long'
    if direction in ('Short bias','Short','Selective short','Selective Short'):return 'short'
    return None


def priority(direction, score, trend, transition, policy=POLICY):
    score=number(score)
    if score is None or not D(0)<=score<=D(100) or trend not in ('Bullish','Bearish','Mixed'):
        return 'Watch'
    direction=side(direction)
    boundary=D(str(policy['score_boundary']))
    if direction=='long' and ((score>=boundary and trend in ('Bullish','Mixed')) or
                             (trend=='Bullish' and transition.get('newly_bullish') is True)):
        return 'Primary long'
    if direction=='short' and ((score<boundary and trend in ('Bearish','Mixed')) or
                              (trend=='Bearish' and transition.get('newly_bearish') is True)):
        return 'Primary short'
    return 'Watch'


def qualifies(label, w, eligibility):
    w=number(w)
    return bool(eligibility.eligible and w is not None and
                ((label=='Primary long' and w>0) or (label=='Primary short' and w<0)))
