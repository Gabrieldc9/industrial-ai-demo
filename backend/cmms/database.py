"""
Base de datos SQLite para el CMMS.
Tablas: work_orders, alerts, maintenance_log, equipment_snapshot.
"""
import sys
import sqlite3

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
import os
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "cmms.db")


def get_db_path():
    return os.path.abspath(DB_PATH)


@contextmanager
def get_conn():
    conn = sqlite3.connect(get_db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS work_orders (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            wo_number   TEXT UNIQUE NOT NULL,
            equipment_id TEXT NOT NULL,
            equipment_name TEXT NOT NULL,
            title       TEXT NOT NULL,
            description TEXT,
            priority    TEXT NOT NULL DEFAULT 'medium',   -- low | medium | high | critical
            type        TEXT NOT NULL DEFAULT 'corrective', -- corrective | preventive | predictive
            status      TEXT NOT NULL DEFAULT 'open',    -- open | in_progress | completed | cancelled
            created_at  REAL NOT NULL,
            updated_at  REAL NOT NULL,
            completed_at REAL,
            fault_mode  TEXT,
            sensor_readings TEXT,   -- JSON snapshot
            ai_diagnosis TEXT,      -- Texto del agente Claude
            ai_recommendation TEXT
        );

        CREATE TABLE IF NOT EXISTS alerts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            equipment_id TEXT NOT NULL,
            equipment_name TEXT NOT NULL,
            sensor      TEXT NOT NULL,
            value       REAL NOT NULL,
            threshold   REAL NOT NULL,
            severity    TEXT NOT NULL,  -- warning | critical
            message     TEXT,
            created_at  REAL NOT NULL,
            acknowledged INTEGER DEFAULT 0,
            wo_id       INTEGER REFERENCES work_orders(id)
        );

        CREATE TABLE IF NOT EXISTS maintenance_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            equipment_id TEXT NOT NULL,
            wo_id       INTEGER REFERENCES work_orders(id),
            action      TEXT NOT NULL,
            health_before REAL,
            health_after  REAL,
            performed_at  REAL NOT NULL,
            notes       TEXT
        );

        CREATE TABLE IF NOT EXISTS agent_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   REAL NOT NULL,
            equipment_id TEXT,
            action_type TEXT NOT NULL,  -- alert_detected | wo_created | diagnosis | maintenance_triggered | rule_fired
            summary     TEXT NOT NULL,
            detail      TEXT,
            wo_id       INTEGER
        );
        """)
