# Repository guide for agents

This repository provides an offline MCP server for reading, generating, validating,
and safely rewriting FATEK WinProLadder files. It does not connect to a PLC.

## Read the relevant source of truth

- Read [ARCHITECTURE.md](ARCHITECTURE.md) before changing module boundaries or the
  generation pipeline.
- Read [docs/agent-guide.md](docs/agent-guide.md) before generating or modifying Ladder.
- Read [docs/development.md](docs/development.md) before implementation or test work.
- Read [docs/ldr-format.md](docs/ldr-format.md) or [docs/pdw-format.md](docs/pdw-format.md)
  before changing a file codec.
- Read `.winproladder-policy.json` for every Ladder operation. Never disable, bypass,
  or weaken it to produce an artifact.

## Non-negotiable invariants

- Preserve the user's I/O, polarity, priority, reset, and timing contract. Never invent
  physical inputs, outputs, or external clocks.
- Do not synthesize meaningless M-to-M relay copies, redundant helper chains, or disguised
  equivalents. Native functions may consume M controls and produce M results/status bits
  when the workspace policy allows them.
- Keep numeric values and sequence state in native registers. Verify the source IR, lowered
  program, and decoded emitted bytes before delivery.
- Preserve unknown file data on lossless read/export paths; reject edits that cannot be
  validated safely.
- Distinguish documented PLC semantics from this repository's serialization and simulation
  support. A missing encoder is not evidence that a PLC operand or mode is illegal.

## Git workflow

- Treat `main` as the only long-lived branch. Normally work on `main` or reuse at most one
  temporary branch for the current task; do not create a branch for every edit or agent run.
- Keep one task's implementation, tests, fixes, and review changes on the same temporary branch.
  Create another branch only for an independent PR or to isolate unrelated work.
- Small, low-risk changes do not require a branch or PR. Use a PR when independent review,
  CI isolation, or a separately mergeable change is useful.
- Before changing branches or preparing commits, inspect `git status` and preserve all existing
  user changes. Never discard, overwrite, or mix unrelated work.
- Keep the checks in [docs/development.md](docs/development.md) intact. Do not weaken formatting,
  lint, type, test, coverage, architecture-boundary, audit, or CI gates to make a change pass.
- After a PR merges, first verify its commits are in an updated local `main`. A temporary branch
  may be cleaned up only when it is fully merged and has no unsaved work.
- Do not merge a PR, delete a local or remote branch, force-push, rewrite remote history, or remove
  uncommitted changes without the user's explicit approval.

## Delivery and release

- Return a newly generated `.ldr` link first. Clearly separate offline checks, MCP simulation,
  WinProLadder GUI import, and real PLC verification.
- Do not overwrite artifacts or source samples.
- Do not bump versions or build wheels, sdists, or installers unless the user explicitly asks.
