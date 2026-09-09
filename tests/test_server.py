"""Server tests through the in-memory FastMCP client: no subprocess, no transport."""

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from mcpserver_template.repositories.memory import InMemoryTaskRepository
from mcpserver_template.repositories.sqlite import SqliteTaskRepository
from mcpserver_template.server import build_repository, create_server


@pytest.fixture(params=["memory", "sqlite"])
def repo(request, tmp_path):
    repository = (
        InMemoryTaskRepository()
        if request.param == "memory"
        else SqliteTaskRepository(tmp_path / "tasks.db")
    )
    yield repository
    repository.close()


@pytest.fixture
def client(repo):
    return Client(create_server(repo))


async def test_exposes_five_tools_six_resources_four_prompts(client) -> None:
    async with client:
        assert len(await client.list_tools()) == 5
        assert len(await client.list_resources()) == 6
        assert len(await client.list_prompts()) == 4


async def test_add_then_read_back(client) -> None:
    async with client:
        result = await client.call_tool("add_task", {"title": "Write report"})
        assert result.data.id == 1
        assert result.data.status == "pending"
        content = await client.read_resource("tasks://all")
        assert "Write report" in content[0].text


async def test_unknown_task_raises_instead_of_returning_an_error_dict(client) -> None:
    async with client:
        with pytest.raises(ToolError):
            await client.call_tool("complete_task", {"task_id": 404})


async def test_invalid_status_is_rejected_by_schema(client) -> None:
    async with client:
        with pytest.raises(ToolError):
            await client.call_tool("filter_tasks", {"task_filter": {"status": "urgent"}})


async def test_filter_combines_criteria(client) -> None:
    async with client:
        await client.call_tool("add_task", {"title": "Quarterly report"})
        second = await client.call_tool("add_task", {"title": "Report follow-up"})
        await client.call_tool("complete_task", {"task_id": second.data.id})
        result = await client.call_tool(
            "filter_tasks", {"task_filter": {"keyword": "report", "status": "pending"}}
        )
        assert [t.title for t in result.data] == ["Quarterly report"]


async def test_empty_filter_returns_empty_list_on_empty_store(client) -> None:
    async with client:
        result = await client.call_tool("filter_tasks", {"task_filter": {}})
        assert result.data == []


async def test_complete_tasks_in_bulk(client) -> None:
    async with client:
        for title in ("A", "B"):
            await client.call_tool("add_task", {"title": title})
        result = await client.call_tool("complete_tasks", {"task_ids": [1, 2]})
        assert all(t.status == "completed" for t in result.data)


async def test_stats_resource_reports_counts(client) -> None:
    async with client:
        await client.call_tool("add_task", {"title": "A"})
        await client.call_tool("add_task", {"title": "B"})
        await client.call_tool("complete_task", {"task_id": 1})
        text = (await client.read_resource("tasks://stats"))[0].text
        assert "Total:           2" in text
        assert "50.0%" in text


async def test_today_resource_lists_new_tasks(client) -> None:
    async with client:
        await client.call_tool("add_task", {"title": "Fresh"})
        assert "Fresh" in (await client.read_resource("tasks://today"))[0].text


async def test_prompt_is_rendered(client) -> None:
    async with client:
        result = await client.get_prompt("scheduling_prompt", {"available_hours": 4})
        assert "4" in result.messages[0].content.text


def test_build_repository_selects_backend(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("TASK_BACKEND", "sqlite")
    monkeypatch.setenv("DB_PATH", str(tmp_path / "tasks.db"))
    repository = build_repository()
    assert isinstance(repository, SqliteTaskRepository)
    repository.close()


def test_build_repository_rejects_unknown_backend() -> None:
    with pytest.raises(ValueError, match="Unknown backend"):
        build_repository("postgres")
