# Requirement-to-file acceptance workflow

The host AI interprets natural-language requirements. The MCP is the local
compiler and checker; it does not contain a general-purpose language model.
Users do not need to provide JSON: the connected agent calls `get_design_guide`,
constructs the ladder and acceptance cases, and calls `generate_ldr`.

## Acceptance before generation

`generate_ldr` accepts optional `acceptance` cases. Each case has a name, optional
initial device states, and a sequence of scans containing `inputs` and `expected`
device states. Every case starts independently. Missing X inputs are false;
internal/output state persists between scans. A failed assertion rejects the
request before creating an output file. The error names the case, scan, device,
expected value and actual value so the agent can correct the design and retry.

The design guide includes start, release/hold, stop, and simultaneous start/stop
assertions for the active-high stop example. Agents should create additional
cases from the actual user's requirements, not blindly reuse this example.

Acceptance defaults to Boolean programs. Set `scan_ms` on a case to enable the
reset-start timer/counter model (also available on `simulate_ladder`). Inputs
apply for one scan duration and networks execute once in display order. Timers
accumulate enabled time and reset when disabled; counters count rising pulses
with reset priority. The model supports presets 0..32767 and assumes default
0.01-second T0..T49 configuration, rejecting other timer addresses and duplicate
block writers. It models scan boundaries, not the PLC's asynchronous clock phase.
Registers and loops are explicitly rejected by simulation. Omitting acceptance
permits compilation of supported actions but returns no acceptance result.
Passing checks is not proof of WinProLadder import or PLC
execution, nor a substitute for machine safety engineering.

## VMware exchange workflow

The server intentionally confines files to its configured root. To use a shared
folder, start it with `--root C:\VM_Share`. Generated files will be under
`C:\VM_Share\artifacts`, not mixed with the user's original samples.

For development, generate all examples through a real MCP connection:

```powershell
uv run python scripts/generate_design_examples.py --root C:\VM_Share --prefix acceptance_01
```

Use a new prefix per run: existing files are never overwritten. The command
prints each actual path and verification status. No VMware credentials, PLC
connection, or installed WinProLadder are needed for compilation. GUI import
testing is a separate verification step and must not be claimed unless observed.
