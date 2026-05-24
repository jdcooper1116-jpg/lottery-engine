# Database Integrity Audit

## Purpose

The audit script performs a **read-only** integrity check across all states and
games in the lottery engine database. It does not modify, ingest, repair, or
clean anything. Its sole job is to surface problems so a human can decide how
to act.

> **Core safety principle: incomplete coverage is safer than false verified coverage.**
>
> A missing draw slot is recoverable — run the targeted ingest and fill it in.
> A fabricated draw corrupts backtest hit counts permanently and silently.
> If in doubt, mark the slot `scrape_error` rather than accepting an ambiguous result.

---

## Quick Start

```bash
# Full audit, all states and games (default DB path from env or data/history_all_states.db)
python3 scripts/audit_database_integrity.py --format all

# Using the production DB path
LOTTERY_DB_PATH=data/history_all_states.db python3 scripts/audit_database_integrity.py --format all

# Single state
python3 scripts/audit_database_integrity.py --state GA --format all

# Single state + game
python3 scripts/audit_database_integrity.py --state GA --game pick3 --format all

# Narrow recent coverage window (last 14 days instead of 45)
python3 scripts/audit_database_integrity.py --recent-days 14

# JSON only (for CI/alerting)
python3 scripts/audit_database_integrity.py --format json

# Verbose debug output
python3 scripts/audit_database_integrity.py --log-level DEBUG
```

Exit codes:
- `0` — PASS (no CRITICAL or HIGH issues)
- `1` — HIGH issues found (no CRITICAL)
- `2` — CRITICAL issues found

---

## Command Reference

| Flag | Default | Description |
|------|---------|-------------|
| `--db-path` | `$LOTTERY_DB_PATH` or `data/history_all_states.db` | SQLite database path |
| `--out-dir` | `outputs/audits/<timestamp>` | Directory for all output files |
| `--state` | all | Restrict audit to one state code (e.g. `GA`) |
| `--game` | all | Restrict audit to one game (`pick3` or `pick4`) |
| `--recent-days` | 45 | Lookback window for the recent coverage gap check |
| `--format` | `all` | Output format: `json`, `csv`, `markdown`, or `all` |
| `--log-level` | `INFO` | Logging verbosity |

---

## Output Files

All files are written to `--out-dir` (default `outputs/audits/<timestamp>/`).

### Summary files

| File | Description |
|------|-------------|
| `audit_summary.md` | Human-readable table of all 15 checks with status, severity, row counts, and interpretation guide |
| `audit_summary.json` | Machine-readable summary with the same data — suitable for CI gates or alerting |

### Detail CSV files

| File | Checks | What's in it |
|------|--------|-------------|
| `duplicate_drawtime_groups.csv` | 2, 15 | Rows where the same winning number from the same source URL appears in 2+ draw_time slots for one date — the core symptom of a daily-aggregate source being copied into multiple draw-time slots |
| `digit_length_issues.csv` | 4, 5 | Pick 3 draws where `winning_number` length ≠ 3, and pick 4 draws where length ≠ 4 |
| `leading_zero_risk.csv` | 6 | Draws where `winning_number` is shorter than expected for the game type — possible `int()` coercion stripping a leading zero (e.g. `"042"` → `"42"`) |
| `conflict_rows.csv` | 7, 9 | Accepted draws where sources disagreed on the winning number (`has_conflict=1`), and canonical_keys where 2+ distinct numbers were observed |
| `coverage_mismatches.csv` | 10, 11 | `scrape_coverage` claims `accepted` but no draw row exists (false positive), and draw rows with no corresponding `accepted` coverage (tracking gap) |
| `latest_coverage_by_state_game_drawtime.csv` | 12 | Most recent accepted draw per state/game/draw_time/source — use to spot stale slots |
| `source_reliability.csv` | 13 | Per-source observation counts broken down by reconciliation status, with conflict% and anomaly% |
| `recent_coverage_gaps.csv` | 14 | Coverage slots in the last N days that are not `accepted` — includes `scrape_error`, `anomaly`, `not_scraped` |
| `observation_bad_status_clusters.csv` | 8 | Clustered view of `conflict`/`anomaly`/`error` observations by source and draw_time |
| `repair_queue_candidates.csv` | all CRITICAL + HIGH | Unified list of all actionable rows from every CRITICAL and HIGH check, tagged with which check surfaced them |

---

## The 15 Audit Checks

### CRITICAL — Stop. Fix before running any backtest.

| # | Name | What it catches |
|---|------|----------------|
| 1 | `duplicate_canonical_keys_in_draws` | `canonical_key` appears more than once in `draws` (UNIQUE constraint violation — should never happen) |
| 2 | `same_number_across_draw_times_in_observations` | Same `winning_number + source_url` on the same date appears in 2+ `draw_time` slots in `draw_observations` — the classic daily-aggregate source duplication pattern |
| 4 | `pick3_wrong_digit_length` | Pick 3 draw row where `winning_number` length ≠ 3 |
| 5 | `pick4_wrong_digit_length` | Pick 4 draw row where `winning_number` length ≠ 4 |
| 6 | `leading_zero_risk` | Pick 3 number with fewer than 3 digits, or pick 4 number with fewer than 4 digits — likely a leading zero stripped by integer coercion |
| 9 | `multiple_winning_numbers_per_canonical_key` | Two or more distinct winning numbers were ever observed for the same `canonical_key` — only one can be correct |
| 15 | `suspicious_all_drawtime_duplication_in_draws` | Same `winning_number + source_url` appears in accepted `draws` rows across 2+ draw_times on one date — means one source page may have been copied into multiple canonical draw slots |

### HIGH — Fix before using the affected state/game in production.

| # | Name | What it catches |
|---|------|----------------|
| 3 | `invalid_draw_time_values` | `draw_time` is not one of: `midday`, `evening`, `night`, `morning`, `day`. `"unknown"` in `draw_observations` is only acceptable when `reconciliation_status = 'anomaly'` |
| 7 | `accepted_draws_with_conflict` | Accepted draw rows where `has_conflict=1` — sources disagreed on the number but one was accepted anyway |
| 10 | `accepted_coverage_but_no_draw_row` | `scrape_coverage.coverage_status = 'accepted'` but the `draws` table has no corresponding row — coverage tracking is lying |

### MEDIUM — Track. Missing coverage is expected during catchup.

| # | Name | What it catches |
|---|------|----------------|
| 8 | `observation_bad_status_clusters` | Clusters of `conflict`/`anomaly`/`error` observations by source — large clusters may indicate a broken parser or a bad source |
| 11 | `draw_row_without_accepted_coverage` | Draw row exists but `scrape_coverage` is missing or not `accepted` — tracking inconsistency |
| 14 | `recent_coverage_gaps` | Slots in the last N days that are not `accepted` — could be genuine missing data or scheduled scrape_errors |

### LOW — Informational. Review periodically.

| # | Name | What it catches |
|---|------|----------------|
| 12 | `latest_coverage_by_state_game_drawtime` | Latest accepted draw per state/game/draw_time/source — spots stale sources (>7 days since last accepted draw) |
| 13 | `source_reliability_summary` | Per-source breakdown of accepted/duplicate/conflict/anomaly counts — flags sources with anomaly_pct > 5% |

---

## How to Interpret Severity

```
CRITICAL  → False or corrupted data is in the canonical draws table.
            Backtest hit counts for this state/game cannot be trusted.
            Do not show results to Sweet404Peaches until fixed.

HIGH      → Data integrity is at risk but may not yet be in the draws table.
            Fix before using the affected slot in a live hit-detection run.

MEDIUM    → Coverage is incomplete or tracking is inconsistent.
            Safe to run backtests for dates that do have accepted rows.
            Missing is better than fabricated.

LOW       → Informational drift. No immediate action required.
            Review before the next major ingest cycle.
```

---

## The GA lotteryusa.com Duplication Pattern

This is the specific bug the audit was designed to catch:

**Root cause:** lotteryusa.com serves a single unlabeled daily result per game.
When that source was mapped to three separate `SourceJobMapping` entries
(midday, evening, night), each fetch returned the same number. The reconciler
accepted one per draw_time slot, creating three `draws` rows for one real draw.

**Backtest effect:** A backtest for candidate `842` would report 3 hits on a
single day — one per fabricated draw_time — instead of the true 0 or 1.

**Audit detection:** Check 15 catches this in the `draws` table. Check 2
catches it at the `draw_observations` layer before it reaches `draws`.

**Fix already applied:**
- `registry/definitions/georgia.py`: lotteryusa.com mappings removed for GA.
- `orchestrator/runner.py`: Phase-2 cross-task dedup discards ambiguous results.
- `sources/lotteryusa.py`: Unlabeled results emit `draw_time="unknown"`.
- `orchestrator/reconciler.py`: `draw_time="unknown"` observations are marked anomaly, not reconciled.
- `scripts/cleanup_ambiguous_lotteryusa.py`: One-time cleanup for existing corrupted rows.

**To clean existing corrupted rows (run once after deploy):**
```bash
# Dry run first
python3 scripts/cleanup_ambiguous_lotteryusa.py --state GA --dry-run

# Apply
python3 scripts/cleanup_ambiguous_lotteryusa.py --state GA
```

---

## Running in CI / Alerting

```bash
# Returns exit code 2 on CRITICAL, 1 on HIGH, 0 on PASS
python3 scripts/audit_database_integrity.py --format json
echo "Exit: $?"

# Parse the JSON for Slack/PagerDuty alerting
python3 -c "
import json, sys
s = json.load(open('outputs/audits/latest/audit_summary.json'))
if s['counts']['critical'] > 0:
    print('CRITICAL DB issues — halt all backtests')
    sys.exit(2)
"
```

To symlink the latest run:
```bash
ln -sfn outputs/audits/$(ls -t outputs/audits/ | head -1) outputs/audits/latest
```

---

## Production Audit Route

### Endpoint

```
POST /admin/audit/database-integrity
```

**Auth:** `X-Ingest-Token: <INGEST_ADMIN_TOKEN>` header required.

**Strictly read-only.** No data is modified, reconciled, ingested, or cleaned.

### Request Body

```json
{
  "state":           null,
  "game":            null,
  "recent_days":     45,
  "format":          "all",
  "write_artifacts": true
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `state` | string \| null | null | Filter to one state (e.g. `"GA"`). Null = all states. |
| `game` | string \| null | null | Filter to one game type (`"pick3"` / `"pick4"`). Null = all. |
| `recent_days` | int | 45 | Look-back window for recency checks. |
| `format` | string | `"all"` | Output format: `"all"` writes md + json + all CSVs. |
| `write_artifacts` | bool | true | When true, writes files to `/data/audits/<timestamp>/`. |

### Response

```json
{
  "ok": false,
  "db_path": "/data/history_all_states.db",
  "audit_timestamp": "2026-05-24T12:00:00.000000+00:00",
  "overall_status": "HIGH",
  "severity_counts": {"critical": 0, "high": 2, "medium": 1, "low": 0},
  "check_summaries": [
    {"check_id": "check_01", "name": "Duplicate canonical keys in draws", "severity": "CRITICAL", "ok": true, "row_count": 0},
    ...
  ],
  "artifact_dir": "/data/audits/20260524T120000Z",
  "artifact_files": ["audit_report.md", "audit_results.json", "repair_queue_candidates.csv", ...],
  "repair_queue_count": 3,
  "critical_count": 0,
  "high_count": 2,
  "medium_count": 1,
  "low_count": 0
}
```

CSV content is **not** returned in the response. Download artifacts from `artifact_dir` directly (Railway volume mount or `railway run cat /data/audits/<ts>/repair_queue_candidates.csv`).

### Example curl

```bash
curl -sS -X POST https://<your-app>.railway.app/admin/audit/database-integrity \
  -H "Content-Type: application/json" \
  -H "X-Ingest-Token: $INGEST_ADMIN_TOKEN" \
  -d '{"recent_days":45,"format":"all","write_artifacts":true}' \
  | python3 -m json.tool
```

### Response Fields

| Field | Meaning |
|-------|---------|
| `ok` | True only if all checks passed (no CRITICAL or HIGH issues). |
| `overall_status` | `PASS`, `HIGH`, or `CRITICAL` — highest severity with a failing check. |
| `severity_counts` | Dict with `critical`, `high`, `medium`, `low` — count of checks at each level that failed. |
| `check_summaries` | One entry per check: `check_id`, `name`, `severity`, `ok`, `row_count`. |
| `artifact_dir` | Path on the Railway volume where output files were written, or null if `write_artifacts=false`. |
| `artifact_files` | List of filenames written (md, json, CSVs). |
| `repair_queue_count` | Row count from `repair_queue_candidates.csv` when artifacts are written; otherwise an approximate count from failing CRITICAL/HIGH checks. |
| `critical_count` etc. | Convenience duplicates of `severity_counts` fields. |

---

## What Each CSV Column Means (Key Fields)

| Column | Meaning |
|--------|---------|
| `canonical_key` | `{state}\|{game_type}\|{draw_date}\|{draw_time}` — unique draw slot identifier |
| `draw_time_count` / `occupied_draw_times` | Number of distinct draw_times that share the same winning_number+source_url |
| `is_full_sweep` | True when the same number covers ALL draw_times for the game — strongest signal of fabrication |
| `conflict_pct` | % of observations from that source that were marked `conflict` |
| `anomaly_pct` | % of observations from that source that were marked `anomaly` |
| `days_since_latest` | Days since the most recent accepted draw from that source |
| `missing_leading_zeros` | How many digits are missing vs. expected length — 1 means one leading zero was likely stripped |
| `coverage_status` | `accepted` / `scrape_error` / `anomaly` / `not_scraped` / `MISSING` (not in coverage table at all) |
