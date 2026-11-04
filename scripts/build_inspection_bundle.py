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


def build(root=ROOT, *, test_report=None):
    root = Path(root)
    config = load_configuration(root)
    report = {'methodology': config.methodology['version'],
              'active_themes': sum(t.status == 'active' for t in config.themes),
              'watch_only_themes': sum(t.status == 'watch-only' for t in config.themes),
              'proposed_relationships': len(config.memberships),
              'unique_tickers': len({m.ticker for m in config.memberships}),
              'review_universe_tickers': len(config.universe['instruments']),
              'launch_effective_dates': 'pending',
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
        (stage / 'index.html').write_text('<!doctype html><meta charset="utf-8"><title>ThemeScope vNext inspection</title>'
            '<h1>ThemeScope vNext — provisional configuration</h1><p>No live market data. Production cutover is blocked.</p>'
            '<pre>'+html.escape(json.dumps(report, indent=2))+'</pre>'
            '<p><a href="methodology.md">Methodology</a> · <a href="migration-report.md">Migration comparison</a>'
            ' · <a href="test-report.txt">Tests</a></p>', encoding='utf-8')
        for path in stage.iterdir():
            safe_file(path)
        destination = root / 'inspection'
        if destination.is_symlink():
            raise ValueError('Inspection destination must not be a symlink')
        if destination.exists():
            # Only the generated allowlist is replaced; do not sweep unrelated work.
            allowed = {'configuration.json', 'migration-report.md', 'methodology.md', 'test-report.txt', 'index.html'}
            if any(p.name not in allowed or not p.is_file() or p.is_symlink() for p in destination.iterdir()):
                raise ValueError('Inspection destination contains unrelated files')
        destination.mkdir(exist_ok=True)
        for path in stage.iterdir():
            shutil.copyfile(path, destination / path.name)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--test-report', type=Path)
    args = parser.parse_args()
    print(json.dumps(build(test_report=args.test_report), indent=2))
