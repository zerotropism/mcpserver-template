"""SQLite backend: the filter is translated to parameterised SQL, never string-formatted."""

import sqlite3
from pathlib import Path

from mcpserver_template.models import Task, TaskFilter, TaskStats, TaskStatus, utcnow
from mcpserver_template.repository import TaskNotFoundError

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    title        TEXT NOT NULL,
    description  TEXT NOT NULL DEFAULT '',
    status       TEXT NOT NULL DEFAULT 'pending',
    created_at   TEXT NOT NULL,
    completed_at TEXT
)
"""

# Whitelist mapping the model's date_field to a real column name. The value is a
# literal from this dict, never caller input, which is what makes the f-string safe.
DATE_COLUMNS = {"created_at": "created_at", "completed_at": "completed_at"}


class SqliteTaskRepository:
    def __init__(self, db_path: Path | str = "tasks.db") -> None:
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        """Explicit, called from __init__ rather than at import time."""
        with self._conn:
            self._conn.execute(SCHEMA)

    @staticmethod
    def _to_task(row: sqlite3.Row) -> Task:
        return Task.model_validate(dict(row))

    def add(self, title: str, description: str = "") -> Task:
        Task(id=0, title=title, description=description, created_at=utcnow())  # validate early
        with self._conn:
            cur = self._conn.execute(
                "INSERT INTO tasks (title, description, status, created_at) VALUES (?, ?, ?, ?)",
                (title, description, TaskStatus.PENDING.value, utcnow().isoformat()),
            )
        return self.get(cur.lastrowid)

    def get(self, task_id: int) -> Task:
        row = self._conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row is None:
            raise TaskNotFoundError(task_id)
        return self._to_task(row)

    def complete(self, task_id: int) -> Task:
        task = self.get(task_id)
        if task.status is TaskStatus.COMPLETED:
            return task
        with self._conn:
            self._conn.execute(
                "UPDATE tasks SET status = ?, completed_at = ? WHERE id = ?",
                (TaskStatus.COMPLETED.value, utcnow().isoformat(), task_id),
            )
        return self.get(task_id)

    def delete(self, task_id: int) -> Task:
        task = self.get(task_id)
        with self._conn:
            self._conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        return task

    def filter(self, task_filter: TaskFilter) -> list[Task]:
        clauses: list[str] = []
        params: list[str] = []

        if task_filter.status is not None:
            clauses.append("status = ?")
            params.append(task_filter.status.value)

        if task_filter.keyword:
            clauses.append("(LOWER(title) LIKE ? OR LOWER(description) LIKE ?)")
            pattern = f"%{task_filter.keyword.lower()}%"
            params += [pattern, pattern]

        if task_filter.date_from or task_filter.date_to:
            column = DATE_COLUMNS[task_filter.date_field]
            clauses.append(f"{column} IS NOT NULL")
            if task_filter.date_from:
                clauses.append(f"date({column}) >= date(?)")
                params.append(task_filter.date_from.isoformat())
            if task_filter.date_to:
                clauses.append(f"date({column}) <= date(?)")
                params.append(task_filter.date_to.isoformat())

        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._conn.execute(f"SELECT * FROM tasks{where} ORDER BY id", params).fetchall()
        return [self._to_task(r) for r in rows]

    def stats(self) -> TaskStats:
        row = self._conn.execute(
            "SELECT COUNT(*) AS total, SUM(status = 'completed') AS completed FROM tasks"
        ).fetchone()
        total = row["total"]
        completed = row["completed"] or 0
        oldest = self._conn.execute(
            "SELECT * FROM tasks WHERE status = 'pending' ORDER BY created_at LIMIT 1"
        ).fetchone()
        return TaskStats(
            total=total,
            completed=completed,
            pending=total - completed,
            oldest_pending=self._to_task(oldest) if oldest else None,
        )

    def close(self) -> None:
        self._conn.close()
