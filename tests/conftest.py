"""
lottery_engine/tests/conftest.py
Shared pytest fixtures.
"""
import os
import pytest
import sqlite3
from pathlib import Path
from datetime import date

# Point all DB operations at an in-memory database during tests
os.environ["LOTTERY_DB_PATH"] = ":memory:"

from db.connection import initialize_db, get_connection
from registry.seed import seed_state


@pytest.fixture(scope="function")
def db_conn():
    """
    Fresh in-memory SQLite connection per test.
    Schema initialized, Georgia seeded.
    """
    import sqlite3 as _sqlite3
    conn = _sqlite3.connect(":memory:")
    conn.row_factory = _sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")

    base = Path(__file__).parent.parent / "db"
    conn.executescript((base / "schema.sql").read_text())
    conn.executescript((base / "views.sql").read_text())
    conn.commit()
    yield conn
    conn.close()


@pytest.fixture(scope="function")
def seeded_db(db_conn):
    """DB with Georgia job definitions and source mappings seeded."""
    from registry.definitions import ALL_JOB_DEFINITIONS, ALL_SOURCE_MAPPINGS
    from registry.seed import seed_job_definitions, seed_source_mappings
    job_id_map = seed_job_definitions(db_conn, ALL_JOB_DEFINITIONS)
    seed_source_mappings(db_conn, ALL_SOURCE_MAPPINGS, job_id_map)
    db_conn.commit()
    return db_conn


@pytest.fixture
def sample_draws(seeded_db):
    """
    Insert a small set of known canonical draws for query testing.
    Returns the connection with draws populated.
    """
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()

    draws = [
        ("GA|pick3|2024-03-15|midday",  "GA","pick3","2024-03-15","midday",  "123",3,"123","lottery.net",1,1,0,now),
        ("GA|pick3|2024-03-15|evening", "GA","pick3","2024-03-15","evening", "456",3,"456","lottery.net",1,1,0,now),
        ("GA|pick3|2024-03-16|midday",  "GA","pick3","2024-03-16","midday",  "789",3,"789","lottery.net",1,0,0,now),
        ("GA|pick3|2024-03-16|evening", "GA","pick3","2024-03-16","evening", "012",3,"012","lottery.net",1,0,0,now),
        ("GA|pick3|2024-03-17|midday",  "GA","pick3","2024-03-17","midday",  "234",3,"234","lotterycorner.com",2,0,0,now),
        ("GA|pick3|2024-03-17|evening", "GA","pick3","2024-03-17","evening", "567",3,"567","lottery.net",1,1,0,now),
        ("GA|pick3|2024-03-20|night",   "GA","pick3","2024-03-20","night",   "890",3,"089","lottery.net",1,0,0,now),
        # Pick 4
        ("GA|pick4|2024-03-15|midday",  "GA","pick4","2024-03-15","midday",  "1234",4,"1234","lottery.net",1,1,0,now),
        ("GA|pick4|2024-03-15|evening", "GA","pick4","2024-03-15","evening", "5678",4,"5678","lottery.net",1,0,0,now),
        # Leading-zero number
        ("GA|pick3|2024-03-18|midday",  "GA","pick3","2024-03-18","midday",  "034",3,"034","lottery.net",1,1,0,now),
        ("GA|pick3|2024-03-18|evening", "GA","pick3","2024-03-18","evening", "007",3,"007","lottery.net",1,1,0,now),
    ]

    seeded_db.executemany(
        """
        INSERT OR IGNORE INTO draws (
            canonical_key, state, game_type, draw_date, draw_time,
            winning_number, digit_count, sorted_digits,
            accepted_from_source, accepted_source_priority,
            is_verified, has_conflict, accepted_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        draws,
    )
    seeded_db.commit()
    return seeded_db
