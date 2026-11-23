#!/usr/bin/env bash
# One command to run the whole benchmark locally and leave a receipt behind.
#
#   ./scripts/run_local.sh datasets/isic2018 40
#   ./scripts/run_local.sh datasets/ph2 200
#
# Creates .venv if missing, installs pinned requirements, runs the battery and
# writes runs/<timestamp>/{stdout.txt,receipt.json}. Exit code is 0 when no
# benign condition produced a tamper claim, 1 otherwise, 2 on a setup error.
set -euo pipefail

DATA="${1:-}"
LIMIT="${2:-40}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [ -z "$DATA" ]; then
  echo "usage: $0 <dataset dir with images/ and masks/> [limit]" >&2
  exit 2
fi
if [ ! -d "$DATA/images" ] || [ ! -d "$DATA/masks" ]; then
  echo "error: $DATA must contain images/ and masks/" >&2
  echo "hint: prepare it first with scripts/prepare_isic.py or scripts/prepare_ph2.py" >&2
  exit 2
fi

if [ ! -d .venv ]; then
  echo "creating .venv"
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="runs/${STAMP}"
mkdir -p "$OUT"

echo "run: $OUT"
set +e
python scripts/bench.py --data "$DATA" --limit "$LIMIT" --receipt "$OUT/receipt.json" \
  2>&1 | tee "$OUT/stdout.txt"
CODE="${PIPESTATUS[0]}"
set -e

echo
echo "artifacts:"
echo "  $OUT/stdout.txt     the table"
echo "  $OUT/receipt.json   command, config, commit, environment, per-condition counts"
exit "$CODE"
