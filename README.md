# Lottery Results Engine

A state-aware, source-aware, queryable historical lottery results engine.
Designed to power backtesting apps — particularly dream-number applications
that search configurable 7–10 day windows across up to 15 years of results.

---

## Architecture overview

```
Sources (3)             Orchestrator              Query layer
─────────────           ─────────────             ───────────
lottery.net    ──┐      scheduler                 service.py
  priority 1     ├──►  runner        ──► draws    backtest_numbers()
lotterycorner  ──┤      reconciler       (canon.)  batch_backtest()
  priority 2     │      coverage     ──► coverage  get_draws_for_date_range()
lotteryusa.com ──┘      tracking         tracking  search_results_by_window()
                                                   ↓
                                              API routes / CLI / other apps
```

**Five tables:**

| Table | Purpose |
|---|---|
| `draws` | One canonical accepted row per `{state}\|{game_type}\|{draw_date}\|{draw_time}` |
| `draw_observations` | Every source claim ever ingested, retained permanently |
| `draw_job_definitions` | Canonical schedule with full lifecycle windows |
| `source_job_mappings` | Per-source slugs, URL templates, coverage ranges |
| `scrape_coverage` | Trust map: not_scraped / accepted / conflict / error per slot |

---

## Installation

```bash
# 1. Clone / unpack the project
cd lottery_engine

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

---

## Georgia smoke-test — exact commands in order

### Step 1 — Create the database and seed the registry

```bash
# Initialises all 5 tables + views, then seeds Georgia and Florida
python -m registry.seed
```

Expected output:
```
Initializing database...
Seeding 10 job definitions...
  10 job definitions in DB
Seeding 28 source mappings...
  28 source mappings processed

Verification:
STATE  GAME     TIME       LABEL                               VER  START        MIN_YR   ACTIVE
-----------------------------------------------------------------------------------------------
FL     pick3    evening    Florida Pick 3 Evening              v1   NULL         2002     YES
FL     pick3    midday     Florida Pick 3 Midday               v1   2000-01-01   2002     YES
...
GA     pick3    evening    Georgia Cash 3 Evening              v1   NULL         2002     YES
GA     pick3    midday     Georgia Cash 3 Midday               v1   NULL         2002     YES
GA     pick3    night      Georgia Cash 3 Night                v1   2012-01-01   2012     YES
GA     pick4    evening    Georgia Cash 4 Evening              v1   NULL         2002     YES
GA     pick4    midday     Georgia Cash 4 Midday               v1   NULL         2002     YES
GA     pick4    night      Georgia Cash 4 Night                v1   2012-01-01   2012     YES
```

Seed only Georgia:
```bash
python -m registry.seed --state GA
```

Verify registry contents without re-seeding:
```bash
python -m registry.seed --verify
```

---

### Step 2 — Run Georgia backfill from lottery.net

Full 15-year historical backfill (all draws, all game types):
```bash
python -m cli.ingest --state GA --start 2009-01-01 --end 2024-12-31 --source lottery.net
```

Pick 3 only:
```bash
python -m cli.ingest --state GA --game pick3 --start 2009-01-01 --end 2024-12-31 --source lottery.net
```

Recent 90 days only (fast smoke-test):
```bash
python -m cli.ingest --state GA --start 2024-10-01 --end 2024-12-31
```

Dry run (shows task plan without fetching):
```bash
python -m cli.ingest --state GA --start 2024-01-01 --end 2024-01-31 --dry-run
```

Cross-verify with secondary source:
```bash
python -m cli.ingest --state GA --start 2024-01-01 --end 2024-12-31 --source lotterycorner.com
```

---

### Step 3 — Run Georgia Pick 3 and Pick 4 queries

**Latest 7 results:**
```bash
python -m cli.query latest --state GA --game pick3
python -m cli.query latest --state GA --game pick4
```

**Date range:**
```bash
python -m cli.query range --state GA --game pick3 --start 2024-03-01 --end 2024-03-31
python -m cli.query range --state GA --game pick4 --start 2024-03-01 --end 2024-03-31
```

**Window search (7-day):**
```bash
python -m cli.query window --state GA --game pick3 --anchor 2024-03-15 --lookahead 7
python -m cli.query window --state GA --game pick3 --anchor 2024-03-15 --lookahead 10
```

**Backtest candidate numbers — exact match:**
```bash
python -m cli.query backtest --state GA --game pick3 \
    --anchor 2024-03-15 --lookahead 7 \
    --numbers 123 456 789

python -m cli.query backtest --state GA --game pick4 \
    --anchor 2024-03-15 --lookahead 10 \
    --numbers 1234 5678
```

**Backtest with box match:**
```bash
python -m cli.query backtest --state GA --game pick3 \
    --anchor 2024-03-15 --lookahead 7 \
    --numbers 123 --mode box
```

**Backtest midday draws only:**
```bash
python -m cli.query backtest --state GA --game pick3 \
    --anchor 2024-03-15 --lookahead 7 \
    --numbers 123 456 --draw-times midday
```

---

### Step 4 — Check coverage and verify data quality

Coverage summary:
```bash
python -m cli.coverage_report --state GA
python -m cli.coverage_report --state GA --game pick3
```

Show coverage gaps:
```bash
python -m cli.coverage_report --state GA --show-gaps
python -m cli.coverage_report --state GA --show-gaps --start 2024-01-01 --end 2024-12-31
```

Show conflicts and unverified draws:
```bash
python -m cli.verify --state GA --show-conflicts --show-unverified
```

Re-run reconciliation after a new source fetch:
```bash
python -m cli.verify --state GA --reconcile-only
```

---

### Step 5 — Run tests

```bash
# All tests
python -m pytest

# With coverage report
python -m pytest --cov=. --cov-report=term-missing

# Individual suites
python -m pytest tests/test_draw_time_map.py
python -m pytest tests/test_registry.py
python -m pytest tests/test_reconciler.py
python -m pytest tests/test_match_engine.py
python -m pytest tests/test_query_service.py
python -m pytest tests/test_sources.py
```

---

### Step 6 — Start the HTTP API

```bash
uvicorn api.routes:app --reload --port 8000
```

API will be live at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

Example requests:
```bash
# Latest results
curl "http://localhost:8000/draws/latest?state=GA&game_type=pick3&n=7"

# 7-day window
curl "http://localhost:8000/draws/window?state=GA&game_type=pick3&anchor=2024-03-15&lookahead=7"

# Backtest
curl -X POST http://localhost:8000/backtest \
  -H "Content-Type: application/json" \
  -d '{
    "state": "GA",
    "game_type": "pick3",
    "anchor_date": "2024-03-15",
    "lookahead_days": 7,
    "candidates": ["123", "456", "789"],
    "label": "dream-001"
  }'

# Batch backtest
curl -X POST http://localhost:8000/backtest/batch \
  -H "Content-Type: application/json" \
  -d '{
    "jobs": [
      {"state":"GA","game_type":"pick3","anchor_date":"2024-03-15","lookahead_days":7,"candidates":["123"],"label":"A"},
      {"state":"GA","game_type":"pick3","anchor_date":"2024-04-01","lookahead_days":10,"candidates":["456"],"label":"B"}
    ]
  }'
```

---

## Using the query layer directly from Python

The query layer is a plain Python library. The dream-number app does not
need the HTTP server running — import `query/service.py` directly:

```python
from datetime import date
from query.service import backtest_numbers, batch_backtest
from query.models import DreamBacktestRequest, BatchBacktestRequest, QueryFilters

# Single dream record backtest
req = DreamBacktestRequest(
    state="GA",
    game_type="pick3",
    anchor_date=date(2024, 3, 15),
    lookahead_days=7,
    candidates=["123", "456", "789"],
    label="dream-2024-03-15",
)
resp = backtest_numbers(req)

print(resp.summary)
print(f"Hits: {resp.hit_count}")
for hit in resp.hits:
    print(f"  {hit.candidate} on {hit.draw_date} {hit.draw_time}")

# Batch: process a full dream log
jobs = [
    DreamBacktestRequest(state="GA", game_type="pick3",
                         anchor_date=date(2024, 3, d), lookahead_days=7,
                         candidates=["123", "456"])
    for d in range(1, 32)
]
batch_resp = batch_backtest(BatchBacktestRequest(jobs=jobs))
print(batch_resp.aggregate_summary)
```

Available query functions:

| Function | Use |
|---|---|
| `backtest_numbers(req)` | Single dream record → window search + match |
| `batch_backtest(req)` | Multiple dream records in one DB pass |
| `get_draws_for_date_range(req)` | All draws in a date range |
| `search_results_by_window(req)` | Sliding window around an anchor date |
| `match_candidate_numbers(req)` | Candidate match across a date range |
| `get_latest_results(state, game, n)` | Most recent N draws |
| `get_schedule_for_date(state, date)` | What draws were scheduled on a date |

---

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `LOTTERY_DB_PATH` | `./lottery.db` | Path to SQLite database file |

```bash
# Use a different database path
export LOTTERY_DB_PATH=/data/lottery/prod.db
python -m cli.ingest --state GA --start 2024-01-01 --end 2024-12-31
```

---

## Match modes

| Mode | Description | Status |
|---|---|---|
| `exact` | Straight match: `"123"` == `"123"` | ✓ v1 |
| `box` | Any digit permutation: `"321"` matches `"123"` | ✓ v1 |
| `digit` | Every candidate digit appears in winning number | ✓ v1 |
| `pair` | Any 2-digit consecutive pair appears | ✓ v1 |
| `triple` | Any 3-digit consecutive run appears | ✓ v1 |
| `presence` | Any single candidate digit appears | ✓ v1 |

---

## Draw-time canonical enum

One and only one set of values used everywhere:

| Value | Meaning |
|---|---|
| `morning` | Early AM, typically 9–11 AM |
| `day` | Daytime, no specific noon alignment |
| `midday` | Noon-aligned, 11 AM–1 PM range |
| `evening` | Early evening, 5–8 PM range |
| `night` | Late draw, 8 PM–midnight range |
| `unknown` | Normalization failed — data quality flag |

`daytime` is not a valid value and maps to `day` on ingestion.

---

## Source priority

| Priority | Source | Role |
|---|---|---|
| 1 | `lottery.net` | Primary — deepest historical coverage |
| 2 | `lotterycorner.com` | Secondary — gap-filler and cross-verifier |
| 3 | `lotteryusa.com` | Supplemental — recent dates only |

`lotterypost.com` is not in this system and never will be.

---

## Adding a new state

1. Create `registry/definitions/{state_code}.py` following the Georgia template.
2. Add `JOB_DEFINITIONS` and `SOURCE_MAPPINGS` lists.
3. Import them in `registry/definitions/__init__.py`.
4. Re-run `python -m registry.seed --state {STATE}`.
5. Run ingest: `python -m cli.ingest --state {STATE} --start ... --end ...`

No parser code changes are required unless the new state uses an unusual
URL structure — in that case, add URL template overrides to `SOURCE_MAPPINGS`.

---

## Project structure

```
lottery_engine/
├── db/
│   ├── schema.sql              ← All 5 tables
│   ├── views.sql               ← Helper views
│   ├── connection.py           ← Connection management
│   └── migrations/             ← Versioned ALTER scripts
│
├── registry/
│   ├── enums.py                ← DrawTime, GameType, SourceName (canonical values)
│   ├── models.py               ← DrawJobDef, SourceJobMapping dataclasses
│   ├── loader.py               ← get_active_jobs(), get_source_mappings_for_job()
│   ├── seed.py                 ← Writes registry to DB; CLI: python -m registry.seed
│   └── definitions/
│       ├── georgia.py          ← GA jobs + source mappings (fully seeded)
│       └── florida.py          ← FL jobs + source mappings (example state)
│
├── sources/
│   ├── base.py                 ← SourceParser ABC, RawDrawResult, utilities
│   ├── draw_time_map.py        ← THE single normalization map (all parsers import here)
│   ├── lottery_net.py          ← Priority 1 parser
│   ├── lotterycorner.py        ← Priority 2 parser
│   └── lotteryusa.py           ← Priority 3 parser
│
├── orchestrator/
│   ├── scheduler.py            ← Builds FetchTask list from registry
│   ├── runner.py               ← Main ingest loop
│   ├── coverage.py             ← scrape_coverage table management
│   └── reconciler.py           ← Promotes observations → canonical draws
│
├── query/
│   ├── models.py               ← All request/response/filter dataclasses
│   ├── match_engine.py         ← Pluggable match modes
│   ├── coverage_checker.py     ← Coverage gap detection with lifecycle awareness
│   └── service.py              ← Public API: backtest_numbers(), batch_backtest(), etc.
│
├── api/
│   └── routes.py               ← FastAPI thin wrapper over query/service.py
│
├── cli/
│   ├── ingest.py               ← python -m cli.ingest
│   ├── query.py                ← python -m cli.query
│   ├── verify.py               ← python -m cli.verify
│   └── coverage_report.py      ← python -m cli.coverage_report
│
└── tests/
    ├── conftest.py             ← In-memory DB fixtures
    ├── test_draw_time_map.py
    ├── test_sources.py
    ├── test_registry.py
    ├── test_reconciler.py
    ├── test_match_engine.py
    └── test_query_service.py
```

---

## Key design decisions

**Leading zeros:** All winning numbers are stored and returned as plain text strings.
`normalize_number()` strips non-digit characters but never casts to `int`.
`"034"` is always `"034"`, never `34`.

**Canonical key:** `"{state}|{game_type}|{draw_date}|{draw_time}"`.
One and only one accepted draw per key. Source conflicts are retained in
`draw_observations` and never silently discarded.

**Reconciliation rules:**

1. New key → insert draw, mark observation `accepted`
2. Same key, same number → mark `duplicate`, increment count, set `is_verified` when count ≥ 2
3. Same key, different number, higher-priority source → update draw, old accepted → `conflict`
4. Same key, different number, lower-priority source → mark new observation `conflict`, keep existing

**Coverage semantics:** A missing result under `not_scraped` means "we never tried."
A missing result under `no_draw_scheduled` means "the draw did not exist on that date
per the registry lifecycle window." These are never conflated.

**Historical lifecycle:** Every job definition carries `active_start_date` and
`active_end_date`. The scheduler clips task date ranges to these windows, so a
15-year backfill never tries to fetch a night draw from 2005 when that draw did
not yet exist. Set unknown start dates to `None` (= always active as far as we know)
and use `source_min_year` as the soft coverage floor.
