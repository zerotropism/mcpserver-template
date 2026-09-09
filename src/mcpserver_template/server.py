"""Single MCP server. Persistence is injected, never imported directly."""

import os
from datetime import timedelta

from fastmcp import FastMCP

from mcpserver_template.models import Task, TaskFilter, TaskStats, TaskStatus, utcnow
from mcpserver_template.repositories.memory import InMemoryTaskRepository
from mcpserver_template.repositories.sqlite import SqliteTaskRepository
from mcpserver_template.repository import TaskRepository

BACKENDS = {
    "memory": lambda: InMemoryTaskRepository(),
    "sqlite": lambda: SqliteTaskRepository(os.getenv("DB_PATH", "tasks.db")),
}


def build_repository(backend: str | None = None) -> TaskRepository:
    """Pick a backend by name; TASK_BACKEND selects it at runtime."""
    name = (backend or os.getenv("TASK_BACKEND", "memory")).lower()
    try:
        return BACKENDS[name]()
    except KeyError:
        raise ValueError(f"Unknown backend '{name}'. Use: {sorted(BACKENDS)}") from None


def _render_tasks(tasks: list[Task], title: str, empty: str) -> str:
    if not tasks:
        return empty
    lines = [f"{title}\n"]
    for task in tasks:
        mark = "[x]" if task.status is TaskStatus.COMPLETED else "[ ]"
        lines.append(f"{mark} [{task.id}] {task.title}")
        if task.description:
            lines.append(f"    {task.description}")
    return "\n".join(lines)


def _render_stats(stats: TaskStats) -> str:
    lines = [
        "Task statistics\n",
        f"Total:           {stats.total}",
        f"Completed:       {stats.completed}",
        f"Pending:         {stats.pending}",
        f"Completion rate: {stats.completion_rate:.1f}%",
    ]
    if stats.oldest_pending:
        oldest = stats.oldest_pending
        lines += [
            "\nOldest pending task:",
            f"  [{oldest.id}] {oldest.title}",
            f"  Created: {oldest.created_at.isoformat()}",
        ]
    return "\n".join(lines)


def create_server(repository: TaskRepository) -> FastMCP:
    """Build a server bound to one repository. Tests inject their own."""
    mcp = FastMCP("Task Manager")

    # ------------------------------------------------------------------ tools

    @mcp.tool
    def add_task(title: str, description: str = "") -> Task:
        """Add a new task to the task list."""
        return repository.add(title, description)

    @mcp.tool
    def complete_task(task_id: int) -> Task:
        """Mark a task as completed. Completing a completed task changes nothing."""
        return repository.complete(task_id)

    @mcp.tool
    def complete_tasks(task_ids: list[int]) -> list[Task]:
        """Mark several tasks as completed in one call."""
        return [repository.complete(task_id) for task_id in task_ids]

    @mcp.tool
    def delete_task(task_id: int) -> Task:
        """Delete a task and return it."""
        return repository.delete(task_id)

    @mcp.tool
    def filter_tasks(task_filter: TaskFilter) -> list[Task]:
        """
        Filter tasks. Every criterion is optional and they are combined with AND.
        An empty filter returns every task; no match returns an empty list.
        """
        return repository.filter(task_filter)

    # -------------------------------------------------------------- resources

    @mcp.resource("tasks://all")
    def all_tasks() -> str:
        """Every task, oldest first."""
        return _render_tasks(repository.filter(TaskFilter()), "All tasks", "No tasks yet.")

    @mcp.resource("tasks://pending")
    def pending_tasks() -> str:
        """Tasks still to be done."""
        tasks = repository.filter(TaskFilter(status=TaskStatus.PENDING))
        return _render_tasks(tasks, "Pending tasks", "No pending tasks.")

    @mcp.resource("tasks://completed")
    def completed_tasks() -> str:
        """Tasks already done."""
        tasks = repository.filter(TaskFilter(status=TaskStatus.COMPLETED))
        return _render_tasks(tasks, "Completed tasks", "No completed tasks.")

    @mcp.resource("tasks://stats")
    def task_stats() -> str:
        """Counts, completion rate and oldest pending task."""
        return _render_stats(repository.stats())

    @mcp.resource("tasks://today")
    def today_tasks() -> str:
        """Tasks created today."""
        today = utcnow().date()
        tasks = repository.filter(TaskFilter(date_from=today, date_to=today))
        return _render_tasks(tasks, f"Today's tasks ({today})", "No tasks for today.")

    @mcp.resource("tasks://weekly-summary")
    def weekly_summary() -> str:
        """Tasks created over the past seven days, split by status."""
        today = utcnow().date()
        week_ago = today - timedelta(days=7)
        recent = repository.filter(TaskFilter(date_from=week_ago))
        done = [t for t in recent if t.status is TaskStatus.COMPLETED]
        todo = [t for t in recent if t.status is TaskStatus.PENDING]
        return (
            f"Weekly summary ({week_ago} -> {today})\n\n"
            + _render_tasks(done, f"Completed this week: {len(done)}", "Completed this week: 0")
            + "\n\n"
            + _render_tasks(todo, f"Still pending: {len(todo)}", "Still pending: 0")
        )

    # ---------------------------------------------------------------- prompts

    @mcp.prompt
    def task_summary_prompt() -> str:
        """Ask the model to summarise the current task list."""
        return (
            "Read the tasks://all resource and summarise the task list: how many tasks "
            "there are, how many are done, and which ones look most urgent. "
            "Base every statement on the resource, do not invent tasks."
        )

    @mcp.prompt
    def priority_analysis_prompt() -> str:
        """Ask the model to rank pending tasks by priority."""
        return (
            "Read the tasks://pending resource and rank the tasks by priority. "
            "For each task give one sentence justifying its rank, using only the "
            "title, description and creation date available in the resource."
        )

    @mcp.prompt
    def scheduling_prompt(available_hours: float = 8.0) -> str:
        """Ask the model to fit pending tasks into the available time."""
        return (
            f"Read the tasks://pending resource and build a schedule for {available_hours} "
            "hours of work. Estimate a duration per task, state your assumptions, and "
            "say explicitly which tasks do not fit."
        )

    @mcp.prompt
    def weekly_review_prompt() -> str:
        """Ask the model to review the past week."""
        return (
            "Read the tasks://weekly-summary and tasks://stats resources and write a "
            "weekly review: what was completed, what slipped, and one suggestion for "
            "next week. Cite the numbers from the resources."
        )

    return mcp


def main() -> None:
    """Console entry point: build the configured repository and serve over stdio."""
    repository = build_repository()
    try:
        create_server(repository).run()
    finally:
        repository.close()


if __name__ == "__main__":
    main()
