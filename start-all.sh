#!/usr/bin/env bash
# AubeStatus - Demarre tous les services Aube en arriere plan
# Chaque service ecrit son log dans logs/<service>.log et son PID dans pids/<service>.pid

set -u

ROOT="$HOME/Library/Mobile Documents/com~apple~CloudDocs"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOGS="$SCRIPT_DIR/logs"
PIDS="$SCRIPT_DIR/pids"
mkdir -p "$LOGS" "$PIDS"

# Format: name | dir (relatif a ROOT) | entry script | port
# Les entries peuvent etre des fichiers Python ou des run.sh
SERVICES=(
  "aubedocs    | AubeDocs                 | docs_api.py          | 5008"
  "aubedrive   | AubeDrive/backend        | app.py               | 5011"
  "aubedata    | AubeData/backend         | app.py               | 5012"
  "aubeforms   | AubeForms                | forms_api.py         | 5015"
  "aubeslides  | AubeSlides/aubeSlides/backend | app.py          | 5013"
  "aubeagenda  | AubeAgenda               | agenda_api.py        | 5006"
  "aubecrm     | AubeCRM/backend          | app.py               | 5007"
  "aubedriver  | AubeDriver/backend       | app.py               | 5013"
  "aubenews    | AubeNews/backend         | wsgi.py              | 5014"
  "aubemusic   | AubeMusic                | app.py               | 5016"
  "aubevideo   | AubeVideo                | app.py               | 5017"
  "aubefinances| AubeFinances/backend     | app.py               | 5018"
  "aubemaps    | AubeMaps/backend         | app.py               | 5005"
)

start_service() {
  local id="$1" dir="$2" entry="$3" port="$4"
  local full_dir="$ROOT/$dir"
  local pid_file="$PIDS/$id.pid"
  local log_file="$LOGS/$id.log"

  if [ -f "$pid_file" ] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
    echo "[$id] deja demarre (PID $(cat "$pid_file"))"
    return 0
  fi

  if [ ! -d "$full_dir" ]; then
    echo "[$id] [FAIL] dossier introuvable: $full_dir"
    return 1
  fi

  if [ ! -f "$full_dir/$entry" ]; then
    echo "[$id] [FAIL] entry introuvable: $full_dir/$entry"
    return 1
  fi

  # Choisir le python: venv local si present, sinon python3 global
  local python_bin="python3"
  if [ -x "$full_dir/venv/bin/python" ]; then
    python_bin="$full_dir/venv/bin/python"
  elif [ -x "$full_dir/.venv/bin/python" ]; then
    python_bin="$full_dir/.venv/bin/python"
  elif [ -x "$full_dir/../venv/bin/python" ]; then
    python_bin="$full_dir/../venv/bin/python"
  elif [ -x "$full_dir/../.venv/bin/python" ]; then
    python_bin="$full_dir/../.venv/bin/python"
  fi

  (
    cd "$full_dir"
    export PORT="$port"
    nohup "$python_bin" "$entry" > "$log_file" 2>&1 &
    echo $! > "$pid_file"
  )

  sleep 1
  if kill -0 "$(cat "$pid_file")" 2>/dev/null; then
    echo "[$id] [OK] demarre (PID $(cat "$pid_file"), port $port) -- $python_bin"
  else
    echo "[$id] [FAIL] crash immediat, voir $log_file"
    tail -5 "$log_file" | sed 's/^/       | /'
    rm -f "$pid_file"
    return 1
  fi
}

echo "=============================================="
echo "  Demarrage des services L'Aube Etoilee"
echo "=============================================="

for line in "${SERVICES[@]}"; do
  IFS='|' read -r id dir entry port <<< "$line"
  id="$(echo "$id" | xargs)"
  dir="$(echo "$dir" | xargs)"
  entry="$(echo "$entry" | xargs)"
  port="$(echo "$port" | xargs)"
  start_service "$id" "$dir" "$entry" "$port"
done

echo ""
echo "=============================================="
echo "  Termine. Logs: $LOGS  |  PIDs: $PIDS"
echo "  Statut: http://localhost:5021"
echo "  Pour arreter tout: ./stop-all.sh"
echo "=============================================="
