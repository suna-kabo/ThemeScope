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
from http.client import HTTPException
from urllib.error import URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_public_snapshot import (SnapshotError, build_locked, iso_session,
    publication_lock, validate_output, strict_json)

BRANCH = 'main'
PROJECT_NAME = re.compile(r'[a-z0-9](?:[a-z0-9-]{0,56}[a-z0-9])?\Z')


def git(*args, root=ROOT):
    try:
        result = subprocess.run(['git', *args], cwd=root, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        raise SnapshotError('Cannot verify the local repository.') from None


def clean_checkout(root=ROOT):
    if git('branch', '--show-current', root=root) != BRANCH:
        raise SnapshotError('Publish only from main.')
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
            env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True,
            encoding='utf-8', errors='strict', timeout=600)
    except (OSError, UnicodeError, subprocess.TimeoutExpired):
        raise SnapshotError('Wrangler could not complete. No deployment success is confirmed.') from None
    if result.returncode:
        # Do not relay arbitrary CLI diagnostics that might include private paths.
        raise SnapshotError('Wrangler failed. Run npx wrangler@4 login locally, verify account/project access and retry.')
    return result.stdout


def metadata(output, expected=list):
    try:
        def unique_object(pairs):
            row = {}
            for key, value in pairs:
                if key in row:
                    raise ValueError
                row[key] = value
            return row
        def invalid_constant(_):
            raise ValueError
        decoder = json.JSONDecoder(object_pairs_hook=unique_object, parse_constant=invalid_constant)
        # A JSON string containing brackets is not a metadata payload.
        if output.lstrip('\ufeff \t\r\n').startswith('"'):
            raise ValueError
        data = None
        offset = 0
        while match := re.search(r'[\[\]{}]', output[offset:]):
            start = offset + match.start()
            if output[start] in ']}':
                raise ValueError
            # Known log-level tags are plain informational text, not JSON starts.
            tag = re.match(r'\[(?:INFO|WARN|WARNING|ERROR|DEBUG|NOTICE|wrangler|npx|npm)\]', output[start:], re.IGNORECASE)
            if tag:
                offset = start + tag.end()
                continue
            candidate, offset = decoder.raw_decode(output, start)
            # Never recover an inner array from a broken/object wrapper, choose
            # among multiple payloads, or ignore malformed JSON after a payload.
            if (data is not None or not isinstance(candidate, expected) or
                    expected is list and any(not isinstance(row, dict) for row in candidate)):
                raise ValueError
            data = candidate
        if data is None:
            raise ValueError
        return data
    except (ValueError, TypeError, RecursionError):
        raise SnapshotError('Wrangler returned unexpected JSON; nothing further will be deployed.') from None


def listing(arguments, directory):
    return metadata(wrangler(arguments, directory))


class NoCloudflareRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise SnapshotError('Cloudflare project verification redirected; publish stopped.')


def production_project(project, directory):
    """Read actual Pages settings using supported Wrangler auth, never log tokens.

    The last production deployment may legitimately predate the branch cutover.
    Its branch is historical evidence, not the project's configured production branch.
    """
    identity = metadata(wrangler(['whoami', '--json'], directory), dict)
    accounts = identity.get('accounts')
    if (identity.get('loggedIn') is not True or not isinstance(accounts, list) or
            not accounts or any(not isinstance(a, dict) for a in accounts)):
        raise SnapshotError('Cannot verify the authenticated Cloudflare account.')
    ids = [a.get('id') for a in accounts]
    if any(not isinstance(a, str) or not re.fullmatch(r'[a-fA-F0-9]{32}', a) for a in ids):
        raise SnapshotError('Cannot verify the authenticated Cloudflare account.')
    account = os.environ.get('CLOUDFLARE_ACCOUNT_ID')
    if account is None and len(ids) == 1:
        account = ids[0]
    if account not in ids:
        raise SnapshotError('Select the intended Cloudflare account with CLOUDFLARE_ACCOUNT_ID.')
    auth = metadata(wrangler(['auth', 'token', '--json'], directory), dict)
    headers = {'Accept': 'application/json'}
    if auth.get('type') in ('oauth', 'api_token') and isinstance(auth.get('token'), str) and auth['token']:
        headers['Authorization'] = 'Bearer ' + auth['token']
    elif auth.get('type') == 'api_key' and all(isinstance(auth.get(k), str) and auth[k] for k in ('key', 'email')):
        headers.update({'X-Auth-Key': auth['key'], 'X-Auth-Email': auth['email']})
    else:
        raise SnapshotError('Cannot verify local Wrangler authentication.')
    request = Request('https://api.cloudflare.com/client/v4/accounts/' + account +
                      '/pages/projects/' + project, headers=headers)
    try:
        # Keep the normal trusted HTTPS proxy/CA configuration. No redirects can
        # forward Cloudflare auth to another host; market-data auth is never used.
        with build_opener(NoCloudflareRedirect()).open(request, timeout=15) as response:
            if response.status != 200 or response.headers.get_content_type() != 'application/json':
                raise SnapshotError('Cannot verify Cloudflare Pages project settings.')
            raw = response.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise SnapshotError('Cannot verify Cloudflare Pages project settings.')
        payload = strict_json(raw.decode('utf-8'))
    except (OSError, URLError, UnicodeError, HTTPException, ValueError, TypeError):
        raise SnapshotError('Cannot verify Cloudflare Pages project settings; nothing will be uploaded.') from None
    settings = payload.get('result') if isinstance(payload, dict) and payload.get('success') is True else None
    if not isinstance(settings, dict) or settings.get('name') != project or settings.get('production_branch') != BRANCH:
        raise SnapshotError('Set the existing Pages project production branch to main before publishing.')
    source = settings.get('source')
    if source is not None:
        config = source.get('config') if isinstance(source, dict) else None
        if not isinstance(config, dict) or config.get('production_deployments_enabled') is not False:
            raise SnapshotError('Disable automatic production Git deployments in Pages before publishing.')


def deployment_rows(project, directory):
    return listing(['pages','deployment','list','--project-name='+project,'--environment=production','--json'], directory)


def publish(expected, project, root=ROOT):
    if not iso_session(expected) or not PROJECT_NAME.fullmatch(project):
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
            production_project(project, directory)
            before = deployment_rows(project, directory)
            if not before or before[0].get('Environment') != 'Production':
                raise SnapshotError('Cannot verify the existing production deployment; publish stopped.')
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
