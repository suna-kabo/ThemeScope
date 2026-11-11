"""Approved terminal economics, separate from trading bars and research prices.

No event discovery, symbol guessing or provider calls. A terminal value belongs
only to the existing holding's final earned session; it never creates a Bar.
"""
from dataclasses import dataclass, replace, asdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlparse
import json
import re
from .domain import iso_date, effective_session_after_close
from .providers.base import ProviderError
from .themes.calculations import deterministic, usable


class CorporateActionError(ProviderError):
    pass


def diagnostic(code, ticker):
    # Never copy provider bodies, URLs, credentials or arbitrary text into status.
    label=ticker if isinstance(ticker,str) and re.fullmatch(r'[A-Z][A-Z0-9.-]{0,19}',ticker) else 'INVALID_SYMBOL'
    return code+':'+label


@dataclass(frozen=True)
class TerminalAction:
    event_id: str
    ticker: str
    event_type: str
    last_trading_session: str
    valuation_session: str
    membership_effective_to: str
    cash_per_share: Decimal
    stock_ticker: str | None
    stock_ratio: Decimal
    replacement_ticker: str | None
    source: str
    source_notice: str
    approval_status: str
    approval_reference: str
    reviewed_on: str
    currency: str = 'USD'

    def __post_init__(self):
        try:
            if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',self.event_id):raise ValueError
            if not re.fullmatch(r'[A-Z][A-Z0-9.-]{0,19}',self.ticker):raise ValueError
            if self.event_type not in ('acquisition','symbol_conversion','delisting'):raise ValueError
            if self.approval_status!='approved' or not isinstance(self.approval_reference,str) or not self.approval_reference.strip() or not iso_date(self.reviewed_on):raise ValueError
            if self.currency!='USD' or urlparse(self.source).scheme!='https' or not urlparse(self.source).netloc or not isinstance(self.source_notice,str) or not self.source_notice.strip():raise ValueError
            dates=(self.last_trading_session,self.valuation_session,self.membership_effective_to)
            if not all(iso_date(d) for d in dates) or not dates[0]<dates[1]<dates[2]:raise ValueError
            for name in ('cash_per_share','stock_ratio'):
                raw=getattr(self,name)
                if isinstance(raw,bool) or not isinstance(raw,(str,Decimal)):raise ValueError
                value=Decimal(raw)
                if not value.is_finite() or value<0:raise ValueError
                object.__setattr__(self,name,value)
            if self.stock_ratio>0:
                if not isinstance(self.stock_ticker,str) or not re.fullmatch(r'[A-Z][A-Z0-9.-]{0,19}',self.stock_ticker) or self.stock_ticker==self.ticker:raise ValueError
            elif self.stock_ticker is not None:raise ValueError
            if self.cash_per_share==0 and self.stock_ratio==0 and self.event_type!='delisting':raise ValueError
            if self.replacement_ticker is not None and (self.replacement_ticker!=self.stock_ticker or not self.stock_ratio):raise ValueError
            if self.event_type=='symbol_conversion' and self.replacement_ticker is None:raise ValueError
        except (ValueError,TypeError,InvalidOperation):
            raise CorporateActionError(diagnostic('invalid_terminal_action',self.ticker)) from None


def validate_actions(actions, sessions=None):
    actions=tuple(actions)
    if any(not isinstance(a,TerminalAction) for a in actions):raise CorporateActionError('invalid_terminal_action_type')
    if len({a.ticker for a in actions})!=len(actions) or len({a.event_id for a in actions})!=len(actions):
        raise CorporateActionError('duplicate_terminal_action')
    if sessions is not None:
        sessions=tuple(sessions)
        for action in actions:
            try:
                valid=(effective_session_after_close(action.last_trading_session,sessions)==action.valuation_session
                       and effective_session_after_close(action.valuation_session,sessions)==action.membership_effective_to)
            except ValueError:
                valid=False
            if not valid:
                raise CorporateActionError(diagnostic('terminal_action_calendar_mismatch',action.ticker))
    return actions


def load_actions(root):
    path=Path(root)/'config/vnext/corporate_actions.json'
    if not path.exists():return ()  # No implicit exception: missing bars still fail.
    try:
        def unique(pairs):
            result={}
            for k,v in pairs:
                if k in result:raise ValueError
                result[k]=v
            return result
        document=json.loads(path.read_text(encoding='utf-8'),object_pairs_hook=unique)
        if type(document['schema_version']) is not int or document['schema_version']!=1 or not isinstance(document['events'],list):raise ValueError
        return validate_actions(TerminalAction(**row) for row in document['events'])
    except CorporateActionError:
        raise  # Already a sanitized code/ticker, useful for deliberate review.
    except (KeyError,TypeError,ValueError):
        raise CorporateActionError('invalid_terminal_action_ledger') from None


def apply_membership_ends(configuration, actions, sessions):
    """Versioned forward amendments; original reviewed launch CSV stays intact.

    Replacement is never inferred: its independently approved ordinary membership
    must already begin on the next earned session in every affected theme.
    """
    actions=validate_actions(actions,sessions)
    amendments={a.ticker:a for a in actions}
    memberships=[]
    for member in configuration.memberships:
        action=amendments.get(member.ticker)
        if action is None or member.effective_to and member.effective_to<=action.valuation_session:
            memberships.append(member);continue
        if (not member.effective_from or member.effective_from>action.valuation_session
                or member.effective_to not in (None,action.membership_effective_to)):
            raise CorporateActionError(diagnostic('terminal_membership_interval_conflict',member.ticker))
        if action.replacement_ticker and member.calculation_eligible:
            replacements=[m for m in configuration.memberships if m.ticker==action.replacement_ticker
                and m.theme_id==member.theme_id and m.effective_from==action.membership_effective_to and m.calculation_eligible]
            if len(replacements)!=1:
                raise CorporateActionError(diagnostic('approved_replacement_membership_missing',member.ticker))
        memberships.append(replace(member,effective_to=action.membership_effective_to))
    return replace(configuration,memberships=tuple(memberships),corporate_actions=actions)


@dataclass(frozen=True)
class TerminalValue:
    event_id: str
    ticker: str
    last_trading_session: str
    valuation_session: str
    previous_raw_close: Decimal
    successor_raw_close: Decimal | None
    value: Decimal


@deterministic
def resolve_values(actions, bars, target):
    """Use raw closes in the share units of explicitly approved consideration."""
    values=[]
    for action in validate_actions(actions):
        if action.valuation_session>target:continue
        if any(s==action.ticker and d>action.last_trading_session for s,d in bars):
            raise CorporateActionError(diagnostic('terminal_trading_bar_conflict',action.ticker))
        old=bars.get((action.ticker,action.last_trading_session))
        if not usable(old) or old.volume<=0:
            raise CorporateActionError(diagnostic('terminal_previous_data_missing',action.ticker))
        successor=None
        if action.stock_ratio:
            row=bars.get((action.stock_ticker,action.valuation_session))
            if not usable(row) or row.volume<=0:
                raise CorporateActionError(diagnostic('terminal_successor_data_missing',action.stock_ticker))
            successor=row.close
        value=action.cash_per_share+action.stock_ratio*(successor or Decimal(0))
        values.append(TerminalValue(action.event_id,action.ticker,action.last_trading_session,
            action.valuation_session,old.close,successor,value))
    return tuple(values)


def action_audit(actions, values, identity):
    ids={v.event_id for v in values}
    return {'schema_version':1,'events':[asdict(a) for a in actions if a.event_id in ids],
            'valuations':[asdict(v) for v in values], 'provider_identity':identity}
