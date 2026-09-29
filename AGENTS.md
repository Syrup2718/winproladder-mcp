# Ladder generation requirements

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
