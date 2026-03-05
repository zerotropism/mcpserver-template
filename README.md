# MCP server template

Un serveur MCP (Model Context Protocol) minimaliste en Python, construit avec [FastMCP](https://github.com/jlowin/fastmcp). Il implémente un gestionnaire de tâches en mémoire exposant des **outils**, des **ressources** et des **prompts** à tout client MCP compatible.

## Fonctionnalités

### Outils (`@mcp.tool`)

| Outil | Description |
|---|---|
| `add_task(title, description?)` | Ajoute une nouvelle tâche |
| `complete_task(task_id)` | Marque une tâche comme terminée |
| `delete_task(task_id)` | Supprime une tâche |
| `filter_tasks_by_status(status)` | Filtre les tâches par statut (`pending` ou `completed`) |
| `filter_tasks_by_date(date_from?, date_to?, field?)` | Filtre les tâches par plage de dates (format ISO `YYYY-MM-DD`) |
| `search_tasks(keyword)` | Recherche par mot-clé dans le titre et la description |
| `filter_tasks(status?, keyword?, date_from?, date_to?)` | Filtre combiné multi-critères |

### Ressources (`@mcp.resource`)

| URI | Description |
|---|---|
| `tasks://all` | Liste toutes les tâches (en attente et terminées) |
| `tasks://pending` | Liste uniquement les tâches en attente |
| `tasks://completed` | Liste uniquement les tâches terminées avec leur date de complétion |
| `tasks://stats` | Statistiques globales (total, taux de complétion, tâche la plus ancienne) |
| `tasks://today` | Tâches créées aujourd'hui |
| `tasks://weekly-summary` | Résumé des tâches des 7 derniers jours |

### Prompts (`@mcp.prompt`)

| Prompt | Description | Paramètres |
|---|---|---|
| `task_summary_prompt` | Analyse la liste complète et propose des actions | — |
| `priority_analysis_prompt` | Matrice urgence/importance + recommandations de priorités | — |
| `scheduling_prompt` | Génère un planning heure par heure pour la journée | `available_hours` (défaut: 8.0) |
| `weekly_review_prompt` | Bilan hebdomadaire + plan de la semaine suivante | — |

## Prérequis

- Python ≥ 3.12
- [uv](https://docs.astral.sh/uv/) (recommandé) ou pip

## Installation

```bash
git clone <repo>
cd fastmcptest

# Avec uv
uv sync

# Ou avec pip dans un venv
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

## Utilisation

### Lancer le serveur

```bash
python test_server.py
```

### Exécuter le client de test

```bash
python test_client.py
```

Le client se connecte au serveur, teste tous les outils (ajout, complétion, filtrage, recherche, suppression), lit toutes les ressources dynamiquement et affiche chaque prompt disponible.

## Structure du projet

```
fastmcptest/
├── test_server.py   # Serveur MCP (outils, ressources, prompts)
├── test_client.py   # Client de test
├── pyproject.toml   # Métadonnées et dépendances
└── README.md
```

## Dépendances

- [`fastmcp`](https://github.com/jlowin/fastmcp) ≥ 3.1.0