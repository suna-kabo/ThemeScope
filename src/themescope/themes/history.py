"""Live transition compatibility is explicit and isolated from legacy history."""
from dataclasses import dataclass
from .calculations import calendar

HISTORY_VERSION = 'themescope-vnext-history-1'
VALID_TRENDS = ('Bullish', 'Bearish', 'Mixed')
VALID_PRIORITIES = ('Primary long', 'Primary short', 'Watch')


@dataclass(frozen=True)
class ThemeHistory:
    session: str
    theme_id: str
    methodology: str
    series_id: str
    trend: str
    priority: str
    bootstrap: bool = False
    history_version: str = HISTORY_VERSION
    signal_eligible: bool = True


def compatible(previous, current, sessions):
    sessions=calendar(sessions)
    if previous is None or current.session not in sessions or previous.session not in sessions:
        return False
    return (not previous.bootstrap and not current.bootstrap
            and previous.signal_eligible and current.signal_eligible
            and bool(current.series_id) and previous.series_id==current.series_id
            and previous.theme_id==current.theme_id
            and current.methodology.startswith('themescope-vnext-')
            and previous.methodology==current.methodology
            and previous.history_version==current.history_version==HISTORY_VERSION
            and sessions.index(current.session)==sessions.index(previous.session)+1)


def transitions(previous, current, sessions):
    if not compatible(previous,current,sessions):
        return {'newly_bullish':None,'newly_bearish':None,'priority_change':None}
    valid = previous.trend in VALID_TRENDS and current.trend in VALID_TRENDS
    priority_valid = previous.priority in VALID_PRIORITIES and current.priority in VALID_PRIORITIES
    return {'newly_bullish':current.trend=='Bullish' and previous.trend!='Bullish' if valid else None,
            'newly_bearish':current.trend=='Bearish' and previous.trend!='Bearish' if valid else None,
            'priority_change':('—' if previous.priority==current.priority else 'New long' if current.priority=='Primary long' else 'New short' if current.priority=='Primary short' else 'Removed')
                              if priority_valid else None}
