# Changelog

[繁體中文](CHANGELOG.md) | **English**

This file lists only user-facing changes. Git history and automated tests retain implementation details and encoding evidence.

## Unreleased

- Added inferred FUN8 MOV signed 16-bit constant-source `F6AC` encode/decode support from the
  established `F4` register / `F6` constant operand-form rule and the user-provided WinProLadder
  screenshot. Offline modeling, references, boundaries, and exact-payload round-trip tests were
  added while explicitly retaining the lack of exported GUI-byte verification.
- Used the user-supplied WinProLadder `add_fix.ldr` export to add FUN11 register-`Sb`
  encode/decode support and the common OR register bank `R3904..R3967`. FUN8 MOV can now
  write OR registers; the offline model, device references, and exact-payload regressions
  were updated together.

## 1.1.1 — 2026-11-10

- Made compact responses the program default and exposed `response_mode`; added
  `--full-responses` for explicit full diagnostics.
- Split validation evidence into exact artifact, prior payload anchor, and physical PLC levels.
- Added stable structured generation errors, recipe-relevant resolved fields and assumptions,
  optional high-level `target_profile`, and prominent assumed-profile/timer warnings.
- Integrated the user-supplied FBs-32MC saved-project layout into the PDW model allowlist and
  mapped it to the existing `FBs-32MC-test30` Ladder profile, with parse, rebuild, and full
  project-generation regressions.
- Fixed compact artifact summaries dropping nested `.ldr` validation warnings. Text summaries,
  top-level structured `warnings`, and `validation.warnings` now agree, with an arithmetic-warning
  stdio regression.
- Shortened global MCP instructions and completed tool purposes, selection boundaries, parameter
  semantics, and output schemas. `get_design_guide(detail=true)` now owns the full Ladder/Network
  IR schema instead of repeating large unions in `tools/list`; runtime Pydantic validation remains.
- Added a named, range-constrained RTC register schema to `inspect_rtc_snapshot`, and clarified
  design-guide detail defaults, full examples, and intended usage.
- Clarified non-overwriting PDW creation and template-revision workflows and sharpened tool
  boundaries used to avoid false shadowing matches.
- Split workspace-audit reporting between broken source links and local-output links.
- Updated the locked `certifi` and `PyJWT` transitive dependencies for known security advisories.
- Reduced the public MCP surface from 22 to 19 base tools: removed `create_ldr` and
  `create_start_stop`, which are superseded by high-level generators, and folded instruction-family
  listing into `get_instruction_capabilities`. With four experimental PDW tools, 23 are exposed.

## 1.1.0 — 2026-11-05

- Added experimental `.pdw` inspection, template-based generation, and binary delivery, bringing the MCP tool count to 26.
- Added variable-length PDW generation through the shared Ladder compiler for local FBs-20MC/40MC/60MC templates.
- Added main-program sections, section/network comments, and CP950/Big5 component comments and descriptions.
- Added preservation, selection, ordering, and duplication of existing local expansion-module records; unknown parameters remain opaque.
- Check source, lowered programs, and decoded emitted bytes before writing, including I/O contracts, workspace policy, and acceptance cases.
- Private PDW templates are supplied locally; the repository includes no private PDW samples or masks.
- Added an English README, feature overview, core usage documentation, and the shared bilingual FUNC support table.
- Adjusted some text layout.

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
