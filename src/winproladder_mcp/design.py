"""Host-agent design workflow and executable examples."""

from typing import Any, get_args

from .control import ControlKind


def design_guide() -> dict[str, Any]:
    return {
        "control_recipes": {
            "tool": "generate_control_ldr",
            "kinds": list(get_args(ControlKind)),
            "default_policy": "Resolve missing fields using disclosed draft defaults.",
        },
        "workflow": [
            "For multiple independent controls use generate_system_ldr to allocate addresses.",
            "For ordered multi-step pause/resume requirements use generate_sequence_ldr. "
            "Choose disclosed draft I/O/timing defaults; do not demand a complete control table.",
            "For common controls use generate_control_ldr and its resolved defaults. "
            "For custom logic use generate_ldr. Do not claim any draft is ready for machinery.",
            "Interpret the user's natural-language requirements into the ladder schema below.",
            "Use AND/OR/NOT conditions; do not ask users for JSON or binary samples.",
            "Resolve input polarity and state intended behavior; examples are only patterns.",
            "Simulate Boolean startup, hold, reset and simultaneous-input cases.",
            "Pass executable acceptance cases to generate_ldr for Boolean programs; "
            "a failed case prevents file creation.",
            "Call generate_ldr for a file; inferred encodings are enabled automatically.",
            "Return file links and verification status. No PLC runtime verification is implied.",
        ],
        "expression_grammar": "Devices, TRUE/FALSE, AND/OR/NOT, &/|/!, parentheses; AND before OR.",
        "sequence_generation": {
            "tool": "generate_sequence_ldr",
            "policy": "Generate a candidate with assumptions, not a deployment-ready safety claim.",
            "pause": "Whole-tick retention using explicit external X4 clock by default; "
            "not native timing or power-loss retention. Disclose clock wiring requirements.",
            "example_spec": {
                "requirement": "Fill, mix, drain; pause and resume",
                "steps": [
                    {"name": "fill", "outputs": [0], "ticks": 10, "complete_when": "X5"},
                    {"name": "mix", "outputs": [1], "ticks": 30},
                    {"name": "drain", "outputs": [2], "ticks": 10, "complete_when": "X6"},
                ],
            },
        },
        "system_generation": {
            "tool": "generate_system_ldr",
            "example_spec": {
                "requirement": "Two independent motor latches",
                "controls": [
                    {"requirement": "Motor A", "kind": "start_stop", "signal": "X0", "stop": "X1"},
                    {"requirement": "Motor B", "kind": "start_stop", "signal": "X2", "stop": "X3"},
                ],
            },
        },
        "timed_acceptance": {
            "usage": "Use scan_ms per acceptance case, or in simulate_ladder, for T/C programs.",
            "limits": "Reset-start T/C model, preset 0..32767, default .01s T0..T49 only; "
            "one writer per block; no register/loop execution or hardware timing guarantees.",
            "on_delay_3_seconds_while_x0": [
                {
                    "name": "3 second enable then reset",
                    "scan_ms": 1000,
                    "scans": [
                        {"inputs": {"X0": True}, "expected": {"Y0": False}},
                        {"inputs": {"X0": True}, "expected": {"Y0": False}},
                        {"inputs": {"X0": True}, "expected": {"Y0": True}},
                        {"inputs": {}, "expected": {"Y0": False}},
                    ],
                }
            ],
        },
        "acceptance_example": [
            {
                "name": "Start, hold, stop, stop priority",
                "scans": [
                    {"inputs": {}, "expected": {"Y0": False}},
                    {"inputs": {"X0": True}, "expected": {"Y0": True}},
                    {"inputs": {}, "expected": {"Y0": True}},
                    {"inputs": {"X1": True}, "expected": {"Y0": False}},
                    {"inputs": {"X0": True, "X1": True}, "expected": {"Y0": False}},
                ],
            }
        ],
        "inferred_profile": "Addresses 0..255; .01s presets 0..65535. Not PLC capacity claims.",
        "unsupported": [
            "register functions except 16-bit direct-register OR (R0..R255)",
            "nested loops, register-valued FOR counts, pulse BREAK, 32-bit/indirect OR",
            "native SET/RST and edge opcodes (Boolean control recipes implement their behavior)",
            "other time bases",
            "PLC communication",
        ],
        "examples": {
            "register_or_loop": {
                "networks": [
                    {"action": {"type": "register_or", "sa": 0, "sb": 1, "destination": 2}},
                    {"action": {"type": "for", "count": 10}},
                    {"condition": "X0", "coils": [{"address": 0}]},
                    {"action": {"type": "break", "enable": "X1"}},
                    {"action": {"type": "next"}},
                ]
            },
            "self_hold_stop_active_high": {
                "networks": [{"condition": "(Y0 OR X0) AND NOT X1", "coils": [{"address": 0}]}]
            },
            "interlocked_forward_reverse_forward_priority": {
                "networks": [
                    {"condition": "(Y0 OR X0) AND NOT X2 AND NOT Y1", "coils": [{"address": 0}]},
                    {"condition": "(Y1 OR X1) AND NOT X2 AND NOT Y0", "coils": [{"address": 1}]},
                ]
            },
            "on_delay_3_seconds_while_x0": {
                "networks": [
                    {
                        "block": {"type": "timer", "address": 0, "preset": 300, "enable": "X0"},
                        "coils": [{"address": 0}],
                    }
                ]
            },
            "counter_10_pulses_reset_x1": {
                "networks": [
                    {
                        "block": {
                            "type": "counter",
                            "address": 0,
                            "preset": 10,
                            "pulse": "X0",
                            "clear": "X1",
                        },
                        "coils": [{"address": 0}],
                    }
                ]
            },
            "nested_branches": {
                "networks": [
                    {"condition": "Y2 AND (X4 OR X5 OR (X6 AND NOT X7))", "coils": [{"address": 9}]}
                ]
            },
        },
    }
