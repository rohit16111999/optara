"""Small persistent document store plus transactional spend reservations."""
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from .schemas import now


class Store:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript('''
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS documents (
                collection TEXT NOT NULL, id TEXT NOT NULL, body TEXT NOT NULL,
                updated TEXT NOT NULL, PRIMARY KEY(collection,id));
            CREATE TABLE IF NOT EXISTS spend (
                id TEXT PRIMARY KEY, scope TEXT NOT NULL, batch_id TEXT,
                run_id TEXT NOT NULL, reserved REAL NOT NULL, actual REAL,
                state TEXT NOT NULL, created TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS events (
                run_id TEXT NOT NULL, sequence INTEGER NOT NULL, body TEXT NOT NULL,
                PRIMARY KEY(run_id,sequence));
            ''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        try:
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def put(self, collection, key, value):
        body = value.model_dump(mode='json') if hasattr(value, 'model_dump') else value
        with self.connect() as db:
            db.execute('INSERT OR REPLACE INTO documents VALUES (?,?,?,?)', (collection, key, json.dumps(body, allow_nan=False), now()))

    def get(self, collection, key):
        with self.connect() as db:
            row = db.execute('SELECT body FROM documents WHERE collection=? AND id=?', (collection, key)).fetchone()
        return json.loads(row['body']) if row else None

    def list(self, collection, limit=1000):
        with self.connect() as db:
            rows = db.execute('SELECT body FROM documents WHERE collection=? ORDER BY updated DESC LIMIT ?', (collection, limit)).fetchall()
        return [json.loads(row['body']) for row in rows]

    def event(self, run_id, stage, status, message, **data):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            sequence = db.execute('SELECT COALESCE(MAX(sequence),0)+1 FROM events WHERE run_id=?', (run_id,)).fetchone()[0]
            event = dict(run_id=run_id, sequence=sequence, stage=stage, status=status, message=message, timestamp=now(), **data)
            db.execute('INSERT INTO events VALUES (?,?,?)', (run_id, sequence, json.dumps(event)))
        return event

    def events(self, run_id, after=0):
        with self.connect() as db:
            rows = db.execute('SELECT body FROM events WHERE run_id=? AND sequence>? ORDER BY sequence', (run_id, after)).fetchall()
        return [json.loads(row['body']) for row in rows]

    def spend_total(self, scope=None):
        with self.connect() as db:
            where, args = (' WHERE scope=?', (scope,)) if scope else ('', ())
            return db.execute('SELECT COALESCE(SUM(COALESCE(actual,reserved)),0) FROM spend'+where, args).fetchone()[0]
