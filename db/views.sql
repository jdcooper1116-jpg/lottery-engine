-- lottery_engine/db/views.sql
-- Helper views. Safe to re-run; uses CREATE VIEW IF NOT EXISTS.

-- ---------------------------------------------------------------
-- v_draws_window: fast window searches (state+game+date+time+number)
-- ---------------------------------------------------------------
CREATE VIEW IF NOT EXISTS v_draws_window AS
SELECT
    canonical_key,
    state,
    game_type,
    draw_date,
    draw_time,
    winning_number,
    digit_count,
    sorted_digits,
    is_verified,
    has_conflict,
    accepted_from_source
FROM draws
ORDER BY state, game_type, draw_date, draw_time;

-- ---------------------------------------------------------------
-- v_coverage_summary: slot counts by state/game/status
-- ---------------------------------------------------------------
CREATE VIEW IF NOT EXISTS v_coverage_summary AS
SELECT
    state,
    game_type,
    coverage_status,
    COUNT(*)       AS slot_count,
    MIN(draw_date) AS earliest_date,
    MAX(draw_date) AS latest_date
FROM scrape_coverage
GROUP BY state, game_type, coverage_status;

-- ---------------------------------------------------------------
-- v_conflicts: all canonical rows with conflicting observations
-- ---------------------------------------------------------------
CREATE VIEW IF NOT EXISTS v_conflicts AS
SELECT
    d.canonical_key,
    d.state,
    d.game_type,
    d.draw_date,
    d.draw_time,
    d.winning_number           AS accepted_number,
    d.accepted_from_source,
    d.accepted_source_priority,
    o.source_name              AS conflicting_source,
    o.source_priority          AS conflicting_priority,
    o.winning_number           AS conflicting_number,
    o.conflict_note,
    o.scraped_at
FROM draws d
JOIN draw_observations o
    ON d.canonical_key = o.canonical_key
    AND o.reconciliation_status = 'conflict'
WHERE d.has_conflict = 1;

-- ---------------------------------------------------------------
-- v_unverified_draws: accepted but only one source seen
-- ---------------------------------------------------------------
CREATE VIEW IF NOT EXISTS v_unverified_draws AS
SELECT
    canonical_key,
    state,
    game_type,
    draw_date,
    draw_time,
    winning_number,
    accepted_from_source,
    accepted_source_priority,
    accepted_at
FROM draws
WHERE is_verified = 0
  AND has_conflict = 0
ORDER BY state, game_type, draw_date;

-- ---------------------------------------------------------------
-- v_coverage_gaps: slots not yet scraped or errored
-- ---------------------------------------------------------------
CREATE VIEW IF NOT EXISTS v_coverage_gaps AS
SELECT
    state,
    game_type,
    draw_date,
    draw_time,
    coverage_status,
    last_attempted_at,
    notes
FROM scrape_coverage
WHERE coverage_status IN ('not_scraped', 'scrape_error')
ORDER BY state, game_type, draw_date;
