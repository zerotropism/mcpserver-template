from fastmcp import FastMCP
from datetime import datetime
import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()

mcp = FastMCP("TaskTracker")

DB_PATH = os.getenv("DB_PATH", "tasks.db")


def get_db() -> sqlite3.Connection:
    """Get a database connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create the tasks table if it doesn't exist."""
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                title        TEXT NOT NULL,
                description  TEXT DEFAULT '',
                status       TEXT DEFAULT 'pending',
                created_at   TEXT NOT NULL,
                completed_at TEXT
            )
        """
        )
        conn.commit()


init_db()


# Tools
@mcp.tool()
def add_task(title: str, description: str = "") -> dict:
    """Add a new task to the task list."""
    now = datetime.now().isoformat()
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO tasks (title, description, status, created_at) VALUES (?, ?, 'pending', ?)",
            (title, description, now),
        )
        conn.commit()
        task = conn.execute(
            "SELECT * FROM tasks WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
    return dict(task)


@mcp.tool()
def complete_task(task_id: int) -> dict:
    """Mark a task as completed."""
    now = datetime.now().isoformat()
    with get_db() as conn:
        conn.execute(
            "UPDATE tasks SET status = 'completed', completed_at = ? WHERE id = ?",
            (now, task_id),
        )
        conn.commit()
        task = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if not task:
        return {"error": f"Task {task_id} not found"}
    return dict(task)


@mcp.tool()
def delete_task(task_id: int) -> dict:
    """Delete a task from the list."""
    with get_db() as conn:
        task = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not task:
            return {"success": False, "error": f"Task {task_id} not found"}
        conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
    return {"success": True, "deleted": dict(task)}


@mcp.tool()
def filter_tasks_by_status(status: str) -> list[dict]:
    """Filter tasks by status. Accepted values: 'pending', 'completed'."""
    valid_statuses = ["pending", "completed"]
    if status not in valid_statuses:
        return [{"error": f"Invalid status '{status}'. Use: {valid_statuses}"}]
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE status = ?", (status,)
        ).fetchall()
    return [dict(r) for r in rows]


@mcp.tool()
def filter_tasks_by_date(
    date_from: str = "", date_to: str = "", field: str = "created_at"
) -> list[dict]:
    """
    Filter tasks between two dates (ISO format: YYYY-MM-DD).
    field: 'created_at' or 'completed_at'
    """
    valid_fields = ["created_at", "completed_at"]
    if field not in valid_fields:
        return [{"error": f"Invalid field '{field}'. Use: {valid_fields}"}]

    query = f"SELECT * FROM tasks WHERE {field} IS NOT NULL"
    params = []
    if date_from:
        query += f" AND {field} >= ?"
        params.append(date_from)
    if date_to:
        query += f" AND {field} <= ?"
        params.append(date_to + "T23:59:59")

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows] or [
        {"message": "No tasks found for this date range"}
    ]


@mcp.tool()
def search_tasks(keyword: str) -> list[dict]:
    """Search tasks by keyword in title or description (case-insensitive)."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE LOWER(title) LIKE ? OR LOWER(description) LIKE ?",
            (f"%{keyword.lower()}%", f"%{keyword.lower()}%"),
        ).fetchall()
    return [dict(r) for r in rows] or [{"message": f"No tasks matching '{keyword}'"}]


@mcp.tool()
def filter_tasks(
    status: str = "", keyword: str = "", date_from: str = "", date_to: str = ""
) -> list[dict]:
    """Filter tasks with multiple optional criteria combined."""
    query = "SELECT * FROM tasks WHERE 1=1"
    params = []

    if status:
        query += " AND status = ?"
        params.append(status)
    if keyword:
        query += " AND (LOWER(title) LIKE ? OR LOWER(description) LIKE ?)"
        params.extend([f"%{keyword.lower()}%", f"%{keyword.lower()}%"])
    if date_from:
        query += " AND created_at >= ?"
        params.append(date_from)
    if date_to:
        query += " AND created_at <= ?"
        params.append(date_to + "T23:59:59")

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows] or [{"message": "No tasks match the given filters"}]


# A tool to mark multiple tasks as completed in one call
@mcp.tool()
def complete_tasks(task_ids: list[int]) -> list[dict]:
    """Mark multiple tasks as completed."""
    return [complete_task(task_id) for task_id in task_ids]


# Resources
@mcp.resource("tasks://all")
def get_all_tasks() -> str:
    """Get the list of all tasks."""
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM tasks ORDER BY created_at DESC").fetchall()
    if not rows:
        return "No tasks found."
    result = "All Tasks:\n\n"
    for task in rows:
        status_emoji = "✅" if task["status"] == "completed" else "⏳"
        result += f"{status_emoji} [{task['id']}] {task['title']}\n"
        if task["description"]:
            result += f"   {task['description']}\n"
        result += f"   Created: {task['created_at']}\n\n"
    return result


@mcp.resource("tasks://pending")
def get_pending_tasks() -> str:
    """Get only pending tasks."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE status = 'pending' ORDER BY created_at ASC"
        ).fetchall()
    if not rows:
        return "No pending tasks."
    result = "Pending Tasks:\n\n"
    for task in rows:
        result += f"⏳ [{task['id']}] {task['title']}\n"
        if task["description"]:
            result += f"   {task['description']}\n"
        result += f"   Created: {task['created_at']}\n\n"
    return result


@mcp.resource("tasks://completed")
def get_completed_tasks() -> str:
    """Get only completed tasks with completion time."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE status = 'completed' ORDER BY completed_at DESC"
        ).fetchall()
    if not rows:
        return "No completed tasks yet."
    result = "Completed Tasks:\n\n"
    for task in rows:
        result += f"✅ [{task['id']}] {task['title']}\n"
        result += f"   Completed at: {task['completed_at']}\n"
        result += f"   Created at:   {task['created_at']}\n\n"
    return result


@mcp.resource("tasks://stats")
def get_task_stats() -> str:
    """Get statistics about the task list."""
    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        completed = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE status = 'completed'"
        ).fetchone()[0]
        oldest = conn.execute(
            "SELECT * FROM tasks WHERE status = 'pending' ORDER BY created_at ASC LIMIT 1"
        ).fetchone()

    pending = total - completed
    result = "Task Statistics:\n\n"
    result += f"📊 Total tasks:     {total}\n"
    result += f"✅ Completed:       {completed}\n"
    result += f"⏳ Pending:         {pending}\n"
    if total > 0:
        result += f"📈 Completion rate: {(completed / total) * 100:.1f}%\n"
    if oldest:
        result += f"\n⚠️  Oldest pending task:\n"
        result += f"   [{oldest['id']}] {oldest['title']}\n"
        result += f"   Created: {oldest['created_at']}\n"
    return result


@mcp.resource("tasks://today")
def get_today_tasks() -> str:
    """Get tasks created today."""
    today = datetime.now().date().isoformat()
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE DATE(created_at) = ?", (today,)
        ).fetchall()
    if not rows:
        return "No tasks for today."
    result = f"Today's Tasks ({today}):\n\n"
    for task in rows:
        status_emoji = "✅" if task["status"] == "completed" else "⏳"
        result += f"{status_emoji} [{task['id']}] {task['title']}\n"
        if task["description"]:
            result += f"   {task['description']}\n\n"
    return result


@mcp.resource("tasks://weekly-summary")
def get_weekly_summary() -> str:
    """Get a summary of tasks from the past 7 days."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE DATE(created_at) >= DATE('now', '-7 days')"
        ).fetchall()

    completed = [r for r in rows if r["status"] == "completed"]
    pending = [r for r in rows if r["status"] == "pending"]
    result = "Weekly Summary (last 7 days):\n\n"
    result += f"🎉 Completed this week: {len(completed)}\n"
    for task in completed:
        result += f"   ✅ [{task['id']}] {task['title']}\n"
    result += f"\n⏳ Still pending: {len(pending)}\n"
    for task in pending:
        result += f"   🔲 [{task['id']}] {task['title']}\n"
    return result


# Prompts
@mcp.prompt()
def task_summary_prompt() -> str:
    """Generate a prompt for summarizing tasks."""
    return """Please analyze the current task list and provide:

1. Total number of tasks (completed vs pending)
2. Any overdue or high-priority items
3. Suggested next actions
4. Overall progress assessment

Use the tasks://all resource to access the complete task list."""


# A prompt to analyze task priorities and provide recommendations
@mcp.prompt()
def priority_analysis_prompt() -> str:
    """Generate a prompt for analyzing task priorities."""
    return """Please analyze the current task list using the following resources:
- tasks://all → full task list
- tasks://stats → completion rate and oldest pending task

Based on this data, evaluate priorities:

1. **Urgency vs Importance matrix**
   - Urgent & Important → do immediately
   - Important but not urgent → schedule
   - Urgent but not important → delegate
   - Neither → consider removing

2. **Risk assessment**
   - Which pending tasks are blocking others?
   - Which tasks have been pending the longest? (see tasks://stats)

3. **Recommendations**
   - Top 3 tasks to tackle first
   - Tasks that can be batched together
   - Tasks to consider dropping

Provide a clear priority ranking with justification for each decision."""


# A prompt to for scheduling tasks across a workday, accounting for energy levels and breaks
@mcp.prompt()
def scheduling_prompt(available_hours: float = 8.0) -> str:
    """Generate a prompt for scheduling tasks across a workday."""
    return f"""Based on the following resources:
- tasks://today → tasks created today
- tasks://pending → all pending tasks

Create a realistic schedule for today.

**Constraints:**
- Available time: {available_hours} hours
- Account for breaks (15min every 2h, 1h lunch)
- Peak focus hours: 9am–12pm (use for complex tasks)
- Low energy hours: 2pm–3pm (use for simple tasks)

**Deliverable:**
Produce a time-blocked schedule in this format:
| Time | Task | Duration | Notes |
|------|------|----------|-------|

Prioritize tasks from tasks://today first, then fill remaining slots
from tasks://pending. Explain any tasks left unscheduled."""


# A prompt to conduct a weekly review of tasks, celebrating wins and identifying blockers
@mcp.prompt()
def weekly_review_prompt() -> str:
    """Generate a prompt for a weekly review of tasks."""
    return """Conduct a weekly review using the following resources:
- tasks://weekly-summary → tasks created or completed this week
- tasks://stats → overall completion rate and oldest pending task
- tasks://completed → full list of completed tasks

Structure your review as follows:

1. **Wins this week** 🎉 (from tasks://weekly-summary)
2. **Still pending** ⏳ — why are they stuck?
3. **Overall health** 📊 (use tasks://stats completion rate)
4. **Patterns** — any recurring blockers?
5. **Next week plan** — top 5 priorities from tasks://pending

Keep it concise and actionable."""


if __name__ == "__main__":
    mcp.run()
