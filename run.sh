#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

export AUBESTATUS_NO_MONITOR="${AUBESTATUS_NO_MONITOR:-0}"

if [ "${1:-dev}" = "prod" ]; then
  exec gunicorn -w 2 -b 0.0.0.0:5021 --access-logfile - app:app
else
  exec python app.py
fi
