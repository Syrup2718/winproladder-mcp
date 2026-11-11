# WinProLadder MCP architecture

This document is the map of the repository: its system boundary, major modules, dependency
direction, artifact pipeline, and sources of truth. Operational details live in the linked
documents rather than in `AGENTS.md`.

## System boundary

WinProLadder MCP is an **offline file tool**. It accepts MCP requests, constructs or reads a
typed Ladder model, validates it, and writes downloadable `.ldr`, `.pdw`, or component-comment
artifacts. It does not operate WinProLadder, download to a PLC, or claim real-machine behavior.

Generated files belong in `artifacts/`. Original evidence belongs in `samples/` and test
fixtures; it must not be rewritten to make an implementation pass.

## Dependency direction

The intended dependency flow is:

```text
MCP client
    |
    v
server.py                 request/response schemas and MCP resources
    |
    v
service.py                filesystem boundary and end-to-end orchestration
    |
    +--> control.py / sequence.py / system.py     high-level builders
    |
    +--> ir.py / logic.py                         typed Ladder model and semantics
    |         |
    |         +--> layout.py / optimize.py        connected-layout lowering
    |         +--> *_functions.py                 native instruction codecs
    |
    +--> architecture.py / io_contract.py         workspace and physical-I/O gates
    +--> acceptance.py / runtime.py                bounded offline behavior model
    +--> ldr.py / pdw.py / pdw_project.py          binary containers
              |
              v
          artifacts/
```

Dependencies should point downward through this diagram. In particular:

- `server.py` translates MCP inputs and outputs; it should not implement binary formats.
- `service.py` owns path safety, no-overwrite writes, and the full validation pipeline.
- Domain and codec modules should be deterministic and independent of MCP transport and the
  workspace filesystem.
- High-level builders produce the same `Ladder` IR accepted by the low-level generator; they
  do not get a separate validation path.
- Format parsers preserve unknown data on lossless operations. Semantic edits require known,
  validated framing and instructions.

This direction is enforced at its highest-value boundaries by
[`tests/test_import_boundaries.py`](tests/test_import_boundaries.py): lower-level modules cannot
import the transport, orchestration, capability, or high-level generation layers. The existing
codec/IR cycle is recorded in
[`tests/fixtures/import-boundaries.json`](tests/fixtures/import-boundaries.json) as a ceiling:
edges and cycle membership may be removed, but new edges inside it or new cycle members fail CI.
This prevents further drift without requiring a core refactor.

## Major areas

| Area | Primary modules | Responsibility |
| --- | --- | --- |
| MCP boundary | `server.py`, `setup.py` | Tool schemas, compact responses, resources, stdio entry point, installation checks |
| Orchestration | `service.py` | Safe paths, artifact lifecycle, generation/read/edit/export workflows |
| Public capability model | `capabilities.py`, `design.py`, `manual_reference.py` | Report implemented scope and documented limitations |
| High-level generation | `control.py`, `sequence.py`, `system.py`, `native_state.py` | Convert control specifications into Ladder IR |
| Ladder domain | `ir.py`, `logic.py`, `analysis.py` | Typed networks, expressions, instruction dispatch, semantic inspection |
| Layout and policy | `layout.py`, `optimize.py`, `architecture.py`, `io_contract.py`, `generation_quality.py` | Lower connected logic and reject unsafe architecture, I/O, or writer behavior |
| Instruction codecs | `*_functions.py`, `instruction_catalog.py`, `registers.py`, `peripheral.py`, `floating.py` | Validate operands and encode/decode native function payloads |
| Offline verification | `acceptance.py`, `runtime.py`, `timing.py`, `validation_evidence.py` | Bounded simulation, executable acceptance cases, and evidence reporting |
| LDR format | `ldr.py`, `profiles.py`, `research.py` | Container framing, records, CRC, sampled headers, forensic inspection |
| PDW format | `pdw.py`, `pdw_project.py`, `pdw_modules.py` | Experimental template and project generation with separate format limits |
| Supporting artifacts | `component_comments.py` | CP950/Big5 component-comment exports |

The large `ir.py` is currently both the domain schema and the instruction codec dispatcher.
Instruction-family implementations are split into focused modules; future extraction should
keep one canonical `Ladder` model rather than introduce parallel representations.

## LDR generation pipeline

Every normal generation path converges in `Service.create`:

1. Validate executable acceptance cases against the source `Ladder`, when supplied.
2. Enforce `.winproladder-policy.json`, writer rules, and the physical I/O contract on source IR.
3. Lower expressions to a connected layout, then repeat architecture and writer checks.
4. Run semantic validation and compile each network to an LDR record.
5. Encode the document, parse the exact bytes, and decode every emitted network.
6. Recheck architecture, writers, I/O, and acceptance against the decoded artifact.
7. Pass through the final write gate, create a new file exclusively, and return its SHA-256.

```text
specification or JSON
        -> source Ladder
        -> validated/lowered Ladder
        -> network payloads
        -> LDR records + CRC
        -> encoded bytes
        -> parsed and decoded Ladder
        -> final policy gate
        -> exclusive artifact write
```

LDR records are stored in physical order, which is the reverse of the displayed network order.
Do not bypass `Service.write`: it is the last architecture check for generate, edit, export, and
direct service writes.

## Core invariants

### Workspace policy

`.winproladder-policy.json` is loaded for each operation. Invalid policy must fail closed. With
the current policy, ordinary M-to-M relay copies, implicit MC relay chains, and helpers introduced
by lowering are forbidden. Native function result/status pins are a narrow explicit exception;
ordinary coils do not become functions through naming or placement.

### File integrity

- LDR parsing is bounded to 16 MiB and validates framing and CRC when requested.
- Read/export paths retain opaque data; editing requires known headers, trailers, and networks.
- Output names are basenames with the required suffix and are created with exclusive mode.
- Unknown opcodes are not guessed, repaired, or silently discarded.

### Verification vocabulary

| Level | What it establishes |
| --- | --- |
| Source validation | The requested IR passes schema, architecture, I/O, writer, and semantic checks |
| Lowered validation | Layout transformation did not introduce forbidden helpers or dependencies |
| Emitted-byte validation | The exact encoded document parses and decodes to a policy-compliant program |
| MCP simulation | Supported instructions satisfy supplied cases in the bounded offline model |
| GUI verification | WinProLadder imports and displays the artifact as intended; performed externally |
| PLC verification | Target hardware behavior has been tested; never implied by this repository |

The offline runtime is intentionally incomplete. Unsupported behavior must fail before execution,
not return a partial trace that looks successful. See [verification scope](docs/verification.md).
Generation failures retain these gates and expose stage-specific diagnostics; safe recovery is
limited to the existing validated normalization and lowering pipeline. See
[generation diagnostics](docs/generation-diagnostics.md).

## Sources of truth

| Question | Source of truth |
| --- | --- |
| Agent entry points and invariants | [AGENTS.md](AGENTS.md) |
| Repository boundaries and pipeline | This document |
| Live workspace relay policy | `.winproladder-policy.json` and `architecture.py` |
| Implemented tool/instruction scope | `capabilities.py` and [supported functions](docs/supported-functions.md) |
| Ladder generation and delivery rules | [Agent guide](docs/agent-guide.md) |
| LDR/PDW serialization evidence | [LDR format](docs/ldr-format.md), [PDW format](docs/pdw-format.md), samples, and tests |
| Development workflow and required checks | [Development guide](docs/development.md) |
| PLC instruction semantics | User-provided FATEK manuals; record exact pages when implementation evidence differs |
| Released versus unreleased behavior | [Changelog](docs/project/CHANGELOG.md) and the current source tree |

## Change rules

- A new instruction needs manual evidence, GUI-exported byte evidence, schema and codec support,
  resource/I/O analysis, tests, and a capability update.
- A new MCP write path must converge on the same service write gate.
- A new high-level generator must emit canonical `Ladder` IR and use the same source/lowered/emitted
  validation pipeline.
- A new architectural invariant should become a test, linter, schema constraint, or service gate;
  prose is the explanation, not the enforcement mechanism.
- Keep serialization support, offline simulation support, GUI evidence, and PLC legality as four
  separate claims.
