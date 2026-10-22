# Contributing Guide

[繁體中文](CONTRIBUTING.md) | **English**

[Home](README.en.md) · [Development guide](docs/development.md) (Traditional Chinese)

## Reporting a Problem

Include the version, environment, minimal reproduction, expected result, and actual error. For `.ldr` issues, attach a shareable file, PLC model, WinProLadder version, and relevant screenshots. Remove private or confidential data first.

## Changes and Checks

Follow [AGENTS.md](AGENTS.md), then run:

```powershell
uv sync --locked
uv run python -m pytest -q
uv run ruff check .
uv run python -m mypy
uv run python -m winproladder_mcp.setup check
```

A pull request should explain what changed, how it was verified, and any remaining limitations.

## Adding an Instruction

1. Confirm the documented semantics, operand ranges, and time units.
2. Preserve original exports and screenshots, and verify each encoded field.
3. Implement the model, codecs, resource checks, and I/O checks.
4. Test raw bytes, boundaries, and invalid forms.
5. Update the feature table, capability reports, and examples.

Do not infer an opcode from a FUNC number. Do not claim support for an unverified form. Track encoding, simulation, GUI import, and physical PLC verification separately.

## Commit Guidelines

- Preserve original samples and save generated files separately.
- Use repository-relative links in documentation. Do not commit local artifacts or vendor PDFs.
- Keep manual titles and page numbers in citations.
- Do not bump the version or build packages unless a release is planned.
