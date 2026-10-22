# Feature overview

[繁體中文](FEATURES.md) | **English**

[Home](README.en.md) · [Supported FUNC instructions](docs/supported-functions.md)

This page summarizes the public capabilities and boundaries of v1.0.0. For exact schemas and operand restrictions, use `get_capabilities`, `list_instruction_families`, and `get_instruction_capabilities`.

## Outputs

| Artifact | Purpose |
| --- | --- |
| `.ldr` | WinProLadder ladder-diagram file |
| `.ldr.design.json` | Design decisions, assumptions, and device allocation from high-level generators |
| `.txt` | Optional component-comment table generated only when explicitly requested |

Component-comment files use `REF`, `COMMENT`, and `DESCRIPTION` columns with tab delimiters, CRLF newlines, and CP950/Big5 encoding.

## Generation methods

| Method | Intended use |
| --- | --- |
| Control recipe | Start/stop, SET/RESET, toggle, edge, delay, pulse, counter, forward/reverse, and star-delta controls |
| Sequence | Up to 16 steps using ordinary timers, native FUN87 pause/resume, or an explicitly supplied external pulse |
| System composition | Up to 24 independent control recipes with internal device allocation |
| Custom Ladder IR | Boolean conditions, timers/counters, registers, and supported native instructions |

All primary generators require an explicit `io_contract`. The MCP server does not invent physical X/Y devices, external clocks, or field wiring.

## Native instruction support

Supported forms are grouped as follows:

| Family | FUNC ranges and examples |
| --- | --- |
| Basic control | MC/MCE, DIFU/DIFD, UDCTR, MOV, TOGG |
| Integer and comparison | FUN11–37, arithmetic, CMP, BCD/BIN, PID, and zone comparison |
| Bit and data conversion | FUN40–65, bit/byte/nibble operations, shifts, Gray code, ASCII, and time conversion |
| Flow and peripherals | FOR/NEXT, IMDIO, keyboards, seven-segment display, PWM, and speed detection |
| Timing and hardware | FUN86–98, accumulative timers, WDT, HSC, and RAMP; some forms are encoding-only |
| Tables and matrices | FUN100–130, transfers, searches, queues/stacks, and matrix operations |
| Memory and status | FUN160–162 and FUN190 |
| Comparison contacts and floating point | FUN170–175 and FUN200–220 |

Support applies only to the documented operand combinations and modes. Unsampled D/P forms, indirect addressing, CPU-specific variants, and other combinations are not implied. CALL is decode-only; JMP generation is restricted to the confirmed complete sample form.

See the [supported FUNC table](docs/supported-functions.md) for instruction numbers and high-level status. Use `get_instruction_capabilities` for exact operands, modes, limits, and evidence.

## Reading and analysis

- Validate `.ldr` structure, CRC, raw payloads, and headers.
- Decode recognized networks in display order and preserve unknown records as opaque data.
- Report device reads and writes, timer settings, duplicate writers, and resource spans.
- Compare added, removed, and replaced networks between two files.
- Write modifications and exports to new files without overwriting the source.

## Safety and quality checks

- Permit only physical X/Y devices declared in the requirement.
- Reject meaningless M-to-M relay copies, redundant relay chains, and automatic relay helpers.
- Allow M devices to control native functions and receive native function results or status bits.
- Reject duplicate normal-coil writers across networks in high-level generators.
- Inspect the source, lowered program, and decoded emitted bytes before writing.
- Do not create a file when acceptance fails; `require_acceptance=true` can require explicit cases.

Workspace rules are defined by `.winproladder-policy.json`; this repository enables the strict policy by default.

## MCP tools

v1.0.0 provides 22 tools in four groups:

- Generation: `generate_control_ldr`, `generate_sequence_ldr`, `generate_system_ldr`, `generate_ldr`, `create_ldr`, `create_start_stop`, `generate_component_comments`
- Validation: `validate_ladder`, `simulate_ladder`
- Reading and modification: `inspect_ldr`, `read_ldr`, `analyze_ldr`, `compare_ldr`, `modify_network`, `export_ldr`, `get_ldr_artifact`
- Help and discovery: `get_capabilities`, `get_design_guide`, `list_instruction_families`, `get_instruction_capabilities`, `get_manual_reference`, `inspect_rtc_snapshot`

## Known limitations

- This is not a complete PLC emulator. Only listed Boolean, numeric, timer/counter, and native-function subsets have an offline model.
- The server does not operate WinProLadder, connect to a PLC, download programs, or control hardware.
- An `.ldr` file alone cannot prove the target CPU, time base, or hardware configuration.
- Some instructions support only sampled forms, decoding, or encoding.
- Component comments are a separate `.txt` file and are not embedded in `.ldr`.

The repository preserves 31 original WinProLadder exports containing 219 networks as regression evidence. These checks do not replace GUI import or physical PLC verification.
