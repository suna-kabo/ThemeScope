"""Personal research bookmarks, independent of the research database and port."""
import json
import re
from threading import Lock

from ..local_refresh_lock import RefreshLock
from .credentials import atomic_write

TICKER = re.compile(r'[A-Z][A-Z0-9.\-]{0,15}')
THEME = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*')


class Saved:
    def __init__(self, path):
        self.path = path
        self.lock = Lock()

    def _read(self):
        try:
            saved = json.loads(self.path.read_text(encoding='utf-8'))
        except FileNotFoundError:
            return {}
        if not isinstance(saved, dict):
            raise OSError('Saved research file is invalid')
        return saved

    def read(self):
        with self.lock:
            return self._read()

    def update(self, entries, *, merge=False):
        with self.lock, RefreshLock(self.path.with_suffix('.lock')):
            saved = self._read()
            for ticker, theme in entries.items():
                if not TICKER.fullmatch(ticker) or (theme is not None and
                        (not isinstance(theme, str) or len(theme) > 100 or (theme and not THEME.fullmatch(theme)))):
                    raise ValueError('Invalid saved stock or theme')
                if theme is None:
                    saved.pop(ticker, None)
                elif merge:
                    saved.setdefault(ticker, theme)
                else:
                    saved[ticker] = theme
            atomic_write(self.path, json.dumps(saved).encode())
            return saved
