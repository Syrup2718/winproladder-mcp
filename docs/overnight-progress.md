# Overnight development handoff - 2026-09-12

## Latest v0.4 work (supersedes older capability notes below)

New modules: control.py (11 synthesized recipes), sequence.py (16-step process,
pause/resume whole external-clock ticks, active timeout, reset/abort/done),
system.py (24 independent recipes, collision-free Y/M/T/C allocation).
New MCP tools: generate_control_ldr, generate_sequence_ldr, generate_system_ldr;
16 tools total. High-level tools create companion .ldr.design.json automatically.
Version 0.4.0, README and docs/v0.4-controls.md describe actual limits.
172 source and isolated-wheel tests passed before the latest report-collision
test. Latest source then needs rerun (report collision test and setup tool checks).
13 real MCP-generated examples and reports are C:\VM_Share\artifacts\v04_full_*.
Do not overwrite these; use new prefixes. Both source archive/wheel build.
Pause is NOT a native retentive timer: X4 external observable clock default100ms;
whole ticks retained only. Do not hide this dependency or claim all functions.
GUI import still not verified. Automation remains PAUSED; user disallowed schedules.

## User authorization

Continue independently toward natural-language requirements -> usable .ldr.
Use VMware and C:\VM_Share for OFFLINE software testing. User calls VM FATEX;
the uniquely observed VMware window/library is FATEK. User opened VM again and
authorized restarting it if necessary. Do not operate physical PLCs. Preserve
unsaved work, original samples and unrelated git changes. Do not commit/push.
User is sleeping: do not ask for samples/next-step choices or routine help.

## Completed this session

- Added acceptance.py: per-case expected bit states, independent initial state,
  rejected mismatches before generate writes a file; MCP schema exposes cases.
- Added timing.py: deterministic scan-boundary timer/counter simulation. Explicit
  limits: preset <=32767, default .01s T0..T49, reset-start, unique block writers,
  no actions/loops/registers. Counter rising pulse with clear priority.
- AcceptanceCase.scan_ms and simulate_ladder.scan_ms expose timing model.
- Added tests/test_acceptance.py and tests/test_timing.py. 131 pytest tests passed
  before latest guide/doc changes; a mypy variable reuse issue was then fixed.
- Real MCP generated six files C:\VM_Share\artifacts\acceptance_20260912_*.ldr.
  Start/stop passed model acceptance. Other files in that batch had no cases.
  New guide now includes timed 3-second acceptance; rerun with NEW prefix.
- docs/acceptance-workflow.md and script --root support shared-folder workflow.
- Thread heartbeat automation id `winproladder-mcp` is PAUSED at user's explicit
  request. Do not resume or create a replacement schedule. Work directly here.

## GUI/manual findings

Read all 19 pages of user-provided WinProLadder service manual Ver0.21 (2000).
F8 = Tools / Syntax Check. F9 / Ctrl+F9 operate PLC: DO NOT USE.
F opens function chooser, Shift+T timer, Shift+C counter, Shift+S/R SET/RST.
Manual has typos; appendix clarifies keys. File Ctrl+O opens PROJECT, not proven
to import .ldr. Need inspect actual menus for resource/program import.

Computer Use skill initialized via node_repl @oai/sky. VM id68076 app
VMware.Workstation.vmui; reacquire current object before using. No custom UIA.
Previously rendered tiny guest on black background. After user reopened and
Ctrl+Alt release, screenshot now shows normal readable WinProLadder with blank
Project0 [FBs-24MA]. DO NOT assume sample header FBs-20MC matches this project.
Clicks at guest File menu / Ctrl+G / Alt+F did not show confirmed menu change.
Both host processes Responding=True. No reboot performed: no evidence it is
needed, nor confirmation of unsaved work. No GUI import or syntax validation
has been observed; do not label outputs GUI verified.

## Next useful work

Latest verification: ruff, mypy and all 131 tests pass. Real MCP generated
`C:\VM_Share\artifacts\timed_20260912_*.ldr`; both start/stop and three-second
timer examples passed acceptance. Rendered manual page18 and visually checked
F8 syntax check versus F9 PLC operation. Other four examples have no acceptance
cases yet. No GUI import observed.

1. Run ruff/mypy/pytest after latest edits; real MCP timed case plus failure case.
2. Recover VMware interaction using supported sky API and fresh screenshots;
   inspect File/project menus for .ldr import. Use separate candidate project,
   F8 syntax check, save/export unique names to shared folder if applicable.
3. Expand reliable instruction coverage by collecting offline software exports
   (MOV/SET/RST/AND/arithmetic), preserve sample hashes, add exact round trips.
4. Add state-machine/sequence recipe coverage, truthful instruction support
   catalog and user-facing install/release documentation. Do not invent opcodes
   from manual function numbers. Existing unknown edge contacts still opaque.
5. Update this log with evidence. Work directly; no heartbeat or new schedule.
   Do not make a superficial 'everything supported' claim.
