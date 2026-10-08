# Ladder generation requirements

## Release preferences

- Do not build installation packages (wheel, sdist, or installers) unless the user
  explicitly requests them. Ordinary feature updates do not authorize packaging.
- Do not bump version numbers unless the user explicitly requests a version update.
  Continue updating implementation, tests, and documentation without a version bump;
  describe unreleased changes separately from the last packaged release.

## Generation constraints

- This workspace forbids M contacts driving M coils (including self-holds, copies,
  SET/RESET destinations, block status outputs, and automatically lowered helpers).
  The user explicitly requested this as a permanent architecture constraint.
- Read `.winproladder-policy.json`; never disable or weaken it to get a file out.
- Use native registers for numeric values and sequence state. Unconditional
  comparisons may produce M status bits used by Y outputs or timer/register EN.
  Do not replace forbidden M chains with equivalent disguised relay chains.
- Check the source, lowered program, and decoded emitted bytes. If supported
  instructions cannot implement the requirement, report the precise limitation.
- For the numeric countdown display, each 50 ms digit slot is ON for 40 ms and
  OFF for 10 ms, including repeated digits such as 9.9 and 0.0. Seconds come first,
  tenths second. Never omit the blank interval just because adjacent digits match.
- Preserve the user's current timing and I/O contract. Do not invent inputs.
- Return the new `.ldr` link first. Clearly distinguish independent offline
  modeling, MCP built-in simulation, GUI import, and real PLC verification.

## Instruction reference

- For instruction modes, operand ranges, units, D/P variants and behavior, consult
  the user-provided `C:/Fatek/FBe進階篇/進階篇應用指令.pdf` before assuming a limitation
  or asking the user to explain it. Use the basic and RTC manuals where applicable.
- Separate documented PLC semantics from implemented `.ldr` serialization. A missing
  encoding is not an illegal PLC operand or unsupported PLC mode. Record exact pages
  for unresolved differences between the manual and supplied GUI exports.
