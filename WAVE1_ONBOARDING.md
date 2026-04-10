# Wave 1 Onboarding Guide

Georgia is fully validated and serves as the reference implementation.
This document covers the controlled onboarding process for the next three states:
**Florida**, **New York**, and **Pennsylvania**.

---

## Onboarding philosophy

Each new state goes through three gates before it is trusted for backfilling:

1. **Dry-run** — Confirm the URL plan and registry structure with no network traffic.
2. **One-month live validation** — Fetch one recent month, confirm the parser
   produces correct rows, draw times remain distinct, and the query layer works.
3. **Slug verification** — Only after a live validation pass, set
   `slug_verified=True` in the state definition file and mark status `"verified"`.

Do not run a multi-year backfill until the state passes gate 2.

---

## Georgia (reference — already complete)

```bash
python -m cli.validate_state --state GA --game pick3 --month 2024-01 --source lottery.net --dry-run
```

Expected: `STATE=GA GAME=pick3 MONTH=2024-01 SOURCE=lottery.net RESULT=PASS`

Georgia's lottery.net slugs are verified. Full backfill can run at any time:

```bash
python -m cli.ingest --state GA --start 2009-01-01 --end 2024-12-31 --source lottery.net
python -m cli.ingest --state GA --start 2009-01-01 --end 2024-12-31 --source lotterycorner.com
```

---

## Florida — first live validation target

Florida uses standard Pick 3 / Pick 4 naming. Slugs follow the same
`pick-3-midday` / `pick-3-evening` pattern as Georgia.
**Risk: LOW.** This is the safest first live test.

### Step 1 — Dry-run (safe, no HTTP)

```bash
python -m cli.validate_state --state FL --game pick3 --month 2024-01 \
    --source lottery.net --dry-run
```

Expected:
```
STATE=FL  GAME=pick3  MONTH=2024-01  SOURCE=lottery.net  RESULT=PASS  WARNS=1
```
The WARN is expected — slugs are ESTIMATED until confirmed live.

Confirm these URLs look correct before proceeding:
- `https://www.lottery.net/florida/pick-3-midday/numbers/2024`
- `https://www.lottery.net/florida/pick-3-evening/numbers/2024`
- `https://www.lottery.net/florida/pick-4-midday/numbers/2024`
- `https://www.lottery.net/florida/pick-4-evening/numbers/2024`

### Step 2 — Live validation (one month)

```bash
python -m cli.validate_state --state FL --game pick3 --month 2024-01 \
    --source lottery.net
```

A passing result looks like:
```
STATE=FL  GAME=pick3  MONTH=2024-01  SOURCE=lottery.net  RESULT=PASS  WARNS=1
```
(The WARN about estimated slugs persists until you set `slug_verified=True`.)

Run pick4 next:
```bash
python -m cli.validate_state --state FL --game pick4 --month 2024-01 \
    --source lottery.net
```

### Step 3 — Mark slugs verified (after live pass)

In `registry/definitions/florida.py`, for each lottery.net SourceJobMapping:
```python
slug_verified=True,   # confirmed: /florida/pick-3-midday/numbers/2024 works
```
Change `status` in `REGISTRY_META` from `"seeded"` to `"verified"`.

Re-run `python -m registry.seed --state FL` to persist to DB.

### Step 4 — Full backfill

```bash
python -m cli.ingest --state FL --game pick3 \
    --start 2002-01-01 --end 2024-12-31 --source lottery.net

python -m cli.ingest --state FL --game pick4 \
    --start 2002-01-01 --end 2024-12-31 --source lottery.net
```

### Step 5 — Check coverage

```bash
python -m cli.coverage_report --state FL
python -m cli.ingest --state FL --start 2002-01-01 --end 2024-12-31 \
    --source lotterycorner.com  # secondary verification pass
```

---

## New York — dry-run first, slug risk is high

New York uses **non-standard game names**: "Numbers" (pick3) and "Win 4" (pick4).
The lottery.net slug compound `numbers-midday` is estimated from the GA pattern —
it may be structured differently on the live site.
**Risk: MODERATE.** Always dry-run first and visually confirm the URLs resolve.

### Step 1 — Dry-run (required before any live fetch)

```bash
python -m cli.validate_state --state NY --game pick3 --month 2024-01 \
    --source lottery.net --dry-run
```

The dry-run will print these URLs for manual verification:
- `https://www.lottery.net/new-york/numbers-midday/numbers/2024`
- `https://www.lottery.net/new-york/numbers-evening/numbers/2024`
- `https://www.lottery.net/new-york/win-4-midday/numbers/2024`
- `https://www.lottery.net/new-york/win-4-evening/numbers/2024`

**Manually open each URL in a browser before running live ingest.**

If a URL 404s, update `source_game_slug` in `registry/definitions/new_york.py`
for the affected mapping. Common alternatives to check:
- `ny-numbers-midday` instead of `numbers-midday`
- `new-york-numbers` (shared midday+evening page)
- `numbers` (single-page, no draw-time suffix)

If lottery.net serves midday and evening on the same page (as with old
Georgia `cash-3`), the mapping needs `source_game_slug="numbers"` and
the parser's `_parse_text_scan` strategy will handle the draw-time attribution
from `mapping.job_def.draw_time`.

### Step 2 — Live validation (after manual URL check)

```bash
python -m cli.validate_state --state NY --game pick3 --month 2024-01 \
    --source lottery.net
```

### Step 3 — Win 4 (pick4)

```bash
python -m cli.validate_state --state NY --game pick4 --month 2024-01 \
    --source lottery.net
```

### Step 4 — Registry report check

```bash
python -m cli.registry_report --state NY --format detail
```

### Step 5 — Full backfill (after both games pass)

```bash
python -m cli.ingest --state NY --start 2002-01-01 --end 2024-12-31 \
    --source lottery.net
```

---

## Pennsylvania — standard validation

Pennsylvania uses standard "Pick 3" / "Pick 4" naming.
Slugs follow the same pattern as Florida.
**Risk: LOW.** Run after Florida confirms the slug pattern is correct.

### Step 1 — Dry-run

```bash
python -m cli.validate_state --state PA --game pick3 --month 2024-01 \
    --source lottery.net --dry-run
```

URLs to verify:
- `https://www.lottery.net/pennsylvania/pick-3-midday/numbers/2024`
- `https://www.lottery.net/pennsylvania/pick-3-evening/numbers/2024`

### Step 2 — Live validation

```bash
python -m cli.validate_state --state PA --game pick3 --month 2024-01 \
    --source lottery.net

python -m cli.validate_state --state PA --game pick4 --month 2024-01 \
    --source lottery.net
```

### Step 3 — Full backfill

```bash
python -m cli.ingest --state PA --start 2002-01-01 --end 2024-12-31 \
    --source lottery.net
```

---

## After FL, NY, PA — Tier 1B states (OH, MI, IL, TN)

Once the three Tier 1A states are verified, the Tier 1B states follow the same
dry-run → live validation → backfill sequence. All are 2-draw states and should
behave like Florida once slugs are confirmed.

```bash
# Ohio (standard, Pick 3 / Pick 4)
python -m cli.validate_state --state OH --game pick3 --month 2024-01 --dry-run

# Michigan (Daily 3 / Daily 4 game names — verify slug)
python -m cli.validate_state --state MI --game pick3 --month 2024-01 --dry-run

# Illinois (standard)
python -m cli.validate_state --state IL --game pick3 --month 2024-01 --dry-run

# Tennessee (Cash 3 / Cash 4 like Georgia)
python -m cli.validate_state --state TN --game pick3 --month 2024-01 --dry-run
```

---

## Registry status check (run anytime)

```bash
python -m cli.registry_report                      # full report
python -m cli.registry_report --format summary     # one-line per state
python -m cli.registry_report --format order       # onboarding order
python -m cli.registry_report --format sources     # slug matrix
```

---

## Pass/fail criteria

A state passes validation when all of the following are true:

| Check | Criterion |
|---|---|
| Registry | Job definitions and source mappings exist |
| URL generation | At least one URL per job, no `{` placeholders |
| Ingest | > 0 observations written |
| Draw times | All expected draw times present in DB results |
| Row counts | ≥ 15 draws per draw_time for the month |
| Leading zeros | Numbers starting with `0` preserved as-is |
| Canonical draws | Observations reconciled to `draws` table |
| Source provenance | `source_name` populated on every DrawRecord |
| Candidate match | Returns ≥ 1 hit using a known winning number |
| Dream backtest | Returns > 0 draws in window |
| Coverage tracking | Accepted slots recorded in `scrape_coverage` |

---

## Marking a state verified

After a state passes the live validation gate:

1. Open `registry/definitions/{state_name}.py`
2. Set `slug_verified=True` on every confirmed lottery.net `SourceJobMapping`
3. Change `REGISTRY_META["status"]` from `"seeded"` to `"verified"`
4. Change `REGISTRY_META["slugs_verified"]` from `False` to `True`
5. Run `python -m registry.seed --state {STATE}` to update the DB
6. Run `python -m cli.registry_report --state {STATE}` to confirm

---

## What NOT to do yet

- Do not backfill Texas (TX) until California (CA) has confirmed 3-draw-per-day
  parsing works correctly, and you are confident in the `day` draw-time slot.
- Do not ingest Oregon (OR) until pick3 game availability is confirmed.
  The current registry has OR defined as pick4-only; verify this is correct
  before any ingest attempt.
