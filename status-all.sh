#!/usr/bin/env bash
# Affiche un resume rapide des services (sans passer par AubeStatus)
set -u

PIDS="$(cd "$(dirname "$0")" && pwd)/pids"
mkdir -p "$PIDS"

printf "%-13s %-8s %-6s %-8s\n" "SERVICE" "PID" "PORT" "ETAT"
printf "%-13s %-8s %-6s %-8s\n" "-------" "---" "----" "----"

while IFS= read -r line; do
  [[ "$line" =~ ^# ]] && continue
  [[ -z "$line" ]] && continue
  id="$1"
  shift
done < /dev/null

declare -A PORTS=(
  [aubedocs]=5008 [aubedrive]=5011 [aubedata]=5012 [aubeforms]=5015
  [aubeslides]=5013 [aubeagenda]=5006 [aubecrm]=5007 [aubedriver]=5013
  [aubenews]=5014 [aubemusic]=5016 [aubevideo]=5017 [aubefinances]=5018
  [aubemaps]=5005
)

for id in aubedocs aubedrive aubedata aubeforms aubeslides aubeagenda \
          aubecrm aubedriver aubenews aubemusic aubevideo aubefinances aubemaps; do
  pid_file="$PIDS/$id.pid"
  port="${PORTS[$id]}"
  if [ -f "$pid_file" ] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
    pid="$(cat "$pid_file")"
    if curl -s -o /dev/null -m 2 "http://localhost:$port/" 2>/dev/null; then
      etat="[OK] UP"
    else
      etat="[WARN] running, HTTP KO"
    fi
    printf "%-13s %-8s %-6s %-8s\n" "$id" "$pid" "$port" "$etat"
  else
    printf "%-13s %-8s %-6s %-8s\n" "$id" "-" "$port" "[DOWN]"
  fi
done
