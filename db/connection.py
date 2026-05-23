"""
lottery_engine/db/connection.py
SQLite connection factory with WAL mode and row factory.
"""
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path


def get_db_path() -> str:
    """
    Resolve the SQLite database path.

    Priority:
    1. LOTTERY_DB_PATH env var
    2. Railway volume database at /data/history_all_states.db
    3. Local canonical database at data/history_all_states.db
    4. Legacy fallback lottery.db
    """
    env_path = os.environ.get("LOTTERY_DB_PATH")
    if env_path:
        return env_path

    railway_path = Path("/data/history_all_states.db")
    if railway_path.exists():
        return str(railway_path)

    local_canonical = Path(__file__).parent.parent / "data" / "history_all_states.db"
    if local_canonical.exists():
        return str(local_canonical)

    return str(Path(__file__).parent.parent / "lottery.db")

@contextmanager
def get_connection(db_path: str | None = None):
    """Yield a committed/rolled-back SQLite connection."""
    path = db_path or get_db_path()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous=NORMAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def initialize_db(db_path: str | None = None) -> None:
    """Create schema and views if they do not exist."""
    base = Path(__file__).parent
    schema_sql = (base / "schema.sql").read_text()
    views_sql = (base / "views.sql").read_text()
    path = db_path or get_db_path()
    with get_connection(path) as conn:
        conn.executescript(schema_sql)
        conn.executescript(views_sql)


def execute_batch(conn: sqlite3.Connection, sql: str, params_seq: list, batch_size: int = 2000) -> int:
    """Execute a parameterized INSERT in batches. Returns total rows inserted."""
    total = 0
    for i in range(0, len(params_seq), batch_size):
        batch = params_seq[i : i + batch_size]
        conn.executemany(sql, batch)
        total += len(batch)
    return total
