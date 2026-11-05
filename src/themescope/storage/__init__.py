"""Versioned local SQLite storage. Configuration in Git remains authoritative."""
from contextlib import contextmanager
from dataclasses import asdict, is_dataclass
from decimal import Decimal
import json
import sqlite3
from ..domain import iso_date
from ..themes.calculations import usable

SCHEMA_VERSION = 1


def canonical(value):
    def convert(item):
        if isinstance(item, Decimal):
            if not item.is_finite():
                raise ValueError('Nonfinite persisted number')
            return str(item)
        if is_dataclass(item):
            return asdict(item)
        raise TypeError(type(item).__name__)
    return json.dumps(value, default=convert, sort_keys=True, separators=(',', ':'), allow_nan=False)


class Store:
    def __init__(self, path, *, timeout=0):
        self.connection = sqlite3.connect(path, timeout=timeout, isolation_level=None)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute('PRAGMA foreign_keys=ON')
        version = self.connection.execute('PRAGMA user_version').fetchone()[0]
        if version not in (0, SCHEMA_VERSION):
            self.connection.close()
            raise ValueError('Unsupported vNext SQLite schema')
        if version == 0:
            self.connection.executescript('''
            BEGIN IMMEDIATE;
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
            COMMIT;
            ''')

    def close(self):
        self.connection.close()

    @contextmanager
    def refresh(self, session, methodology, config_hash):
        if not iso_date(session) or not methodology.startswith('themescope-vnext-') or not config_hash:
            raise ValueError('Explicit vNext session, methodology and config hash required')
        db = self.connection
        db.execute('BEGIN IMMEDIATE')  # One writer; a competing writer fails without touching good state.
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

    def active(self):
        row = self.connection.execute('SELECT payload FROM publication WHERE id=1').fetchone()
        return json.loads(row[0]) if row else None


class Refresh:
    def __init__(self, db, run, session):
        self.db, self.run, self.session = db, run, session
        self.target_symbols = set()
        self.published = False

    def bars(self, bars):
        for bar in bars:
            self.db.execute('INSERT INTO daily_bars VALUES(?,?,?,?)', (self.run, bar.ticker, bar.session, canonical(bar)))
            if bar.session == self.session and usable(bar):
                self.target_symbols.add(bar.ticker)

    def theme(self, theme_id, payload):
        self.db.execute('INSERT INTO theme_snapshot VALUES(?,?,?)', (self.run, theme_id, canonical(payload)))

    def stock(self, ticker, theme_id, payload):
        self.db.execute('INSERT INTO stock_theme_snapshot VALUES(?,?,?,?)', (self.run, ticker, theme_id, canonical(payload)))

    def index(self, theme_id, session, payload):
        if not iso_date(session) or session > self.session:
            raise ValueError('Invalid index session')
        self.db.execute('INSERT INTO theme_index VALUES(?,?,?,?)', (self.run, theme_id, session, canonical(payload)))

    def publish(self, payload, *, required_symbols):
        required = set(required_symbols)
        if not required or not required <= self.target_symbols:
            raise ValueError('Required target-session data missing')
        previous = self.db.execute('SELECT r.session FROM publication p JOIN refresh_run r ON r.id=p.run_id').fetchone()
        # Older replay is retained for inspection but cannot replace the active session.
        if previous is None or self.session >= previous[0]:
            self.db.execute('INSERT INTO publication VALUES(1,?,?) ON CONFLICT(id) DO UPDATE SET run_id=excluded.run_id,payload=excluded.payload',
                            (self.run, canonical(payload)))
        self.published = True
