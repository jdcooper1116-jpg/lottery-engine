import io
import json
import os
import sqlite3
import sys
import dataclasses
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ.setdefault("LOTTERY_DB_PATH", ":memory:")

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _fresh_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    base = Path(__file__).parent.parent / "db"
    conn.executescript((base / "schema.sql").read_text())
    conn.executescript((base / "views.sql").read_text())
    conn.commit()
    return conn

def _seed(conn, rows):
    conn.executemany(
        """INSERT OR IGNORE INTO draws (
        canonical_key,state,game_type,draw_date,draw_time,
        winning_number,digit_count,sorted_digits,
        accepted_from_source,accepted_source_priority,
        is_verified,has_conflict,accepted_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        rows,
    )
    conn.commit()

def _make_row(state, game, d, t, num, src="lottery.net", prio=1, verified=1):
    ckey = f"{state}|{game}|{d}|{t}"
    dc = len(num)
    sd = "".join(sorted(num))
    return (ckey, state, game, d, t, num, dc, sd, src, prio, verified, 0, _now())

_DRAWS = [
    _make_row("GA","pick3","2024-01-25","midday", "297", "lottery.net", 1, 1),
    _make_row("GA","pick3","2024-01-26","evening", "716", "lottery.net", 1, 1),
    _make_row("GA","pick3","2024-01-27","midday", "999", "lotterycorner.com",2,0),
    _make_row("GA","pick3","2024-01-28","night", "034", "lottery.net", 1, 1),
    _make_row("GA","pick3","2024-01-29","midday", "297", "lotteryusa.com", 3, 0),
    _make_row("GA","pick3","2024-01-31","midday", "123", "lottery.net", 1, 1),
    _make_row("GA","pick4","2024-01-25","midday", "2970","lottery.net", 1, 1),
    _make_row("GA","pick4","2024-01-26","evening", "7161","lottery.net", 1, 0),
]

@pytest.fixture
def conn_with_draws():
    conn = _fresh_conn()
    _seed(conn, _DRAWS)
    return conn

class TestMatchHitSourceName:
    def test_source_name_is_a_field(self):
        from query.models import MatchHit
        field_names = [f.name for f in dataclasses.fields(MatchHit)]
        assert "source_name" in field_names

class TestBacktestServiceProvenance:
    def _run(self, conn, candidates, anchor="2024-01-25", lookahead=7, mode="exact", game="pick3"):
        import importlib
        import query.service as svc
        importlib.reload(svc)
        from query.models import DreamBacktestRequest, QueryFilters
        req = DreamBacktestRequest(
            state="GA", game_type=game,
            anchor_date=date.fromisoformat(anchor),
            lookahead_days=lookahead,
            candidates=candidates,
            filters=QueryFilters(match_mode=mode),
        )
        with patch("query.service.get_connection") as mock_ctx:
            mock_ctx.return_value.__enter__ = lambda s: conn
            mock_ctx.return_value.__exit__ = lambda s, *a: False
            return svc.backtest_numbers(req)

    def test_hits_carry_source_name(self, conn_with_draws):
        resp = self._run(conn_with_draws, ["297", "716"])
        assert resp.hit_count >= 2
        for h in resp.hits:
            assert h.source_name

class TestDrawRecordSourceOnAllPaths:
    def _fetch(self, conn, start, end):
        from query.service import _fetch_draws
        from query.models import QueryFilters
        return _fetch_draws(conn, "GA", "pick3", start, end, QueryFilters())

    def test_date_range_draws_have_source_name(self, conn_with_draws):
        draws = self._fetch(conn_with_draws, "2024-01-25", "2024-01-31")
        assert draws
        for d in draws:
            assert d.source_name
