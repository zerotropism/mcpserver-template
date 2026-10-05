"""Render every combination of the template and hold each result to its own CI."""

import subprocess
from pathlib import Path

import pytest
from copier import run_copy
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

ROOT = Path(__file__).resolve().parent.parent
SLUG = "demo-tasks"
TOOLS = {"add_task", "complete_task", "complete_tasks", "delete_task", "filter_tasks"}
COMBINATIONS = [{"backend": "memory"}, {"backend": "sqlite"}]


def run(cwd: Path, *command: str) -> str:
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
    assert result.returncode == 0, f"{' '.join(command)}\n{result.stdout}\n{result.stderr}"
    return result.stdout


@pytest.fixture(params=COMBINATIONS, ids=lambda answers: "-".join(answers.values()))
def project(request, tmp_path) -> Path:
    """A freshly generated project. vcs_ref=HEAD renders this checkout, not the latest tag."""
    destination = tmp_path / SLUG
    answers = {"project_name": "Demo Tasks", "author_name": "Test", **request.param}
    run_copy(str(ROOT), destination, data=answers, defaults=True, vcs_ref="HEAD", quiet=True)
    run(destination, "uv", "sync", "--all-groups", "-q")
    return destination


def test_generated_project_passes_its_own_checks(project) -> None:
    run(project, "uv", "run", "ruff", "check", ".")
    run(project, "uv", "run", "ruff", "format", "--check", ".")
    run(project, "uv", "run", "pytest", "-q")


async def test_generated_server_lists_its_tools_over_stdio(project, tmp_path) -> None:
    command = ["run", "--directory", str(project), SLUG]
    transport = StdioTransport("uv", command, env={"DB_PATH": str(tmp_path / "e2e.db")})
    async with Client(transport) as client:
        names = {tool.name for tool in await client.list_tools()}
    assert names == TOOLS


def test_answers_are_recorded_for_copier_update(project) -> None:
    answers = (project / ".copier-answers.yml").read_text()
    assert "_src_path:" in answers
    assert "backend:" in answers
