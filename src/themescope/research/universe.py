"""Explicit research selection; never changes official membership intervals."""
from dataclasses import dataclass
from ..domain import effective_session_after_close


@dataclass(frozen=True)
class LaunchResearchUniverse:
    research_session: str
    launch_rebalance_session: str
    first_earned_session: str
    relationships: tuple
    methodology: str

    def members_for(self,theme_id):
        # The original effective-dated Membership objects are kept intact.
        return tuple(m for m in self.relationships if m.theme_id==theme_id and m.calculation_eligible)

    @property
    def series_id(self):
        return self.methodology+':pre-launch-research:'+self.launch_rebalance_session+':'+self.research_session

    def metadata(self):
        return {'state':'pre_launch_research','research_session':self.research_session,
                'membership_basis':'approved_launch_membership',
                'membership_basis_session':self.first_earned_session,
                'launch_rebalance_session':self.launch_rebalance_session,
                'first_earned_session':self.first_earned_session,'official_live_history':False,
                'approved_relationships':len(self.relationships),
                'calculation_relationships':sum(m.calculation_eligible for m in self.relationships)}


def approved_launch_universe(configuration,target,sessions,*,activation_blockers=()):
    """Use an approved future universe for today's research, not return accounting.

    Runtime roster blockers are supplied by the caller in addition to config gates.
    Official members_on/active_on and all effective dates remain unchanged.
    """
    launch=configuration.methodology.get('launch_rebalance_session')
    if activation_blockers or configuration.production_blockers() or not launch or target>=launch:
        return None
    if launch not in sessions:
        return None  # Cannot verify a launch beyond an incomplete supplied calendar.
    earned=effective_session_after_close(launch,sessions)
    active={t.theme_id for t in configuration.themes if t.status=='active'}
    rows=tuple(m for m in configuration.memberships if m.theme_id in active and m.active_on(earned))
    return LaunchResearchUniverse(target,launch,earned,rows,configuration.methodology['version'])


def contiguous_suffix(items,valid):
    """Use recent contiguous observations; never fill gaps or drop holdings."""
    start=len(items)
    for i in range(len(items)-1,-1,-1):
        if not valid(items[i]):break
        start=i
    return items[start:]
