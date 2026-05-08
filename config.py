"""Configuration AubeStatus - Liste des services a monitorer.

Les ports correspondent aux valeurs REELLES trouvees dans le code de chaque service.
"""
import os

PORT = 5021
HOST = "0.0.0.0"
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aubestatus.db")
PING_INTERVAL_SECONDS = 60
PING_TIMEOUT_SECONDS = 10
RETENTION_DAYS = 90

# --- Auto-restart ---
AUTO_RESTART_ENABLED = True
RESTART_COOLDOWN_SECONDS = 120          # attente minimale entre 2 tentatives pour un meme service
RESTART_MAX_PER_HOUR = 5                # au-dela, on arrete d'essayer (cassage definitif)
RESTART_KILL_PORT_SQUATTER = False      # si True, tue le process qui occupe deja le port avant restart

# Cible de redemarrage par service. Les cles correspondent aux IDs de SERVICES.
# Les services sans cible (Aube Portail, L'Aube Mail statique, AubeFiches vide) ne sont pas auto-restartes.
SERVICE_ROOT = os.path.expanduser("~/Library/Mobile Documents/com~apple~CloudDocs")
RESTART_TARGETS = {
    "aubedocs":     {"dir": "AubeDocs",                  "entry": "docs_api.py",   "port": 5008},
    "aubedrive":    {"dir": "AubeDrive/backend",         "entry": "app.py",        "port": 5011},
    "aubedata":     {"dir": "AubeData/backend",          "entry": "app.py",        "port": 5012},
    "aubeforms":    {"dir": "AubeForms",                 "entry": "forms_api.py",  "port": 5015},
    "aubeslides":   {"dir": "AubeSlides/aubeSlides/backend", "entry": "app.py",    "port": 5013},
    "aubeagenda":   {"dir": "AubeAgenda",                "entry": "agenda_api.py", "port": 5006},
    "aubecrm":      {"dir": "AubeCRM/backend",           "entry": "app.py",        "port": 5007},
    "aubedriver":   {"dir": "AubeDriver/backend",        "entry": "app.py",        "port": 5013},
    "aubenews":     {"dir": "AubeNews/backend",          "entry": "wsgi.py",       "port": 5014},
    "aubemusic":    {"dir": "AubeMusic",                 "entry": "app.py",        "port": 5016},
    "aubevideo":    {"dir": "AubeVideo",                 "entry": "app.py",        "port": 5017},
    "aubefinances": {"dir": "AubeFinances/backend",      "entry": "app.py",        "port": 5018},
    "aubemaps":     {"dir": "AubeMaps/backend",          "entry": "app.py",        "port": 5005},
    "aubepilot":    {"dir": "AubePilot",                 "entry": "app.py",        "port": 5034},
}

SERVICES = [
    {
        "id": "aubedocs",
        "name": "AubeDocs",
        "description": "Editeur de documents",
        "url": "http://localhost:5008/",
        "public_url": "https://docs.aubeetoilee.com",
        "category": "Bureautique",
    },
    {
        "id": "aubedrive",
        "name": "AubeDrive",
        "description": "Stockage de fichiers cloud",
        "url": "http://localhost:5011/",
        "public_url": "https://drive.aubeetoilee.com",
        "category": "Bureautique",
    },
    {
        "id": "aubedata",
        "name": "AubeData",
        "description": "Tableurs et visualisation",
        "url": "http://localhost:5012/",
        "public_url": "https://data.aubeetoilee.com",
        "category": "Bureautique",
    },
    {
        "id": "aubeforms",
        "name": "AubeForms",
        "description": "Formulaires et sondages",
        "url": "http://localhost:5015/",
        "public_url": "https://forms.aubeetoilee.com",
        "category": "Bureautique",
    },
    {
        "id": "aubeslides",
        "name": "AubeSlides",
        "description": "Presentations",
        "url": "http://localhost:5013/",
        "public_url": "https://slides.aubeetoilee.com",
        "category": "Bureautique",
    },
    {
        "id": "aubeagenda",
        "name": "AubeAgenda",
        "description": "Calendrier et evenements",
        "url": "http://localhost:5006/",
        "public_url": "https://agenda.aubeetoilee.com",
        "category": "Bureautique",
    },
    {
        "id": "aubefiches",
        "name": "AubeFiches",
        "description": "Fiches de revision",
        "url": "http://localhost:5020/",
        "public_url": "https://fiches.aubeetoilee.com",
        "category": "Bureautique",
    },
    {
        "id": "aubecrm",
        "name": "AubeCRM",
        "description": "Gestion de prospects",
        "url": "http://localhost:5007/",
        "public_url": "https://crm.aubeetoilee.com",
        "category": "Business",
    },
    {
        "id": "aubefinances",
        "name": "AubeFinances",
        "description": "Marche boursier",
        "url": "http://localhost:5018/",
        "public_url": "https://finances.aubeetoilee.com",
        "category": "Business",
    },
    {
        "id": "aubedriver",
        "name": "AubeDriver",
        "description": "Ride-hailing",
        "url": "http://localhost:5013/",
        "public_url": "https://driver.aubeetoilee.com",
        "category": "Mobilite",
    },
    {
        "id": "aubemaps",
        "name": "AubeMaps",
        "description": "Cartographie",
        "url": "http://localhost:5005/",
        "public_url": "https://maps.aubeetoilee.com",
        "category": "Mobilite",
    },
    {
        "id": "aubepilot",
        "name": "Aube Pilot",
        "description": "Marketplace pilotes de drone",
        "url": "http://localhost:5034/api/stats",
        "public_url": "https://pilot.aubeetoilee.com",
        "category": "Mobilite",
    },
    {
        "id": "aubenews",
        "name": "AubeNews",
        "description": "Agregation de news francophones",
        "url": "http://localhost:5014/",
        "public_url": "https://news.aubeetoilee.com",
        "category": "Media",
    },
    {
        "id": "aubemusic",
        "name": "AubeMusic",
        "description": "Streaming musical",
        "url": "http://localhost:5016/",
        "public_url": "https://music.aubeetoilee.com",
        "category": "Media",
    },
    {
        "id": "aubevideo",
        "name": "AubeVideo",
        "description": "Plateforme video",
        "url": "http://localhost:5017/",
        "public_url": "https://video.aubeetoilee.com",
        "category": "Media",
    },
    {
        "id": "laubemail",
        "name": "L'Aube Mail",
        "description": "Messagerie",
        "url": "http://localhost:5019/",
        "public_url": "https://mail.aubeetoilee.com",
        "category": "Communication",
    },
    {
        "id": "aubesite",
        "name": "Aube Portail",
        "description": "Portail principal aubeetoilee.com",
        "url": "https://aubeetoilee.com",
        "public_url": "https://aubeetoilee.com",
        "category": "Portail",
    },
]
