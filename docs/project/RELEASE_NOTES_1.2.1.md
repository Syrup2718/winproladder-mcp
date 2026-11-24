# WinProLadder MCP v1.2.1

WinProLadder MCP v1.2.1 is a backward-compatible patch release that fixes constant operands in
FUN170–175 comparison contacts. The server remains an offline file tool and does not connect to,
download to, or control a PLC.

## Fixed

- FUN170–175 comparison contacts no longer reject ordinary constant `Sb` operands from 0 through
  32767.
- Constant comparisons can appear in the first or a subsequent series position for all six signed
  16-bit relations: equal, greater-than, less-than, not-equal, greater-or-equal, and less-or-equal.
- Expressions such as `R100 > 0 AND R100 < 100 AND D1 = 1` can now be emitted directly as FUN171,
  FUN172, and FUN170 contacts without helper registers or FUN37 ZNCMP substitution.
- The bounded offline model can execute direct R/D comparison chains, enabling source and decoded
  emitted-byte acceptance checks for these programs.

No MCP tools were added or removed. The public surface remains 24 tools, and the Common FUN matrix
remains 131 evidence keys; this patch expands operand forms within existing FUN170–175 entries.

## Encoding and evidence boundary

The encoder uses the F6 constant marker established by a native FUN175 series-constant sample and
the existing FUN170–175 first/series opcode families. The exact artifact below has user-confirmed
WinProLadder GUI display evidence:

```text
R100 > 0 AND R100 < 100 AND D1 = 1 -> Y0
```

Its GUI display shows FUN171, FUN172, and FUN170 with the expected operands and output. Other
constant values, relations, and position combinations are parameterized and round-trip tested but
remain classified as inferred until separately checked in WinProLadder.

GUI display verification does not mean that the file has completed a WinProLadder save/reopen
round trip, and it is not physical PLC execution verification. Hardware-dependent behavior and
field wiring remain the user's responsibility.

## Compatibility

- Existing valid v1.2.0 requests and generated forms remain supported.
- The accepted schema is widened only for constant operands that were previously rejected.
- Constant `Sb` values remain limited to 0 through 32767. Negative comparison constants are not
  accepted by this patch.
- Comparison contacts remain a series-chain form; arbitrary OR branching or mixed Boolean/contact
  wiring is not introduced.
- The comparison-chain offline model is limited to direct R/D word operands.

## Verification

The v1.2.1 release candidate includes:

- Exact byte and decode/readback checks for the GUI-confirmed three-contact chain.
- Parameterized encode/decode round trips for all six relations, first/series positions, and
  representative constant boundaries.
- Eight acceptance cases covering strict range boundaries, negative register values, and D1
  mismatch cases.
- CRC, architecture policy, I/O contract, MCP self-check, Ruff, strict mypy, pytest coverage, and
  public-release safety-gate checks.

The public repository continues to exclude native customer or vendor evidence, GUI screenshots,
reverse-engineering workspaces, proprietary binaries, manuals, and credentials.
