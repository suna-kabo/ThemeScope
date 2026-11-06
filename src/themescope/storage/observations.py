"""Schema 1 -> 2: immutable observations and cheap run references."""
from hashlib import sha256
import json


def migrate(db,canonical):
    # Store owns the transaction, including schema creation and the version check.
    if not db.in_transaction:
        raise ValueError('Schema migration requires the initialization transaction')
    db.execute('ALTER TABLE daily_bars RENAME TO daily_bars_v1')
    db.execute('CREATE TABLE observations(id TEXT PRIMARY KEY, identity TEXT NOT NULL,ticker TEXT NOT NULL,session TEXT NOT NULL,payload TEXT NOT NULL, observed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)')
    db.execute('CREATE INDEX observation_lookup ON observations(identity,ticker,session)')
    db.execute('CREATE TABLE bar_cache(identity TEXT,ticker TEXT,session TEXT,observation_id TEXT NOT NULL REFERENCES observations(id),PRIMARY KEY(identity,ticker,session))')
    db.execute('CREATE TABLE daily_bars(run_id INTEGER REFERENCES refresh_run(id),ticker TEXT,session TEXT,observation_id TEXT NOT NULL REFERENCES observations(id),PRIMARY KEY(run_id,ticker,session))')
    for row in db.execute('SELECT * FROM daily_bars_v1 ORDER BY run_id'):
        oid=put(db,'legacy-vnext-schema1:unknown-source',row['ticker'],row['session'],row['payload'])
        db.execute('INSERT INTO daily_bars VALUES(?,?,?,?)',(row['run_id'],row['ticker'],row['session'],oid))
    db.execute('DROP TABLE daily_bars_v1')
    db.execute('INSERT INTO schema_version VALUES(2)')
    db.execute('PRAGMA user_version=2')


def put(db,identity,ticker,session,payload):
    oid=sha256((identity+'\n'+ticker+'\n'+session+'\n'+payload).encode()).hexdigest()
    db.execute('INSERT OR IGNORE INTO observations(id,identity,ticker,session,payload) VALUES(?,?,?,?,?)',(oid,identity,ticker,session,payload))
    db.execute('INSERT INTO bar_cache VALUES(?,?,?,?) ON CONFLICT(identity,ticker,session) DO UPDATE SET observation_id=excluded.observation_id',(identity,ticker,session,oid))
    return oid
