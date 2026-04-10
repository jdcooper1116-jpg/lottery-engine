"""
lottery_engine/tests/test_reconciler.py

Tests for all four reconciliation rules.
"""
import pytest
from datetime import datetime, timezone
from orchestrator.reconciler import reconcile_pending


def _insert_obs(conn, canonical_key, state, game_type, draw_date, draw_time,
                winning_number, source_name, source_priority, status="pending"):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    digit_count = len(winning_number)
    sorted_digits = "".join(sorted(winning_number))
    conn.execute(
        """
        INSERT INTO draw_observations (
            canonical_key, state, game_type, draw_date, draw_time,
            winning_number, digit_count, sorted_digits,
            source_name, source_priority, scraped_at,
            reconciliation_status
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (canonical_key, state, game_type, draw_date, draw_time,
         winning_number, digit_count, sorted_digits,
         source_name, source_priority, now, status),
    )
    conn.commit()


def _get_draw(conn, canonical_key):
    return conn.execute(
        "SELECT * FROM draws WHERE canonical_key=?", (canonical_key,)
    ).fetchone()


def _get_obs_statuses(conn, canonical_key):
    rows = conn.execute(
        "SELECT reconciliation_status FROM draw_observations WHERE canonical_key=?",
        (canonical_key,)
    ).fetchall()
    return [r["reconciliation_status"] for r in rows]


class TestRule1NewDraw:
    """New canonical_key, no existing draw → insert and accept."""

    def test_creates_canonical_draw(self, seeded_db):
        _insert_obs(seeded_db, "GA|pick3|2024-01-01|midday",
                    "GA","pick3","2024-01-01","midday","123","lottery.net",1)
        stats = reconcile_pending(seeded_db)
        assert stats["accepted"] == 1
        draw = _get_draw(seeded_db, "GA|pick3|2024-01-01|midday")
        assert draw is not None
        assert draw["winning_number"] == "123"

    def test_observation_marked_accepted(self, seeded_db):
        _insert_obs(seeded_db, "GA|pick3|2024-01-02|midday",
                    "GA","pick3","2024-01-02","midday","456","lottery.net",1)
        reconcile_pending(seeded_db)
        statuses = _get_obs_statuses(seeded_db, "GA|pick3|2024-01-02|midday")
        assert statuses == ["accepted"]

    def test_leading_zeros_preserved(self, seeded_db):
        _insert_obs(seeded_db, "GA|pick3|2024-01-03|midday",
                    "GA","pick3","2024-01-03","midday","034","lottery.net",1)
        reconcile_pending(seeded_db)
        draw = _get_draw(seeded_db, "GA|pick3|2024-01-03|midday")
        assert draw["winning_number"] == "034"

    def test_coverage_set_to_accepted(self, seeded_db):
        _insert_obs(seeded_db, "GA|pick3|2024-01-04|evening",
                    "GA","pick3","2024-01-04","evening","789","lottery.net",1)
        reconcile_pending(seeded_db)
        cov = seeded_db.execute(
            "SELECT coverage_status FROM scrape_coverage "
            "WHERE state='GA' AND game_type='pick3' AND draw_date='2024-01-04' AND draw_time='evening'"
        ).fetchone()
        assert cov is not None
        assert cov["coverage_status"] == "accepted"

    def test_digit_count_and_sorted_digits_set(self, seeded_db):
        _insert_obs(seeded_db, "GA|pick3|2024-01-05|midday",
                    "GA","pick3","2024-01-05","midday","312","lottery.net",1)
        reconcile_pending(seeded_db)
        draw = _get_draw(seeded_db, "GA|pick3|2024-01-05|midday")
        assert draw["digit_count"] == 3
        assert draw["sorted_digits"] == "123"

    def test_accepted_source_priority_stored(self, seeded_db):
        _insert_obs(seeded_db, "GA|pick3|2024-01-06|midday",
                    "GA","pick3","2024-01-06","midday","111","lottery.net",1)
        reconcile_pending(seeded_db)
        draw = _get_draw(seeded_db, "GA|pick3|2024-01-06|midday")
        assert draw["accepted_source_priority"] == 1


class TestRule2Duplicate:
    """Existing draw, same number → duplicate, is_verified."""

    def test_duplicate_increments_count(self, seeded_db):
        key = "GA|pick3|2024-02-01|midday"
        _insert_obs(seeded_db, key, "GA","pick3","2024-02-01","midday","555","lottery.net",1)
        reconcile_pending(seeded_db)
        _insert_obs(seeded_db, key, "GA","pick3","2024-02-01","midday","555","lotterycorner.com",2)
        reconcile_pending(seeded_db)
        draw = _get_draw(seeded_db, key)
        assert draw["observation_count"] == 2

    def test_is_verified_set_after_second_source(self, seeded_db):
        key = "GA|pick3|2024-02-02|midday"
        _insert_obs(seeded_db, key, "GA","pick3","2024-02-02","midday","777","lottery.net",1)
        reconcile_pending(seeded_db)
        _insert_obs(seeded_db, key, "GA","pick3","2024-02-02","midday","777","lotterycorner.com",2)
        reconcile_pending(seeded_db)
        draw = _get_draw(seeded_db, key)
        assert draw["is_verified"] == 1

    def test_second_observation_marked_duplicate(self, seeded_db):
        key = "GA|pick3|2024-02-03|evening"
        _insert_obs(seeded_db, key, "GA","pick3","2024-02-03","evening","888","lottery.net",1)
        reconcile_pending(seeded_db)
        _insert_obs(seeded_db, key, "GA","pick3","2024-02-03","evening","888","lotterycorner.com",2)
        reconcile_pending(seeded_db)
        statuses = _get_obs_statuses(seeded_db, key)
        assert "duplicate" in statuses


class TestRule3ConflictNewWins:
    """Existing draw, new obs has HIGHER priority → update draw."""

    def test_higher_priority_wins(self, seeded_db):
        key = "GA|pick3|2024-03-01|midday"
        # Priority 2 arrives first (unusual but valid test case)
        _insert_obs(seeded_db, key, "GA","pick3","2024-03-01","midday","111","lotterycorner.com",2)
        reconcile_pending(seeded_db)
        draw = _get_draw(seeded_db, key)
        assert draw["winning_number"] == "111"

        # Priority 1 arrives with different number → should supersede
        _insert_obs(seeded_db, key, "GA","pick3","2024-03-01","midday","222","lottery.net",1)
        reconcile_pending(seeded_db)
        draw = _get_draw(seeded_db, key)
        assert draw["winning_number"] == "222"
        assert draw["accepted_from_source"] == "lottery.net"
        assert draw["accepted_source_priority"] == 1

    def test_conflict_flag_set(self, seeded_db):
        key = "GA|pick3|2024-03-02|midday"
        _insert_obs(seeded_db, key, "GA","pick3","2024-03-02","midday","333","lotterycorner.com",2)
        reconcile_pending(seeded_db)
        _insert_obs(seeded_db, key, "GA","pick3","2024-03-02","midday","444","lottery.net",1)
        reconcile_pending(seeded_db)
        draw = _get_draw(seeded_db, key)
        assert draw["has_conflict"] == 1

    def test_old_accepted_obs_marked_conflict(self, seeded_db):
        key = "GA|pick3|2024-03-03|midday"
        _insert_obs(seeded_db, key, "GA","pick3","2024-03-03","midday","555","lotterycorner.com",2)
        reconcile_pending(seeded_db)
        _insert_obs(seeded_db, key, "GA","pick3","2024-03-03","midday","666","lottery.net",1)
        reconcile_pending(seeded_db)
        statuses = _get_obs_statuses(seeded_db, key)
        assert "conflict" in statuses


class TestRule4ConflictExistingWins:
    """Existing draw, new obs has LOWER priority → reject new, flag conflict."""

    def test_lower_priority_rejected(self, seeded_db):
        key = "GA|pick3|2024-04-01|midday"
        _insert_obs(seeded_db, key, "GA","pick3","2024-04-01","midday","123","lottery.net",1)
        reconcile_pending(seeded_db)
        _insert_obs(seeded_db, key, "GA","pick3","2024-04-01","midday","999","lotteryusa.com",3)
        reconcile_pending(seeded_db)
        draw = _get_draw(seeded_db, key)
        assert draw["winning_number"] == "123"  # unchanged
        assert draw["accepted_from_source"] == "lottery.net"

    def test_new_obs_marked_conflict(self, seeded_db):
        key = "GA|pick3|2024-04-02|midday"
        _insert_obs(seeded_db, key, "GA","pick3","2024-04-02","midday","321","lottery.net",1)
        reconcile_pending(seeded_db)
        _insert_obs(seeded_db, key, "GA","pick3","2024-04-02","midday","987","lotteryusa.com",3)
        reconcile_pending(seeded_db)
        statuses = _get_obs_statuses(seeded_db, key)
        assert statuses.count("conflict") == 1

    def test_conflict_note_populated(self, seeded_db):
        key = "GA|pick3|2024-04-03|midday"
        _insert_obs(seeded_db, key, "GA","pick3","2024-04-03","midday","111","lottery.net",1)
        reconcile_pending(seeded_db)
        _insert_obs(seeded_db, key, "GA","pick3","2024-04-03","midday","222","lotteryusa.com",3)
        reconcile_pending(seeded_db)
        obs = seeded_db.execute(
            "SELECT conflict_note FROM draw_observations "
            "WHERE canonical_key=? AND reconciliation_status='conflict'",
            (key,)
        ).fetchone()
        assert obs is not None
        assert obs["conflict_note"] is not None and len(obs["conflict_note"]) > 0


class TestIdempotency:
    def test_reconcile_twice_no_duplicates(self, seeded_db):
        key = "GA|pick3|2024-05-01|midday"
        _insert_obs(seeded_db, key, "GA","pick3","2024-05-01","midday","456","lottery.net",1)
        reconcile_pending(seeded_db)
        stats2 = reconcile_pending(seeded_db)
        assert stats2["accepted"] == 0   # nothing pending second time
        count = seeded_db.execute(
            "SELECT COUNT(*) FROM draws WHERE canonical_key=?", (key,)
        ).fetchone()[0]
        assert count == 1
