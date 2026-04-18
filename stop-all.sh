#!/usr/bin/env bash
# Arrete tous les services demarres par start-all.sh
set -u

PIDS="$(cd "$(dirname "$0")" && pwd)/pids"

if [ ! -d "$PIDS" ]; then
  echo "Aucun service a arreter (dossier pids/ absent)."
  exit 0
fi

for pid_file in "$PIDS"/*.pid; do
  [ -f "$pid_file" ] || continue
  id="$(basename "$pid_file" .pid)"
  pid="$(cat "$pid_file")"
  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null
    sleep 0.3
    if kill -0 "$pid" 2>/dev/null; then
      kill -9 "$pid" 2>/dev/null
    fi
    echo "[$id] [OK] arrete (PID $pid)"
  else
    echo "[$id] deja arrete"
  fi
  rm -f "$pid_file"
done
