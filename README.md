# FastMCP — Task Tracker Template

Serveur MCP (Model Context Protocol) construit avec [FastMCP](https://github.com/jlowin/fastmcp),
illustrant l'injection de persistance : un seul serveur, plusieurs backends de stockage
interchangeables derrière un `Protocol`.

## Démarrage rapide

```bash
uv sync
uv run pytest                      # la suite tourne sur les deux backends
OLLAMA_MODEL=<modèle> uv run mcpserver-template-agent
```

## Structure

```
src/mcpserver_template/
├── models.py             # Task, TaskFilter, TaskStats (pydantic)
├── repository.py         # Protocol TaskRepository + TaskNotFoundError
├── repositories/
│   ├── memory.py         # stockage en mémoire, perdu au redémarrage
│   └── sqlite.py         # stockage persistant dans un fichier
├── server.py             # outils, ressources, prompts ; repository injecté
└── ollama_client.py      # chat interactif avec un LLM local
tests/
├── test_models.py        # logique de filtrage, sans stockage
├── test_repositories.py  # même suite, paramétrée sur chaque backend
└── test_server.py        # via le Client FastMCP in-memory
```

Le serveur ne connaît que le `Protocol`. Ajouter un backend (Postgres, Redis…) consiste à
écrire une classe implémentant les sept méthodes et à l'ajouter au registre `BACKENDS` :
la suite de tests s'y applique sans être modifiée, en ajoutant une valeur au paramètre
de la fixture.

## Choix du backend

`TASK_BACKEND` sélectionne la persistance au lancement, `DB_PATH` le fichier SQLite.

```bash
TASK_BACKEND=memory  uv run mcpserver-template                # défaut
TASK_BACKEND=sqlite  DB_PATH=tasks.db uv run mcpserver-template
```

| | `memory` | `sqlite` |
|---|---|---|
| Persistance | perdue au redémarrage | fichier `DB_PATH` |
| Filtrage | en Python, via `TaskFilter.matches()` | traduit en SQL paramétré |
| Usage | tests, démonstration | cas réels |

## API MCP

### Outils

| Outil | Description |
|---|---|
| `add_task(title, description?)` | Ajoute une tâche |
| `complete_task(task_id)` | Marque une tâche comme terminée (idempotent) |
| `complete_tasks(task_ids)` | Marque plusieurs tâches comme terminées |
| `delete_task(task_id)` | Supprime une tâche et la retourne |
| `filter_tasks(task_filter)` | Filtre unique multi-critères |

`TaskFilter` regroupe tous les critères, tous optionnels et combinés en ET :
`status`, `keyword` (titre et description, insensible à la casse), `date_from`, `date_to`
(bornes incluses, format ISO `YYYY-MM-DD`) et `date_field` (`created_at` ou `completed_at`).
Un filtre vide retourne tout ; aucune correspondance retourne une liste vide.

```json
{"task_filter": {"status": "pending", "keyword": "rapport"}}
```

Les erreurs sont levées en exceptions et remontées comme erreurs MCP : un identifiant
inconnu déclenche `TaskNotFoundError`, un critère inconnu une erreur de validation.
Aucun outil ne retourne de dictionnaire `{"error": ...}`.

### Ressources

| URI | Description |
|---|---|
| `tasks://all` | Toutes les tâches |
| `tasks://pending` | Tâches en attente |
| `tasks://completed` | Tâches terminées |
| `tasks://stats` | Compteurs, taux d'achèvement, plus ancienne tâche en attente |
| `tasks://today` | Tâches créées aujourd'hui |
| `tasks://weekly-summary` | Résumé des 7 derniers jours |

### Prompts

| Prompt | Description | Paramètres |
|---|---|---|
| `task_summary_prompt` | Synthèse de la liste et urgences | — |
| `priority_analysis_prompt` | Classement des tâches en attente | — |
| `scheduling_prompt` | Planning sur le temps disponible | `available_hours` (défaut : 8.0) |
| `weekly_review_prompt` | Bilan hebdomadaire chiffré | — |

Chaque prompt désigne explicitement la ressource à lire et interdit d'inventer des tâches.

## Chat interactif avec un LLM local

```
Vous → Ollama (LLM local) → tool_calls → FastMCP Client → serveur MCP
                          ←  résultat  ←
```

```bash
brew install ollama
ollama pull <modèle>
OLLAMA_MODEL=<modèle> TASK_BACKEND=sqlite DB_PATH=tasks.db uv run mcpserver-template-agent
```

```
Vous : ajoute deux tâches : préparer le rapport et faire la démo
  🔧 Appel outil : add_task({'title': 'préparer le rapport'})
  🔧 Appel outil : add_task({'title': 'faire la démo'})

Assistant : J'ai ajouté les deux tâches à votre liste.

Vous : quelles tâches sont en attente ?
  🔧 Appel outil : filter_tasks({'task_filter': {'status': 'pending'}})

Assistant : Vous avez 2 tâches en attente : préparer le rapport, faire la démo.
```

### Modèle requis

`filter_tasks` attend un objet imbriqué. Les petits modèles n'y parviennent pas :
`llama3.2` (3B) invente des champs, puis cesse d'émettre des appels d'outils et se met
à imprimer du JSON dans sa réponse. Un modèle de 7B ou plus, entraîné aux appels d'outils,
produit l'objet correctement dès le premier essai.

### Robustesse face aux modèles imparfaits

| Fonction | Problème corrigé |
|---|---|
| `normalize_args` | Le modèle encode les valeurs comme `{"type": "string", "value": "..."}` au lieu d'une chaîne |
| `sanitize_args` | Le modèle hallucine des paramètres absents du schéma |

### Variables d'environnement et transport stdio

Le SDK MCP ne transmet pas l'environnement au sous-processus serveur : il n'hérite que
d'une liste blanche (`HOME`, `LOGNAME`, `PATH`, `SHELL`, `TERM`, `USER`). Toute variable
de configuration doit être passée explicitement au transport, ce que fait `server_env()` :

```python
StdioTransport("uv", ["run", "mcpserver-template"], env=server_env())
```

Sans cela, `TASK_BACKEND` et `DB_PATH` sont silencieusement ignorés et le serveur retombe
sur son backend par défaut.

## Développement

```bash
uv sync --all-groups
uv run ruff check . && uv run ruff format --check .
uv run pytest
```

Les tests n'ont besoin ni d'Ollama ni d'un sous-processus : `create_server(repository)`
reçoit un repository de test et le `Client` FastMCP s'y connecte en mémoire.

## Prérequis

- Python ≥ 3.12
- [uv](https://docs.astral.sh/uv/)
- [Ollama](https://ollama.com/) pour le chat interactif uniquement
