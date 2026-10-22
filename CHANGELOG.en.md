# Changelog

[繁體中文](CHANGELOG.md) | **English**

This file lists only user-facing changes. Git history and automated tests retain implementation details and encoding evidence.

## Unreleased

- Added an English README, feature overview, core usage documentation, and the shared bilingual FUNC support table.

## 1.0.0 — 2026-10-21

- Added generation, parsing, analysis, modification, and binary download of WinProLadder `.ldr` files.
- Added high-level control recipes, sequence control, custom Ladder IR, and 22 MCP tools.
- Added pre-write checks for schemas, I/O contracts, resource spans, workspace policy, and decoded output.
- Added compact capability queries, acceptance reports, and strict writer checks.
- Added CP950/Big5 component-comment `.txt` generation.
- Added Windows, macOS, and Linux installation entry points with locked dependencies.
- Adopted the MIT License, copyright syrup2718.
- Streamlined public examples and moved test-only IR into test fixtures.

Tests, static checks, and MCP integration passed for this release. These are offline verification results; they do not mean that every output has been imported into the WinProLadder GUI or tested on a physical PLC.
