"""File provenance and a versioned completed-session clock for local startup."""
from hashlib import sha256
from threading import Lock
import json
import time

from ..providers.base import Schedule

CALENDAR = 'calendars/xnys_2020_2035_v1.json'
INPUTS = ('themes.csv', 'memberships.csv', 'review_universe.json', 'methodology.json',
          'evidence_gate.json', 'membership_review_provenance.json', 'membership_master_review.json',
          'industry_rule_registry.json', 'primary_source_attachments.json',
          'primary_source_attachment_tasks.json', 'launch_approval.json', 'evidence_review_queue.csv',
          'corporate_actions.json', 'research_v2_membership_review.json', 'research_v2.json',
          'research_context.json')


class Freshness:
    def __init__(self, root):
        self.config = root / 'config'
        self.files = (CALENDAR, 'market_universes/rosters.json', 'tradingview_symbols.json',
                      *(f'vnext/{name}' for name in INPUTS))
        self.lock = Lock()
        self.checked = float('-inf')
        self.signature = None
        self.digest = None
        self.schedule = None

    def check(self, *, force=False):
        with self.lock:
            now = time.monotonic()
            if force or now - self.checked >= 5:
                self._scan(force)
                self.checked = now
            return self.digest, self.schedule

    def _scan(self, force):
        def stamp(name):
            try:
                info = (self.config / name).stat()
                return info.st_size, info.st_mtime_ns, info.st_ctime_ns
            except FileNotFoundError:
                return None

        signature = tuple(map(stamp, self.files))
        if force or signature != self.signature:
            digest = sha256()
            calendar = None
            for name, metadata in zip(self.files, signature):
                data = (self.config / name).read_bytes() if metadata else b''
                digest.update(name.encode() + b'\0' + (sha256(data).digest() if metadata else b''))
                if name == CALENDAR:
                    calendar = Schedule(json.loads(data)['sessions'])
            self.signature, self.digest, self.schedule = signature, digest.hexdigest(), calendar
