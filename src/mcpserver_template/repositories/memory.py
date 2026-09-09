"""In-memory backend: no persistence, filtering delegated to TaskFilter.matches()."""

from mcpserver_template.models import Task, TaskFilter, TaskStats, TaskStatus, utcnow
from mcpserver_template.repository import TaskNotFoundError


class InMemoryTaskRepository:
    def __init__(self) -> None:
        self._tasks: dict[int, Task] = {}
        self._next_id = 1

    def add(self, title: str, description: str = "") -> Task:
        task = Task(
            id=self._next_id,
            title=title,
            description=description,
            created_at=utcnow(),
        )
        self._tasks[task.id] = task
        self._next_id += 1
        return task

    def get(self, task_id: int) -> Task:
        try:
            return self._tasks[task_id]
        except KeyError:
            raise TaskNotFoundError(task_id) from None

    def complete(self, task_id: int) -> Task:
        task = self.get(task_id)
        if task.status is TaskStatus.COMPLETED:
            return task
        updated = task.model_copy(update={"status": TaskStatus.COMPLETED, "completed_at": utcnow()})
        self._tasks[task_id] = updated
        return updated

    def delete(self, task_id: int) -> Task:
        task = self.get(task_id)
        del self._tasks[task_id]
        return task

    def filter(self, task_filter: TaskFilter) -> list[Task]:
        return [t for t in self._tasks.values() if task_filter.matches(t)]

    def stats(self) -> TaskStats:
        tasks = list(self._tasks.values())
        pending = [t for t in tasks if t.status is TaskStatus.PENDING]
        return TaskStats(
            total=len(tasks),
            completed=len(tasks) - len(pending),
            pending=len(pending),
            oldest_pending=min(pending, key=lambda t: t.created_at, default=None),
        )

    def close(self) -> None:
        """Nothing to release."""
