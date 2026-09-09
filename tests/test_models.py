"""Model-level tests: no repository, no server, pure domain logic."""

from datetime import date, datetime, timedelta

import pytest
from pydantic import ValidationError

from mcpserver_template.models import Task, TaskFilter, TaskStats, TaskStatus, utcnow

NOW = datetime(2026, 9, 9, 12, 0, tzinfo=utcnow().tzinfo)


def make_task(**overrides) -> Task:
    defaults = {
        "id": 1,
        "title": "Write the report",
        "description": "Quarterly figures",
        "created_at": NOW,
    }
    return Task(**{**defaults, **overrides})


def test_title_cannot_be_empty() -> None:
    with pytest.raises(ValidationError):
        make_task(title="")


def test_empty_filter_matches_everything() -> None:
    assert TaskFilter().matches(make_task())


def test_keyword_is_case_insensitive_across_title_and_description() -> None:
    task = make_task()
    assert TaskFilter(keyword="REPORT").matches(task)
    assert TaskFilter(keyword="quarterly").matches(task)
    assert not TaskFilter(keyword="invoice").matches(task)


def test_criteria_are_combined_with_and() -> None:
    task = make_task()
    assert not TaskFilter(keyword="report", status=TaskStatus.COMPLETED).matches(task)


def test_date_bounds_are_inclusive() -> None:
    task = make_task()
    day = NOW.date()
    assert TaskFilter(date_from=day, date_to=day).matches(task)
    assert not TaskFilter(date_from=day + timedelta(days=1)).matches(task)


def test_date_filter_on_completed_at_excludes_pending_tasks() -> None:
    """Reproduces the original 'if not task_date_str: continue' behaviour."""
    task = make_task()
    assert not TaskFilter(date_from=date(2020, 1, 1), date_field="completed_at").matches(task)


def test_pending_task_matches_when_no_date_filter_is_set() -> None:
    assert TaskFilter(date_field="completed_at").matches(make_task())


def test_completion_rate_is_zero_on_empty_list() -> None:
    assert TaskStats(total=0, completed=0, pending=0).completion_rate == 0.0


def test_completion_rate() -> None:
    assert TaskStats(total=4, completed=1, pending=3).completion_rate == 25.0


def test_unknown_criteria_are_rejected() -> None:
    """A model hallucinating a field must get an error, not a silently empty filter."""
    with pytest.raises(ValidationError):
        TaskFilter(completed=False)
