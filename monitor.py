"""Thread de ping pour AubeStatus."""
import logging
import threading
import time
from urllib.parse import urlparse

import requests

from config import PING_INTERVAL_SECONDS, PING_TIMEOUT_SECONDS, SERVICES, AUTO_RESTART_ENABLED
import db
import restarter

log = logging.getLogger("aubestatus.monitor")

_last_status = {}


def ping_service(service):
    url = service["url"]
    start = time.monotonic()
    status = 0
    http_code = None
    error = None
    response_ms = None
    try:
        r = requests.get(
            url,
            timeout=PING_TIMEOUT_SECONDS,
            allow_redirects=True,
            headers={"User-Agent": "AubeStatus/1.0"},
        )
        http_code = r.status_code
        response_ms = int((time.monotonic() - start) * 1000)
        if 200 <= r.status_code < 500:
            status = 1
        else:
            status = 0
            error = f"HTTP {r.status_code}"
    except requests.exceptions.ConnectTimeout:
        error = "Connect timeout"
    except requests.exceptions.ReadTimeout:
        error = "Read timeout"
    except requests.exceptions.ConnectionError as e:
        error = f"Connection refused ({urlparse(url).netloc})"
        log.debug("ConnectionError %s: %s", service["id"], e)
    except Exception as e:
        error = f"{type(e).__name__}: {e}"

    db.insert_check(service["id"], status, http_code, response_ms, error)

    prev = _last_status.get(service["id"])
    if status == 0 and prev != 0:
        db.open_incident(service["id"], error or "Unknown")
        log.warning("INCIDENT ouvert pour %s: %s", service["id"], error)
    elif status == 1 and prev == 0:
        db.close_open_incident(service["id"])
        log.info("INCIDENT resolu pour %s", service["id"])
    _last_status[service["id"]] = status

    # Auto-restart si le service est DOWN. Le gate interne de restarter impose
    # cooldown et quota horaire -- on peut donc l'appeler a chaque tick.
    if status == 0 and AUTO_RESTART_ENABLED:
        ok, reason = restarter.try_restart(service["id"])
        if ok:
            log.warning("Auto-restart %s declenche: %s", service["id"], reason)
        else:
            log.debug("Auto-restart %s ignore: %s", service["id"], reason)


def run_once():
    threads = []
    for svc in SERVICES:
        t = threading.Thread(target=ping_service, args=(svc,), daemon=True)
        t.start()
        threads.append(t)
    for t in threads:
        t.join(timeout=PING_TIMEOUT_SECONDS + 2)


def _loop():
    purge_every = 3600
    last_purge = 0
    while True:
        try:
            run_once()
            now = time.time()
            if now - last_purge > purge_every:
                db.purge_old()
                last_purge = now
        except Exception as e:
            log.exception("Erreur boucle monitor: %s", e)
        time.sleep(PING_INTERVAL_SECONDS)


def start_background():
    for svc in SERVICES:
        latest = db.latest_status(svc["id"])
        if latest:
            _last_status[svc["id"]] = latest["status"]
    t = threading.Thread(target=_loop, daemon=True, name="aubestatus-monitor")
    t.start()
    log.info("Monitor lance pour %d services (intervalle %ds)", len(SERVICES), PING_INTERVAL_SECONDS)
    return t
