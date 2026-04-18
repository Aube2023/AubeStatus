"""Couche SQLite pour AubeStatus."""
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta

from config import DB_PATH, RETENTION_DAYS

_lock = threading.Lock()


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with _lock, get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_id TEXT NOT NULL,
                ts TEXT NOT NULL,
                status INTEGER NOT NULL,
                http_code INTEGER,
                response_ms INTEGER,
                error TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_checks_service_ts
                ON checks(service_id, ts DESC);

            CREATE TABLE IF NOT EXISTS incidents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_id TEXT NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                reason TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_incidents_service
                ON incidents(service_id, started_at DESC);

            CREATE TABLE IF NOT EXISTS daily_stats (
                service_id TEXT NOT NULL,
                day TEXT NOT NULL,
                total INTEGER NOT NULL DEFAULT 0,
                up INTEGER NOT NULL DEFAULT 0,
                avg_ms INTEGER,
                PRIMARY KEY (service_id, day)
            );

            CREATE TABLE IF NOT EXISTS restarts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_id TEXT NOT NULL,
                ts TEXT NOT NULL,
                success INTEGER NOT NULL,
                message TEXT,
                pid INTEGER
            );
            CREATE INDEX IF NOT EXISTS idx_restarts_service
                ON restarts(service_id, ts DESC);
            """
        )


def insert_check(service_id, status, http_code, response_ms, error=None):
    ts = datetime.utcnow().isoformat(timespec="seconds")
    day = ts[:10]
    with _lock, get_conn() as conn:
        conn.execute(
            "INSERT INTO checks(service_id, ts, status, http_code, response_ms, error) "
            "VALUES (?,?,?,?,?,?)",
            (service_id, ts, status, http_code, response_ms, error),
        )
        row = conn.execute(
            "SELECT total, up, avg_ms FROM daily_stats WHERE service_id=? AND day=?",
            (service_id, day),
        ).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO daily_stats(service_id, day, total, up, avg_ms) VALUES (?,?,?,?,?)",
                (service_id, day, 1, 1 if status == 1 else 0, response_ms or 0),
            )
        else:
            total = row["total"] + 1
            up = row["up"] + (1 if status == 1 else 0)
            prev_avg = row["avg_ms"] or 0
            new_avg = int(((prev_avg * row["total"]) + (response_ms or 0)) / total) if total else 0
            conn.execute(
                "UPDATE daily_stats SET total=?, up=?, avg_ms=? WHERE service_id=? AND day=?",
                (total, up, new_avg, service_id, day),
            )


def latest_status(service_id):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT ts, status, http_code, response_ms, error FROM checks "
            "WHERE service_id=? ORDER BY id DESC LIMIT 1",
            (service_id,),
        ).fetchone()
        return dict(row) if row else None


def history_days(service_id, days=90):
    start = (datetime.utcnow() - timedelta(days=days - 1)).date().isoformat()
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT day, total, up, avg_ms FROM daily_stats "
            "WHERE service_id=? AND day >= ? ORDER BY day ASC",
            (service_id, start),
        ).fetchall()
        return [dict(r) for r in rows]


def uptime_percent(service_id, days=90):
    days_rows = history_days(service_id, days)
    total = sum(r["total"] for r in days_rows)
    up = sum(r["up"] for r in days_rows)
    if total == 0:
        return None
    return round((up / total) * 100, 3)


def recent_checks(service_id, limit=60):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT ts, status, http_code, response_ms, error FROM checks "
            "WHERE service_id=? ORDER BY id DESC LIMIT ?",
            (service_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def open_incident(service_id, reason):
    ts = datetime.utcnow().isoformat(timespec="seconds")
    with _lock, get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM incidents WHERE service_id=? AND ended_at IS NULL",
            (service_id,),
        ).fetchone()
        if row:
            return row["id"]
        cur = conn.execute(
            "INSERT INTO incidents(service_id, started_at, reason) VALUES (?,?,?)",
            (service_id, ts, reason),
        )
        return cur.lastrowid


def close_open_incident(service_id):
    ts = datetime.utcnow().isoformat(timespec="seconds")
    with _lock, get_conn() as conn:
        conn.execute(
            "UPDATE incidents SET ended_at=? WHERE service_id=? AND ended_at IS NULL",
            (ts, service_id),
        )


def recent_incidents(limit=20):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, service_id, started_at, ended_at, reason "
            "FROM incidents ORDER BY started_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def purge_old():
    cutoff = (datetime.utcnow() - timedelta(days=RETENTION_DAYS)).isoformat()
    cutoff_day = cutoff[:10]
    with _lock, get_conn() as conn:
        conn.execute("DELETE FROM checks WHERE ts < ?", (cutoff,))
        conn.execute("DELETE FROM daily_stats WHERE day < ?", (cutoff_day,))
        conn.execute(
            "DELETE FROM incidents WHERE ended_at IS NOT NULL AND ended_at < ?",
            (cutoff,),
        )
        conn.execute("DELETE FROM restarts WHERE ts < ?", (cutoff,))


def log_restart(service_id, success, message, pid=None):
    ts = datetime.utcnow().isoformat(timespec="seconds")
    with _lock, get_conn() as conn:
        conn.execute(
            "INSERT INTO restarts(service_id, ts, success, message, pid) VALUES (?,?,?,?,?)",
            (service_id, ts, 1 if success else 0, message, pid),
        )


def restart_count_24h(service_id):
    cutoff = (datetime.utcnow() - timedelta(hours=24)).isoformat()
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM restarts WHERE service_id=? AND ts>=?",
            (service_id, cutoff),
        ).fetchone()
        return row["c"] if row else 0


def recent_restarts(service_id=None, limit=30):
    with get_conn() as conn:
        if service_id:
            rows = conn.execute(
                "SELECT ts, service_id, success, message, pid FROM restarts "
                "WHERE service_id=? ORDER BY id DESC LIMIT ?",
                (service_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT ts, service_id, success, message, pid FROM restarts "
                "ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]


def last_restart(service_id):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT ts, success, message, pid FROM restarts "
            "WHERE service_id=? ORDER BY id DESC LIMIT 1",
            (service_id,),
        ).fetchone()
        return dict(row) if row else None
