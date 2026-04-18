# AubeStatus

Page de statut publique pour la suite **L'Aube Étoilée**.

- Ping HTTP des services toutes les **60s**
- Historique **90 jours** (graphiques à barres)
- Détection et journalisation automatique des **incidents**
- Page publique + **API JSON** + **badges SVG**
- Stack minimaliste : Flask + SQLite

## Démarrage rapide

```bash
./run.sh          # développement (port 5021)
./run.sh prod     # production via gunicorn
```

Ensuite : http://localhost:5021

## Déploiement serveur

```bash
sudo cp aubestatus.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now aubestatus
```

Nginx (status.aubeetoilee.com) :
```nginx
location / {
    proxy_pass http://127.0.0.1:5021;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

## Configuration des services

Édite `config.py` pour ajouter / modifier la liste `SERVICES`. Chaque entrée :

```python
{
  "id": "aubexyz",
  "name": "AubeXYZ",
  "description": "...",
  "url": "http://localhost:5099/",
  "public_url": "https://xyz.aubeetoilee.com",
  "category": "Bureautique",
}
```

## API

| Endpoint | Description |
|---|---|
| `GET /api/status` | Statut global de tous les services |
| `GET /api/service/<id>` | Détail d'un service + 60 derniers checks |
| `GET /api/health` | Ping de l'app AubeStatus elle-même |
| `GET /badge/<id>.svg` | Badge SVG (README) |

## Rétention

Par défaut **90 jours**. Les anciens checks et daily_stats sont purgés automatiquement toutes les heures.

## Alternatives à considérer

Si tu veux plus de features sans coder : [Uptime Kuma](https://github.com/louislam/uptime-kuma) (Node) ou [Gatus](https://github.com/TwiN/gatus) (Go).
AubeStatus reste volontairement minimal et 100% Python — cohérent avec le reste de la suite Aube.
