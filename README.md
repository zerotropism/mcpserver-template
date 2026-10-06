# mcpserver-template

A [copier](https://copier.readthedocs.io/) template for MCP servers built with
[FastMCP](https://github.com/jlowin/fastmcp): one server, persistence injected behind a
`Protocol`, and a contract test suite that any backend must pass unchanged.

## Generate a server

```bash
uvx copier copy gh:zerotropism/mcpserver-template my-server
cd my-server
uv sync --all-groups && uv run pytest
uv run my-server          # serves over stdio
```

| Question | Choices | Effect |
|---|---|---|
| `project_name` | free text, 60 characters at most | name shown to MCP clients |
| `project_slug` | lowercase, digits, dashes | distribution and command name; the module is the same with underscores |
| `description` | free text | `pyproject.toml` and README |
| `backend` | `memory`, `sqlite` | the one repository generated and wired in |
| `transport` | `stdio`, `http` | subprocess server, or streamable HTTP on a port with a Dockerfile |
| `auth` | `none`, `bearer` | asked for `http` only: JWT bearer tokens checked against a public key or a JWKS URL |
| `author_name` | free text | `LICENSE` |

The generated project comes with its tests, a CI workflow (ruff, pytest, pip-audit),
pre-commit hooks that run ruff from the project's own lock, Dependabot, an MIT licence and a
README. Commit `uv.lock` after the first `uv sync`.

## Drive it from a client

[mcp-servers-cli](https://pypi.org/project/mcp-servers-cli/) inspects the generated server and
lets a model use its tools:

```bash
uvx mcp-servers-cli inspect --stdio "uv run --directory $PWD my-server"
uvx mcp-servers-cli agent "Add a task: write the report" --model qwen3.5:4b-mlx \
  --stdio "uv run --directory $PWD my-server"
```

## Update a generated project

Answers are stored in the project's `.copier-answers.yml`; `uvx copier update` applies a newer
version of this template on top of local changes.

## Working on the template

```bash
uv sync --all-groups
uv run pytest
```

For each of the six combinations of answers, the tests render the template, run the generated
project's own ruff and pytest, then start the server and list its tools with the FastMCP
client: over stdio, or over HTTP on a free port, with a signed token for `bearer`, which must
also answer 401 to a request without one. Where Docker is installed, as on the CI runners, one
HTTP project is built into an image. The tests render the current checkout (`vcs_ref="HEAD"`),
not the latest tag.

```
copier.yml                         questions
template/
├── Dockerfile.jinja               HTTP only, excluded otherwise (see _exclude)
├── pyproject.toml.jinja
├── README.md.jinja
├── src/{{module_name}}/
│   ├── models.py                  plain Python, linted from this repository
│   ├── repository.py
│   ├── repositories/{{backend}}.py.jinja   one file, the chosen backend
│   └── server.py.jinja
└── tests/                         contract suite, server tests, entry-point check
tests/test_template.py             renders and checks every combination
```

Inside the generated package, imports are relative: most source files then need no Jinja and
stay lintable here. Only the files that depend on an answer carry the `.jinja` suffix.
