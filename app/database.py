import sqlite3
import json
from contextlib import contextmanager

_db_path = None


def init_db(db_path):
    global _db_path
    _db_path = db_path
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS parts (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                part_number TEXT UNIQUE NOT NULL,
                description TEXT NOT NULL,
                unit        TEXT,
                location    TEXT,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS checkouts (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                checkout_date DATE NOT NULL,
                employee_name TEXT NOT NULL,
                department    TEXT NOT NULL,
                part_id       INTEGER REFERENCES parts(id),
                part_number   TEXT NOT NULL,
                description   TEXT NOT NULL,
                quantity      REAL NOT NULL,
                notes         TEXT,
                source_file   TEXT,
                confirmed_by  TEXT,
                created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS upload_log (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                filename     TEXT NOT NULL,
                file_type    TEXT NOT NULL,
                status       TEXT NOT NULL,
                row_count    INTEGER,
                error_msg    TEXT,
                uploaded_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS checkout_pending (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                upload_id   INTEGER REFERENCES upload_log(id),
                row_data    TEXT NOT NULL,
                needs_review INTEGER DEFAULT 0
            );
        """)


@contextmanager
def get_db():
    conn = sqlite3.connect(_db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def upsert_parts(parts_list):
    with get_db() as conn:
        conn.executemany(
            """INSERT INTO parts (part_number, description, unit, location, updated_at)
               VALUES (:part_number, :description, :unit, :location, CURRENT_TIMESTAMP)
               ON CONFLICT(part_number) DO UPDATE SET
                   description = excluded.description,
                   unit        = excluded.unit,
                   location    = excluded.location,
                   updated_at  = CURRENT_TIMESTAMP""",
            parts_list,
        )
    return len(parts_list)


def get_all_parts():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, part_number, description, unit, location FROM parts ORDER BY part_number"
        ).fetchall()
    return [dict(r) for r in rows]


def insert_checkout(data):
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO checkouts
               (checkout_date, employee_name, department, part_id, part_number,
                description, quantity, notes, source_file, confirmed_by)
               VALUES (:checkout_date, :employee_name, :department, :part_id,
                       :part_number, :description, :quantity, :notes,
                       :source_file, :confirmed_by)""",
            data,
        )
    return cur.lastrowid


def insert_checkouts_bulk(rows):
    with get_db() as conn:
        conn.executemany(
            """INSERT INTO checkouts
               (checkout_date, employee_name, department, part_id, part_number,
                description, quantity, notes, source_file, confirmed_by)
               VALUES (:checkout_date, :employee_name, :department, :part_id,
                       :part_number, :description, :quantity, :notes,
                       :source_file, :confirmed_by)""",
            rows,
        )


def get_checkouts(filters=None):
    filters = filters or {}
    clauses = []
    params = []

    if filters.get('date_from'):
        clauses.append("checkout_date >= ?")
        params.append(filters['date_from'])
    if filters.get('date_to'):
        clauses.append("checkout_date <= ?")
        params.append(filters['date_to'])
    if filters.get('employee'):
        clauses.append("LOWER(employee_name) LIKE ?")
        params.append(f"%{filters['employee'].lower()}%")
    if filters.get('department'):
        clauses.append("department = ?")
        params.append(filters['department'])
    if filters.get('part_number'):
        clauses.append("LOWER(part_number) LIKE ?")
        params.append(f"%{filters['part_number'].lower()}%")

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = f"SELECT * FROM checkouts {where} ORDER BY checkout_date DESC, id DESC"

    with get_db() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def log_upload(filename, file_type):
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO upload_log (filename, file_type, status) VALUES (?, ?, 'processing')",
            (filename, file_type),
        )
    return cur.lastrowid


def update_upload_log(upload_id, status, row_count=None, error_msg=None):
    with get_db() as conn:
        conn.execute(
            "UPDATE upload_log SET status=?, row_count=?, error_msg=? WHERE id=?",
            (status, row_count, error_msg, upload_id),
        )


def save_pending_rows(upload_id, rows):
    records = [
        (upload_id, json.dumps(r), 1 if r.get('needs_review') else 0)
        for r in rows
    ]
    with get_db() as conn:
        conn.executemany(
            "INSERT INTO checkout_pending (upload_id, row_data, needs_review) VALUES (?, ?, ?)",
            records,
        )


def get_pending_rows(upload_id):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, row_data, needs_review FROM checkout_pending WHERE upload_id=? ORDER BY id",
            (upload_id,),
        ).fetchall()
    return [
        {'pending_id': r['id'], **json.loads(r['row_data']), 'needs_review': bool(r['needs_review'])}
        for r in rows
    ]


def delete_pending_rows(upload_id):
    with get_db() as conn:
        conn.execute("DELETE FROM checkout_pending WHERE upload_id=?", (upload_id,))


def get_upload_log_entry(upload_id):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM upload_log WHERE id=?", (upload_id,)).fetchone()
    return dict(row) if row else None
