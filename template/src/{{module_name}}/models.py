"""Domain models shared by every repository implementation."""

from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

DateField = Literal["created_at", "completed_at"]


class TaskStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"


def utcnow() -> datetime:
    """Timezone-aware creation timestamp, unlike the naive datetime.now() it replaces."""
    return datetime.now(UTC)


class Task(BaseModel):
    id: int
    title: str = Field(min_length=1)
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime
    completed_at: datetime | None = None


class TaskFilter(BaseModel):
    """Every filtering tool collapses into this single, fully optional filter."""

    model_config = ConfigDict(extra="forbid")

    status: TaskStatus | None = None
    keyword: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    date_field: DateField = "created_at"

    def matches(self, task: Task) -> bool:
        if self.status is not None and task.status != self.status:
            return False

        if self.keyword:
            kw = self.keyword.lower()
            if kw not in task.title.lower() and kw not in task.description.lower():
                return False

        if self.date_from or self.date_to:
            value: datetime | None = getattr(task, self.date_field)
            if value is None:
                return False
            day = value.date()
            if self.date_from and day < self.date_from:
                return False
            if self.date_to and day > self.date_to:
                return False

        return True


class TaskStats(BaseModel):
    """Numbers only — rendering belongs to the resource layer."""

    total: int
    completed: int
    pending: int
    oldest_pending: Task | None = None

    @property
    def completion_rate(self) -> float:
        """Percentage of completed tasks; 0.0 when the list is empty."""
        return (self.completed / self.total * 100) if self.total else 0.0
