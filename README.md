# MCP server template

Un serveur MCP (Model Context Protocol) minimaliste en Python, construit avec [FastMCP](https://github.com/jlowin/fastmcp). Il implémente un gestionnaire de tâches en mémoire exposant des **outils**, des **ressources** et un **prompt** à tout client MCP compatible.

## Fonctionnalités

### Outils (`@mcp.tool`)

| Outil | Description |
|---|---|
| `add_task(title, description?)` | Ajoute une nouvelle tâche |
| `complete_task(task_id)` | Marque une tâche comme terminée |
| `delete_task(task_id)` | Supprime une tâche |

### Ressources (`@mcp.resource`)

| URI | Description |
|---|---|
| `tasks://all` | Liste toutes les tâches (en attente et terminées) |
| `tasks://pending` | Liste uniquement les tâches en attente |

### Prompt (`@mcp.prompt`)

- `task_summary_prompt` — génère un prompt demandant à l'IA d'analyser la liste des tâches et de proposer des actions.

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

Le client liste les outils disponibles, ajoute une tâche et affiche la ressource `tasks://all`.

## Structure du projet

```
fastmcptest/
├── test_server.py   # Serveur MCP (outils, ressources, prompt)
├── test_client.py   # Client de test
├── pyproject.toml   # Métadonnées et dépendances
└── README.md
```

## Dépendances

- [`fastmcp`](https://github.com/jlowin/fastmcp) ≥ 3.1.0
