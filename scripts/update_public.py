"""Refresh the normal loopback app, verify its new publication, then publish it.

No calendar, calculation, provider, membership or export logic lives here.
Credentials stay in process environments; errors never relay raw API/CLI output.
"""
from datetime import datetime, timezone
from http.client import HTTPException
from pathlib import Path
import argparse
import errno
import os
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import publish_public_snapshot as publisher
from scripts.build_public_snapshot import (SnapshotError, NoRedirect, strict_json,
                                          project_snapshot, iso_session, LIMIT)

ORIGIN = 'http://127.0.0.1:8766'
PATHS = {'/api/status', '/api/refresh/status', '/api/refresh', '/api/dashboard-data'}


class ServerUnavailable(SnapshotError):
    """Connection refused permits starting an owned server, not adopting another app."""


class LoopbackClient:
    def __init__(self):
        self.opener = build_opener(ProxyHandler({}), NoRedirect())

    def request(self, path, *, post=False, timeout=15):
        if path not in PATHS or post != (path == '/api/refresh'):
            raise SnapshotError('Invalid local automation request.')
        headers = {'Accept': 'application/json'}
        if post:
            headers.update({'Origin': ORIGIN, 'Content-Type': 'application/json'})
        request = Request(ORIGIN + path, data=b'{}' if post else None,
                          headers=headers, method='POST' if post else 'GET')
        try:
            with self.opener.open(request, timeout=timeout) as response:
                if response.status != (202 if post else 200) or response.headers.get_content_type() != 'application/json':
                    raise SnapshotError('Local ThemeScope returned an unexpected response.')
                raw = response.read(LIMIT + 1)
            if not raw or len(raw) > LIMIT:
                raise SnapshotError('Local ThemeScope response is empty or too large.')
            return strict_json(raw.decode('utf-8'))
        except HTTPError:
            raise SnapshotError('Local ThemeScope request refused; no publication will start.') from None
        except URLError as error:
            reason = error.reason
            if isinstance(reason, ConnectionRefusedError) or getattr(reason, 'errno', None) in (errno.ECONNREFUSED, 10061):
                raise ServerUnavailable('Local ThemeScope is not running.') from None
            raise SnapshotError('Cannot contact local ThemeScope; no publication will start.') from None
        except (OSError, UnicodeError, HTTPException):
            raise SnapshotError('Cannot read local ThemeScope; no publication will start.') from None


def live_status(value):
    if (not isinstance(value, dict) or value.get('mode') != 'live' or
            value.get('state') not in ('idle', 'running', 'success', 'failed', 'interrupted')):
        raise SnapshotError('A recognized live ThemeScope server is required; fixture mode cannot publish.')
    return value


def stamp(value):
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if parsed.tzinfo is None:
            raise ValueError
        return parsed.astimezone(timezone.utc)
    except (ValueError, TypeError, AttributeError, OverflowError):
        raise SnapshotError('Refresh publication timestamp is unavailable or invalid.') from None


def remaining(deadline):
    seconds = deadline - time.monotonic()
    if seconds <= 0:
        raise SnapshotError('Refresh timed out; no publication will start.')
    return min(15, seconds)


def stop_owned(process):
    if process is None or process.poll() is not None:
        return
    try:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        # Never search for/kill a port owner or any process we did not start.
        raise SnapshotError('The owned headless server could not be stopped; inspect it locally.') from None


def update(project='themescope', *, root=ROOT, timeout=600):
    if not isinstance(project, str) or not publisher.PROJECT_NAME.fullmatch(project):
        raise SnapshotError('Use the exact existing Pages project name.')
    if not isinstance(timeout, (int, float)) or not 0 < timeout <= 600:
        raise SnapshotError('Refresh timeout must be greater than zero and at most 600 seconds.')
    root = Path(root)
    commit = publisher.clean_checkout(root)
    if any(not os.environ.get(name, '').strip() for name in ('APCA_API_KEY_ID', 'APCA_API_SECRET_KEY')):
        raise SnapshotError('Set APCA_API_KEY_ID and APCA_API_SECRET_KEY in this local shell first.')
    client = LoopbackClient()
    owned = None
    deadline = time.monotonic() + timeout
    try:
        try:
            initial = live_status(client.request('/api/status', timeout=remaining(deadline)))
        except ServerUnavailable:
            # The existing launcher uses this same runtime. Never bootstrap into
            # another interpreter or start fixture mode to make publication pass.
            python = root / '.venv-vnext' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
            if not python.is_file():
                raise SnapshotError('Run setup.cmd (or bootstrap_dev.py) before the daily update.') from None
            owned = subprocess.Popen([str(python), str(root / 'scripts/run_vnext.py'), '--no-browser'],
                                     cwd=root, env=os.environ.copy(), stdin=subprocess.DEVNULL,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            startup = min(deadline, time.monotonic() + 30)
            while True:
                if owned.poll() is not None:
                    raise SnapshotError('Headless ThemeScope could not start; inspect ThemeScope.cmd locally.')
                try:
                    initial = live_status(client.request('/api/status', timeout=remaining(startup)))
                    break
                except ServerUnavailable:
                    time.sleep(min(.25, remaining(startup)))
        if initial['state'] == 'running':
            raise SnapshotError('Another refresh is active; wait for it before the daily update.')
        requested = datetime.now(timezone.utc)
        reply = client.request('/api/refresh', post=True, timeout=remaining(deadline))
        if not isinstance(reply, dict) or reply.get('state') != 'running':
            raise SnapshotError('ThemeScope did not accept the refresh request.')
        while True:
            state = live_status(client.request('/api/refresh/status', timeout=remaining(deadline)))
            if state['state'] == 'success':
                break
            if state['state'] != 'running':
                raise SnapshotError('Refresh did not succeed; the prior publication is preserved.')
            time.sleep(min(1, remaining(deadline)))
        target = state.get('target_session')  # Only the service selects a session.
        if not iso_session(target) or state.get('last_successful_session') != target:
            raise SnapshotError('Refresh target and successful session do not match.')
        if not isinstance(state.get('completeness'), dict) or state['completeness'].get('complete') is not True:
            raise SnapshotError('Refresh completeness is not confirmed.')
        snapshot = client.request('/api/dashboard-data', timeout=remaining(deadline))
        project_snapshot(snapshot, target)  # Existing strict public contract, no recalculation.
        published = stamp(snapshot.get('refreshed_at'))
        if (published < requested or published > datetime.now(timezone.utc) or
                snapshot.get('refreshed_at') != state.get('last_successful_refresh')):
            raise SnapshotError('Snapshot is stale or does not belong to this successful refresh.')
        previous = initial.get('last_successful_refresh')
        if previous is not None and published <= stamp(previous):
            raise SnapshotError('The refresh did not publish a new snapshot.')
        if publisher.clean_checkout(root) != commit:
            raise SnapshotError('Repository changed during refresh; no publication will start.')
        publisher.publish(target, project, root)
        print('Refresh: ' + target + ' PASS')
        print('Completeness: PASS')
        print('Public deployment: CONFIRMED')
        return target
    finally:
        stop_owned(owned)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', default='themescope')
    parser.add_argument('--timeout', type=float, default=600, help='Refresh deadline in seconds (maximum 600).')
    args = parser.parse_args(argv)
    try:
        update(args.project, timeout=args.timeout)
    except SnapshotError as error:
        print('Daily update stopped: ' + str(error), file=sys.stderr)
        return 1
    except Exception:
        print('Daily update stopped by a local error. No deployment success is confirmed.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
