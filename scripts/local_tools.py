"""Manage private provider credentials and create SQLite research backups."""
import argparse
from contextlib import closing
from datetime import datetime, timezone
from getpass import GetPassWarning
from pathlib import Path
import sqlite3
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.themescope.local.credentials import app_data, configure


def backup(source, destination):
    destination.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    target = destination / f'ThemeScope-{stamp}.sqlite'
    with tempfile.NamedTemporaryFile(dir=destination, delete=False) as handle:
        temp = Path(handle.name)
    try:
        with (closing(sqlite3.connect(source.resolve().as_uri() + '?mode=ro', uri=True)) as live,
              closing(sqlite3.connect(temp)) as copy):
            live.backup(copy)
            if copy.execute('PRAGMA quick_check').fetchall() != [('ok',)]:
                raise sqlite3.DatabaseError('Backup integrity check failed')
        temp.rename(target)
        return target
    finally:
        temp.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('credentials', 'backup'))
    parser.add_argument('--if-missing', action='store_true')
    args = parser.parse_args()
    try:
        if args.command == 'credentials':
            configure(only_if_missing=args.if_missing)
        else:
            source = ROOT / 'runtime/vnext/runtime.sqlite'
            if not source.is_file():
                print('There is no live research database yet. Launch ThemeScope first.', file=sys.stderr)
                return 1
            print(f'Research backup saved to {backup(source, app_data() / "Backups")}')
    except (OSError, ValueError, GetPassWarning, EOFError, sqlite3.Error):
        print(f'Unable to complete {args.command}. Check the local console and application-data permissions.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
