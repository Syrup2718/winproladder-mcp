# PDW support (experimental)

[文件索引](README.md) · [功能總覽](project/FEATURES.md)

PDW inspection and generation are experimental and intentionally narrower than LDR support.
The public repository contains the parser and generator code, but does not distribute vendor or
customer project files, manuals, or private templates.

## Supported workflow

- Inspect a user-supplied local PDW within the configured workspace.
- Generate equal-length replacements through `generate_pdw`.
- Generate supported project layouts through `generate_project_pdw` when the caller supplies a
  compatible local template and all required project information.
- Preserve supported sections, CP950 comments, and selected module records.
- Write to a new file and return it through the MCP artifact resource.

## Limits

- PDW is not a general project editor and does not inherit every LDR instruction capability.
- Unsupported control flow, opaque sections, or incompatible templates are rejected.
- No bundled template implies compatibility with every CPU or WinProLadder version.
- Offline validation does not establish GUI round-trip or physical PLC behavior.

Keep local templates outside the repository and ensure that you have permission to use them.
