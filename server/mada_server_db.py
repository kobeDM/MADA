#!/usr/bin/env python3

"""The server's own runtime state: operation history and notifications
(docs/specs/2026-11-12_3.md section 5). Login users are not here -- they
live in the server config file (see mada_server_config.py), modeled on
MPOD's config-based accounts. Everything in this module is the server's, not
the DAQ's: file/warning/log content stays on the client and is read through
mada_server_client.py instead. SQLite, one connection shared by the whole
process; callers serialize through _lock since sqlite3 connections aren't
safe for concurrent use from multiple threads/tasks."""

import sqlite3
import threading
import time

SCHEMA = """
CREATE TABLE IF NOT EXISTS operations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    time REAL NOT NULL,
    username TEXT NOT NULL,
    action TEXT NOT NULL CHECK(action IN ('start', 'stop')),
    params TEXT,
    status_code INTEGER,
    error_code TEXT,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    time REAL NOT NULL,
    kind TEXT NOT NULL,
    message TEXT NOT NULL,
    acknowledged INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS warnings_cursor (
    run TEXT NOT NULL,
    period INTEGER NOT NULL,
    last_t REAL NOT NULL,
    PRIMARY KEY (run, period)
);
"""

_lock = threading.Lock()
_conn = None


def init_db(path):
    global _conn
    _conn = sqlite3.connect(path, check_same_thread=False)
    _conn.row_factory = sqlite3.Row
    with _lock:
        _conn.executescript(SCHEMA)
        _conn.commit()
    return _conn


# -- operation history (append-only; spec 3.5) -----------------------------

def record_operation(username, action, params, status_code, error_code=None, error_message=None):
    with _lock:
        _conn.execute(
            'INSERT INTO operations (time, username, action, params, status_code, error_code, error_message) '
            'VALUES (?, ?, ?, ?, ?, ?, ?)',
            (time.time(), username, action, params, status_code, error_code, error_message))
        _conn.commit()


def list_operations(limit=200):
    with _lock:
        rows = _conn.execute('SELECT * FROM operations ORDER BY id DESC LIMIT ?', (limit,)).fetchall()
    return [dict(r) for r in rows]


# -- notifications (spec 3.4) ----------------------------------------------

def add_notification(kind, message):
    with _lock:
        cur = _conn.execute('INSERT INTO notifications (time, kind, message) VALUES (?, ?, ?)',
                             (time.time(), kind, message))
        _conn.commit()
        return cur.lastrowid


def list_notifications(include_acknowledged=False, limit=200):
    query = 'SELECT * FROM notifications'
    if not include_acknowledged:
        query += ' WHERE acknowledged = 0'
    query += ' ORDER BY id DESC LIMIT ?'
    with _lock:
        rows = _conn.execute(query, (limit,)).fetchall()
    return [dict(r) for r in rows]


def acknowledge_notification(notification_id):
    with _lock:
        _conn.execute('UPDATE notifications SET acknowledged = 1 WHERE id = ?', (notification_id,))
        _conn.commit()


# -- warnings cursor (spec section 5, "取りこぼし防止") ----------------------

def get_warnings_cursor(run, period):
    with _lock:
        row = _conn.execute('SELECT last_t FROM warnings_cursor WHERE run = ? AND period = ?',
                             (run, period)).fetchone()
    return row['last_t'] if row else None


def set_warnings_cursor(run, period, last_t):
    with _lock:
        _conn.execute(
            'INSERT INTO warnings_cursor (run, period, last_t) VALUES (?, ?, ?) '
            'ON CONFLICT(run, period) DO UPDATE SET last_t = excluded.last_t',
            (run, period, last_t))
        _conn.commit()
