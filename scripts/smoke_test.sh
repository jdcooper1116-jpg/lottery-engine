#!/usr/bin/env bash
set -e

source .venv/bin/activate

echo "== Latest =="
python -m cli.query latest --state GA --game pick3 --n 5
python -m cli.query latest --state TX --game pick4 --n 5
python -m cli.query latest --state OR --game pick4 --n 5
python -m cli.query latest --state DC --game pick3 --n 5

echo "== Coverage =="
python -m cli.coverage_report --state GA --game pick3 --start 2024-01-25 --end 2024-02-01 --show-gaps --limit 20

echo "== Dry-run validation =="
python -m cli.validate_state --state WA --game pick4 --month 2024-01 --source lottery.net --dry-run
python -m cli.validate_state --state MA --game pick4 --month 2024-01 --source lottery.net --dry-run

echo "== API smoke =="
curl -s -X POST http://127.0.0.1:8000/backtest \
  -H "Content-Type: application/json" \
  -d '{"state":"GA","game_type":"pick3","anchor_date":"2024-01-25","lookahead_days":7,"candidates":["297","716","999"],"label":"GA smoke"}'

curl -s -X POST http://127.0.0.1:8000/backtest \
  -H "Content-Type: application/json" \
  -d '{"state":"TX","game_type":"pick4","anchor_date":"2024-01-25","lookahead_days":7,"candidates":["3266","7036","1234"],"label":"TX smoke"}'

curl -s -X POST http://127.0.0.1:8000/backtest \
  -H "Content-Type: application/json" \
  -d '{"state":"OR","game_type":"pick4","anchor_date":"2024-01-25","lookahead_days":7,"candidates":["3704","1234","9999"],"label":"OR smoke"}'

curl -s -X POST http://127.0.0.1:8000/backtest \
  -H "Content-Type: application/json" \
  -d '{"state":"DC","game_type":"pick3","anchor_date":"2024-01-25","lookahead_days":7,"candidates":["914","123","593"],"label":"DC smoke"}'

echo
echo "Smoke test complete."
