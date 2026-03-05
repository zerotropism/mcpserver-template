from fastmcp import FastMCP
from datetime import datetime

mcp = FastMCP("TaskTracker")

# Simple in-memory task storage
# In real applications, this would be a database
tasks = []
task_id_counter = 1


# Tools with @mcp.tool() decorator
# A tool to add a new task to the task list
@mcp.tool()
def add_task(title: str, description: str = "") -> dict:
    """Add a new task to the task list."""
    global task_id_counter

    task = {
        "id": task_id_counter,
        "title": title,
        "description": description,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
    }

    tasks.append(task)
    task_id_counter += 1

    return task


# A tool to mark tasks as completed
@mcp.tool()
def complete_task(task_id: int) -> dict:
    """Mark a task as completed."""
    for task in tasks:
        if task["id"] == task_id:
            task["status"] = "completed"
            task["completed_at"] = datetime.now().isoformat()
            return task

    return {"error": f"Task {task_id} not found"}


# A tool to delete a task from the list
@mcp.tool()
def delete_task(task_id: int) -> dict:
    """Delete a task from the list."""
    for i, task in enumerate(tasks):
        if task["id"] == task_id:
            deleted_task = tasks.pop(i)
            return {"success": True, "deleted": deleted_task}

    return {"success": False, "error": f"Task {task_id} not found"}


# A tool to filter tasks by status
@mcp.tool()
def filter_tasks_by_status(status: str) -> list[dict]:
    """Filter tasks by status. Accepted values: 'pending', 'completed'."""
    valid_statuses = ["pending", "completed"]
    if status not in valid_statuses:
        return [{"error": f"Invalid status '{status}'. Use: {valid_statuses}"}]

    return [t for t in tasks if t["status"] == status]


# A tool to filter tasks by date
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

    result = []
    for task in tasks:
        task_date_str = task.get(field)
        if not task_date_str:
            continue

        task_date = datetime.fromisoformat(task_date_str).date()

        if date_from:
            if task_date < datetime.fromisoformat(date_from).date():
                continue
        if date_to:
            if task_date > datetime.fromisoformat(date_to).date():
                continue

        result.append(task)

    return result if result else [{"message": "No tasks found for this date range"}]


# A tool to search tasks by keyword
@mcp.tool()
def search_tasks(keyword: str) -> list[dict]:
    """Search tasks by keyword in title or description (case-insensitive)."""
    keyword_lower = keyword.lower()
    result = [
        t
        for t in tasks
        if keyword_lower in t["title"].lower()
        or keyword_lower in t.get("description", "").lower()
    ]

    return result if result else [{"message": f"No tasks matching '{keyword}'"}]


# A combined tool to filter tasks by multiple criteria
@mcp.tool()
def filter_tasks(
    status: str = "",
    keyword: str = "",
    date_from: str = "",
    date_to: str = "",
) -> list[dict]:
    """
    Filter tasks with multiple optional criteria combined.
    - status: 'pending' or 'completed'
    - keyword: searched in title and description
    - date_from / date_to: ISO format YYYY-MM-DD (based on created_at)
    """
    result = tasks[:]

    if status:
        result = [t for t in result if t["status"] == status]

    if keyword:
        kw = keyword.lower()
        result = [
            t
            for t in result
            if kw in t["title"].lower() or kw in t.get("description", "").lower()
        ]

    if date_from:
        from_date = datetime.fromisoformat(date_from).date()
        result = [
            t
            for t in result
            if datetime.fromisoformat(t["created_at"]).date() >= from_date
        ]

    if date_to:
        to_date = datetime.fromisoformat(date_to).date()
        result = [
            t
            for t in result
            if datetime.fromisoformat(t["created_at"]).date() <= to_date
        ]

    return result if result else [{"message": "No tasks match the given filters"}]


# Resources with @mcp.resource() decorator
# A resource to get the list of all tasks
@mcp.resource("tasks://all")  # creates a resource with a URI-like identifier
def get_all_tasks() -> str:
    """Get all tasks as formatted text."""
    if not tasks:
        return "No tasks found"

    result = "Current Tasks:\n\n"
    for task in tasks:
        status_emoji = "✅" if task["status"] == "completed" else "⏳"
        result += f"{status_emoji} [{task['id']}] {task['title']}\n"
        if task["description"]:
            result += f"   Description: {task['description']}\n"
        result += f"   Status: {task['status']}\n"
        result += f"   Created: {task['created_at']}\n\n"

    return result


# A resource to get only pending tasks
@mcp.resource("tasks://pending")
def get_pending_tasks() -> str:
    """Get only pending tasks."""
    pending = [t for t in tasks if t["status"] == "pending"]

    if not pending:
        return "No pending tasks!"

    result = "Pending Tasks:\n\n"
    for task in pending:
        result += f"⏳ [{task['id']}] {task['title']}\n"
        if task["description"]:
            result += f"   {task['description']}\n"
        result += "\n"

    return result


# A resource to get only completed tasks with completion time
@mcp.resource("tasks://completed")
def get_completed_tasks() -> str:
    """Get only completed tasks with completion time."""
    completed = [t for t in tasks if t["status"] == "completed"]

    if not completed:
        return "No completed tasks yet."

    result = "Completed Tasks:\n\n"
    for task in completed:
        result += f"✅ [{task['id']}] {task['title']}\n"
        result += f"   Completed at: {task.get('completed_at', 'N/A')}\n"
        result += f"   Created at:   {task['created_at']}\n\n"

    return result


# A resource to get statistics about the task list
@mcp.resource("tasks://stats")
def get_task_stats() -> str:
    """Get statistics about the task list."""
    total = len(tasks)
    completed = sum(1 for t in tasks if t["status"] == "completed")
    pending = total - completed

    oldest_pending = None
    if pending:
        pending_tasks = [t for t in tasks if t["status"] == "pending"]
        oldest_pending = min(pending_tasks, key=lambda t: t["created_at"])

    result = "Task Statistics:\n\n"
    result += f"📊 Total tasks:     {total}\n"
    result += f"✅ Completed:       {completed}\n"
    result += f"⏳ Pending:         {pending}\n"

    if total > 0:
        rate = (completed / total) * 100
        result += f"📈 Completion rate: {rate:.1f}%\n"

    if oldest_pending:
        result += f"\n⚠️  Oldest pending task:\n"
        result += f"   [{oldest_pending['id']}] {oldest_pending['title']}\n"
        result += f"   Created: {oldest_pending['created_at']}\n"

    return result


# A resource to get tasks created or due today
@mcp.resource("tasks://today")
def get_today_tasks() -> str:
    """Get tasks created or due today."""
    today = datetime.now().date()
    today_tasks = [
        t for t in tasks if datetime.fromisoformat(t["created_at"]).date() == today
    ]

    if not today_tasks:
        return "No tasks for today."

    result = f"Today's Tasks ({today}):\n\n"
    for task in today_tasks:
        status_emoji = "✅" if task["status"] == "completed" else "⏳"
        result += f"{status_emoji} [{task['id']}] {task['title']}\n"
        if task["description"]:
            result += f"   {task['description']}\n"
        result += "\n"

    return result


# A resource to get a summary of tasks from the past week
@mcp.resource("tasks://weekly-summary")
def get_weekly_summary() -> str:
    """Get a summary of tasks from the past 7 days."""
    from datetime import timedelta

    today = datetime.now().date()
    week_ago = today - timedelta(days=7)

    recent_tasks = [
        t for t in tasks if datetime.fromisoformat(t["created_at"]).date() >= week_ago
    ]

    completed_this_week = [t for t in recent_tasks if t["status"] == "completed"]
    pending_this_week = [t for t in recent_tasks if t["status"] == "pending"]

    result = f"Weekly Summary ({week_ago} → {today}):\n\n"
    result += f"🎉 Completed this week: {len(completed_this_week)}\n"
    for task in completed_this_week:
        result += f"   ✅ [{task['id']}] {task['title']}\n"

    result += f"\n⏳ Still pending: {len(pending_this_week)}\n"
    for task in pending_this_week:
        result += f"   🔲 [{task['id']}] {task['title']}\n"

    return result


# Prompts with @mcp.prompt() decorator
# A prompt to summarize the current task list and provide insights
# Tells the AI what information to include, and references the resource to use for data
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
