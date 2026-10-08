"""Host-agent design workflow and executable examples."""

from typing import Any, get_args

from .control import ControlKind


def design_guide() -> dict[str, Any]:
    return {
        "control_recipes": {
            "tool": "generate_control_ldr",
            "kinds": list(get_args(ControlKind)),
            "default_policy": "Physical signal/output required; no automatic X/Y assignment.",
        },
        "workflow": [
            "test17: integer mean/sqrt/neg/abs/ext/crc16. MEAN count is a register, "
            "not its numeric address: reserve/check 256 possible source words. "
            "EXT writes 2 words. CRC16 MD=1 is reserved in the supplied manual; "
            "preserve sampled encoding and do not claim known runtime semantics. "
            "DIV48 single_input is F474, separate from F46C with U/S. "
            "No execution simulation for these actions.",
            "test16: div48 uses 3-word Sa/Sb/D; sum uses count=1..511 words. "
            "pid enable is A/M, with separate bumpless BUM and direction D/R. "
            "SR8/OR1/PR7/WR5; exclusive WR; status error/high/low coils. "
            "PID interval and WDT setting use 10 ms units. WDT accepts 50,60,...120. "
            "HSCTR only HSC0; HSCTW only sampled 93D source=0,target=PV,HSC0. "
            "No native runtime simulation; do not infer other HSC selector layouts.",
            "test15: native tkey/hkey/dsw/7sgdl/muxi. Supply full physical I/O contract, "
            "not just starts. Reserve KL10/16 and WR1 (DSW WR2); WR cannot be reused. "
            "MUXI uses ceil(rows/2) destination words. Implicit KL outputs are M-policy checked. "
            "7SGDL mode is output polarity (0..3), not digit count or a 50 ms timing setting. "
            "No scan/hardware simulation or D variants; exact special operands R3999/V supported.",
            "test14: float_operation log/pow/asin/acos/atan. pow sa=Sy exponent, sb=Sx base, "
            "result=sb**sa. Inverse trig results are radians, not 0.01 degree integers. "
            "Normal error coils on float actions are checked by I/O and M-to-M policy. "
            "imdio start/count refreshes the full consecutive X/Y range; require all points "
            "in io_contract and main-unit capacity verification. No execution simulator.",
            "test13 adds float_operation sin/cos/tan/neg/abs/ln/exp. Trig Sa is an integer "
            "in 0.01 degrees (-18000..18000), occupying one source word; destination is two. "
            "For neg/abs omit Sa/Sb: destination is read and written in place. "
            "ln/exp use floating sources, D bank ends at D3999 per their manual pages. "
            "No runtime simulation or P; ERR wiring is supported for eligible operations; "
            "FBs-44MN-test13 exact header available.",
            "Use get_manual_reference for operand maxima, manual edition differences and RTC. "
            "Sample addresses are not PLC maxima. RTC R4128..R4135 and M1952..M1955 are "
            "documented, but special-register/relay binary encoding remains unsupported. "
            "inspect_rtc_snapshot checks supplied values without PLC access. Never invent I/O "
            "or M-to-M control chains for clock setting; preserve project timer units.",
            "Unreleased test12: FDIV/FSQR via float_operation div/sqrt; FCMP via float_compare; "
            "FZCP via float_zone_compare. Finite numeric sources are rounded to binary32. "
            "Reserve two words per float register, including R8000/R8001 and D4094/D4095. "
            "M999 is supported; comparison outputs remain subject to M-to-M policy. "
            "F5/F6 constant markers sampled; F7 combinations inferred. No runtime simulation.",
            "comparison_chain supports all six relations in first/series positions; "
            "all 12 positions user GUI-confirmed in the position probe; "
            "new combinations remain inferred. "
            "Float_operation actions use two consecutive registers for float values; "
            "I->F reads one integer word and writes two, F->I reads two and writes one. "
            "Reserve the full spans. WM0 comparisons read M0..15 and cannot drive M outputs "
            "under forbid_m_to_m. No built-in execution simulation for either new family.",
            "test10 adds exclusive_logic (xor/xnr), zone_compare and word_conversion. "
            "T operands are numeric values, not contacts. WX0/WY0 are 16-bit I/O groups; "
            "include every X0..15/Y0..15 in the contract only when that word was requested. "
            "No runtime simulation for these functions. to_bcd currently accepts constants only.",
            "Use native difu/difd actions with trigger and Y/M destination. "
            "Do not replace the function block with synthesized M helpers.",
            "Native increment/decrement, compare and bitwise actions are supported from test8. "
            "MC/MCE and 07P.UDCTR are supported from test9, with no built-in runtime simulation. "
            "Respect the workspace policy even for implicit M dependencies through MC regions.",
            "FUN11..14 use arithmetic actions: register Sa and nonnegative immediate Sb only. "
            "MUL/DIV write D and D+1; reserve both. No arithmetic runtime acceptance available.",
            "Native edge networks can pulse Y/M directly without helper M contacts. "
            "Only isolated X rising/falling contacts; model starts from initial/FALSE.",
            "For independent controls use generate_system_ldr to allocate internal M/T/C only.",
            "Copy user-specified X/Y into mandatory io_contract; never add missing hardware. "
            "Use native T for timed sequences. Retentive FUN87/88/89 encoding is unavailable.",
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
            "pause": "Native retentive timing rejected: missing FUN87/88/89 LDR encoding. "
            "Explicit external pulse counting is supported only if requested by the user.",
            "example_spec": {
                "requirement": "Fill, mix, drain using native T timers",
                "start": "X0",
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
                    {
                        "requirement": "Motor A",
                        "kind": "start_stop",
                        "signal": "X0",
                        "stop": "X1",
                        "output": 0,
                    },
                    {
                        "requirement": "Motor B",
                        "kind": "start_stop",
                        "signal": "X2",
                        "stop": "X3",
                        "output": 1,
                    },
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
            "register functions except 16-bit direct-register OR and FUN33 LCNV",
            "nested loops, register-valued FOR counts, pulse BREAK, 32-bit/indirect OR",
            "LCNV pulse/indirect forms and register-valued L; LCNV runtime simulation",
            "native SET/RST and edge opcodes (Boolean control recipes implement their behavior)",
            "other time bases",
            "accumulative timers FUN87/88/89: manual behavior known; no export encoding evidence",
            "PLC communication",
        ],
        "lcnv_generation": {
            "action_type": "lcnv",
            "fun": 33,
            "mode": "0/1: two-point calibration; 2/3: ratio plus offset",
            "table": "0/2 share one parameter group; 1/3 use one group per source word",
            "table_words": "4 for modes 0/1, 3 for 2/3; multiplied by L for modes 1/3",
            "evidence": "test6 observes Md=0 and L=1. Other modes, lengths and addresses inferred.",
            "required_context": "Pre-initialized conversion table; LDR does not supply its values",
            "profile": "Use ladder.profile=FBs-24MA to reproduce test6 header exactly",
        },
        "examples": {
            "lcnv_observed": {
                "profile": "FBs-24MA",
                "networks": [
                    {
                        "action": {
                            "type": "lcnv",
                            "mode": 0,
                            "source": "R3840",
                            "table": "R2001",
                            "destination": "D1000",
                            "length": 1,
                        }
                    }
                ],
            },
            "native_rising_x0_y1": {
                "networks": [
                    {"edge": {"kind": "rising", "input": "X0"}, "coils": [{"address": 1}]}
                ],
            },
            "native_float_conversions": {
                "profile": "FBs-32MA-test11",
                "networks": [
                    {
                        "action": {
                            "type": "float_operation",
                            "operation": "i_to_f",
                            "sa": "R101",
                            "destination": "R101",
                        }
                    },
                    {
                        "action": {
                            "type": "float_operation",
                            "operation": "f_to_i",
                            "sa": "R102",
                            "destination": "D103",
                        }
                    },
                ],
            },
            "native_xor_xnr": {
                "profile": "FBs-24MA-test7",
                "networks": [
                    {
                        "action": {
                            "type": "exclusive_logic",
                            "operation": "xor",
                            "sa": "R1234",
                            "sb": "D300",
                            "destination": "R110",
                        }
                    },
                    {
                        "action": {
                            "type": "exclusive_logic",
                            "operation": "xnr",
                            "sa": "R205",
                            "sb": "T1",
                            "destination": "R233",
                        }
                    },
                ],
            },
            "native_bcd_constant": {
                "profile": "FBs-24MA-test7",
                "networks": [
                    {
                        "action": {
                            "type": "word_conversion",
                            "operation": "to_bcd",
                            "source": 333,
                            "destination": "R222",
                        }
                    }
                ],
            },
            "native_difu_difd_sample": {
                "profile": "FBs-24MA-test7",
                "networks": [
                    {"action": {"type": "difu", "trigger": "TRUE", "destination": "M100"}},
                    {"action": {"type": "difd", "trigger": "TRUE", "destination": "M101"}},
                ],
            },
            "native_increment_decrement": {
                "profile": "FBs-24MA-test7",
                "networks": [
                    {"action": {"type": "increment", "destination": "R100"}},
                    {"action": {"type": "decrement", "destination": "D200"}},
                ],
            },
            "native_compare_and": {
                "profile": "FBs-24MA-test7",
                "networks": [
                    {
                        "action": {
                            "type": "compare",
                            "sa": "R3840",
                            "sb": "R3841",
                            "equal": [{"device": "M", "address": 100}],
                            "greater": [{"device": "M", "address": 101}],
                            "less": [{"device": "M", "address": 102}],
                        }
                    },
                    {
                        "action": {
                            "type": "bitwise",
                            "operation": "and",
                            "sa": "R3844",
                            "sb": "D120",
                            "destination": "D150",
                        }
                    },
                ],
            },
            "native_udctr_sample": {
                "profile": "FBs-24MA-test7",
                "networks": [
                    {
                        "action": {
                            "type": "udctr",
                            "cv": "R200",
                            "preset": 100,
                            "pulse": "X1",
                            "up": "X2",
                            "clear": "X3",
                        }
                    }
                ],
            },
            "arithmetic_offset_scale_quotient": {
                "profile": "FBs-24MA-test7",
                "networks": [
                    {
                        "action": {
                            "type": "arithmetic",
                            "operation": "add",
                            "sa": "R3840",
                            "sb": 5,
                            "destination": "D100",
                        }
                    },
                    {
                        "action": {
                            "type": "arithmetic",
                            "operation": "mul",
                            "sa": "R3841",
                            "sb": 2,
                            "destination": "D102",
                        },
                        "comment": "Product occupies D102 (low) and D103 (high).",
                    },
                    {
                        "action": {
                            "type": "arithmetic",
                            "operation": "div",
                            "sa": "R3842",
                            "sb": 20,
                            "destination": "D104",
                        },
                        "comment": "Quotient D104; remainder D105.",
                    },
                ],
            },
            "derived_increment_decrement": {
                "profile": "FBs-24MA-test7",
                "networks": [
                    {
                        "action": {
                            "type": "arithmetic",
                            "operation": "add",
                            "sa": "D200",
                            "sb": 1,
                            "destination": "D200",
                        },
                        "comment": "Increment every enabled scan via FUN11, not native FUN15. "
                        "Uses FUN11 status semantics; no saturation or wrapping guarantee.",
                    },
                    {
                        "action": {
                            "type": "arithmetic",
                            "operation": "sub",
                            "sa": "D201",
                            "sb": 1,
                            "destination": "D201",
                        },
                        "comment": "Decrement every enabled scan via FUN12, not native FUN16.",
                    },
                ],
            },
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
