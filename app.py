"""AubeStatus - Page de statut publique pour L'Aube Etoilee."""
import logging
import os
from datetime import datetime, timedelta

from flask import Flask, jsonify, render_template, abort

import db
import monitor
from config import HOST, PORT, SERVICES, RETENTION_DAYS, AUTO_RESTART_ENABLED, RESTART_TARGETS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("aubestatus")

app = Flask(__name__)


SERVICES_BY_ID = {s["id"]: s for s in SERVICES}


def _service_payload(service):
    latest = db.latest_status(service["id"])
    history = db.history_days(service["id"], days=90)
    uptime = db.uptime_percent(service["id"], days=90)

    history_map = {r["day"]: r for r in history}
    today = datetime.utcnow().date()
    days = []
    for i in range(89, -1, -1):
        d = (today - timedelta(days=i)).isoformat()
        row = history_map.get(d)
        if row and row["total"] > 0:
            pct = round((row["up"] / row["total"]) * 100, 2)
            state = "up" if pct >= 99 else ("degraded" if pct >= 70 else "down")
        else:
            pct = None
            state = "unknown"
        days.append({"day": d, "uptime": pct, "state": state})

    if latest is None:
        current = "unknown"
    elif latest["status"] == 1:
        current = "up"
    else:
        current = "down"

    initials = "".join(w[0] for w in service["name"].replace("'", " ").split()[:2]).upper()
    restart_last = db.last_restart(service["id"])
    return {
        "id": service["id"],
        "name": service["name"],
        "description": service["description"],
        "url": service["url"],
        "public_url": service["public_url"],
        "category": service["category"],
        "initials": initials,
        "auto_restart": service["id"] in RESTART_TARGETS,
        "restart_count_24h": db.restart_count_24h(service["id"]),
        "last_restart": restart_last,
        "status": current,
        "uptime_90d": uptime,
        "latency_ms": latest["response_ms"] if latest else None,
        "http_code": latest["http_code"] if latest else None,
        "last_error": latest["error"] if latest else None,
        "last_check": latest["ts"] if latest else None,
        "history": days,
    }


@app.route("/")
def index():
    services_data = [_service_payload(s) for s in SERVICES]
    down = sum(1 for s in services_data if s["status"] == "down")
    unknown = sum(1 for s in services_data if s["status"] == "unknown")
    up = len(services_data) - down - unknown

    if down == 0 and unknown == 0:
        overall = ("operational", "Tous les systemes sont operationnels")
    elif down == 0:
        overall = ("partial", "Certains services n'ont pas encore ete verifies")
    elif down == len(services_data):
        overall = ("major", "Panne majeure en cours")
    else:
        overall = ("partial", "Incident partiel en cours")

    categories = {}
    for s in services_data:
        categories.setdefault(s["category"], []).append(s)

    incidents = db.recent_incidents(limit=10)
    for inc in incidents:
        svc = SERVICES_BY_ID.get(inc["service_id"])
        inc["service_name"] = svc["name"] if svc else inc["service_id"]

    uptimes = [s["uptime_90d"] for s in services_data if s["uptime_90d"] is not None]
    global_uptime = round(sum(uptimes) / len(uptimes), 2) if uptimes else None
    latencies = [s["latency_ms"] for s in services_data if s["latency_ms"] is not None]
    avg_latency = round(sum(latencies) / len(latencies)) if latencies else None
    ongoing_incidents = sum(1 for i in incidents if not i.get("ended_at"))
    total_restarts_24h = sum(s["restart_count_24h"] for s in services_data)

    return render_template(
        "index.html",
        services=services_data,
        categories=categories,
        overall_status=overall[0],
        overall_label=overall[1],
        counts={"up": up, "down": down, "unknown": unknown, "total": len(services_data)},
        incidents=incidents,
        global_uptime=global_uptime,
        avg_latency=avg_latency,
        ongoing_incidents=ongoing_incidents,
        total_restarts_24h=total_restarts_24h,
        auto_restart_enabled=AUTO_RESTART_ENABLED,
        retention_days=RETENTION_DAYS,
        now=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    )


@app.route("/service/<service_id>")
def service_detail(service_id):
    service = SERVICES_BY_ID.get(service_id)
    if not service:
        abort(404)
    payload = _service_payload(service)
    recent = db.recent_checks(service_id, limit=60)
    restarts = db.recent_restarts(service_id, limit=20)
    return render_template(
        "service.html",
        service=payload,
        recent=recent,
        restarts=restarts,
        now=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    )


@app.route("/api")
def api_docs():
    sample_id = SERVICES[0]["id"] if SERVICES else "aubedocs"
    endpoints = [
        {
            "method": "GET",
            "path": "/api/status",
            "title": "Statut global",
            "description": "Retourne l'etat courant de tous les services monitores + historique 90 jours.",
            "response_type": "application/json",
            "example_fields": [
                "generated_at", "services[].id", "services[].name",
                "services[].status", "services[].uptime_90d", "services[].history[]",
            ],
        },
        {
            "method": "GET",
            "path": "/api/service/" + sample_id,
            "title": "Detail d'un service",
            "description": "Meme payload que /api/status pour un seul service + les 60 dernieres verifications.",
            "response_type": "application/json",
            "example_fields": ["status", "latency_ms", "http_code", "history[]", "recent[]"],
        },
        {
            "method": "GET",
            "path": "/api/health",
            "title": "Ping interne",
            "description": "Health check de AubeStatus lui-meme. Utile pour supervision tierce.",
            "response_type": "application/json",
            "example_fields": ["status", "service", "services_monitored"],
        },
        {
            "method": "GET",
            "path": "/badge/" + sample_id + ".svg",
            "title": "Badge SVG",
            "description": "Image SVG auto-actualisee pour README ou landing. Trois etats: operationnel / indisponible / inconnu.",
            "response_type": "image/svg+xml",
            "example_fields": [],
        },
    ]
    return render_template(
        "api.html",
        endpoints=endpoints,
        sample_id=sample_id,
        services=SERVICES,
        now=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    )


@app.route("/api/status")
def api_status():
    return jsonify({
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "services": [_service_payload(s) for s in SERVICES],
    })


@app.route("/api/service/<service_id>")
def api_service(service_id):
    service = SERVICES_BY_ID.get(service_id)
    if not service:
        return jsonify({"error": "unknown service"}), 404
    payload = _service_payload(service)
    payload["recent"] = db.recent_checks(service_id, limit=60)
    return jsonify(payload)


@app.route("/api/health")
def api_health():
    return jsonify({"status": "ok", "service": "AubeStatus", "services_monitored": len(SERVICES)})


@app.route("/badge/<service_id>.svg")
def badge(service_id):
    service = SERVICES_BY_ID.get(service_id)
    if not service:
        abort(404)
    latest = db.latest_status(service_id)
    if latest is None:
        label, color = "inconnu", "#9ca3af"
    elif latest["status"] == 1:
        label, color = "operationnel", "#16a34a"
    else:
        label, color = "indisponible", "#dc2626"
    name = service["name"]
    label_w = max(60, len(name) * 7 + 10)
    status_w = max(80, len(label) * 7 + 10)
    total_w = label_w + status_w
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{total_w}" height="20">
<rect width="{label_w}" height="20" fill="#555"/>
<rect x="{label_w}" width="{status_w}" height="20" fill="{color}"/>
<g fill="#fff" text-anchor="middle" font-family="Verdana,sans-serif" font-size="11">
<text x="{label_w/2}" y="14">{name}</text>
<text x="{label_w + status_w/2}" y="14">{label}</text>
</g></svg>"""
    from flask import Response
    return Response(svg, mimetype="image/svg+xml", headers={"Cache-Control": "no-cache"})


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


def _boot():
    db.init_db()
    if os.environ.get("AUBESTATUS_NO_MONITOR") != "1":
        monitor.start_background()


_boot()


if __name__ == "__main__":
    log.info("AubeStatus demarre sur %s:%d", HOST, PORT)
    app.run(host=HOST, port=PORT, debug=False, use_reloader=False)
