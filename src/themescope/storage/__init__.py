"""Versioned local SQLite storage. Configuration in Git remains authoritative."""
from contextlib import contextmanager
from dataclasses import asdict, is_dataclass
from decimal import Decimal
import json
import sqlite3
from pathlib import Path
from ..domain import iso_date
from ..themes.calculations import Bar, usable

SCHEMA_VERSION = 2
# Finite wait for short local writer/commit locks; no WAL/journal-mode change.
BUSY_TIMEOUT_SECONDS = 5.0


def is_busy(error):
    """Only SQLite BUSY/LOCKED (including extended codes), never other failures."""
    return (isinstance(error, sqlite3.OperationalError)
            and (getattr(error, 'sqlite_errorcode', 0) & 0xff)
            in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED))


def canonical(value):
    def convert(item):
        if isinstance(item, Decimal):
            if not item.is_finite():
                raise ValueError('Nonfinite persisted number')
            return str(item)
        if is_dataclass(item):
            result=asdict(item)
            if isinstance(item,Bar):
                for key in ('adjusted_high','adjusted_low'):
                    if result[key] is None:result.pop(key)
            return result
        raise TypeError(type(item).__name__)
    return json.dumps(value, default=convert, sort_keys=True, separators=(',', ':'), allow_nan=False)


class Store:
    def __init__(self, path, *, timeout=BUSY_TIMEOUT_SECONDS, read_only=False):
        # URI escaping also preserves Windows drive names, spaces, '#' and '?'.
        location=Path(path).resolve().as_uri()+'?mode=ro' if read_only else path
        self.connection = sqlite3.connect(location, timeout=timeout, isolation_level=None, uri=read_only)
        self.connection.row_factory = sqlite3.Row
        try:
            self.connection.execute('PRAGMA foreign_keys=ON')
            if not read_only:
                self._initialize()
        except BaseException:
            self.connection.close()
            raise

    def _initialize(self):
        db=self.connection
        version=db.execute('PRAGMA user_version').fetchone()[0]
        if version not in (0, 1, SCHEMA_VERSION):
            raise ValueError('Unsupported vNext SQLite schema')
        if version == SCHEMA_VERSION:
            return  # Ordinary ready-store opens never acquire a writer lock.
        db.execute('BEGIN IMMEDIATE')
        try:
            # Another process may have completed initialization while we waited.
            version=db.execute('PRAGMA user_version').fetchone()[0]
            if version not in (0, 1, SCHEMA_VERSION):
                raise ValueError('Unsupported vNext SQLite schema')
            if version == 0:
                _create_schema1(db)
            if version in (0, 1):
                from .observations import migrate
                migrate(db, canonical)
            db.commit()  # Fresh 0 -> 1 -> 2 is one atomic transaction.
        except BaseException:
            db.rollback()
            raise

    def close(self):
        self.connection.close()

    @contextmanager
    def refresh(self, session, methodology, config_hash):
        if not iso_date(session) or not methodology.startswith('themescope-vnext-') or not config_hash:
            raise ValueError('Explicit vNext session, methodology and config hash required')
        db = self.connection
        db.execute('BEGIN IMMEDIATE')  # One writer; contention waits only up to the connection timeout.
        try:
            run = db.execute('INSERT INTO refresh_run(session,methodology,config_hash,status) VALUES(?,?,?,?)',
                             (session, methodology, config_hash, 'running')).lastrowid
            writer = Refresh(db, run, session)
            yield writer
            if not writer.published:
                raise ValueError('Refresh is incomplete: no validated publication')
            db.execute("UPDATE refresh_run SET status='success' WHERE id=?", (run,))
            db.commit()
        except BaseException as error:
            db.rollback()
            # Keep failure diagnostics separate from the rolled-back data transaction.
            db.execute('INSERT INTO refresh_run(session,methodology,config_hash,status,error) VALUES(?,?,?,?,?)',
                       (session, methodology, config_hash, 'incomplete', type(error).__name__))
            raise

    def theme_at(self, theme_id, session, methodology):
        """Exact session only; no stale or legacy fallback for transition history."""
        row = self.connection.execute(
            "SELECT t.payload FROM theme_snapshot t JOIN refresh_run r ON r.id=t.run_id "
            "WHERE t.theme_id=? AND r.session=? AND r.methodology=? AND r.status='success' "
            "ORDER BY r.id DESC LIMIT 1", (theme_id, session, methodology)).fetchone()
        return json.loads(row[0]) if row else None

    def research_at(self, session, methodology):
        """One successful run's entire theme universe and market context, read only."""
        row=self.connection.execute(
            "SELECT r.id,m.payload FROM refresh_run r JOIN market_snapshot m ON m.run_id=r.id "
            "WHERE r.session=? AND r.methodology=? AND r.status='success' ORDER BY r.id DESC LIMIT 1",
            (session,methodology)).fetchone()
        if row is None:return None
        themes=[json.loads(t[0]) for t in self.connection.execute(
            'SELECT payload FROM theme_snapshot WHERE run_id=? ORDER BY theme_id',(row['id'],))]
        return {'session':session,'methodology':methodology,'market':json.loads(row['payload']),'themes':themes}

    def active_publication(self):
        """Version and payload from ONE committed publication-pointer read."""
        row = self.connection.execute('SELECT run_id,payload FROM publication WHERE id=1').fetchone()
        return (row['run_id'], json.loads(row['payload'])) if row else (0, None)

    def active(self):
        return self.active_publication()[1]


class Refresh:
    def __init__(self, db, run, session):
        self.db, self.run, self.session = db, run, session
        self.target_symbols = set()
        self.published = False
        self._bars = {}
        self._identities = set()

    def bars(self, bars, identity="synthetic:gate-b"):
        from .observations import put
        self._identities.add(identity)
        for bar in bars:
            self._bars[bar.ticker,bar.session]=bar
            oid=put(self.db,identity,bar.ticker,bar.session,canonical(bar))
            self.db.execute('INSERT INTO daily_bars VALUES(?,?,?,?)', (self.run, bar.ticker, bar.session, oid))
            if bar.session == self.session and usable(bar) and bar.volume>0:
                self.target_symbols.add(bar.ticker)

    def theme(self, theme_id, payload):
        self.db.execute('INSERT INTO theme_snapshot VALUES(?,?,?)', (self.run, theme_id, canonical(payload)))

    def stock(self, ticker, theme_id, payload):
        self.db.execute('INSERT INTO stock_theme_snapshot VALUES(?,?,?,?)', (self.run, ticker, theme_id, canonical(payload)))

    def index(self, theme_id, session, payload):
        if not iso_date(session) or session > self.session:
            raise ValueError('Invalid index session')
        self.db.execute('INSERT INTO theme_index VALUES(?,?,?,?)', (self.run, theme_id, session, canonical(payload)))

    def publish(self, payload, *, required_symbols, terminal_actions=()):
        from ..corporate_actions import resolve_values, action_audit
        values=resolve_values(terminal_actions,self._bars,self.session)
        terminal={v.ticker for v in values if v.valuation_session==self.session}
        if values:
            if len(self._identities)!=1:
                raise ValueError('Terminal accounting requires pinned provider identity')
            expected=action_audit(terminal_actions,values,next(iter(self._identities)))
            if canonical(payload.get('corporate_actions'))!=canonical(expected):
                raise ValueError('Terminal accounting audit differs from pinned observations')
        required = set(required_symbols)
        if not required or not required <= self.target_symbols|terminal:
            raise ValueError('Required target-session data missing')
        previous = self.db.execute('SELECT r.session FROM publication p JOIN refresh_run r ON r.id=p.run_id').fetchone()
        # Older replay is retained for inspection but cannot replace the active session.
        if previous is None or self.session >= previous[0]:
            self.db.execute('INSERT INTO publication VALUES(1,?,?) ON CONFLICT(id) DO UPDATE SET run_id=excluded.run_id,payload=excluded.payload',
                            (self.run, canonical(payload)))
        self.published = True


def _create_schema1(db):
    """Called only inside the initializer's serialized transaction."""
    statements = '''
            CREATE TABLE schema_version(version INTEGER PRIMARY KEY);
            INSERT INTO schema_version VALUES(1);
            CREATE TABLE refresh_run(id INTEGER PRIMARY KEY, session TEXT NOT NULL,
                methodology TEXT NOT NULL, config_hash TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('running','success','incomplete')),
                error TEXT);
            CREATE TABLE instruments(ticker TEXT PRIMARY KEY, metadata TEXT NOT NULL);
            CREATE TABLE daily_bars(run_id INTEGER REFERENCES refresh_run(id), ticker TEXT NOT NULL,
                session TEXT NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(run_id,ticker,session));
            CREATE TABLE membership_reviews(review_id TEXT PRIMARY KEY, payload TEXT NOT NULL);
            CREATE TABLE market_roster(benchmark TEXT NOT NULL CHECK(benchmark IN ('SPY','QQQ')),
                effective_from TEXT NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(benchmark,effective_from));
            CREATE TABLE theme_index(run_id INTEGER REFERENCES refresh_run(id), theme_id TEXT NOT NULL,
                session TEXT NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(run_id,theme_id,session));
            CREATE TABLE theme_snapshot(run_id INTEGER REFERENCES refresh_run(id), theme_id TEXT NOT NULL,
                payload TEXT NOT NULL, PRIMARY KEY(run_id,theme_id));
            CREATE TABLE stock_theme_snapshot(run_id INTEGER REFERENCES refresh_run(id), ticker TEXT NOT NULL,
                theme_id TEXT NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(run_id,ticker,theme_id));
            CREATE TABLE market_snapshot(run_id INTEGER PRIMARY KEY REFERENCES refresh_run(id), payload TEXT NOT NULL);
            CREATE TABLE earnings_event(ticker TEXT NOT NULL, event_date TEXT NOT NULL,
                payload TEXT NOT NULL, PRIMARY KEY(ticker,event_date));
            CREATE TABLE publication(id INTEGER PRIMARY KEY CHECK(id=1), run_id INTEGER NOT NULL REFERENCES refresh_run(id),
                payload TEXT NOT NULL);
            CREATE INDEX successful_session ON refresh_run(status,session);
            PRAGMA user_version=1;
    '''
    for statement in statements.split(';'):
        if statement.strip():
            db.execute(statement)
