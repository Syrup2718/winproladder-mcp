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

## Delivery and release

- Return a newly generated `.ldr` link first. Clearly separate offline checks, MCP simulation,
  WinProLadder GUI import, and real PLC verification.
- Do not overwrite artifacts or source samples.
- Do not bump versions or build wheels, sdists, or installers unless the user explicitly asks.
