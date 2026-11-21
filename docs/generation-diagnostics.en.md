# LDR Generation Failure Diagnosis and Safe Recovery

[Documentation index](README.md) · [Architecture](../ARCHITECTURE.md) · [Verification](verification.en.md)

Generation tools keep every existing safety gate and add `generation_code` plus `diagnosis` to
handled failures. A diagnosis records the stage, Network index, instruction, operands, reason,
retry condition, verified alternative, next step, artifact state, and verification levels.
Failures always report `artifact_created=false` and preserve the original request.

| Code | Existing source | Status |
| --- | --- | --- |
| `INVALID_IR` | Ladder schema or required request fields | Public request path |
| `UNSUPPORTED_INSTRUCTION` | Action discriminator absent from the IR schema | Public request path |
| `UNSUPPORTED_OPERAND` | Unsupported bank, mode, constant, span, or physical-I/O operand | Public request path |
| `UNSUPPORTED_NETWORK_STRUCTURE` | Invalid flow structure, writer conflict, or policy-safe lowering failure | Validation/lowering path |
| `MISSING_ENCODING_EVIDENCE` | Decode-only anchor or unresolved relocation such as CALL/JMP/TDSP | Public validation path |
| `ENCODING_FAILURE` | Encoder fails after validation | Defensive gate; valid IR should not reach it |
| `ARTIFACT_VALIDATION_FAILURE` | Emitted bytes fail decode, policy, I/O, or acceptance replay | Defensive gate |
| `IMPORT_UNVERIFIED` | Strict Service path requires an exact GUI anchor | Strict candidate gate; ordinary MCP candidates remain explicitly unverified |

Automatic recovery is limited to Pydantic canonical normalization and the existing
truth-table-tested `lower_ladder` transformations. There is currently no separately evidenced
equivalent instruction encoding that is safe for automatic substitution. The MCP never guesses
opcodes, drops networks, removes interlocks, bypasses policy, or claims GUI/PLC verification.
Missing evidence requires a minimal native WinProLadder export with CPU/profile, software version,
and a one-variable operand comparison.
