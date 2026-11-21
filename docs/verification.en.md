# Verification scope

[繁體中文](verification.md) | **English**

[Documentation](README.md) · [Features](project/FEATURES.en.md)

Serialization, offline-model, WinProLadder GUI, and physical PLC verification are tracked
separately. Passing one layer never proves the next layer.

| Level | What the public project establishes | What it does not establish |
| --- | --- | --- |
| Schema and policy | Valid IR, I/O contract, writer rules, and workspace policy | GUI acceptance |
| Container and encoding | Framing, CRC, decode round-trip, and operand semantics | PLC execution |
| Offline model | Acceptance cases within the supported subset | Complete PLC scan semantics |
| GUI display | A specific artifact was opened and displayed by the user | Save/reopen or all variants |
| GUI round-trip | A specific artifact was saved and reopened | Physical PLC behavior |
| PLC | A specific CPU and site configuration was tested | Untested CPUs or forms |

## Public tests and private evidence

Public tests use only synthetic or programmatically generated data. They cover CRC, container
round-trips, parameterized Common FUN generation, decoded semantics, MCP stdio, ResourceLink
delivery, and safety rejections. Original WinProLadder exports, customer files, GUI screenshots,
manuals, and the native byte-anchor suite are retained outside the repository and are not needed
to install, run, or test the public project.

`sample-backed` means a form was compared with a privately retained native export. `inferred`
means it extends a known encoding rule. `GUI display verified` applies only to the specific
artifact observed. GUI save/reopen and PLC verification are not claimed unless explicitly stated.

Private verification records currently cover at least one representative form for each of the
**131 Common evidence keys** displayed by WinProLadder. This is not 131 distinct FUN numbers and
does not cover every valid parameter combination. No GUI save/reopen or physical PLC execution is
claimed for that set.

See [supported FUNC instructions](supported-functions.md) and query the running server with
`get_instruction_capabilities` for the exact current scope.
