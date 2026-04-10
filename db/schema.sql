-- lottery_engine/db/schema.sql
-- Five-table canonical schema. Run once on a fresh database.

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------
-- draws: one accepted canonical row per canonical_key
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS draws (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_key            TEXT    NOT NULL UNIQUE,
    -- format: "{state}|{game_type}|{draw_date}|{draw_time}"

    state                    TEXT    NOT NULL,
    game_type                TEXT    NOT NULL,
    draw_date                TEXT    NOT NULL,   -- YYYY-MM-DD
    draw_time                TEXT    NOT NULL,   -- canonical enum only

    winning_number           TEXT    NOT NULL,   -- plain text, leading zeros preserved
    digit_count              INTEGER NOT NULL,   -- len(winning_number)
    sorted_digits            TEXT    NOT NULL,   -- digits sorted ascending, e.g. "312" -> "123"

    accepted_from_source     TEXT    NOT NULL,   -- source_name that owns this row
    accepted_source_priority INTEGER NOT NULL,   -- priority of accepted_from_source at time of insert

    observation_count        INTEGER NOT NULL DEFAULT 1,
    is_verified              INTEGER NOT NULL DEFAULT 0, -- 1 = 2+ sources agree on winning_number
    has_conflict             INTEGER NOT NULL DEFAULT 0, -- 1 = sources disagree on winning_number
    accepted_at              TEXT    NOT NULL             -- ISO-8601 UTC
);

CREATE INDEX IF NOT EXISTS idx_draws_state         ON draws(state);
CREATE INDEX IF NOT EXISTS idx_draws_game          ON draws(game_type);
CREATE INDEX IF NOT EXISTS idx_draws_date          ON draws(draw_date);
CREATE INDEX IF NOT EXISTS idx_draws_time          ON draws(draw_time);
CREATE INDEX IF NOT EXISTS idx_draws_number        ON draws(winning_number);
CREATE INDEX IF NOT EXISTS idx_draws_state_date    ON draws(state, draw_date);
CREATE INDEX IF NOT EXISTS idx_draws_state_game    ON draws(state, game_type, draw_date);
CREATE INDEX IF NOT EXISTS idx_draws_verified      ON draws(is_verified);
CREATE INDEX IF NOT EXISTS idx_draws_canonical     ON draws(canonical_key);
CREATE INDEX IF NOT EXISTS idx_draws_sorted        ON draws(sorted_digits);

-- ---------------------------------------------------------------
-- draw_observations: every source claim ever ingested
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS draw_observations (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_key         TEXT    NOT NULL,

    state                 TEXT    NOT NULL,
    game_type             TEXT    NOT NULL,
    draw_date             TEXT    NOT NULL,
    draw_time             TEXT    NOT NULL,   -- canonical enum only

    winning_number        TEXT    NOT NULL,   -- plain text, leading zeros preserved
    digit_count           INTEGER NOT NULL,
    sorted_digits         TEXT    NOT NULL,

    source_name           TEXT    NOT NULL,
    source_priority       INTEGER NOT NULL,
    source_url            TEXT,
    scraped_at            TEXT    NOT NULL,   -- ISO-8601 UTC

    reconciliation_status TEXT    NOT NULL DEFAULT 'pending',
    -- pending | accepted | duplicate | conflict | anomaly

    conflict_note         TEXT,
    raw_draw_time_label   TEXT    -- original label from source before normalization
);

CREATE INDEX IF NOT EXISTS idx_obs_canonical    ON draw_observations(canonical_key);
CREATE INDEX IF NOT EXISTS idx_obs_source       ON draw_observations(source_name);
CREATE INDEX IF NOT EXISTS idx_obs_status       ON draw_observations(reconciliation_status);
CREATE INDEX IF NOT EXISTS idx_obs_date         ON draw_observations(draw_date);
CREATE INDEX IF NOT EXISTS idx_obs_state_date   ON draw_observations(state, draw_date);
CREATE INDEX IF NOT EXISTS idx_obs_pending      ON draw_observations(reconciliation_status)
    WHERE reconciliation_status = 'pending';

-- ---------------------------------------------------------------
-- draw_job_definitions: canonical schedule with lifecycle windows
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS draw_job_definitions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    state               TEXT    NOT NULL,
    game_type           TEXT    NOT NULL,   -- "pick3" | "pick4"
    draw_time           TEXT    NOT NULL,   -- canonical enum
    draw_label          TEXT    NOT NULL,
    schedule_version    TEXT    NOT NULL DEFAULT 'v1',

    active_start_date   TEXT,               -- YYYY-MM-DD or NULL (unknown / always active)
    active_end_date     TEXT,               -- YYYY-MM-DD or NULL (still active)
    source_min_year     INTEGER,            -- earliest year any source reliably covers
    source_max_year     INTEGER,            -- latest year (NULL = ongoing)
    draw_days           TEXT    NOT NULL DEFAULT 'daily',
    -- "daily" | "mon-sat" | "mon-fri" | JSON array ["mon","wed","fri"]

    canonical_time_key  TEXT    NOT NULL,   -- the draw_time token used in canonical_key
    notes               TEXT,
    is_active           INTEGER NOT NULL DEFAULT 1,

    UNIQUE(state, game_type, draw_time, schedule_version)
);

CREATE INDEX IF NOT EXISTS idx_jobs_state  ON draw_job_definitions(state);
CREATE INDEX IF NOT EXISTS idx_jobs_active ON draw_job_definitions(is_active);

-- ---------------------------------------------------------------
-- source_job_mappings: per-source slug/URL/coverage per job
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS source_job_mappings (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    job_definition_id      INTEGER NOT NULL REFERENCES draw_job_definitions(id),

    source_name            TEXT    NOT NULL,
    source_priority        INTEGER NOT NULL,

    source_state_slug      TEXT,   -- e.g. "georgia" or "ga"
    source_game_slug       TEXT,   -- e.g. "cash-3" or "pick3"
    source_draw_time_label TEXT,   -- raw label this source uses, e.g. "Midday", "Evening"
    url_template           TEXT,   -- Python .format()-style template

    source_min_year        INTEGER,
    source_max_year        INTEGER,
    is_enabled             INTEGER NOT NULL DEFAULT 1,
    notes                  TEXT,

    UNIQUE(job_definition_id, source_name)
);

CREATE INDEX IF NOT EXISTS idx_mappings_job    ON source_job_mappings(job_definition_id);
CREATE INDEX IF NOT EXISTS idx_mappings_source ON source_job_mappings(source_name);

-- ---------------------------------------------------------------
-- scrape_coverage: one row per (state, game, date, draw_time)
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS scrape_coverage (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    state             TEXT    NOT NULL,
    game_type         TEXT    NOT NULL,
    draw_date         TEXT    NOT NULL,
    draw_time         TEXT    NOT NULL,  -- canonical enum

    coverage_status   TEXT    NOT NULL DEFAULT 'not_scraped',
    -- not_scraped | no_draw_scheduled | accepted | conflict | anomaly | scrape_error

    observation_count INTEGER NOT NULL DEFAULT 0,
    verified_count    INTEGER NOT NULL DEFAULT 0,
    last_attempted_at TEXT,
    last_source       TEXT,
    notes             TEXT,

    UNIQUE(state, game_type, draw_date, draw_time)
);

CREATE INDEX IF NOT EXISTS idx_cov_state_date  ON scrape_coverage(state, draw_date);
CREATE INDEX IF NOT EXISTS idx_cov_status      ON scrape_coverage(coverage_status);
CREATE INDEX IF NOT EXISTS idx_cov_state_game  ON scrape_coverage(state, game_type, draw_date);
