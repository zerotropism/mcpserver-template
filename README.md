# FastMCP — Task Tracker Template

Un repo pédagogique illustrant deux approches de persistance pour un serveur
MCP (Model Context Protocol) construit avec [FastMCP](https://github.com/jlowin/fastmcp).

## Structure du repo

```
fastmcptest/
├── list-based-memory/     # Version 1 — stockage en liste Python (in-memory)
│   ├── server.py
│   ├── client.py          # Client de test automatisé
│   └── ollama_client.py   # Chat interactif avec un LLM local via Ollama
├── sqlite-based-memory/   # Version 2 — stockage persistant avec SQLite
│   ├── server.py
│   ├── client.py          # Client de test automatisé
│   ├── ollama_client.py   # Chat interactif avec un LLM local via Ollama
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
python client.py         # tests automatisés
python ollama_client.py  # chat interactif (nécessite Ollama)
```

### 🗄️ `sqlite-based-memory` — Stockage SQLite

Stockage persistant dans un fichier `tasks.db`. Les données survivent aux
redémarrages. Même API MCP, seule la couche de persistance change.

```bash
cd sqlite-based-memory

# Créer le fichier .env
echo "DB_PATH=tasks.db" > .env

python client.py         # tests automatisés
python ollama_client.py  # chat interactif (nécessite Ollama)
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

## Chat interactif avec un LLM local (`ollama_client.py`)

`ollama_client.py` connecte un modèle Ollama au serveur MCP pour interagir
en langage naturel avec le gestionnaire de tâches.

```
Vous → Ollama (LLM local) → tool_calls → FastMCP Client → server.py
                          ←  résultat  ←
```

### Prérequis Ollama

```bash
brew install ollama
ollama pull <model>
uv add ollama
```

### Exemple

```
Vous : Ajoute une tâche "Préparer la démo" avec la description "Slides pour vendredi"
  🔧 Appel outil : add_task({'title': 'Préparer la démo', 'description': 'Slides pour vendredi'})

Assistant : La tâche "Préparer la démo" a été ajoutée avec l'ID 1.

Vous : Quelles sont mes tâches en attente ?
  🔧 Appel outil : filter_tasks_by_status({'status': 'pending'})

Assistant : Tu as 1 tâche en attente : [1] Préparer la démo.
```

### Robustesse face aux modèles imparfaits

`ollama_client.py` inclut deux garde-fous pour les modèles à tool calling fragile (ex: `llama3.2`) :

| Fonction | Problème corrigé |
|---|---|
| `normalize_args` | Le modèle encode les valeurs comme `{"type": "string", "value": "..."}` au lieu d'une chaîne |
| `sanitize_args` | Le modèle hallucine des paramètres inexistants dans le schéma |

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