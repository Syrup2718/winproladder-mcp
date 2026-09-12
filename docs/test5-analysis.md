# test5: register OR and loop generation

The original WinProLadder v3.28 export is preserved as `samples/test5.ldr`.
All seven records have valid CRCs. Decoding and rebuilding all seven networks
reproduces the entire 377-byte file, not just its instruction payloads.

| Network | Meaning | Payload |
| --- | --- | --- |
| N000 | X0 -> Y0 | `4000c100` |
| N001 | 19.OR R0 R1 R2 | `4fe8f4c80a000a020a04` |
| N002 | FOR 10 | `f590000a` |
| N003 | T1 preset 100 | `4fe8fd8000640392` |
| N004 | T1 -> Y1 | `4201c101` |
| N005 | X1 -> BREAK | `4001f476a7fe` |
| N006 | NEXT | `f491` |

## Agent usage

`get_design_guide` includes `register_or_loop`, and its returned JSON schema
describes the new `action` field. Send that IR to `generate_ldr` as usual.
Users still describe requirements in natural language; the host agent builds IR.

An action occupies its entire network. OR takes integer R-register indexes
`sa`, `sb`, `destination` (0..255) and a Boolean `enable` expression.
FOR takes `count` (1..16383); NEXT has no operands; BREAK takes `enable`.
FOR/NEXT cannot have contacts or coils. Unmatched loops and BREAK outside loops
are rejected during generation and semantic edits. Nested loops are rejected.
Boolean simulation explicitly refuses these instructions rather than producing
a misleading trace.

## Evidence and limitations

The basic manual page 7-36 defines FUN19 as bitwise OR, not Boolean contact OR.
Only ordinary 16-bit direct R-register operation is implemented. R-address
encoding `0x0A00 + 2*n` is inferred from R0/R1/R2; other addresses need import
verification. D/P modifiers, constants, indirect addressing and output flags
are not encoded by this implementation.

Advanced manual page 7-2 specifies BREAK inside FOR/NEXT. Pages 7-64 and 7-65
describe unconditioned FOR/NEXT, counts 1..16383, and a hardware maximum of five
nested levels. This compiler intentionally supports only one level: test5 alone
does not establish nested binary encoding. The observed BREAK suffix `A7FE` is
preserved in inferred generation but its meaning is not independently known.
Loop counts can cause watchdog expiry; no PLC execution is performed.

Basic manual page 7-2 specifies timer configuration-dependent time bases and
0..32767 constant presets. Existing compiler bounds describe its inferred binary
encoding, not validated PLC execution limits. Do not assume every T number is
0.01 seconds on an arbitrary PLC project. These FBe manuals are semantic
references, not proof of FBs-20MC hardware compatibility or `.ldr` opcodes.

## Remaining instruction families

The manuals also cover SET/RST, MC/SKP, edge functions, shift/counter functions,
MOV, arithmetic, comparison, conversion, tables/matrices, I/O, positioning,
interrupts, communication and floating-point instructions (through FUN220).
Their function numbers are not `.ldr` opcode values. They remain unsupported
for generation until their operand layout and binary encoding are implemented.
Unknown networks remain losslessly preserved by the forensic export path.
This release does not claim all manual instructions are implemented.
