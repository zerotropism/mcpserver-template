"""Persistence contract. Implementations live in repositories/."""

from typing import Protocol, runtime_checkable

from mcpserver_template.models import Task, TaskFilter, TaskStats


class TaskNotFoundError(LookupError):
    """Raised when an operation targets an unknown task id."""

    def __init__(self, task_id: int) -> None:
        super().__init__(f"Task {task_id} not found")
        self.task_id = task_id


@runtime_checkable
class TaskRepository(Protocol):
    """Storage backends implement this; the server knows nothing else about them."""

    def add(self, title: str, description: str = "") -> Task: ...

    def get(self, task_id: int) -> Task:
        """Raise TaskNotFoundError when the id is unknown."""
        ...

    def complete(self, task_id: int) -> Task:
        """Idempotent: completing an already completed task keeps its completed_at."""
        ...

    def delete(self, task_id: int) -> Task:
        """Return the deleted task so callers can report what disappeared."""
        ...

    def filter(self, task_filter: TaskFilter) -> list[Task]:
        """Return matching tasks, oldest first. Empty list means no match."""
        ...

    def stats(self) -> TaskStats: ...

    def close(self) -> None:
        """Release resources. No-op for in-memory backends."""
        ...
