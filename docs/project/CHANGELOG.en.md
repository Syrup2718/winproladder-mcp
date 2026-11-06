# Changelog

[繁體中文](CHANGELOG.md) | **English**

This file lists only user-facing changes. Git history and automated tests retain implementation details and encoding evidence.

## 1.1.0 — 2026-11-05

- Added experimental `.pdw` inspection, template-based generation, and binary delivery, bringing the MCP tool count to 26.
- Added variable-length PDW generation through the shared Ladder compiler for local FBs-20MC/40MC/60MC templates.
- Added main-program sections, section/network comments, and CP950/Big5 component comments and descriptions.
- Added preservation, selection, ordering, and duplication of existing local expansion-module records; unknown parameters remain opaque.
- Check source, lowered programs, and decoded emitted bytes before writing, including I/O contracts, workspace policy, and acceptance cases.
- Private PDW templates are supplied locally; the repository includes no private PDW samples or masks.
- Added an English README, feature overview, core usage documentation, and the shared bilingual FUNC support table.
- Adjusted some text layout.
- The workspace audit summary now separates broken source links from local-output links.
- Updated the locked `certifi` and `PyJWT` transitive dependencies to address known security advisories.
- Reduced the public MCP surface from 22 tools to 19: removed `create_ldr` and `create_start_stop`, which are superseded by the high-level generators, and folded instruction-family listing into `get_instruction_capabilities`.

PDW remains experimental: supplied 24MC/32MC samples are not yet integrated. FUNC199 is opaque inspection only. Control-flow generation, initialization of unknown module parameters, and hardware compatibility checks are not provided. User-reported GUI checks apply to specific artifacts, not all new outputs; physical PLC verification is pending.

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
