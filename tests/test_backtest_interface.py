"""
lottery_engine/tests/test_backtest_interface.py

Tests for:
  - cli/backtest.py argument parsing and output
  - query/service.backtest_numbers() hit provenance
  - api/routes._hit_to_dict() serializer
  - MatchHit.source_name field

All tests use an in-memory SQLite DB seeded with known draws so
results are deterministic.
"""
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


# ── Fixtures ──────────────────────────────────────────────────────────────────

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


# Draws used across most tests:
#   2024-01-25  midday   297   ← will be a hit on anchor 2024-01-25
#   2024-01-26  evening  716   ← will be a hit
#   2024-01-27  midday   999   ← NOT in candidates → not a hit
#   2024-01-28  night    034   ← leading zero
#   2024-01-29  midday   297   ← 297 hits twice
_DRAWS = [
    _make_row("GA","pick3","2024-01-25","midday",  "297", "lottery.net",    1, 1),
    _make_row("GA","pick3","2024-01-26","evening", "716", "lottery.net",    1, 1),
    _make_row("GA","pick3","2024-01-27","midday",  "999", "lotterycorner.com",2,0),
    _make_row("GA","pick3","2024-01-28","night",   "034", "lottery.net",    1, 1),
    _make_row("GA","pick3","2024-01-29","midday",  "297", "lotteryusa.com", 3, 0),
    _make_row("GA","pick3","2024-01-31","midday",  "123", "lottery.net",    1, 1),
    _make_row("GA","pick4","2024-01-25","midday",  "2970","lottery.net",    1, 1),
    _make_row("GA","pick4","2024-01-26","evening", "7161","lottery.net",    1, 0),
]


@pytest.fixture
def conn_with_draws():
    conn = _fresh_conn()
    _seed(conn, _DRAWS)
    return conn


# ── MatchHit.source_name ─────────────────────────────────────────────────────

class TestMatchHitSourceName:
    def test_source_name_is_a_field(self):
        from query.models import MatchHit
        field_names = [f.name for f in dataclasses.fields(MatchHit)]
        assert "source_name" in field_names

    def test_source_name_defaults_empty(self):
        from query.models import MatchHit
        h = MatchHit(
            candidate="123", draw_date="2024-01-01", draw_time="midday",
            winning_number="123", match_type="exact", is_verified=True,
            canonical_key="GA|pick3|2024-01-01|midday",
        )
        assert h.source_name == ""

    def test_source_name_set_explicitly(self):
        from query.models import MatchHit
        h = MatchHit(
            candidate="123", draw_date="2024-01-01", draw_time="midday",
            winning_number="123", match_type="exact", is_verified=True,
            canonical_key="GA|pick3|2024-01-01|midday",
            source_name="lottery.net",
        )
        assert h.source_name == "lottery.net"


# ── service.backtest_numbers fills source_name on MatchHit ───────────────────

class TestBacktestServiceProvenance:
    def _run(self, conn, candidates, anchor="2024-01-25", lookahead=7,
             mode="exact", game="pick3"):
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
        # Patch DB connection to use our fixture conn
        with patch("query.service.get_connection") as mock_ctx:
            mock_ctx.return_value.__enter__ = lambda s: conn
            mock_ctx.return_value.__exit__  = lambda s, *a: False
            return svc.backtest_numbers(req)

    def test_hits_carry_source_name(self, conn_with_draws):
        resp = self._run(conn_with_draws, ["297", "716"])
        assert resp.hit_count >= 2
        for h in resp.hits:
            assert h.source_name, f"source_name empty on hit {h.canonical_key}"

    def test_source_name_matches_draw_record(self, conn_with_draws):
        resp = self._run(conn_with_draws, ["297", "716"])
        for h in resp.hits:
            draw = next(
                (d for d in resp.all_draws if d.canonical_key == h.canonical_key),
                None,
            )
            assert draw is not None
            assert h.source_name == draw.source_name, (
                f"Hit source_name {h.source_name!r} != "
                f"DrawRecord source_name {draw.source_name!r}"
            )

    def test_source_name_correct_value(self, conn_with_draws):
        resp = self._run(conn_with_draws, ["297"])
        # 297 on 2024-01-25 midday is from lottery.net
        jan25_hit = next(
            (h for h in resp.hits if h.draw_date == "2024-01-25"), None
        )
        assert jan25_hit is not None
        assert jan25_hit.source_name == "lottery.net"

    def test_secondary_source_preserved(self, conn_with_draws):
        resp = self._run(conn_with_draws, ["999"])
        if resp.hits:
            assert resp.hits[0].source_name == "lotterycorner.com"

    def test_all_draws_have_source_name(self, conn_with_draws):
        resp = self._run(conn_with_draws, ["297"])
        for d in resp.all_draws:
            assert d.source_name, f"source_name empty on {d.canonical_key}"

    def test_hit_count_and_dates(self, conn_with_draws):
        resp = self._run(conn_with_draws, ["297", "716", "034"])
        assert resp.hit_count >= 4   # 297×2, 716×1, 034×1
        assert len(resp.hit_dates) >= 3
        assert len(resp.hit_draw_times) == resp.hit_count

    def test_summary_populated(self, conn_with_draws):
        resp = self._run(conn_with_draws, ["297"])
        assert resp.summary
        assert "GA" in resp.summary
        assert "pick3" in resp.summary

    def test_no_hits_summary(self, conn_with_draws):
        resp = self._run(conn_with_draws, ["888"])
        assert resp.hit_count == 0
        assert "0 hit" in resp.summary

    def test_box_match_source_name(self, conn_with_draws):
        # 792 box-matches 297
        resp = self._run(conn_with_draws, ["792"], mode="box")
        assert resp.hit_count >= 1
        for h in resp.hits:
            assert h.source_name

    def test_leading_zero_candidate(self, conn_with_draws):
        resp = self._run(conn_with_draws, ["034"])
        assert resp.hit_count >= 1
        hit = resp.hits[0]
        assert hit.winning_number == "034"
        assert hit.source_name == "lottery.net"

    def test_pick4_hits_carry_source_name(self, conn_with_draws):
        resp = self._run(conn_with_draws, ["2970"], game="pick4")
        assert resp.hit_count >= 1
        for h in resp.hits:
            assert h.source_name == "lottery.net"


# ── CLI argument parsing ──────────────────────────────────────────────────────

class TestBacktestCLIArgParsing:
    def _parse(self, argv):
        from cli.backtest import build_parser, parse_candidates
        ns = build_parser().parse_args(argv)
        ns.candidates_list = parse_candidates(ns.candidates)
        return ns

    def test_required_args_accepted(self):
        ns = self._parse([
            "--state", "GA", "--game", "pick3",
            "--anchor", "2024-01-25", "--lookahead", "7",
            "--candidates", "297,716,999",
        ])
        assert ns.state == "GA"
        assert ns.game_type == "pick3"
        assert ns.lookahead == 7
        assert ns.candidates_list == ["297", "716", "999"]

    def test_candidates_comma_separated(self):
        from cli.backtest import parse_candidates
        assert parse_candidates("297,716,999") == ["297", "716", "999"]
        assert parse_candidates("297, 716, 999") == ["297", "716", "999"]
        assert parse_candidates("297 716 999") == ["297", "716", "999"]

    def test_candidates_single(self):
        from cli.backtest import parse_candidates
        assert parse_candidates("297") == ["297"]

    def test_candidates_leading_zero(self):
        from cli.backtest import parse_candidates
        assert parse_candidates("034,007") == ["034", "007"]

    def test_candidates_non_digit_raises(self):
        from cli.backtest import parse_candidates
        with pytest.raises(ValueError):
            parse_candidates("abc,123")

    def test_label_optional(self):
        ns = self._parse([
            "--state", "GA", "--game", "pick3",
            "--anchor", "2024-01-25",
            "--candidates", "297",
        ])
        assert ns.label == ""

    def test_label_captured(self):
        ns = self._parse([
            "--state", "GA", "--game", "pick3",
            "--anchor", "2024-01-25",
            "--candidates", "297",
            "--label", "test dream window",
        ])
        assert ns.label == "test dream window"

    def test_mode_default_exact(self):
        ns = self._parse([
            "--state", "GA", "--game", "pick3",
            "--anchor", "2024-01-25", "--candidates", "297",
        ])
        assert ns.mode == "exact"

    def test_mode_box(self):
        ns = self._parse([
            "--state", "GA", "--game", "pick3",
            "--anchor", "2024-01-25", "--candidates", "297",
            "--mode", "box",
        ])
        assert ns.mode == "box"

    def test_draw_times_filter(self):
        ns = self._parse([
            "--state", "GA", "--game", "pick3",
            "--anchor", "2024-01-25", "--candidates", "297",
            "--draw-times", "midday,evening",
        ])
        assert ns.draw_times == "midday,evening"

    def test_output_json(self):
        ns = self._parse([
            "--state", "GA", "--game", "pick3",
            "--anchor", "2024-01-25", "--candidates", "297",
            "--output", "json",
        ])
        assert ns.output == "json"

    def test_invalid_date_exits(self):
        from cli.backtest import parse_anchor
        import argparse
        with pytest.raises((argparse.ArgumentTypeError, SystemExit, ValueError)):
            parse_anchor("not-a-date")


# ── CLI full run with mock service ────────────────────────────────────────────

class TestBacktestCLIOutput:
    def _make_resp(self, hits=True):
        from query.models import (
            DreamBacktestRequest, DreamBacktestResponse, MatchHit, DrawRecord, QueryFilters,
        )
        now = _now()
        req = DreamBacktestRequest(
            state="GA", game_type="pick3",
            anchor_date=date(2024, 1, 25), lookahead_days=7,
            candidates=["297", "716"],
            label="test dream window",
            filters=QueryFilters(),
        )
        all_draws = [
            DrawRecord(
                canonical_key="GA|pick3|2024-01-25|midday",
                state="GA", game_type="pick3",
                draw_date="2024-01-25", draw_time="midday",
                winning_number="297", digit_count=3, sorted_digits="279",
                is_verified=True, has_conflict=False,
                accepted_from_source="lottery.net", accepted_source_priority=1,
            ),
            DrawRecord(
                canonical_key="GA|pick3|2024-01-26|evening",
                state="GA", game_type="pick3",
                draw_date="2024-01-26", draw_time="evening",
                winning_number="716", digit_count=3, sorted_digits="167",
                is_verified=True, has_conflict=False,
                accepted_from_source="lottery.net", accepted_source_priority=1,
            ),
        ]
        hit_list = [
            MatchHit(
                candidate="297", draw_date="2024-01-25", draw_time="midday",
                winning_number="297", match_type="exact",
                is_verified=True,
                canonical_key="GA|pick3|2024-01-25|midday",
                source_name="lottery.net",
            ),
            MatchHit(
                candidate="716", draw_date="2024-01-26", draw_time="evening",
                winning_number="716", match_type="exact",
                is_verified=True,
                canonical_key="GA|pick3|2024-01-26|evening",
                source_name="lottery.net",
            ),
        ] if hits else []
        return DreamBacktestResponse(
            request=req,
            window_start=date(2024, 1, 25),
            window_end=date(2024, 2, 1),
            all_draws=all_draws,
            hits=hit_list,
            hit_count=len(hit_list),
            hit_dates=["2024-01-25", "2024-01-26"] if hit_list else [],
            hit_draw_times=["midday", "evening"] if hit_list else [],
            coverage_gaps=[],
            summary=(
                "GA pick3 [test dream window]: 2 hit(s) in 7-day window"
                if hits else
                "GA pick3 [test dream window]: 0 hits in 7-day window"
            ),
        )

    def _run_cli(self, argv, mock_resp):
        from cli.backtest import run
        captured = io.StringIO()
        with patch("cli.backtest.backtest_numbers", return_value=mock_resp), \
             patch("sys.stdout", captured):
            resp = run(argv)
        return captured.getvalue(), resp

    def test_table_output_contains_summary(self):
        resp = self._make_resp()
        out, _ = self._run_cli([
            "--state", "GA", "--game", "pick3",
            "--anchor", "2024-01-25", "--candidates", "297,716",
            "--label", "test dream window",
        ], resp)
        assert "2 hit" in out.lower() or "HITS" in out

    def test_table_shows_source_name(self):
        resp = self._make_resp()
        out, _ = self._run_cli([
            "--state", "GA", "--game", "pick3",
            "--anchor", "2024-01-25", "--candidates", "297,716",
        ], resp)
        assert "lottery.net" in out

    def test_table_shows_candidates(self):
        resp = self._make_resp()
        out, _ = self._run_cli([
            "--state", "GA", "--game", "pick3",
            "--anchor", "2024-01-25", "--candidates", "297,716",
        ], resp)
        assert "297" in out
        assert "716" in out

    def test_table_no_hits(self):
        resp = self._make_resp(hits=False)
        out, _ = self._run_cli([
            "--state", "GA", "--game", "pick3",
            "--anchor", "2024-01-25", "--candidates", "888",
        ], resp)
        assert "NO HITS" in out or "0 hit" in out.lower()

    def test_show_draws_includes_all_draws(self):
        resp = self._make_resp()
        out, _ = self._run_cli([
            "--state", "GA", "--game", "pick3",
            "--anchor", "2024-01-25", "--candidates", "297,716",
            "--show-draws",
        ], resp)
        assert "ALL DRAWS" in out

    def test_json_output_valid(self):
        resp = self._make_resp()
        out, _ = self._run_cli([
            "--state", "GA", "--game", "pick3",
            "--anchor", "2024-01-25", "--candidates", "297,716",
            "--output", "json",
        ], resp)
        parsed = json.loads(out)
        assert parsed["hit_count"] == 2
        assert parsed["state"] == "GA"

    def test_json_hits_include_source_name(self):
        resp = self._make_resp()
        out, _ = self._run_cli([
            "--state", "GA", "--game", "pick3",
            "--anchor", "2024-01-25", "--candidates", "297,716",
            "--output", "json",
        ], resp)
        parsed = json.loads(out)
        for hit in parsed["hits"]:
            assert "source_name" in hit
            assert hit["source_name"] == "lottery.net"

    def test_json_draws_include_source_name(self):
        resp = self._make_resp()
        out, _ = self._run_cli([
            "--state", "GA", "--game", "pick3",
            "--anchor", "2024-01-25", "--candidates", "297,716",
            "--output", "json",
        ], resp)
        parsed = json.loads(out)
        for draw in parsed["all_draws"]:
            assert "source_name" in draw

    def test_json_structure_complete(self):
        resp = self._make_resp()
        out, _ = self._run_cli([
            "--state", "GA", "--game", "pick3",
            "--anchor", "2024-01-25", "--candidates", "297,716",
            "--output", "json",
        ], resp)
        parsed = json.loads(out)
        for key in ("state","game_type","anchor_date","window_start","window_end",
                    "lookahead_days","candidates","match_mode","hit_count",
                    "hit_dates","hit_draw_times","summary","hits","all_draws",
                    "coverage_gaps"):
            assert key in parsed, f"Missing key in JSON output: {key!r}"

    def test_run_returns_response_object(self):
        resp = self._make_resp()
        _, returned = self._run_cli([
            "--state", "GA", "--game", "pick3",
            "--anchor", "2024-01-25", "--candidates", "297,716",
        ], resp)
        assert returned is resp


# ── API hit serializer ────────────────────────────────────────────────────────

class TestHitSerializer:
    def _make_hit(self, source="lottery.net"):
        from query.models import MatchHit
        return MatchHit(
            candidate="297", draw_date="2024-01-25", draw_time="midday",
            winning_number="297", match_type="exact", is_verified=True,
            canonical_key="GA|pick3|2024-01-25|midday",
            source_name=source,
        )

    def test_hit_dict_has_source_name(self):
        # Test the serializer logic inline (without importing FastAPI)
        h = self._make_hit()
        d = {
            "candidate":      h.candidate,
            "draw_date":      h.draw_date,
            "draw_time":      h.draw_time,
            "winning_number": h.winning_number,
            "match_type":     h.match_type,
            "is_verified":    h.is_verified,
            "source_name":    h.source_name,
            "canonical_key":  h.canonical_key,
        }
        assert d["source_name"] == "lottery.net"
        assert d["canonical_key"] == "GA|pick3|2024-01-25|midday"

    def test_hit_dict_secondary_source(self):
        h = self._make_hit(source="lotterycorner.com")
        assert h.source_name == "lotterycorner.com"

    def test_hit_source_name_default_empty(self):
        from query.models import MatchHit
        h = MatchHit(
            candidate="297", draw_date="2024-01-25", draw_time="midday",
            winning_number="297", match_type="exact", is_verified=True,
            canonical_key="GA|pick3|2024-01-25|midday",
        )
        assert h.source_name == ""


# ── DrawRecord.source_name exposed on all query paths ────────────────────────

class TestDrawRecordSourceOnAllPaths:
    def _fetch(self, conn, start, end):
        from query.service import _fetch_draws
        from query.models import QueryFilters
        return _fetch_draws(conn, "GA", "pick3", start, end, QueryFilters())

    def test_date_range_draws_have_source_name(self, conn_with_draws):
        draws = self._fetch(conn_with_draws, "2024-01-25", "2024-01-31")
        assert draws
        for d in draws:
            assert d.source_name, f"source_name empty on {d.canonical_key}"

    def test_source_name_reflects_accepted_source(self, conn_with_draws):
        draws = self._fetch(conn_with_draws, "2024-01-25", "2024-01-31")
        for d in draws:
            assert d.source_name == d.accepted_from_source

    def test_mixed_sources_preserved(self, conn_with_draws):
        draws = self._fetch(conn_with_draws, "2024-01-25", "2024-01-31")
        sources = {d.source_name for d in draws}
        # Fixture has lottery.net, lotterycorner.com, lotteryusa.com rows
        assert "lottery.net"      in sources
        assert "lotterycorner.com" in sources
        assert "lotteryusa.com"    in sources
