import sqlite3
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime, timezone

SERVICES = ('demo-api', 'demo-worker')
ACTIVE = ('starting', 'running', 'stopping', 'cleanup_failed')


def now():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds')


@contextmanager
def connect(path):
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    try:
        yield db
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()


def initialize(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as db:
        db.execute('PRAGMA journal_mode=WAL')
        db.executescript('''
        CREATE TABLE IF NOT EXISTS environment (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, status TEXT NOT NULL,
            isolation_verified INTEGER NOT NULL CHECK(isolation_verified IN (0,1)), checked_at TEXT
        );
        CREATE TABLE IF NOT EXISTS service (
            id TEXT PRIMARY KEY, environment_id TEXT NOT NULL REFERENCES environment(id),
            name TEXT NOT NULL, internal_address TEXT NOT NULL, status TEXT NOT NULL, checked_at TEXT
        );
        CREATE TABLE IF NOT EXISTS experiment (
            id TEXT PRIMARY KEY, service_id TEXT NOT NULL REFERENCES service(id),
            fault_type TEXT NOT NULL CHECK(fault_type IN ('http_500','latency','overload','unavailability')),
            intensity INTEGER NOT NULL CHECK(typeof(intensity)='integer'),
            duration_seconds INTEGER NOT NULL CHECK(typeof(duration_seconds)='integer' AND duration_seconds BETWEEN 1 AND 300),
            status TEXT NOT NULL CHECK(status IN ('draft','starting','running','stopping','completed','stopped','failed','cleanup_failed')),
            created_at TEXT NOT NULL, started_at TEXT, deadline_at TEXT, ended_at TEXT, error_message TEXT,
            CHECK((fault_type='http_500' AND intensity BETWEEN 1 AND 100)
               OR (fault_type='latency' AND intensity BETWEEN 1 AND 5000)
               OR (fault_type='overload' AND intensity BETWEEN 1 AND 50)
               OR (fault_type='unavailability' AND intensity=100))
        );
        CREATE UNIQUE INDEX IF NOT EXISTS one_active_experiment ON experiment((1))
          WHERE status IN ('starting','running','stopping','cleanup_failed');
        CREATE TABLE IF NOT EXISTS measurement (
            id INTEGER PRIMARY KEY AUTOINCREMENT, experiment_id TEXT NOT NULL REFERENCES experiment(id),
            window_start TEXT NOT NULL, window_end TEXT NOT NULL,
            request_count INTEGER NOT NULL CHECK(request_count>=0),
            response_count INTEGER NOT NULL CHECK(response_count>=0),
            http_5xx_count INTEGER NOT NULL CHECK(http_5xx_count>=0),
            timeout_count INTEGER NOT NULL CHECK(timeout_count>=0),
            connection_error_count INTEGER NOT NULL CHECK(connection_error_count>=0),
            successful_count INTEGER NOT NULL CHECK(successful_count>=0),
            avg_response_ms REAL CHECK(avg_response_ms IS NULL OR avg_response_ms>=0),
            UNIQUE(experiment_id,window_start),
            CHECK(request_count=response_count+timeout_count+connection_error_count),
            CHECK(successful_count+http_5xx_count<=response_count)
        );
        ''')
        db.execute("INSERT OR IGNORE INTO environment VALUES ('local','Lokalne laboratorium','unknown',0,NULL)")
        for name in SERVICES:
            db.execute('INSERT OR IGNORE INTO service VALUES (?,?,?,?,?,?)',
                       (name, 'local', name, 'loopback:/' + name, 'unknown', None))


def aggregate(samples):
    responses = [s for s in samples if s['status'] is not None]
    return {
        'request_count': len(samples), 'response_count': len(responses),
        'http_5xx_count': sum(500 <= s['status'] < 600 for s in responses),
        'timeout_count': sum(s['error'] == 'timeout' for s in samples),
        'connection_error_count': sum(s['error'] == 'connection' for s in samples),
        'successful_count': sum(200 <= s['status'] < 400 for s in responses),
        'avg_response_ms': round(sum(s['elapsed_ms'] for s in responses) / len(responses), 2) if responses else None,
    }
