# Direct test run - 2026-09-12

The hourly automation `winproladder-mcp` was paused at the user's request.
No future execution is scheduled by this work. Tests were run directly.

## Passed

- Source suite: 141 tests, including six complete real-stdio MCP example flows.
- Every example: generate, strict-CRC parse, MCP read, regeneration, identical
  SHA-256. This proves encoding round trips, not PLC behavior.
- Boolean acceptance: start, hold, stop priority, incorrect polarity and
  incorrect expectations. Failed requirements do not create a file.
- Timing: threshold, reset/restart, scan periods 1/7/20/60000ms, rising-edge
  counting, reset priority, duplicate writers, invalid inputs/configurations,
  later-network T contacts and inverted coils.
- Real MCP negative timed acceptance: failure is returned and no file exists.
- Ruff and strict mypy pass.
- `uv build`: wheel and source archive build successfully.
- Isolated wheel install: real MCP self-check passes with 13 tools and the
  previously verified start/stop SHA-256; no repository assets are required.
- Full suite against the isolated installed wheel, launched outside the project
  from C:\VM_Share: all 141 tests passed (9.71 seconds).

## Explicitly not passed / not established

- WinProLadder GUI import and F8 syntax check have not been observed. Resetting
  the Computer Use session, reacquiring and activating the window, clicking
  the host View menu and using host keyboard shortcuts did not produce a
  confirmed menu change. Do not count this as successful GUI testing.
- VMware's management CLI reports exactly one running VM, display name FATEK,
  with VMware Tools running and C:\VM_Share read/write sharing enabled. There
  is no evidence that guest reboot is necessary; no unsaved work was discarded.
- The current guest project is FBs-24MA; sampled .ldr header is FBs-20MC.
  Cross-model import compatibility has not been established.
- No physical PLC operation, hardware safety validation or timing calibration.
- Unimplemented instruction families and indirect/nested variants remain
  unsupported. Passing all existing tests does not mean every user requirement
  or every WinProLadder instruction is supported.

The original samples remain protected by SHA-256 tests and were not modified.
Existing working-tree changes were preserved; nothing was committed or pushed.
