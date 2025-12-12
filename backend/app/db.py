import sqlite3
import os
from typing import Dict, Any
from datetime import datetime

DB_PATH = os.getenv("SQLITE_PATH", "/app/data/devices.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS telemetry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    q0 TEXT,
    q1 INTEGER,
    q2 TEXT,
    q3 TEXT,        -- imei
    q4 TEXT,        -- project
    q5 TEXT,        -- site
    q6 TEXT,        -- device
    q7 TEXT,
    q8 TEXT,
    q9 REAL,
    q10 REAL,
    q11 REAL,
    time TEXT,
    date TEXT,
    q14 INTEGER,
    q15 INTEGER,
    q16 INTEGER,
    battery INTEGER,
    q18 INTEGER,
    q19 INTEGER,
    q20 INTEGER,
    received_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_imei ON telemetry(q3);
CREATE INDEX IF NOT EXISTS idx_project ON telemetry(q4);
CREATE INDEX IF NOT EXISTS idx_site ON telemetry(q5);
CREATE INDEX IF NOT EXISTS idx_device ON telemetry(q6);
"""

_conn = None

def get_conn():
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _conn.execute("PRAGMA journal_mode=WAL;")
        _conn.executescript(CREATE_SQL)
        _conn.commit()
    return _conn

def insert_record(rec: Dict[str, Any]):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO telemetry(
            q0,q1,q2,q3,q4,q5,q6,q7,q8,q9,q10,q11,time,date,
            q14,q15,q16,battery,q18,q19,q20,received_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            rec.get("q0"),
            int(rec.get("q1") or 0),
            rec.get("q2"),
            rec.get("q3"),
            rec.get("q4"),
            rec.get("q5"),
            rec.get("q6"),
            rec.get("q7"),
            rec.get("q8"),
            float(rec.get("q9") or 0.0),
            float(rec.get("q10") or 0.0),
            float(rec.get("q11") or 0.0),
            rec.get("time"),
            rec.get("date"),
            int(rec.get("q14") or 0),
            int(rec.get("q15") or 0),
            int(rec.get("q16") or 0),
            int(rec.get("battery") or 0),
            int(rec.get("q18") or 0),
            int(rec.get("q19") or 0),
            int(rec.get("q20") or 0),
            datetime.utcnow().isoformat()
        )
    )
    conn.commit()

def fetch_latest_by_imei(imei: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM telemetry WHERE q3 = ? ORDER BY id DESC LIMIT 1", (imei,))
    cols = [c[0] for c in cur.description]
    row = cur.fetchone()
    return dict(zip(cols, row)) if row else None

def fetch_devices():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT q3 as imei, q4 as project, q5 as site, q6 as device FROM telemetry")
    rows = cur.fetchall()
    return [{"imei": r[0], "project": r[1], "site": r[2], "device": r[3]} for r in rows]

def query_history(imei=None, project=None, site=None, device=None, limit=100):
    conn = get_conn()
    cur = conn.cursor()
    q = "SELECT * FROM telemetry WHERE 1=1"
    params = []
    if imei:
        q += " AND q3 = ?"; params.append(imei)
    if project:
        q += " AND q4 = ?"; params.append(project)
    if site:
        q += " AND q5 = ?"; params.append(site)
    if device:
        q += " AND q6 = ?"; params.append(device)
    q += " ORDER BY id DESC LIMIT ?"; params.append(limit)
    cur.execute(q, params)
    cols = [c[0] for c in cur.description]
    rows = cur.fetchall()
    return [dict(zip(cols, r)) for r in rows]

