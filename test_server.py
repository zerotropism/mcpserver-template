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


if __name__ == "__main__":
    mcp.run()
