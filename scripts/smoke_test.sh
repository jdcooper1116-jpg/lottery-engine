#!/usr/bin/env bash
set -euo pipefail

source .venv/bin/activate

echo "== Latest =="
python -m cli.query latest --state GA --game pick3 --n 5
python -m cli.query latest --state TX --game pick4 --n 5
python -m cli.query latest --state OR --game pick4 --n 5
python -m cli.query latest --state DC --game pick3 --n 5

echo
echo "== Coverage =="
python -m cli.coverage_report \
  --state GA \
  --game pick3 \
  --start 2024-01-25 \
  --end 2024-02-01 \
  --show-gaps \
  --limit 20

echo
echo "== Dry-run validation =="
python -m cli.validate_state --state WA --game pick4 --month 2024-01 --source lottery.net --dry-run
python -m cli.validate_state --state MA --game pick4 --month 2024-01 --source lottery.net --dry-run

echo
echo "== API smoke summaries =="

run_backtest () {
  local payload="$1"
  python - <<'PY' "$payload"
import json, sys, urllib.request

payload_str = sys.argv[1]
payload_bytes = payload_str.encode("utf-8")

req = urllib.request.Request(
    "http://127.0.0.1:8000/backtest",
    data=payload_bytes,
    headers={"Content-Type": "application/json"},
    method="POST",
)

with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode("utf-8"))

summary = data.get("summary")
hit_count = data.get("hit_count", 0)
draws = len(data.get("all_draws", []))
gaps = len(data.get("coverage_gaps", []))
hit_dates = data.get("hit_dates", [])[:5]

print(json.dumps({
    "summary": summary,
    "hit_count": hit_count,
    "draws_returned": draws,
    "coverage_gaps": gaps,
    "hit_dates": hit_dates
}, indent=2))
PY
}

run_backtest '{"state":"GA","game_type":"pick3","anchor_date":"2024-01-25","lookahead_days":7,"candidates":["297","716","999"],"label":"GA smoke"}'
run_backtest '{"state":"TX","game_type":"pick4","anchor_date":"2024-01-25","lookahead_days":7,"candidates":["3266","7036","1234"],"label":"TX smoke"}'
run_backtest '{"state":"OR","game_type":"pick4","anchor_date":"2024-01-25","lookahead_days":7,"candidates":["3704","1234","9999"],"label":"OR smoke"}'
run_backtest '{"state":"DC","game_type":"pick3","anchor_date":"2024-01-25","lookahead_days":7,"candidates":["914","123","593"],"label":"DC smoke"}'

echo
echo "Smoke test complete."
