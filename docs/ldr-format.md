# LDR codec boundary

[文件索引](README.md) · [驗證範圍](verification.md)

The public codec implements the container operations required by the MCP tools without
publishing private reverse-engineering records or third-party samples.

## Public guarantees

- Input size and record framing are bounded before allocation.
- Record CRC is validated by default; forensic reads must opt out explicitly.
- Known records decode to typed Ladder IR and re-encode deterministically.
- Unknown records remain opaque on lossless read/export paths.
- Semantic edits are rejected when the document contains unsupported framing or networks.
- Generated files are parsed and decoded from the exact emitted bytes before the final write gate.
- Writes create a new artifact and never overwrite the source.

The supported CPU headers and instruction forms are implementation details exposed through
`get_capabilities` and `get_instruction_capabilities`. A recognized header or valid CRC does not
prove GUI importability, CPU suitability, or PLC behavior.

Original exports, vendor binaries, manuals, byte maps, addresses, and investigative notes are
maintained outside the public repository. Public tests use synthetic containers and generated
programs; the private interoperability suite is not a runtime dependency.
