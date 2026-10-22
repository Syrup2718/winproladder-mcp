# Usage Reference

[繁體中文](reference.md) | **English**

[Documentation index](README.md) · [Features](../FEATURES.en.md)

## Control Recipes

`generate_control_ldr` supports:

- `start_stop`, `set_reset`, and `toggle`
- `rising_edge` and `falling_edge`
- `on_delay`, `off_delay`, `pulse`, and `counter`
- `forward_reverse` and `star_delta`

`signal` and `output` are required. Recipes that need `stop`, `reset`, or `reverse` also require the corresponding condition. Every Y address used by a multi-output recipe must appear in `io_contract.outputs`.

`generate_system_ldr` can combine up to 24 independent recipes and allocate internal M/T/C devices. It does not coordinate a process across recipes.

## Sequence Control

`generate_sequence_ldr` supports 1–16 steps. Each step may define outputs, duration, a completion condition, and a timeout.

- Native T devices are used by default, and durations must be multiples of 10 ms.
- If pause is required without an external clock, FUN87 and register state are used.
- External pulse mode is used only when the requirement explicitly supplies a clock.
- At most one transition occurs per scan. Completion takes priority when completion and timeout occur together.

## Custom Ladder IR

Minimal example:

```json
{"networks": [{"condition": "(Y0 OR X0) AND NOT X1", "coils": [{"device": "Y", "address": 0}]}]}
```

Conditions support AND/OR/NOT, `&`/`|`/`!`, parentheses, and TRUE/FALSE. All primary generation tools require an I/O contract. The source, lowered program, and emitted bytes are checked separately.

Timer example:

```json
{"networks": [{"block": {"type": "timer", "address": 0, "preset": 100, "enable": "X0"}}]}
```

Timer `preset` is measured in time-base ticks, not milliseconds. With a `.01S` time base, `preset=100` means one second. The MCP cannot determine the target project's time base from the `.ldr` file alone.

Use `get_design_guide` for the complete schema. Use `get_instruction_capabilities` for operands and modes of individual native FUNC instructions.

## Component Comments

When the user explicitly asks to “add component comments,” call `generate_component_comments`. Each item contains:

| Field | Description |
| --- | --- |
| `ref` | Device reference, such as X0, Y0, M0, or D1 |
| `comment` | Short comment; may be empty |
| `description` | Additional description; may be empty |

The result is a separate `.txt` file with `REF`, `COMMENT`, and `DESCRIPTION` columns, separated by tabs and encoded as CP950/Big5 with CRLF line endings. Duplicate references, control characters, and text that cannot be represented in CP950 are rejected.

## Simulation and Acceptance

`simulate_ladder` runs up to 256 scans. Without `scan_ms`, it simulates Boolean logic only. With `scan_ms`, it can also simulate the supported Timer/Counter and FUN87–89 subset.

Generation tools may include 1–32 acceptance cases. Each case checks the source model and then replays the emitted bytes. No file is written if an assertion fails. Set `require_acceptance=true` to require cases.

The model is not a PLC simulator. Unsupported native functions are rejected explicitly instead of returning a partial trace.

## File Operations

- `inspect_ldr`: inspect structure, payloads, and CRCs
- `read_ldr`: decode records in display order
- `analyze_ldr`: explain networks and cross-reference devices
- `compare_ldr`: compare two files
- `modify_network`: insert, replace, or delete a network and save as a new file
- `export_ldr`: preserve unknown data and save as a new file

All writes are restricted to the workspace output directory, and existing files are not overwritten. Unknown records can be preserved and analyzed; they are not regenerated when compliance with the current policy cannot be proven.
