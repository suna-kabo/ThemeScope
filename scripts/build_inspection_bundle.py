"""Build an allowlisted inspection directory from config and synthetic artifacts.

Never copies a runtime folder or whole working tree. Rejects unsafe inputs before
writing. Source-tree safety is reported separately from inspection-folder safety.
"""
from pathlib import Path
import argparse
import html
import json
import re
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.themescope.domain import load_configuration


def safe_file(path):
    if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
        raise ValueError('Symlinks are not inspection assets')
    name = path.name.lower()
    if name.startswith('.env') or any(x in name for x in ('.sqlite', '.db', 'raw_inputs', 'cache')):
        raise ValueError('Private/runtime file rejected: ' + name)
    if path.suffix not in {'.json', '.md', '.html', '.txt', '.csv', '.css', '.js'}:
        raise ValueError('Unsupported inspection asset: ' + name)
    data = path.read_bytes()
    if data.startswith(b'SQLite format 3\x00'):
        raise ValueError('SQLite runtime database rejected: ' + name)
    text = data.decode('utf-8')
    patterns = [r'-----BEGIN .*PRIVATE KEY-----', r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b',
                r'\bgh[pousr]_[A-Za-z0-9]{20,}',
                r'(?i)(?:api[_-]?key(?:[_-]?id)?|api[_-]?secret(?:[_-]?key)?|secret[_-]?key|access[_-]?token)[\"\x27]?\s*[=:]\s*[\"\x27]?[A-Za-z0-9_-]{12,}',
                r'(?i)(?:[A-Z]:[\\/](?:Users|Documents and Settings)[\\/]|/(?:home|Users|workspace|tmp)/)']
    if any(re.search(pattern, text) for pattern in patterns):
        raise ValueError('Secret or personal absolute path rejected: ' + name)
    if 'query1.finance.yahoo.com/v8/finance/chart' in text or any(re.search(pattern, text) for pattern in
        (r'"observations"\s*:', r'"bars"\s*:', r'"daily_bars"\s*:', r'"quoteResponse"\s*:')):
        raise ValueError('Raw provider data rejected: ' + name)
    return text


def build(root=ROOT, *, test_report=None, engine_report=None, provider_report=None, ui_snapshot=None):
    root = Path(root)
    config = load_configuration(root)
    report = {'methodology': config.methodology['version'],
              'active_themes': sum(t.status == 'active' for t in config.themes),
              'watch_only_themes': sum(t.status == 'watch-only' for t in config.themes),
              'proposed_relationships': len(config.memberships),
              'unique_tickers': len({m.ticker for m in config.memberships}),
              'review_universe_tickers': len(config.universe['instruments']),
              'launch_effective_dates': 'pending' if any(not m.effective_from for m in config.memberships) else sorted({m.effective_from for m in config.memberships}),
              'production_enabled': config.methodology['production_enabled'],
              'launch_rebalance_session': config.methodology['launch_rebalance_session'],
              'production_blockers': config.production_blockers(),
              'data_kind': 'configuration and synthetic fixtures only'}
    with tempfile.TemporaryDirectory(prefix='.inspection-', dir=root) as temporary:
        stage = Path(temporary)
        (stage / 'configuration.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
        for source, name in [(root/'docs/vnext_preflight.md', 'migration-report.md'),
                             (root/'docs/vnext/ThemeScope_vNext_Product_and_Methodology_Spec.md', 'methodology.md')]:
            (stage / name).write_text('\n'.join(line.rstrip() for line in safe_file(source).splitlines()) + '\n', encoding='utf-8')
        (stage / 'test-report.txt').write_text(safe_file(Path(test_report)) if test_report else
            'No test report supplied; checkpoint is not certified.\n', encoding='utf-8')
        engine_preview = ''
        if engine_report:
            engine_text = safe_file(Path(engine_report))
            engine = json.loads(engine_text)
            if engine.get('synthetic_fixture') is not True:
                raise ValueError('Engine inspection must be explicitly synthetic')
            (stage / 'engine-report.json').write_text(engine_text, encoding='utf-8')
            engine_preview = '<h2>Synthetic calculation fixture</h2><p><a href="engine-report.json">Full formulas, peer results and exports</a></p>'
            for direction, scenario in engine.get('scenarios', {}).items():
                engine_preview += '<h3>'+html.escape(direction)+'</h3><table><tr><th>Theme</th><th>Score</th><th>Trend</th><th>Priority</th></tr>'
                for theme in scenario['themes']:
                    engine_preview += '<tr>'+''.join('<td>'+html.escape(str(theme[key]))+'</td>' for key in ('theme_id','score','trend','priority'))+'</tr>'
                engine_preview += '</table><h4>Combined TXT</h4><pre>'+html.escape(scenario['exports']['combined'])+'</pre>'
                for ticker, assignment in scenario['exports']['assignments'].items():
                    engine_preview += '<p>'+html.escape(ticker+' → '+assignment['assigned_section']+'; also qualifies in: '+', '.join(assignment['also_qualifies_in']))+'</p>'
        if provider_report:
            (stage / 'provider-report.md').write_text(safe_file(Path(provider_report)), encoding='utf-8')
            engine_preview += '<h2>Gate C provider</h2><p><a href="provider-report.md">Provider, cache migration and local SIP command</a></p>'
        if ui_snapshot:
            snapshot_text = safe_file(Path(ui_snapshot))
            snapshot = json.loads(snapshot_text)
            if snapshot.get('synthetic_fixture') is not True:
                raise ValueError('UI inspection must be synthetic')
            (stage/'ui-report.md').write_text(safe_file(root/'docs/vnext_local_ui.md'), encoding='utf-8')
            ui = stage / 'ui'
            ui.mkdir()
            for name in ('index.html', 'app.js', 'app.css'):
                (ui/name).write_text(safe_file(root/'static/vnext'/name), encoding='utf-8')
            (ui/'preview.js').write_text('window.FIXTURE_SNAPSHOT='+snapshot_text+';', encoding='utf-8')
            engine_preview += '<h2>Gate D local UI</h2><p><a href="ui/index.html">Open synthetic interactive UI preview</a> · <a href="ui-report.md">Local launch and validation report</a></p>'
        (stage / 'index.html').write_text('<!doctype html><meta charset="utf-8"><title>ThemeScope vNext inspection</title>'
            '<style>body{font:16px system-ui;max-width:1000px;margin:3rem auto;padding:0 1rem}table{border-collapse:collapse}td,th{padding:.5rem;border:1px solid #aaa;text-align:left}pre{white-space:pre-wrap;background:#eee;padding:1rem}a{color:#1463b8}</style><h1>ThemeScope vNext — provisional configuration</h1><p>No live market data. See configuration activation status below.</p>'
            '<pre>'+html.escape(json.dumps(report, indent=2))+'</pre>'
            '<p><a href="methodology.md">Methodology</a> · <a href="migration-report.md">Migration comparison</a>'
            ' · <a href="test-report.txt">Tests</a></p>'+engine_preview, encoding='utf-8')
        for path in stage.rglob('*'):
            if path.is_file(): safe_file(path)
        destination = root / 'inspection'
        if destination.is_symlink():
            raise ValueError('Inspection destination must not be a symlink')
        if destination.exists():
            # Only the generated allowlist is replaced; do not sweep unrelated work.
            allowed = {p.name for p in stage.iterdir()}
            if any(p.name not in allowed or p.is_symlink() or (not p.is_file() and p.name != 'ui') for p in destination.iterdir()):
                raise ValueError('Inspection destination contains unrelated files')
        if (destination/'ui').exists():
            if any(p.name not in {'index.html','app.js','app.css','preview.js'} or not p.is_file() or p.is_symlink() for p in (destination/'ui').iterdir()):
                raise ValueError('Inspection UI contains unrelated files')
        destination.mkdir(exist_ok=True)
        for path in stage.iterdir():
            if path.is_dir(): shutil.copytree(path, destination/path.name, dirs_exist_ok=True)
            else: shutil.copyfile(path, destination / path.name)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--test-report', type=Path)
    parser.add_argument('--engine-report', type=Path)
    parser.add_argument('--provider-report', type=Path)
    parser.add_argument('--ui-snapshot', type=Path)
    args = parser.parse_args()
    print(json.dumps(build(test_report=args.test_report, engine_report=args.engine_report, provider_report=args.provider_report, ui_snapshot=args.ui_snapshot), indent=2))
