# WinProLadder MCP

Reverse-engineering and tooling project for FATEK WinProLadder `.ldr` files.

A working local stdio MCP server with lossless LDR parsing/encoding, a conservative
semantic IR, file editing tools, and a user-import-verified start/stop template.
Target profile: WinProLadder v3.28 / FBs-20MC. This is not full instruction coverage.

## Agent quick start

```powershell
uv sync --locked
uv run --locked winproladder-mcp --root C:/Fatek/winproladder-mcp
```

The server waits for MCP requests on stdin. Use the project `.codex/config.toml`
or adapt `examples/mcp-client.json` to your MCP client. Reload the client connection
after setup. See [agent guide](docs/agent-guide.md) for exact schemas, paths and limits.

Tools: `get_capabilities`, `inspect_ldr`, `read_ldr`, `validate_ladder`,
`simulate_ladder`, `create_ldr`, `create_start_stop`, `export_ldr`, `modify_network`.
New files go to `artifacts/`; existing files and original samples are never overwritten.
Timer, Counter, edge instructions and nested branches remain opaque/preserved;
they cannot yet be generated from IR.

## Development setup

Install [uv](https://docs.astral.sh/uv/), then run:

```powershell
uv sync
uv run pytest
uv run ruff check .
uv run mypy
```

The project pins Python 3.12 in `.python-version`; `uv sync` can install that
Python version when it is not already available.

## Repository layout

```text
src/winproladder_mcp/  Python package
samples/               Immutable ground-truth WinProLadder exports
tests/                 Automated tests
docs/                  Reverse-engineered format documentation
```

Do not edit existing `.ldr` samples. Add a new minimal sample when testing a new
instruction or varying one binary property.

## Read-only binary research

```powershell
uv run python -m winproladder_mcp.research inspect samples/test.ldr
uv run python -m winproladder_mcp.research hexdump samples/test.ldr
uv run python -m winproladder_mcp.research diff samples/w1.ldr samples/test2.ldr
```

`inspect` tests the currently observed framing and reports CRC validity; it is
not a semantic ladder parser. `diff` compares absolute byte offsets, so insertions
shift subsequent comparisons. These commands print to stdout and do not write files.
See [format findings](docs/ldr-format.md) and [requested samples](docs/sample-requests.md).
