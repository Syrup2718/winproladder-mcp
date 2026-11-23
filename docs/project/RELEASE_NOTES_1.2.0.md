# WinProLadder MCP v1.2.0

WinProLadder MCP v1.2.0 is a backward-compatible feature release focused on safe,
parameterized generation of commonly used FATEK instructions. The server remains an offline file
tool: it does not connect to, download to, or control a PLC.

## Highlights

- Added `generate_common_fun_ldr`, bringing the public MCP surface to 24 tools.
- Added parameterized generation for 131 Common FUN evidence keys through the existing Production
  codec, workspace policy, I/O contract, CRC validation, emitted-byte decode/readback, and writer
  checks.
- Added structured LDR generation diagnostics with stable failure categories, pipeline stage,
  network and operand context, evidence gaps, retry conditions, and verification levels.
- Added an isolated public-release gate that rejects restricted evidence paths and common secret or
  private-path patterns before running the full validation suite.

The 131 evidence keys are supported generation entries, not a claim that 131 complete FUN
instructions or every operand, mode, CPU profile, indirect form, and wiring arrangement are
supported.

## Instruction and operand updates

- FUN11 through FUN14 accept signed 16-bit constant `Sb` values. Negative-constant forms have
  user-confirmed WinProLadder GUI display evidence.
- FUN11 ADD supports the sampled direct-register `Sb` form. Register forms for SUB, MUL, and DIV
  remain identified as inferred where native sample evidence is unavailable.
- FUN8 MOV and the shared direct-register codec support the documented OR register window used by
  the Common FUN generator.
- FUN92 HSCTR supports HSC1, HSC2, HSC3, and HSTA selectors when an explicit compatible CPU profile
  is supplied. These selectors have user-confirmed GUI display evidence.
- Common generation includes the documented subsets of integer, logical, comparison, conversion,
  timer/counter, PID, floating-point, table, matrix, packing, shift, peripheral, pulse, memory, and
  system-status instruction families listed in `docs/supported-functions.md`.

## Fixes and safety changes

- Corrected the FUN8 MOV signed 16-bit constant-source opcode using sampled WinProLadder export
  evidence.
- Rejected ADCNV `Pl=1` after GUI probing showed that the inferred bytes display as FUN161P.
- Restricted FUN93D to the sampled HSC0 form after probing showed that non-HSC0 selector bytes alter
  the 32-bit source value rather than selecting another counter.
- Artifact download tools now return a stable `ARTIFACT_NOT_FOUND` result with `written=false` for
  missing files.
- Component comments are checked against WinProLadder's 16-byte CP950/Big5 limit before writing.

## Compatibility

- This is a backward-compatible minor release. Existing supported MCP tools and valid v1.1.1
  requests remain available.
- The new MCP tool and additional response diagnostics are additive.
- Requests that relied on the invalid inferred ADCNV `Pl=1` or FUN93D non-HSC0 encodings are now
  rejected before writing. Those forms were not established supported PLC behavior.
- PDW generation remains experimental and template-based. Existing format, model, and instruction
  restrictions still apply.

## Verification

The v1.2.0 release candidate passed:

- Ruff formatting and lint checks.
- Strict mypy validation for 50 source files.
- 1,143 pytest tests with 90.34% total coverage.
- MCP subprocess self-check with 24 listed tools.
- Common FUN evidence-key count and parameterized generation checks for 131 entries.
- LDR generation, CRC validation, emitted-byte decode/readback, workspace audit, and public-content
  safety checks.

These are offline repository and serialization checks. GUI display evidence applies only to the
specific forms documented above. It does not mean that every generated variant has completed a
WinProLadder save/reopen round trip, and it is not physical PLC execution verification. Users must
validate hardware-dependent I/O, timing, CPU profiles, peripheral resources, and field wiring in
their target environment.

## Security and publication boundary

The public repository excludes native customer or vendor `.ldr` evidence, GUI screenshots,
reverse-engineering workspaces, private research scripts, proprietary binaries, manuals, and local
credentials. Public tests use synthetic or programmatically generated fixtures and do not require
the private evidence archive.
