"""Local-only publisher: clean branch, frozen allowlist, existing Pages project."""
from pathlib import Path
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_public_snapshot import (SnapshotError, build_locked, iso_session,
    publication_lock, validate_output)

BRANCH = 'refactor/themescope-vnext'


def git(*args, root=ROOT):
    try:
        result = subprocess.run(['git', *args], cwd=root, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        raise SnapshotError('Cannot verify the local repository.') from None


def clean_checkout(root=ROOT):
    if git('branch', '--show-current', root=root) != BRANCH:
        raise SnapshotError('Publish only from refactor/themescope-vnext.')
    if git('status', '--porcelain', '--untracked-files=all', root=root):
        raise SnapshotError('Commit or resolve working-tree changes before publishing.')
    # An ignored real artifact must never have been explicitly staged/tracked.
    if git('ls-files', '--', 'dist', 'runtime', root=root):
        raise SnapshotError('Runtime/output files must not be tracked in Git.')
    return git('rev-parse', 'HEAD', root=root)


def wrangler(arguments, directory):
    executable = shutil.which('npx')
    if not executable:
        raise SnapshotError('Node.js/npx is required locally. Install a current Node.js LTS release.')
    # Run away from repo .env/config/Functions; OAuth stays in Wrangler's normal
    # user-local storage. Never pass market-data credentials to the deployment CLI.
    env = {k:v for k,v in os.environ.items() if k.upper() not in
           ('APCA_API_KEY_ID','APCA_API_SECRET_KEY','ALPHAVANTAGE_API_KEY')}
    env.update(CI='true', WRANGLER_SEND_METRICS='false', NO_COLOR='1')
    try:
        result = subprocess.run([executable, '--yes', 'wrangler@4', *arguments], cwd=directory,
            env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=600)
    except (OSError, subprocess.TimeoutExpired):
        raise SnapshotError('Wrangler could not complete. No deployment success is confirmed.') from None
    if result.returncode:
        # Do not relay arbitrary CLI diagnostics that might include private paths.
        raise SnapshotError('Wrangler failed. Run npx wrangler@4 login locally, verify account/project access and retry.')
    return result.stdout


def listing(arguments, directory):
    try:
        data = json.loads(wrangler(arguments, directory))
        if not isinstance(data, list) or any(not isinstance(row, dict) for row in data):
            raise ValueError
        return data
    except (ValueError, TypeError):
        raise SnapshotError('Wrangler returned unexpected JSON; nothing further will be deployed.') from None


def deployment_rows(project, directory):
    return listing(['pages','deployment','list','--project-name='+project,'--environment=production','--json'], directory)


def publish(expected, project, root=ROOT):
    if not iso_session(expected) or not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,56}[a-z0-9])?', project):
        raise SnapshotError('Use YYYY-MM-DD and the exact existing Pages project name.')
    commit = clean_checkout(root)
    with publication_lock(root):
        output = build_locked(expected, root)
        with tempfile.TemporaryDirectory(prefix='themescope-pages-') as temporary:
            directory = Path(temporary)
            projects = listing(['pages','project','list','--json'], directory)
            matches = [p for p in projects if p.get('Project Name') == project]
            if len(matches) != 1:
                raise SnapshotError('Existing Pages project not found. No project will be created.')
            before = deployment_rows(project, directory)
            if not before or before[0].get('Environment') != 'Production' or before[0].get('Branch') != BRANCH:
                raise SnapshotError('Existing production deployment must use refactor/themescope-vnext. Check Pages branch settings first.')
            known_ids = {d.get('Id') for d in before}
            print('Target existing Pages production project: '+project+' · '+BRANCH)
            print('Automatic production Git builds must be disabled in Pages before publishing.')
            # Immutable isolated upload copy prevents another manual build/edit from
            # adding runtime files, Functions or a Wrangler config to this upload.
            upload = directory/'site'
            shutil.copytree(output, upload)
            validate_output(upload)
            if clean_checkout(root) != commit:
                raise SnapshotError('Repository changed during preparation; publish aborted.')
            wrangler(['pages','deploy',str(upload),'--project-name='+project,'--branch='+BRANCH,
                      '--commit-hash='+commit,'--commit-message=ThemeScope public snapshot '+expected,
                      '--commit-dirty=false'], directory)
            # Never equate a successful CLI exit/preview alias with production.
            for attempt in range(4):
                rows = deployment_rows(project, directory)
                new = [d for d in rows if d.get('Id') not in known_ids and d.get('Branch') == BRANCH
                       and d.get('Environment') == 'Production' and d.get('Source') == commit[:7]]
                # Wrangler formats successful ended stages as a time-ago string.
                # Unknown output or still-pending/failed stages never prove success.
                if new and re.fullmatch(r'just now|\d+ (?:second|minute|hour|day|week|month|year)s? ago', str(new[0].get('Status', ''))):
                    print('Confirmed new production deployment for session '+expected+'.')
                    print('Verify the completed session banner on the existing Pages production domain.')
                    return
                if attempt < 3:
                    time.sleep(2)
            raise SnapshotError('Upload returned, but a new successful production deployment could not be confirmed. Check Pages before retrying.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('session')
    parser.add_argument('project')
    args = parser.parse_args()
    try:
        publish(args.session, args.project)
    except SnapshotError as error:
        print('Public publish stopped: '+str(error), file=sys.stderr)
        return 1
    except OSError:
        print('Public publish stopped by a local file error. No success is confirmed.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
