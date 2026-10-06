"""Render every combination of the template and hold each result to its own CI."""

import asyncio
import os
import shutil
import socket
import subprocess
import urllib.error
import urllib.request
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from copier import run_copy
from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from fastmcp.server.auth.providers.jwt import RSAKeyPair

ROOT = Path(__file__).resolve().parent.parent
SLUG = "demo-tasks"
TOOLS = {"add_task", "complete_task", "complete_tasks", "delete_task", "filter_tasks"}
ISSUER = "https://issuer.test"
COMBINATIONS = [
    {"backend": "memory", "transport": "stdio"},
    {"backend": "sqlite", "transport": "stdio"},
    {"backend": "memory", "transport": "http", "auth": "none"},
    {"backend": "sqlite", "transport": "http", "auth": "none"},
    {"backend": "memory", "transport": "http", "auth": "bearer"},
    {"backend": "sqlite", "transport": "http", "auth": "bearer"},
]


def run(cwd: Path, *command: str) -> str:
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
    assert result.returncode == 0, f"{' '.join(command)}\n{result.stdout}\n{result.stderr}"
    return result.stdout


def render(destination: Path, answers: dict) -> Path:
    """vcs_ref=HEAD renders this checkout, not the latest tag."""
    data = {"project_name": "Demo Tasks", "author_name": "Test", **answers}
    run_copy(str(ROOT), destination, data=data, defaults=True, vcs_ref="HEAD", quiet=True)
    run(destination, "uv", "sync", "--all-groups", "-q")
    return destination


@pytest.fixture(params=COMBINATIONS, ids=lambda answers: "-".join(answers.values()))
def generated(request, tmp_path) -> tuple[Path, dict]:
    return render(tmp_path / SLUG, request.param), request.param


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


async def wait_for_port(port: int, timeout: float = 30.0) -> None:
    for _ in range(int(timeout * 10)):
        try:
            _, writer = await asyncio.open_connection("127.0.0.1", port)
        except OSError:
            await asyncio.sleep(0.1)
        else:
            writer.close()
            return
    raise TimeoutError(f"nothing listening on port {port}")


@asynccontextmanager
async def http_server(project: Path, env: dict) -> AsyncIterator[str]:
    """Run the generated server on a free port and yield its MCP endpoint."""
    port = free_port()
    command = ["uv", "run", "--directory", str(project), SLUG]
    environment = {**os.environ, **env, "MCP_PORT": str(port)}
    server = subprocess.Popen(command, env=environment, stdout=subprocess.DEVNULL)
    try:
        await wait_for_port(port)
        yield f"http://127.0.0.1:{port}/mcp"
    finally:
        server.terminate()
        server.wait(timeout=10)


async def tool_names(client: Client) -> set[str]:
    async with client:
        return {tool.name for tool in await client.list_tools()}


def status_without_token(url: str) -> int:
    request = urllib.request.Request(url, data=b"{}", method="POST")
    request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request) as response:
            return response.status
    except urllib.error.HTTPError as error:
        return error.code


def test_generated_project_passes_its_own_checks(generated) -> None:
    project, _ = generated
    run(project, "uv", "run", "ruff", "check", ".")
    run(project, "uv", "run", "ruff", "format", "--check", ".")
    run(project, "uv", "run", "pytest", "-q")


async def test_generated_server_lists_its_tools(generated, tmp_path) -> None:
    project, answers = generated
    env = {"DB_PATH": str(tmp_path / "e2e.db")}
    if answers["transport"] == "stdio":
        command = ["run", "--directory", str(project), SLUG]
        names = await tool_names(Client(StdioTransport("uv", command, env=env)))
    elif answers["auth"] == "none":
        async with http_server(project, env) as url:
            names = await tool_names(Client(url))
    else:
        keys = RSAKeyPair.generate()
        env |= {"MCP_JWT_PUBLIC_KEY": keys.public_key, "MCP_JWT_ISSUER": ISSUER}
        env |= {"MCP_JWT_AUDIENCE": SLUG}
        token = keys.create_token(subject="e2e", issuer=ISSUER, audience=SLUG)
        async with http_server(project, env) as url:
            names = await tool_names(Client(url, auth=token))
            assert status_without_token(url) == 401
    assert names == TOOLS


def test_docker_files_come_with_http_only(generated) -> None:
    project, answers = generated
    expected = answers["transport"] == "http"
    assert (project / "Dockerfile").exists() is expected
    assert (project / ".dockerignore").exists() is expected


def test_answers_are_recorded_for_copier_update(generated) -> None:
    project, answers = generated
    recorded = (project / ".copier-answers.yml").read_text()
    assert "_src_path:" in recorded
    assert f"transport: {answers['transport']}" in recorded


def docker_available() -> bool:
    """The binary alone is not enough: Docker Desktop may be installed but not running."""
    if shutil.which("docker") is None:
        return False
    return subprocess.run(["docker", "info"], capture_output=True).returncode == 0


@pytest.mark.skipif(not docker_available(), reason="no running Docker daemon")
def test_docker_image_builds_and_imports_the_server(tmp_path) -> None:
    answers = {"backend": "sqlite", "transport": "http", "auth": "bearer"}
    project = render(tmp_path / SLUG, answers)
    tag = f"{SLUG}:template-test"
    run(project, "docker", "build", "--quiet", "-t", tag, ".")
    try:
        check = ["docker", "run", "--rm", "--entrypoint", "python", tag]
        run(project, *check, "-c", "import demo_tasks.server")
    finally:
        subprocess.run(["docker", "rmi", "-f", tag], capture_output=True)
