"""Auto-restart des services L'Aube Etoilee quand ils passent DOWN.

Contraintes:
- Cooldown minimum entre deux tentatives pour un meme service (evite thrashing)
- Plafond horaire (evite les boucles de crash permanent)
- Chaque tentative est journalisee en base (table `restarts`)
- Detection du venv dans le dossier du service pour utiliser le bon Python
"""
import logging
import os
import signal
import subprocess
import sys
import threading
import time

import db
from config import (
    AUTO_RESTART_ENABLED,
    RESTART_COOLDOWN_SECONDS,
    RESTART_MAX_PER_HOUR,
    RESTART_KILL_PORT_SQUATTER,
    RESTART_TARGETS,
    SERVICE_ROOT,
)

log = logging.getLogger("aubestatus.restarter")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR = os.path.join(SCRIPT_DIR, "logs")
PIDS_DIR = os.path.join(SCRIPT_DIR, "pids")

_lock = threading.Lock()
_last_attempt = {}      # service_id -> epoch seconds
_history = {}           # service_id -> [epoch seconds] sur la derniere heure


def _python_bin(service_dir):
    """Choisit le python du venv local si dispo, sinon le systeme."""
    candidates = [
        os.path.join(service_dir, ".venv", "bin", "python"),
        os.path.join(service_dir, "venv", "bin", "python"),
        os.path.join(os.path.dirname(service_dir), ".venv", "bin", "python"),
        os.path.join(os.path.dirname(service_dir), "venv", "bin", "python"),
    ]
    for c in candidates:
        if os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    return sys.executable or "/usr/bin/python3"


def _gate(service_id):
    """Verifie cooldown + quota horaire. Retourne (ok, raison)."""
    now = time.time()
    last = _last_attempt.get(service_id, 0)
    if now - last < RESTART_COOLDOWN_SECONDS:
        return False, f"cooldown {int(RESTART_COOLDOWN_SECONDS - (now - last))}s"
    hist = [t for t in _history.get(service_id, []) if now - t < 3600]
    _history[service_id] = hist
    if len(hist) >= RESTART_MAX_PER_HOUR:
        return False, f"limite {RESTART_MAX_PER_HOUR}/h atteinte"
    return True, None


def _kill_port_squatter(port):
    """Si RESTART_KILL_PORT_SQUATTER, tue le process qui ecoute deja sur le port."""
    try:
        out = subprocess.check_output(
            ["lsof", "-t", "-iTCP:%d" % port, "-sTCP:LISTEN"],
            stderr=subprocess.DEVNULL,
            timeout=3,
        ).decode().strip()
    except Exception:
        return False
    if not out:
        return False
    for pid_str in out.splitlines():
        try:
            pid = int(pid_str)
            if pid == os.getpid():
                continue
            os.kill(pid, signal.SIGTERM)
            log.info("Port %d squatter PID %d tue (SIGTERM)", port, pid)
        except Exception as e:
            log.debug("kill %s: %s", pid_str, e)
    time.sleep(1)
    return True


def try_restart(service_id):
    """Tente de relancer un service. Retourne (ok: bool, message: str)."""
    if not AUTO_RESTART_ENABLED:
        return False, "auto-restart desactive"
    target = RESTART_TARGETS.get(service_id)
    if not target:
        return False, "pas de cible de restart configuree"

    with _lock:
        ok, reason = _gate(service_id)
        if not ok:
            return False, reason

        full_dir = os.path.join(SERVICE_ROOT, target["dir"])
        entry = target["entry"]
        port = int(target["port"])
        entry_path = os.path.join(full_dir, entry)

        if not os.path.isdir(full_dir):
            db.log_restart(service_id, False, f"dossier introuvable: {full_dir}")
            return False, "dossier introuvable"
        if not os.path.isfile(entry_path):
            db.log_restart(service_id, False, f"entry introuvable: {entry_path}")
            return False, "entry introuvable"

        os.makedirs(LOGS_DIR, exist_ok=True)
        os.makedirs(PIDS_DIR, exist_ok=True)
        log_file = os.path.join(LOGS_DIR, f"{service_id}.log")
        pid_file = os.path.join(PIDS_DIR, f"{service_id}.pid")

        if RESTART_KILL_PORT_SQUATTER:
            _kill_port_squatter(port)

        env = os.environ.copy()
        env["PORT"] = str(port)

        py = _python_bin(full_dir)

        try:
            lf = open(log_file, "ab", buffering=0)
            proc = subprocess.Popen(
                [py, entry],
                cwd=full_dir,
                env=env,
                stdout=lf,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
                close_fds=True,
            )
        except Exception as e:
            db.log_restart(service_id, False, f"spawn error: {e}")
            return False, f"spawn error: {e}"

        try:
            with open(pid_file, "w") as f:
                f.write(str(proc.pid))
        except Exception:
            pass

        _last_attempt[service_id] = time.time()
        _history.setdefault(service_id, []).append(time.time())

        msg = f"PID {proc.pid} via {os.path.basename(py)}"
        db.log_restart(service_id, True, msg, pid=proc.pid)
        log.warning(
            "AUTO-RESTART %s — %s (port %d, dir=%s)",
            service_id, msg, port, target["dir"],
        )
        return True, msg
