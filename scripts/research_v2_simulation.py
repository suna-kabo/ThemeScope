"""Offline rule diagnostics: immutable inputs, aggregate output, no P&L backtest."""
from collections import Counter
from decimal import Decimal as D
from hashlib import sha256
from pathlib import Path
from statistics import mean
import argparse
import json
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.themescope.domain import load_configuration
from src.themescope.themes.calculations import Bar, benchmarks, breadth, deterministic, usable
from src.themescope.themes.index import ema


def classify(score, previous, direction, threshold):
    """Compare five-session score change in the chosen research direction."""
    if score is None:
        return 'Unavailable'
    strength = score if direction == 'long' else D(100) - score
    change = None if previous is None else (score - previous) * (1 if direction == 'long' else -1)
    if strength >= 50:
        return 'Fading' if change is not None and change <= -threshold else 'Leading'
    return 'Improving' if change is not None and change >= threshold else 'Lagging'


@deterministic
def average_dollar_volume(bars, ticker, sessions, index, window):
    if index + 1 < window:
        return None
    rows = [bars.get((ticker, day)) for day in sessions[index-window+1:index+1]]
    if any(not usable(row) for row in rows):
        return None
    return sum(row.close * row.volume for row in rows) / window


def load_inputs(root, database):
    """Pin the active successful run's observations, never mutable cache rows."""
    connection = sqlite3.connect(Path(database).resolve().as_uri() + '?mode=ro', uri=True)
    try:
        run, payload = connection.execute('SELECT run_id,payload FROM publication WHERE id=1').fetchone()
        snapshot = json.loads(payload)
        rows = connection.execute('SELECT o.identity,o.payload FROM daily_bars b JOIN observations o '
                                  'ON o.id=b.observation_id WHERE b.run_id=? ORDER BY b.ticker,b.session', (run,))
        bars = {}; identities = set(); digest = sha256()
        for identity, payload in rows:
            identities.add(identity); digest.update((identity + '\n' + payload + '\n').encode())
            bar = Bar(**json.loads(payload))
            bars[bar.ticker, bar.session] = bar
        official = connection.execute("SELECT session,count(*) FROM refresh_run WHERE status='success' "
                                      'GROUP BY session ORDER BY session').fetchall()
    finally:
        connection.close()
    if snapshot.get('synthetic_fixture') or len(identities) != 1:
        raise ValueError('One real pinned provider identity required')
    first = min(day for _, day in bars)
    calendar = json.loads((root/'config/calendars/xnys_2020_2035_v1.json').read_text())['sessions']
    sessions = tuple(row['session'] for row in calendar if first <= row['session'] <= snapshot['session'])
    config = load_configuration(root)
    members = {t.theme_id: config.members_on(t.theme_id, snapshot['session']) for t in config.themes if t.status == 'active'}
    return config, bars, sessions, members, {
        'snapshot_session': snapshot['session'], 'pinned_run': run,
        'identity': next(iter(identities)), 'observations_sha256': digest.hexdigest(),
        'observations': len(bars), 'official_sessions': [day for day, _ in official],
        'reviewed_membership_sha256': sha256(json.dumps({key: [(m.ticker, m.role, m.effective_from, m.effective_to)
            for m in rows] for key, rows in members.items()}, sort_keys=True).encode()).hexdigest(),
        'official_available_trends': dict(Counter(t.get('index', {}).get('trend', 'Unavailable') for t in snapshot['themes'] if t['status'] == 'active')),
    }


def summarize(values):
    return {'minimum': min(values), 'mean': round(mean(values), 3), 'maximum': max(values)} if values else None


def transition_diagnostics(histories, changes, strengths, threshold):
    """Observed state episodes, with incomplete edge episodes explicitly censored."""
    output = {}
    for label in ('Improving', 'Fading'):
        durations = []; leading_times = []; exits = Counter(); left = right = 0; pairs = persistent = 0
        for theme, states in histories.items():
            for current, following in zip(states, states[1:]):
                if current == label and following != 'Unavailable':
                    pairs += 1; persistent += following == label
            index = 0
            while index < len(states):
                if states[index] != label:
                    index += 1; continue
                end = index + 1
                while end < len(states) and states[end] == label:
                    end += 1
                left_edge = index == 0 or states[index-1] == 'Unavailable'
                right_edge = end == len(states) or states[end] == 'Unavailable'
                left += left_edge; right += right_edge
                if not (left_edge or right_edge):
                    durations.append(end-index); exits[states[end]] += 1
                    if states[end] == 'Leading':leading_times.append(end-index)
                index = end
        completed = len(durations)
        output[label.lower()] = dict(completed_episodes=completed, left_censored=left,
            right_censored=right, completed_duration_sessions=summarize(durations),
            next_session_pairs=pairs, next_session_persistence=round(persistent/pairs, 6) if pairs else None,
            direct_exit_counts=dict(sorted(exits.items())),
            direct_to_leading_rate=round(exits['Leading']/completed, 6) if completed else None,
            direct_to_lagging_rate=round(exits['Lagging']/completed, 6) if completed else None)
        output[label.lower()]['sessions_to_direct_leading'] = summarize(leading_times)
    near = changed = 0
    for theme, states in histories.items():
        for index in range(1, len(states)):
            a, b = changes[theme][index-1:index+1]
            s, t = strengths[theme][index-1:index+1]
            if (None in (a,b,s,t) or 'Unavailable' in (states[index-1],states[index])
                    or (s >= 50) != (t >= 50)):
                continue
            if min(abs(abs(a)-threshold),abs(abs(b)-threshold)) <= 2:
                near += 1; changed += states[index-1] != states[index]
    output['threshold_neighborhood'] = dict(width_points=2, same_structural_zone_pairs=near,
        state_changes=changed, change_rate=round(changed/near, 6) if near else None)
    return output


@deterministic
def diagnose(config, bars, sessions, members, metadata):
    symbols = sorted({m.ticker for rows in members.values() for m in rows})
    start = max(config.methodology['return_sessions'])
    scores = []; populations = []; participations = []; dollar = {}; ranks = []
    stock_emas = {ticker: [] for ticker in symbols}
    # Seed once, then update only across contiguous valid sessions.
    ema_values = {}; streaks = {ticker: [] for ticker in symbols}
    for index, day in enumerate(sessions):
        for ticker in symbols:
            row = bars.get((ticker, day)); value = row.adjusted_close if usable(row) else None
            if value is None:
                streaks[ticker] = []; ema_values.pop(ticker, None)
            else:
                streaks[ticker].append(value)
                if ticker in ema_values:
                    ema_values[ticker] = D(2)/22*value + (1-D(2)/22)*ema_values[ticker]
                elif len(streaks[ticker]) >= 21:
                    ema_values[ticker] = ema(streaks[ticker], 21)
            stock_emas[ticker].append(ema_values.get(ticker))
        if index < start:
            continue
        metrics, score, _ = benchmarks(config, bars, sessions, day, members_for=lambda theme: members.get(theme, ()))
        scores.append(score)
        populations.append(tuple(frozenset(theme for theme, pair in metrics.items() if pair[horizon].value is not None)
                                 for horizon in (0, 1)) +
                           (frozenset(theme for theme, value in score.items() if value is not None),))
        ranks.append({theme: 1+sum(other > value for other in score.values() if other is not None)
                      for theme, value in score.items() if value is not None})
        closes = {ticker: bars[ticker, day].adjusted_close for ticker in symbols if usable(bars.get((ticker, day)))}
        participations.append({theme: breadth([m.ticker for m in rows], closes,
            {ticker: stock_emas[ticker][index] for ticker in symbols}, config.methodology)
            for theme, rows in members.items()})
        for window in (10, 20):
            dollar[index, window] = {ticker: average_dollar_volume(bars, ticker, sessions, index, window) for ticker in symbols}
    diagnostic_days = sessions[start:]
    if len(diagnostic_days) < 6:
        raise ValueError('At least six scored diagnostic sessions required')
    reasons = ['insufficient_completed_history' if index < 5 else
               'ranked_universe_changed' if populations[index] != populations[index-5] else
               'unavailable_score' if not populations[index][2] else 'comparable'
               for index in range(len(scores))]
    comparable = [reason == 'comparable' for reason in reasons]
    eligible = {}; liquidity = []
    for window in (10, 20):
        for millions in (5, 10, 20, 30):
            sets = []
            for index in range(start, len(sessions)):
                names = {ticker for ticker, value in dollar[index, window].items()
                         if value is not None and value >= D(millions)*1000000
                         and usable(bars.get((ticker, sessions[index]))) and bars[ticker, sessions[index]].close > 5}
                eligible[window, millions, index-start] = names; sets.append(names)
            liquidity.append({'window': window, 'floor_millions': millions,
                              'eligible_stocks': summarize([len(names) for names in sets]),
                              'daily_membership_changes': summarize([len(a ^ b) for a, b in zip(sets, sets[1:])]),
                              'latest_eligible': len(sets[-1]),
                              'latest_missing_history': sum(value is None for value in dollar[len(sessions)-1, window].values())})
    models = []; per_session = []; recent_models = []
    for threshold in (D(5), D(10), D(15)):
        for breadth_gate in (False, True):
            for direction in ('long', 'short'):
                prior_states = {}; churn = []; counts = []; stocks = []; leader_retained = []; emerging = []
                histories = {theme: [] for theme in members}
                changes = {theme: [] for theme in members}; strengths = {theme: [] for theme in members}
                state_totals = Counter(); latest_states = Counter()
                for offset, day in enumerate(diagnostic_days):
                    previous = scores[offset-5] if comparable[offset] else {}
                    states = {theme: classify(score, previous.get(theme), direction, threshold) for theme, score in scores[offset].items()}
                    for theme, label in states.items():
                        score, before = scores[offset][theme], previous.get(theme)
                        histories[theme].append(label if comparable[offset] else 'Unavailable')
                        changes[theme].append(None if score is None or before is None else (score-before)*(1 if direction=='long' else -1))
                        strengths[theme].append(None if score is None else score if direction=='long' else 100-score)
                    chosen = {theme for theme, state in states.items() if state in ('Leading', 'Improving', 'Fading')}
                    if breadth_gate:
                        chosen = {theme for theme in chosen if participations[offset][theme].value is not None
                                  and (participations[offset][theme].value >= 50 if direction == 'long'
                                       else participations[offset][theme].value <= 50)}
                    stock_set = {m.ticker for theme in chosen for m in members[theme]} & eligible[20, 10, offset]
                    counts.append(len(chosen)); stocks.append(len(stock_set)); state_totals.update(states.values())
                    if prior_states and comparable[offset] and comparable[offset-1]:
                        churn.append(sum(states[theme] != prior_states[theme] for theme in states
                                         if 'Unavailable' not in (states[theme], prior_states[theme])))
                    structural = {theme for theme, score in scores[offset].items() if score is not None and
                                  (score >= 50 if direction == 'long' else score <= 50)}
                    if structural:
                        leader_retained.append(len(chosen & structural) / len(structural))
                    emerging.append(sum(state == 'Improving' for state in states.values()))
                    prior_states = states; latest_states = Counter(states.values())
                    if threshold == 10 and not breadth_gate:
                        per_session.append({'session': day, 'side': direction, 'researchable_themes': len(chosen),
                                            'research_stocks': len(stock_set), 'states': dict(latest_states),
                                            'comparison_available': comparable[offset], 'comparison_reason': reasons[offset]})
                models.append({'delta_threshold': int(threshold), 'breadth_gate': breadth_gate, 'side': direction,
                               'researchable_themes': summarize(counts), 'research_stocks': summarize(stocks),
                               'state_changes_per_session': summarize(churn), 'improving_themes': summarize(emerging),
                               'state_churn_comparable_session_pairs': len(churn),
                               'structural_leader_retention': summarize(leader_retained),
                               'state_observations': dict(state_totals), 'latest_states': dict(latest_states)})
                if not breadth_gate:
                    recent_models.append(dict(delta_threshold=int(threshold), side=direction,
                        **transition_diagnostics(histories, changes, strengths, threshold)))
    rank_moves = [abs(now[theme]-old[theme]) for old, now in zip(ranks, ranks[1:]) for theme in old.keys() & now.keys()]
    pullbacks = []
    for offset, day in enumerate(diagnostic_days):
        index = start+offset
        pairs = [(bars.get((ticker, sessions[index-5])), bars.get((ticker, day))) for ticker in ('SPY', 'QQQ')]
        if all(usable(a) and usable(b) and b.adjusted_close < a.adjusted_close for a, b in pairs):
            row = next(r for r in per_session if r['session'] == day and r['side'] == 'long')
            pullbacks.append({key: row[key] for key in ('session', 'researchable_themes', 'research_stocks', 'states')})
    sensitivity = {}
    for label, minimum, maximum in (('small', 0, 9), ('larger', 10, len(symbols))):
        sample = [metric for day in participations for metric in day.values()
                  if minimum <= metric.valid <= maximum and metric.value is not None]
        sensitivity[label] = {
            'theme_session_observations': len(sample),
            'one_member_percentage_point_move': summarize([100 / metric.valid for metric in sample]),
            'breadth_50pct_gate_within_one_member': sum(abs(metric.value-D(50)) <= D(100)/metric.valid for metric in sample),
            'selected_state_or_ranking_influence': 0,
        }
    return {'schema': 'themescope-research-v2-diagnostics-1', 'inputs': metadata,
            'scope': {'membership': 'Frozen current reviewed Core+Enabler; offline diagnostic only; not historical membership reconstruction',
                      'first_session': diagnostic_days[0], 'last_session': diagnostic_days[-1],
                      'sessions': len(diagnostic_days), 'themes': len(members), 'unique_members': len(symbols),
                      'no_accounting_writes': True, 'no_profit_optimization': True},
            'liquidity_candidates': liquidity, 'state_candidates': models,
            'comparison_availability': dict(reason_counts=dict(sorted(Counter(reasons).items())),
                eligible_five_session_pairs=max(0, len(scores)-5), available_session_comparisons=sum(comparable),
                unavailable_session_comparisons=len(scores)-sum(comparable)),
            'recent_change_diagnostics': recent_models,
            'retention_interpretation': 'No-veto retention of structural leaders is a definition invariant, not independent validation of recent-change thresholds',
            'rank_absolute_daily_change': summarize(rank_moves),
            'selected_session_counts': per_session, 'broad_pullbacks': pullbacks,
            'small_themes': {theme: len(rows) for theme, rows in members.items() if len(rows) < 10},
            'breadth_sample_sensitivity': sensitivity,
            'selected': {'structural_boundary': 50, 'change_sessions': 5, 'change_threshold': 10,
                         'liquidity_sessions': 20, 'average_dollar_volume_floor': 10000000, 'price_exclusive': 5,
                         'breadth_ranking_weight': 0, 'small_breadth_below': 10,
                         'w_is_filter': False, 'trend_is_filter': False}}


def write_report(result, folder):
    folder.mkdir(parents=True, exist_ok=True)
    (folder/'research-v2-rule-simulation.json').write_text(json.dumps(result, indent=2, sort_keys=True)+'\n', encoding='utf-8', newline='\n')
    scope = result['scope']; inputs = result['inputs']
    lines = ['# Research Logic v2 rule simulation', '',
        f"Read-only pinned successful snapshot: {inputs['snapshot_session']}; {scope['sessions']} offline sessions "
        f"({scope['first_session']}–{scope['last_session']}), {scope['themes']} themes and {scope['unique_members']} unique members.", '',
        'The frozen current reviewed Core/Enabler selection is used retrospectively **only for diagnostics**. '
        'This has survivorship/look-ahead selection bias and is not a performance backtest, point-in-time membership '
        'reconstruction, or official launch history. Official snapshots and observations are never changed. '
        'No P&L, entries, or portfolio returns are optimized.', '',
        'Inputs come from the active successful run’s immutable observation references, not mutable cache rows. '
        'The JSON records run ID, provider identity and observation digest; it contains aggregate diagnostics, not raw prices/volumes.', '',
        '## Candidate theme models', '',
        'All candidates preserve the existing 60/40 score and use an exact five-completed-session score comparison. '
        'Short transforms score to 100−score and reverses change, so the rules are symmetric. '
        'At directional strength ≥50: Leading, or Fading when change ≤−threshold. '
        'Below 50: Improving when change ≥threshold; otherwise Lagging. '
        'Leading, Improving and Fading are researchable. Missing score is Unavailable; '
        'missing prior score does not invent a change. Breadth-veto alternatives require directional participation ≥50%.', '',
        '| Δ threshold | Breadth veto | Side | Themes min/mean/max | Stocks min/mean/max | Mean state changes/day | Mean improving | Structural retention |',
        '| --- | --- | --- | --- | --- | --- | --- | --- |']
    def span(value):
        return f"{value['minimum']}/{value['mean']}/{value['maximum']}" if value else 'Unavailable'
    for row in result['state_candidates']:
        lines.append(f"| {row['delta_threshold']} | {row['breadth_gate']} | {row['side']} | {span(row['researchable_themes'])} | "
                     f"{span(row['research_stocks'])} | {row['state_changes_per_session']['mean'] if row['state_changes_per_session'] else 'Unavailable'} | "
                     f"{row['improving_themes']['mean']} | {row['structural_leader_retention']['mean']} |")
    availability = result['comparison_availability']
    lines += ['', f"Five-session comparisons: {availability['available_session_comparisons']} available of "
              f"{availability['eligible_five_session_pairs']} eligible session pairs. "
              'Unavailable diagnostic dates: ' + ', '.join(f'{key}={value}' for key, value in availability['reason_counts'].items() if key != 'comparable') + '.',
              'The 1M, 3M and combined scored-theme populations must each match globally across t and t-5. '
              'Unavailable comparisons use structural Leading/Lagging fallback for product/list counts. '
              'They censor temporal episodes and are excluded from recent-state churn; availability changes '
              'are not counted as market-state changes. State churn uses adjacent dates with valid comparisons '
              'on both dates, and excludes missing-score theme pairs. JSON records the included session-pair count.', '',
              '**Retention is a definition check, not independent evidence for the recent-change threshold.** '
              'Every structurally strong theme is Leading or Fading and both are researchable, so the '
              'no-veto model necessarily reports 1.0. The breadth-veto comparison measures how many '
              'of those deliberately retained themes that extra gate would remove; it does not validate ±10.', '',
              '## Recent-state persistence and transitions', '',
              'Rates below are observed fractions (0–1), not profit metrics. Persistence is the fraction '
              'of valid next-session pairs that remain Improving. Transition rates use completed '
              'episodes only; left-edge and right-edge/missing-data episodes are censored and reported '
              'separately in JSON (one episode may touch both edges). Time to Leading counts sessions to a direct Improving → Leading '
              'exit, rather than counting later recoveries after a different state. Fading exits '
              'separate loss of directional structure (Lagging) from recovery (Leading).', '',
              '| Δ threshold | Side | Improving next-session persistence | Completed Improving episodes | Direct to Leading | Mean sessions to Leading | Fading to Lagging | Fading recovery to Leading | Near-threshold change rate |',
              '| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for row in result['recent_change_diagnostics']:
        improving, fading = row['improving'], row['fading']
        duration = improving['sessions_to_direct_leading']
        lines.append(f"| {row['delta_threshold']} | {row['side']} | {improving['next_session_persistence']} | "
                     f"{improving['completed_episodes']} | {improving['direct_to_leading_rate']} | "
                     f"{duration['mean'] if duration else 'Unavailable'} | {fading['direct_to_lagging_rate']} | "
                     f"{fading['direct_to_leading_rate']} | {row['threshold_neighborhood']['change_rate']} |")
    lines += ['', 'Near-threshold change rate counts state changes among pairs within two score-change '
              'points of either material-change boundary, while both dates stay in the same directional '
              'structural zone. It isolates material-change sensitivity from crossing structural score 50. '
              'These diagnostics distinguish temporal behavior without optimizing P&L or list size. '
              'The established ±10 rule is retained; the diagnostics do not establish predictive superiority.', '',
              'Rank instability is measured independently: absolute daily competition-rank movement '
              f"min/mean/max = {span(result['rank_absolute_daily_change'])}. State changes above count changed theme labels, "
              'not stock churn or profitable trades.', '', '## Daily liquidity candidates', '',
              'Price must be **above $5**. Liquidity is the arithmetic mean of each completed session’s '
              'raw close × raw volume. Every session in the 10- or 20-session window must exist and be completed/regular. '
              'No one-day turnover or share-volume gate is added. Eligibility never edits membership.', '',
              '| Sessions | Floor $M | Eligible min/mean/max | Daily eligibility changes min/mean/max | Latest eligible | Missing window |',
              '| --- | --- | --- | --- | --- | --- |']
    for row in result['liquidity_candidates']:
        lines.append(f"| {row['window']} | {row['floor_millions']} | {span(row['eligible_stocks'])} | "
                     f"{span(row['daily_membership_changes'])} | {row['latest_eligible']} | {row['latest_missing_history']} |")
    selected = [r for r in result['state_candidates'] if r['delta_threshold'] == 10 and not r['breadth_gate']]
    liquidity = {(r['window'], r['floor_millions']): r for r in result['liquidity_candidates']}
    lines += ['', '## Selected model', '',
              '- Keep the existing structural boundary at 50; use a 10-point five-session score move to identify meaningful improvement/deterioration.',
              '- Include every daily-eligible Core/Enabler member of researchable themes. W orders peers only; opposite-sign and unavailable W remain visible.',
              '- Use 20 completed sessions and $10M average dollar volume, with price >$5. Compare all eight liquidity candidates without targeting a stock count.',
              '- Keep breadth entirely contextual for every sample size. Below 10 valid members, flag the small sample; show numerator/denominator. One member moves a five-member theme by 20 percentage points, versus 5 points at 20 members.',
              '- Keep synthetic EMA trend visible as context. Do not gate on it: the inspected official snapshot has trend availability '
              f"{inputs['official_available_trends']}; a trend veto would suppress otherwise valid research during warmup.", '',
              'Rejected alternatives: the 5-point change model is more sensitive to modest cross-theme rotation; '
              '15 points delays emerging-theme discovery. The middle 10-point candidate balances the measured churn '
              'and discovery counts above. A breadth veto loses established structural leaders during participation '
              'pullbacks; it also makes one stock disproportionately decisive in small themes. '
              'The $20M/$30M alternatives remove additional reviewed names without a demonstrated research need; '
              '$5M admits thinner names. On these inputs the $10M/20-session rule has mean eligibility churn '
              f"{liquidity[20, 10]['daily_membership_changes']['mean']} versus "
              f"{liquidity[10, 10]['daily_membership_changes']['mean']} changes/day for its 10-session counterpart, "
              f"while retaining {liquidity[20, 10]['latest_eligible']-liquidity[20, 20]['latest_eligible']} more names "
              'than $20M at the latest snapshot. This supports a moderate floor without claiming an optimal liquidity rule.', '',
              '## Pullbacks, retention and symmetry', '',
              f"Both SPY and QQQ declined across five sessions on {len(result['broad_pullbacks'])} diagnostic sessions. "
              'Per-session researchable and state counts are in the JSON. By the explicit retention policy, structural leaders are retained '
              f"at mean ratios Long={selected[0]['structural_leader_retention']['mean']} and "
              f"Short={selected[1]['structural_leader_retention']['mean']} without the breadth veto. "
              'Fading is a label change, not deletion. Exact mirrored inputs are unit-tested for Long/Short symmetry; '
              'actual Long/Short counts differ because market behavior is not symmetric.', '',
              f"Small themes (<10 configured members): {len(result['small_themes'])}; their IDs and counts are in the JSON. "
              'They receive no breadth ranking weight, the same as larger themes. '
              'The state classifier takes no breadth input, so 0% and 100% breadth have identical state/ranking influence. '
              'The JSON measures actual one-member percentage-point sensitivity and observations within one member '
              'of a hypothetical 50% gate, separately for valid samples below 10 and samples of 10 or more.', '',
              '## Reproduce', '', '```powershell',
              '.venv-vnext/Scripts/python.exe scripts/research_v2_simulation.py',
              '.venv-vnext/Scripts/python.exe -m unittest discover -s tests -p test_research_v2_simulation.py -v', '```', '',
              'This workflow never calls a provider, changes membership, writes the runtime DB, or emits raw market data. '
              'New observations or memberships change results; the JSON pins the inspected inputs. Threshold selection '
              'is a transparent research policy choice, not predictive evidence. Production may calculate an '
              'explicitly labelled same-basis five-session research comparison from sufficient completed bars; '
              'that comparison never becomes or rewrites official accounting history.', '']
    (folder/'research-v2-rule-simulation.md').write_text('\n'.join(lines), encoding='utf-8', newline='\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, default=ROOT/'runtime/vnext/runtime.sqlite')
    parser.add_argument('--output', type=Path, default=ROOT/'reports')
    args = parser.parse_args()
    config, bars, sessions, members, metadata = load_inputs(ROOT, args.database)
    result = diagnose(config, bars, sessions, members, metadata)
    write_report(result, args.output)
    print(json.dumps({'scope': result['scope'], 'selected': result['selected'],
                      'liquidity_candidates': result['liquidity_candidates']}, indent=2))


if __name__ == '__main__':
    main()
