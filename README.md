# FastMCP — Task Tracker Template

Un repo pédagogique illustrant deux approches de persistance pour un serveur
MCP (Model Context Protocol) construit avec [FastMCP](https://github.com/jlowin/fastmcp).

## Structure du repo

```
fastmcptest/
├── list-based-memory/     # Version 1 — stockage en liste Python (in-memory)
│   ├── server.py
│   └── client.py
├── sqlite-based-memory/   # Version 2 — stockage persistant avec SQLite
│   ├── server.py
│   ├── client.py
│   └── .env               # à créer (voir ci-dessous)
├── pyproject.toml
└── README.md
```

## Versions

### 📋 `list-based-memory` — Stockage en mémoire

Stockage des tâches dans une liste Python. Simple, sans dépendances, mais
les données sont **perdues à chaque redémarrage**. Idéal pour comprendre
les bases de FastMCP.

```bash
cd list-based-memory
python server.py
# dans un autre terminal
python client.py
```

### 🗄️ `sqlite-based-memory` — Stockage SQLite

Stockage persistant dans un fichier `tasks.db`. Les données survivent aux
redémarrages. Même API MCP, seule la couche de persistance change.

```bash
cd sqlite-based-memory

# Créer le fichier .env
echo "DB_PATH=tasks.db" > .env

# Lancer le serveur
python server.py
# dans un autre terminal
python client.py
```

## Fonctionnalités (communes aux deux versions)

### Outils (`@mcp.tool`)

| Outil | Description |
|---|---|
| `add_task(title, description?)` | Ajoute une nouvelle tâche |
| `complete_task(task_id)` | Marque une tâche comme terminée |
| `delete_task(task_id)` | Supprime une tâche |
| `filter_tasks_by_status(status)` | Filtre par statut (`pending` / `completed`) |
| `filter_tasks_by_date(date_from?, date_to?, field?)` | Filtre par plage de dates ISO `YYYY-MM-DD` |
| `search_tasks(keyword)` | Recherche dans titre et description |
| `filter_tasks(status?, keyword?, date_from?, date_to?)` | Filtre combiné multi-critères |

### Ressources (`@mcp.resource`)

| URI | Description |
|---|---|
| `tasks://all` | Toutes les tâches |
| `tasks://pending` | Tâches en attente |
| `tasks://completed` | Tâches terminées |
| `tasks://stats` | Statistiques globales |
| `tasks://today` | Tâches créées aujourd'hui |
| `tasks://weekly-summary` | Résumé des 7 derniers jours |

### Prompts (`@mcp.prompt`)

| Prompt | Description | Paramètres |
|---|---|---|
| `task_summary_prompt` | Analyse et actions suggérées | — |
| `priority_analysis_prompt` | Matrice urgence/importance | — |
| `scheduling_prompt` | Planning heure par heure | `available_hours` (défaut: 8.0) |
| `weekly_review_prompt` | Bilan hebdomadaire | — |

## Prérequis

- Python ≥ 3.12
- [uv](https://docs.astral.sh/uv/)

## Installation

```bash
git clone <repo>
cd fastmcptest
uv sync
```

## Différences entre les deux versions

| | `list-based-memory` | `sqlite-based-memory` |
|---|---|---|
| **Persistance** | ❌ Perdue au redémarrage | ✅ Fichier `tasks.db` |
| **Dépendances** | `fastmcp` | `fastmcp` + `python-dotenv` |
| **Configuration** | Aucune | `.env` avec `DB_PATH` |
| **Complexité** | ⭐ Débutant | ⭐⭐ Intermédiaire |
| **Usage** | Apprendre MCP | Cas réels |