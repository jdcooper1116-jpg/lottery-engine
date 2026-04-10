"""
lottery_engine/tests/test_query_service.py

Tests for query/service.py.
Uses the sample_draws fixture (seeded in-memory DB).

Because service.py opens its own connection via get_connection(),
we patch LOTTERY_DB_PATH to ":memory:" in conftest.py, but the
fixture's seeded data won't be visible to a second connection to ":memory:".

Strategy: call the low-level _fetch_draws() directly with the fixture
connection for unit tests, and use a file-based temp DB for integration
tests that go through the full service API.
"""
import os
import pytest
from datetime import date
from pathlib import Path


# ---------------------------------------------------------------
# Helpers that bypass service.py's connection management
# and operate on the fixture connection directly
# ---------------------------------------------------------------

def _direct_fetch(conn, state, game_type, start, end, filters=None):
    from query.service import _fetch_draws
    from query.models import QueryFilters
    return _fetch_draws(
        conn,
        state=state,
        game_type=game_type,
        start_date=start,
        end_date=end,
        filters=filters or QueryFilters(),
    )


def _direct_gaps(conn, state, game_type, start, end):
    from query.coverage_checker import get_coverage_gaps
    return get_coverage_gaps(conn, state, game_type, start, end)


# ---------------------------------------------------------------
# DrawRecord shape
# ---------------------------------------------------------------

class TestDrawRecordShape:
    def test_all_fields_present(self, sample_draws):
        from query.models import DrawRecord
        rows = sample_draws.execute(
            "SELECT * FROM draws WHERE state='GA' AND game_type='pick3' LIMIT 1"
        ).fetchall()
        assert rows
        record = DrawRecord.from_row(rows[0])
        assert record.state == "GA"
        assert record.game_type == "pick3"
        assert isinstance(record.draw_date, str)
        assert isinstance(record.winning_number, str)
        assert isinstance(record.is_verified, bool)
        assert isinstance(record.has_conflict, bool)
        assert record.digit_count == len(record.winning_number)
        assert record.sorted_digits == "".join(sorted(record.winning_number))

    def test_leading_zeros_preserved_in_record(self, sample_draws):
        from query.models import DrawRecord
        row = sample_draws.execute(
            "SELECT * FROM draws WHERE winning_number='034'"
        ).fetchone()
        assert row is not None
        record = DrawRecord.from_row(row)
        assert record.winning_number == "034"
        assert not record.winning_number.startswith("34")

    def test_sorted_digits_for_leading_zero(self, sample_draws):
        from query.models import DrawRecord
        row = sample_draws.execute(
            "SELECT * FROM draws WHERE winning_number='034'"
        ).fetchone()
        record = DrawRecord.from_row(row)
        assert record.sorted_digits == "034"   # sorted: 0, 3, 4


# ---------------------------------------------------------------
# _fetch_draws filter surface
# ---------------------------------------------------------------

class TestFetchDrawsFilters:
    def test_returns_correct_state(self, sample_draws):
        results = _direct_fetch(
            sample_draws, "GA", "pick3", "2024-03-15", "2024-03-20"
        )
        assert all(r.state == "GA" for r in results)

    def test_returns_correct_game_type(self, sample_draws):
        results = _direct_fetch(
            sample_draws, "GA", "pick3", "2024-03-15", "2024-03-20"
        )
        assert all(r.game_type == "pick3" for r in results)

    def test_date_range_inclusive(self, sample_draws):
        results = _direct_fetch(
            sample_draws, "GA", "pick3", "2024-03-15", "2024-03-15"
        )
        assert all(r.draw_date == "2024-03-15" for r in results)

    def test_date_range_excludes_outside(self, sample_draws):
        results = _direct_fetch(
            sample_draws, "GA", "pick3", "2024-03-15", "2024-03-15"
        )
        assert not any(r.draw_date == "2024-03-16" for r in results)

    def test_draw_time_filter(self, sample_draws):
        from query.models import QueryFilters
        filters = QueryFilters(draw_times=["midday"])
        results = _direct_fetch(
            sample_draws, "GA", "pick3",
            "2024-03-15", "2024-03-20",
            filters=filters,
        )
        assert all(r.draw_time == "midday" for r in results)
        assert len(results) > 0

    def test_multiple_draw_times_filter(self, sample_draws):
        from query.models import QueryFilters
        filters = QueryFilters(draw_times=["midday", "evening"])
        results = _direct_fetch(
            sample_draws, "GA", "pick3",
            "2024-03-15", "2024-03-20",
            filters=filters,
        )
        assert all(r.draw_time in ("midday", "evening") for r in results)

    def test_verified_only_filter(self, sample_draws):
        from query.models import QueryFilters
        filters = QueryFilters(include_verified_only=True)
        results = _direct_fetch(
            sample_draws, "GA", "pick3",
            "2024-03-15", "2024-03-20",
            filters=filters,
        )
        assert all(r.is_verified for r in results)

    def test_exclude_conflicts_filter(self, sample_draws):
        from query.models import QueryFilters
        filters = QueryFilters(exclude_conflicts=True)
        results = _direct_fetch(
            sample_draws, "GA", "pick3",
            "2024-03-15", "2024-03-20",
            filters=filters,
        )
        assert all(not r.has_conflict for r in results)

    def test_source_name_filter(self, sample_draws):
        from query.models import QueryFilters
        filters = QueryFilters(source_name="lotterycorner.com")
        results = _direct_fetch(
            sample_draws, "GA", "pick3",
            "2024-03-15", "2024-03-20",
            filters=filters,
        )
        assert all(r.accepted_from_source == "lotterycorner.com" for r in results)

    def test_results_ordered_by_date_then_time(self, sample_draws):
        results = _direct_fetch(
            sample_draws, "GA", "pick3", "2024-03-15", "2024-03-20"
        )
        dates = [(r.draw_date, r.draw_time) for r in results]
        assert dates == sorted(dates)

    def test_pick4_separate_from_pick3(self, sample_draws):
        pick3 = _direct_fetch(sample_draws, "GA", "pick3", "2024-03-15", "2024-03-15")
        pick4 = _direct_fetch(sample_draws, "GA", "pick4", "2024-03-15", "2024-03-15")
        pick3_keys = {r.canonical_key for r in pick3}
        pick4_keys = {r.canonical_key for r in pick4}
        assert pick3_keys.isdisjoint(pick4_keys)

    def test_empty_range_returns_empty(self, sample_draws):
        results = _direct_fetch(
            sample_draws, "GA", "pick3", "2020-01-01", "2020-01-31"
        )
        assert results == []


# ---------------------------------------------------------------
# Window search via _fetch_draws
# ---------------------------------------------------------------

class TestWindowSearch:
    def test_window_contains_anchor_date(self, sample_draws):
        anchor = "2024-03-15"
        # 7-day window starting on anchor
        results = _direct_fetch(
            sample_draws, "GA", "pick3", "2024-03-15", "2024-03-22"
        )
        dates = {r.draw_date for r in results}
        assert "2024-03-15" in dates

    def test_window_10_days(self, sample_draws):
        results = _direct_fetch(
            sample_draws, "GA", "pick3", "2024-03-15", "2024-03-25"
        )
        # All draws returned should be within window
        assert all("2024-03-15" <= r.draw_date <= "2024-03-25" for r in results)


# ---------------------------------------------------------------
# Candidate matching via filter_draws_by_candidates
# ---------------------------------------------------------------

class TestCandidateMatching:
    def test_exact_match_found(self, sample_draws):
        from query.match_engine import filter_draws_by_candidates
        from query.models import DrawRecord
        rows = sample_draws.execute(
            "SELECT * FROM draws WHERE state='GA' AND game_type='pick3'"
        ).fetchall()
        draws = [DrawRecord.from_row(r) for r in rows]
        hits = filter_draws_by_candidates(draws, ["123"], "exact")
        assert any(d.winning_number == "123" for _, d in hits)

    def test_box_match_found(self, sample_draws):
        from query.match_engine import filter_draws_by_candidates
        from query.models import DrawRecord
        rows = sample_draws.execute(
            "SELECT * FROM draws WHERE state='GA' AND game_type='pick3'"
        ).fetchall()
        draws = [DrawRecord.from_row(r) for r in rows]
        # "321" should box-match "123" in sample data
        hits = filter_draws_by_candidates(draws, ["321"], "box")
        assert any(d.winning_number == "123" for _, d in hits)

    def test_leading_zero_exact_match(self, sample_draws):
        from query.match_engine import filter_draws_by_candidates
        from query.models import DrawRecord
        rows = sample_draws.execute(
            "SELECT * FROM draws WHERE state='GA' AND game_type='pick3'"
        ).fetchall()
        draws = [DrawRecord.from_row(r) for r in rows]
        hits = filter_draws_by_candidates(draws, ["034"], "exact")
        assert len(hits) == 1
        assert hits[0][1].winning_number == "034"

    def test_no_false_positive_leading_zeros(self, sample_draws):
        from query.match_engine import filter_draws_by_candidates
        from query.models import DrawRecord
        rows = sample_draws.execute(
            "SELECT * FROM draws WHERE state='GA' AND game_type='pick3'"
        ).fetchall()
        draws = [DrawRecord.from_row(r) for r in rows]
        # "34" should NOT match "034" (different lengths)
        hits = filter_draws_by_candidates(draws, ["34"], "exact")
        assert not any(d.winning_number == "034" for _, d in hits)


# ---------------------------------------------------------------
# DreamBacktestResponse shape and summary
# ---------------------------------------------------------------

class TestBacktestSummary:
    def test_summary_no_hits(self):
        from query.service import _build_summary
        from query.models import DreamBacktestRequest, QueryFilters
        req = DreamBacktestRequest(
            state="GA", game_type="pick3",
            anchor_date=date(2024, 3, 15),
            lookahead_days=7,
            candidates=["999"],
        )
        summary = _build_summary(req, [], date(2024, 3, 15), date(2024, 3, 22))
        assert "0 hit" in summary
        assert "999" in summary

    def test_summary_with_hits(self):
        from query.service import _build_summary
        from query.models import DreamBacktestRequest, MatchHit
        req = DreamBacktestRequest(
            state="GA", game_type="pick3",
            anchor_date=date(2024, 3, 15),
            lookahead_days=7,
            candidates=["123"],
        )
        hits = [
            MatchHit(
                candidate="123",
                draw_date="2024-03-15",
                draw_time="midday",
                winning_number="123",
                match_type="exact",
                is_verified=True,
                canonical_key="GA|pick3|2024-03-15|midday",
            )
        ]
        summary = _build_summary(req, hits, date(2024, 3, 15), date(2024, 3, 22))
        assert "1 hit" in summary
        assert "2024-03-15" in summary
        assert "midday" in summary

    def test_summary_with_label(self):
        from query.service import _build_summary
        from query.models import DreamBacktestRequest
        req = DreamBacktestRequest(
            state="GA", game_type="pick3",
            anchor_date=date(2024, 3, 15),
            lookahead_days=7,
            candidates=["123"],
            label="dream-001",
        )
        summary = _build_summary(req, [], date(2024, 3, 15), date(2024, 3, 22))
        assert "dream-001" in summary


# ---------------------------------------------------------------
# BatchBacktestResponse aggregation
# ---------------------------------------------------------------

class TestBatchBacktestAggregation:
    def test_aggregate_counts_all_jobs(self):
        from query.models import BatchBacktestResponse, DreamBacktestResponse, DreamBacktestRequest
        req = DreamBacktestRequest(
            state="GA", game_type="pick3",
            anchor_date=date(2024, 3, 15),
            lookahead_days=7,
            candidates=["123"],
        )
        resp1 = DreamBacktestResponse(
            request=req,
            window_start=date(2024, 3, 15), window_end=date(2024, 3, 22),
            all_draws=[], hits=[], hit_count=0,
            hit_dates=[], hit_draw_times=[], coverage_gaps=[],
            summary="no hits",
        )
        resp2 = DreamBacktestResponse(
            request=req,
            window_start=date(2024, 3, 15), window_end=date(2024, 3, 22),
            all_draws=[], hits=[
                __import__("query.models", fromlist=["MatchHit"]).MatchHit(
                    candidate="123", draw_date="2024-03-15", draw_time="midday",
                    winning_number="123", match_type="exact", is_verified=True,
                    canonical_key="GA|pick3|2024-03-15|midday",
                )
            ], hit_count=1,
            hit_dates=["2024-03-15"], hit_draw_times=["midday"], coverage_gaps=[],
            summary="1 hit",
        )
        batch = BatchBacktestResponse(
            results=[resp1, resp2],
            total_hits=1,
            total_draws_searched=0,
            jobs_with_hits=1,
            aggregate_summary="1 total hits across 2 jobs",
        )
        assert batch.total_hits == 1
        assert batch.jobs_with_hits == 1
        assert len(batch.results) == 2


# ---------------------------------------------------------------
# Coverage gap shape
# ---------------------------------------------------------------

class TestCoverageGap:
    def test_gap_fields(self):
        from query.models import CoverageGap
        gap = CoverageGap(
            draw_date="2024-03-15",
            draw_time="midday",
            coverage_status="not_scraped",
            last_attempted_at=None,
        )
        assert gap.draw_date == "2024-03-15"
        assert gap.coverage_status == "not_scraped"
        assert gap.last_attempted_at is None


# ---------------------------------------------------------------
# Integration: file-based DB + full service call
# ---------------------------------------------------------------

class TestServiceIntegration:
    """
    Full end-to-end through service.py using a temp file DB.
    These tests seed data, call the real service function, and
    verify the response shape.
    """

    @pytest.fixture
    def file_db(self, tmp_path, monkeypatch):
        db_file = str(tmp_path / "test.db")
        monkeypatch.setenv("LOTTERY_DB_PATH", db_file)
        from db.connection import initialize_db
        initialize_db(db_file)
        # Re-import connection to pick up patched env var
        import importlib
        import db.connection as dbc
        importlib.reload(dbc)
        yield db_file
        monkeypatch.delenv("LOTTERY_DB_PATH", raising=False)

    def _seed_draws(self, db_file):
        import sqlite3
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row
        rows = [
            ("GA|pick3|2024-06-01|midday",  "GA","pick3","2024-06-01","midday",  "111",3,"111","lottery.net",1,1,0,now),
            ("GA|pick3|2024-06-01|evening", "GA","pick3","2024-06-01","evening", "222",3,"222","lottery.net",1,1,0,now),
            ("GA|pick3|2024-06-02|midday",  "GA","pick3","2024-06-02","midday",  "333",3,"333","lottery.net",1,0,0,now),
            ("GA|pick3|2024-06-03|midday",  "GA","pick3","2024-06-03","midday",  "111",3,"111","lottery.net",1,1,0,now),
            ("GA|pick3|2024-06-07|evening", "GA","pick3","2024-06-07","evening", "444",3,"444","lottery.net",1,0,0,now),
        ]
        conn.executemany(
            """INSERT OR IGNORE INTO draws (
                canonical_key, state, game_type, draw_date, draw_time,
                winning_number, digit_count, sorted_digits,
                accepted_from_source, accepted_source_priority,
                is_verified, has_conflict, accepted_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            rows,
        )
        conn.commit()
        conn.close()

    def test_get_draws_for_date_range(self, file_db, monkeypatch):
        import importlib, db.connection as dbc
        monkeypatch.setenv("LOTTERY_DB_PATH", file_db)
        importlib.reload(dbc)
        self._seed_draws(file_db)

        from query.models import DateRangeRequest, QueryFilters
        import query.service as svc
        importlib.reload(svc)

        req = DateRangeRequest(
            state="GA", game_type="pick3",
            start_date=date(2024, 6, 1), end_date=date(2024, 6, 7),
        )
        resp = svc.get_draws_for_date_range(req)
        assert resp.total_count == 5
        assert all(r.state == "GA" for r in resp.draws)
        assert all("2024-06-0" in r.draw_date for r in resp.draws)

    def test_backtest_numbers(self, file_db, monkeypatch):
        import importlib, db.connection as dbc
        monkeypatch.setenv("LOTTERY_DB_PATH", file_db)
        importlib.reload(dbc)
        self._seed_draws(file_db)

        import query.service as svc
        importlib.reload(svc)
        from query.models import DreamBacktestRequest

        req = DreamBacktestRequest(
            state="GA", game_type="pick3",
            anchor_date=date(2024, 6, 1),
            lookahead_days=7,
            candidates=["111", "999"],
        )
        resp = svc.backtest_numbers(req)

        assert resp.hit_count == 2           # "111" appears on 6-01 midday + 6-03 midday
        assert "111" in [h.candidate for h in resp.hits]
        assert "999" not in [h.candidate for h in resp.hits]
        assert resp.window_start == date(2024, 6, 1)
        assert resp.window_end   == date(2024, 6, 8)

    def test_get_latest_results(self, file_db, monkeypatch):
        import importlib, db.connection as dbc
        monkeypatch.setenv("LOTTERY_DB_PATH", file_db)
        importlib.reload(dbc)
        self._seed_draws(file_db)

        import query.service as svc
        importlib.reload(svc)
        results = svc.get_latest_results("GA", "pick3", n=3)
        assert len(results) == 3
        # Results should be in reverse date order
        dates = [r.draw_date for r in results]
        assert dates == sorted(dates, reverse=True)

    def test_batch_backtest(self, file_db, monkeypatch):
        import importlib, db.connection as dbc
        monkeypatch.setenv("LOTTERY_DB_PATH", file_db)
        importlib.reload(dbc)
        self._seed_draws(file_db)

        import query.service as svc
        importlib.reload(svc)
        from query.models import DreamBacktestRequest, BatchBacktestRequest

        jobs = [
            DreamBacktestRequest(
                state="GA", game_type="pick3",
                anchor_date=date(2024, 6, 1),
                lookahead_days=7, candidates=["111"], label="dream-A",
            ),
            DreamBacktestRequest(
                state="GA", game_type="pick3",
                anchor_date=date(2024, 6, 1),
                lookahead_days=7, candidates=["999"], label="dream-B",
            ),
        ]
        batch_resp = svc.batch_backtest(BatchBacktestRequest(jobs=jobs))
        assert batch_resp.jobs_with_hits == 1
        assert batch_resp.total_hits >= 1
        labels = [r.request.label for r in batch_resp.results]
        assert "dream-A" in labels
        assert "dream-B" in labels

# ---------------------------------------------------------------
# Source provenance on DrawRecord
# ---------------------------------------------------------------

class TestDrawRecordSourceProvenance:
    """
    source_name is a @property alias for accepted_from_source.
    Both must be present and identical on every DrawRecord.
    """

    def test_source_name_attribute_exists(self, sample_draws):
        from query.models import DrawRecord
        row = sample_draws.execute("SELECT * FROM draws LIMIT 1").fetchone()
        record = DrawRecord.from_row(row)
        assert hasattr(record, "source_name"), "DrawRecord missing source_name"

    def test_source_name_equals_accepted_from_source(self, sample_draws):
        from query.models import DrawRecord
        rows = sample_draws.execute("SELECT * FROM draws").fetchall()
        for row in rows:
            record = DrawRecord.from_row(row)
            assert record.source_name == record.accepted_from_source, (
                f"Mismatch on {record.canonical_key}: "
                f"source_name={record.source_name!r} "
                f"accepted_from_source={record.accepted_from_source!r}"
            )

    def test_source_name_is_property_not_field(self):
        import dataclasses
        from query.models import DrawRecord
        field_names = [f.name for f in dataclasses.fields(DrawRecord)]
        assert "source_name" not in field_names, (
            "source_name should be a @property, not a dataclass field"
        )
        assert "accepted_from_source" in field_names, (
            "accepted_from_source must remain as the backing dataclass field"
        )
        assert hasattr(DrawRecord, "source_name"), (
            "DrawRecord must expose source_name as a property"
        )

    def test_source_name_non_empty(self, sample_draws):
        from query.models import DrawRecord
        rows = sample_draws.execute("SELECT * FROM draws").fetchall()
        for row in rows:
            record = DrawRecord.from_row(row)
            assert record.source_name, (
                f"source_name is empty/None on {record.canonical_key}"
            )

    def test_source_name_reflects_correct_source(self, sample_draws):
        from query.models import DrawRecord
        # sample_draws has rows from lottery.net and lotterycorner.com
        rows = sample_draws.execute(
            "SELECT * FROM draws WHERE accepted_from_source='lotterycorner.com' LIMIT 1"
        ).fetchone()
        if rows:
            record = DrawRecord.from_row(rows)
            assert record.source_name == "lotterycorner.com"

    def test_user_print_loop_runs(self, sample_draws):
        """Exact snippet from the feature request must execute without AttributeError."""
        from query.models import DrawRecord
        rows = sample_draws.execute(
            "SELECT * FROM draws ORDER BY draw_date, draw_time LIMIT 15"
        ).fetchall()
        draws = [DrawRecord.from_row(r) for r in rows]

        # This is the exact code the user reported wanting to use:
        output = []
        for draw in draws[:15]:
            output.append(
                (draw.draw_date, draw.draw_time, draw.winning_number, draw.source_name)
            )
        assert len(output) > 0
        for row in output:
            assert row[3], f"source_name blank for {row}"

    def test_source_name_in_api_serializer(self):
        """_draw_to_dict must include source_name in its output dict."""
        from api.routes import _draw_to_dict
        from query.models import DrawRecord
        from datetime import datetime, timezone
        import sqlite3, pathlib
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        base = pathlib.Path("db")
        conn.executescript((base / "schema.sql").read_text())
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """INSERT INTO draws (
                canonical_key,state,game_type,draw_date,draw_time,
                winning_number,digit_count,sorted_digits,
                accepted_from_source,accepted_source_priority,
                is_verified,has_conflict,accepted_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            ("GA|pick3|2024-01-01|midday","GA","pick3","2024-01-01","midday",
             "123",3,"123","lottery.net",1,1,0,now),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM draws LIMIT 1").fetchone()
        record = DrawRecord.from_row(row)
        d = _draw_to_dict(record)
        assert "source_name" in d, f"source_name missing from _draw_to_dict output: {list(d)}"
        assert d["source_name"] == "lottery.net"
        assert "accepted_from_source" in d, "accepted_from_source must also remain in output"
        conn.close()

