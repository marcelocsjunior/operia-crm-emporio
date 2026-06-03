import sqlite3
from contextlib import contextmanager
from operia_crm.config.settings import settings

SCHEMA = '''
CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    company TEXT,
    phone TEXT,
    whatsapp TEXT,
    email TEXT,
    city TEXT,
    segment TEXT,
    origin TEXT NOT NULL,
    status TEXT NOT NULL,
    score INTEGER NOT NULL DEFAULT 0,
    next_followup TEXT,
    notes TEXT,
    is_client INTEGER NOT NULL DEFAULT 0,
    opportunity_type TEXT,
    event_or_delivery_date TEXT,
    estimated_value REAL,
    people_count INTEGER,
    source_channel TEXT,
    emporio_status TEXT,
    next_action TEXT,
    operational_notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER NOT NULL,
    kind TEXT NOT NULL,
    summary TEXT NOT NULL,
    channel TEXT,
    pending INTEGER NOT NULL DEFAULT 0,
    followup_date TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(lead_id) REFERENCES leads(id)
);
CREATE TABLE IF NOT EXISTS proposals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER NOT NULL,
    number TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL,
    total_value REAL NOT NULL,
    validity_date TEXT,
    content TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(lead_id) REFERENCES leads(id)
);
CREATE TABLE IF NOT EXISTS attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER NOT NULL,
    original_name TEXT NOT NULL,
    saved_name TEXT NOT NULL,
    extension TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    note TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(lead_id) REFERENCES leads(id)
);
CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT,
    details TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
'''

EMPORIO_LEAD_COLUMNS = {
    "opportunity_type": "TEXT",
    "event_or_delivery_date": "TEXT",
    "estimated_value": "REAL",
    "people_count": "INTEGER",
    "source_channel": "TEXT",
    "emporio_status": "TEXT",
    "next_action": "TEXT",
    "operational_notes": "TEXT",
}


def ensure_emporio_schema(conn) -> None:
    existing = {row[1] for row in conn.execute("PRAGMA table_info(leads)").fetchall()}
    for column, column_type in EMPORIO_LEAD_COLUMNS.items():
        if column not in existing:
            conn.execute(f"ALTER TABLE leads ADD COLUMN {column} {column_type}")

def init_db() -> None:
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(settings.db_path) as conn:
        conn.executescript(SCHEMA)
        ensure_emporio_schema(conn)

@contextmanager
def get_conn():
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
