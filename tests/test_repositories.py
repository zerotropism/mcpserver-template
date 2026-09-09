"""Same suite for every backend: behaviour must not depend on persistence."""

from datetime import timedelta

import pytest
from pydantic import ValidationError

from mcpserver_template.models import TaskFilter, TaskStatus, utcnow
from mcpserver_template.repositories.memory import InMemoryTaskRepository
from mcpserver_template.repositories.sqlite import SqliteTaskRepository
from mcpserver_template.repository import TaskNotFoundError, TaskRepository


@pytest.fixture(params=["memory", "sqlite"])
def repo(request, tmp_path):
    if request.param == "memory":
        repository = InMemoryTaskRepository()
    else:
        repository = SqliteTaskRepository(tmp_path / "tasks.db")
    yield repository
    repository.close()


def test_implements_protocol(repo) -> None:
    assert isinstance(repo, TaskRepository)


def test_add_assigns_incrementing_ids_and_pending_status(repo) -> None:
    first = repo.add("Write report")
    second = repo.add("Review PR", "before Friday")
    assert (first.id, second.id) == (1, 2)
    assert first.status is TaskStatus.PENDING
    assert first.completed_at is None
    assert second.description == "before Friday"


def test_created_at_is_timezone_aware(repo) -> None:
    assert repo.add("Task").created_at.tzinfo is not None


def test_empty_title_is_rejected_by_every_backend(repo) -> None:
    with pytest.raises(ValidationError):
        repo.add("")
    assert repo.filter(TaskFilter()) == []


def test_get_unknown_id_raises(repo) -> None:
    with pytest.raises(TaskNotFoundError):
        repo.get(404)


def test_complete_sets_status_and_timestamp(repo) -> None:
    task = repo.complete(repo.add("Task").id)
    assert task.status is TaskStatus.COMPLETED
    assert task.completed_at is not None
    assert repo.get(task.id).status is TaskStatus.COMPLETED


def test_complete_is_idempotent(repo) -> None:
    task_id = repo.add("Task").id
    first = repo.complete(task_id)
    assert repo.complete(task_id).completed_at == first.completed_at


def test_delete_returns_task_and_removes_it(repo) -> None:
    task_id = repo.add("Task").id
    assert repo.delete(task_id).id == task_id
    with pytest.raises(TaskNotFoundError):
        repo.get(task_id)


def test_delete_unknown_id_raises(repo) -> None:
    with pytest.raises(TaskNotFoundError):
        repo.delete(404)


def test_empty_filter_returns_everything_oldest_first(repo) -> None:
    repo.add("A")
    repo.add("B")
    assert [t.title for t in repo.filter(TaskFilter())] == ["A", "B"]


def test_no_match_returns_empty_list_not_a_sentinel(repo) -> None:
    repo.add("A")
    assert repo.filter(TaskFilter(keyword="nothing")) == []


def test_filter_by_status(repo) -> None:
    repo.add("A")
    repo.complete(repo.add("B").id)
    assert [t.title for t in repo.filter(TaskFilter(status=TaskStatus.COMPLETED))] == ["B"]


def test_keyword_is_case_insensitive_over_title_and_description(repo) -> None:
    repo.add("Quarterly REPORT", "figures")
    repo.add("Invoice", "Send the Report to accounting")
    assert len(repo.filter(TaskFilter(keyword="report"))) == 2
    assert len(repo.filter(TaskFilter(keyword="FIGURES"))) == 1


def test_criteria_are_combined_with_and(repo) -> None:
    repo.add("Report")
    repo.complete(repo.add("Report follow-up").id)
    found = repo.filter(TaskFilter(keyword="report", status=TaskStatus.PENDING))
    assert [t.title for t in found] == ["Report"]


def test_date_bounds_are_inclusive(repo) -> None:
    repo.add("Task")
    today = utcnow().date()
    assert len(repo.filter(TaskFilter(date_from=today, date_to=today))) == 1
    assert repo.filter(TaskFilter(date_from=today + timedelta(days=1))) == []


def test_date_filter_on_completed_at_excludes_pending_tasks(repo) -> None:
    repo.add("Pending")
    repo.complete(repo.add("Done").id)
    today = utcnow().date()
    found = repo.filter(TaskFilter(date_from=today, date_field="completed_at"))
    assert [t.title for t in found] == ["Done"]


def test_stats_on_empty_repository(repo) -> None:
    stats = repo.stats()
    assert (stats.total, stats.completed, stats.pending) == (0, 0, 0)
    assert stats.oldest_pending is None
    assert stats.completion_rate == 0.0


def test_stats_counts_and_oldest_pending(repo) -> None:
    repo.add("Oldest")
    repo.add("Newer")
    repo.complete(repo.add("Done").id)
    stats = repo.stats()
    assert (stats.total, stats.completed, stats.pending) == (3, 1, 2)
    assert stats.oldest_pending.title == "Oldest"
    assert stats.completion_rate == pytest.approx(33.33, abs=0.01)
