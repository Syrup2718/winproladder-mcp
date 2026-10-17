"""Behavioral oracles for the new numeric model and policy-compatible recipes."""

import json
from itertools import product
from typing import get_args

import pytest

from winproladder_mcp.acceptance import AcceptanceCase
from winproladder_mcp.control import ControlKind, ControlSpec, control_ladder
from winproladder_mcp.io_contract import IOContract
from winproladder_mcp.ir import Ladder, Network, network_coils
from winproladder_mcp.runtime import simulate_runtime
from winproladder_mcp.sequence import SequenceSpec, sequence_ladder
from winproladder_mcp.service import Service
from winproladder_mcp.system import SystemSpec, system_ladder

POLICY = {"forbid_m_to_m": True, "allow_function_m_to_m": True}


def strict_service(path):
    (path / ".winproladder-policy.json").write_text(json.dumps(POLICY))
    return Service(path)


def program(*actions):
    return Ladder.model_validate({"networks": [{"action": a} for a in actions]})


@pytest.mark.parametrize("kind", get_args(ControlKind))
def test_all_control_recipes_deliver_under_current_policy(tmp_path, kind):
    service = strict_service(tmp_path)
    ladder, design = control_ladder(
        ControlSpec(
            kind=kind,
            requirement="strict policy regression",
            signal="X0",
            stop="X1",
            reset="X2",
            reverse="X3",
            output=0,
        )
    )
    result = service.generate_design(
        "control.ldr",
        ladder,
        design,
        io_contract=IOContract(inputs=["X0", "X1", "X2", "X3"], outputs=["Y0", "Y1", "Y2"]),
    )
    assert result["architecture"]["valid"] and result["layout"]["helper_devices"] == []
    decoded = Ladder.model_validate(service.read(result["path"])["ladder"])
    scans = [
        {f"X{i}": v for i, v in enumerate(values)} for values in product([False, True], repeat=4)
    ]
    assert simulate_runtime(decoded, scans, {}, 10) == simulate_runtime(ladder, scans, {}, 10)


@pytest.mark.parametrize(
    "operation,left,right,expected",
    [
        ("add", 32767, 1, [32768]),
        ("sub", 0, 1, [65535]),
        ("mul", -123, 12, [(-1476) & 65535, 65535]),
        ("mul", 30000, 3, [90000 & 65535, 1]),
        ("div", -100, 7, [(-14) & 65535, (-2) & 65535]),
        ("div", 100, 7, [14, 2]),
    ],
)
def test_numeric_acceptance_replays_emitted_bytes(tmp_path, operation, left, right, expected):
    service = strict_service(tmp_path)
    ladder = program(
        {"type": "arithmetic", "operation": operation, "sa": "R0", "sb": right, "destination": "D0"}
    )
    case = AcceptanceCase(
        name="independent arithmetic oracle",
        initial={"R0": left},
        scans=[{"expected": {f"D{i}": v for i, v in enumerate(expected)}}],
    )
    result = service.generate("arithmetic.ldr", ladder, [case])
    assert result["acceptance"]["passed"] and result["compiled_acceptance"]["passed"]


def test_unsigned_and_signed_comparison_and_disabled_flag_retention():
    ladder = program(
        {
            "type": "compare",
            "sa": "R0",
            "sb": "R1",
            "unsigned_when": "X1",
            "enable": "X0",
            "less": [{"address": 0}],
            "greater": [{"address": 1}],
        }
    )
    trace = simulate_runtime(
        ladder, [{"X0": True}, {}, {"X0": True, "X1": True}], {"R0": 65535, "R1": 1}
    )
    assert [(s["Y0"], s["Y1"]) for s in trace] == [(True, False), (True, False), (False, True)]


@pytest.mark.parametrize("unit_ms", [10, 100, 1000])
def test_accumulative_pause_fraction_reset_and_resume(unit_ms):
    ladder = program(
        {
            "type": "accumulative_timer",
            "unit_ms": unit_ms,
            "cv": "R0",
            "pv": "R1",
            "timing": "X0",
            "enable": "X1",
            "done": [{"address": 0}],
            "not_done": [{"address": 1}],
        }
    )
    quarter = unit_ms // 2
    trace = simulate_runtime(
        ladder,
        [
            {"X0": True, "X1": True},
            {"X1": True},
            {"X0": True, "X1": True},
            {},
            {"X0": True, "X1": True},
        ],
        {"R1": 1},
        quarter,
    )
    assert [s["R0"] for s in trace] == [0, 0, 1, 0, 0]
    assert [s["Y0"] for s in trace] == [False, False, True, False, False]
    assert [s["Y1"] for s in trace] == [True, True, False, False, True]


def test_unknown_action_fails_before_any_partial_trace():
    ladder = program(
        {"type": "increment", "destination": "R0"}, {"type": "for", "count": 2}, {"type": "next"}
    )
    with pytest.raises(ValueError, match="cannot execute for"):
        simulate_runtime(ladder, [{}], {})


@pytest.mark.parametrize("initial", [{"R0": True}, {"Y0": 1}, {"R00": 0}, {"R0": 65536}])
def test_numeric_and_boolean_state_types_are_not_coerced(initial):
    with pytest.raises(ValueError):
        simulate_runtime(program({"type": "increment", "destination": "R0"}), [{}], initial)


def test_numeric_compiler_corruption_is_rejected_before_writing(tmp_path, monkeypatch):
    from winproladder_mcp import service as module

    service = strict_service(tmp_path)
    compile_original = module.compile_network

    def wrong_constant(network):
        copy = network.model_copy(deep=True)
        copy.action.sb = 2
        return compile_original(copy)

    monkeypatch.setattr(module, "compile_network", wrong_constant)
    ladder = program(
        {"type": "arithmetic", "operation": "add", "sa": "R0", "sb": 1, "destination": "R0"}
    )
    with pytest.raises(ValueError, match="Compiled acceptance failed"):
        service.generate(
            "bad.ldr", ladder, [AcceptanceCase(name="increment", scans=[{"expected": {"R0": 1}}])]
        )
    assert not (tmp_path / "artifacts").exists()


def test_register_allocation_and_explicit_collision():
    spec = SystemSpec(
        requirement="two independent pulses",
        controls=[
            {"kind": "pulse", "requirement": "one", "signal": "X0", "output": 0},
            {
                "kind": "pulse",
                "requirement": "two",
                "signal": "X1",
                "output": 1,
                "register_base": 0,
            },
        ],
    )
    ladder, design = system_ladder(spec)
    assert design["controls"][0]["resolved_spec"]["register_base"] == 2
    trace = simulate_runtime(ladder, [{"X0": True}, {}, {"X1": True}], {}, 10)
    assert trace[-1]["Y0"] and trace[-1]["Y1"]
    spec.controls[0].register_base = 1
    with pytest.raises(ValueError, match="register_base resources overlap"):
        system_ladder(spec)


def test_strict_policy_rejects_even_x_only_automatic_helpers(tmp_path):
    service = strict_service(tmp_path)
    ladder = Ladder(
        networks=[Network(condition="(X0 OR X1) AND (X2 OR X3)", coils=[{"address": 0}])]
    )
    with pytest.raises(ValueError, match="automatically lowered relay helpers"):
        service.generate("forbidden.ldr", ladder)
    assert not (tmp_path / "artifacts").exists()


@pytest.mark.parametrize("pause,clock", [("FALSE", None), ("X1", None), ("X1", "X4")])
def test_maximum_sequence_no_helpers_and_reset_wins_abort(tmp_path, pause, clock):
    service = strict_service(tmp_path)
    ladder, _ = sequence_ladder(
        SequenceSpec(
            requirement="16 stages",
            start="X0",
            pause=pause,
            clock=clock,
            reset="X2",
            abort="X3",
            steps=[{"name": str(i), "ticks": 0, "outputs": [i]} for i in range(16)],
        )
    )
    result = service.generate("max.ldr", ladder)
    assert not result["layout"]["helper_devices"]
    emitted = Ladder.model_validate(service.read(result["path"])["ladder"])
    for candidate in (ladder, emitted):
        destinations = [
            (coil.device, coil.address)
            for network in candidate.networks
            for coil in network_coils(network)
        ]
        assert len(destinations) == len(set(destinations)), "Repeated coil writers"
    trace = simulate_runtime(
        emitted, [{"X0": True}] + [{}] * 16 + [{"X2": True, "X3": True}], {}, 10
    )
    for i, state in enumerate(trace[:16]):
        assert [j for j in range(16) if state[f"Y{j}"]] == [i]
    assert trace[16]["M5"]
    assert trace[-1]["R0"] == 0 and not trace[-1]["M6"]


@pytest.mark.parametrize("number", [99, 0, 98])
def test_numeric_display_slots_have_blank_even_when_digits_repeat(tmp_path, number):
    # Test-only I/O: Y0 seconds select, Y1 tenths select. R10 is supplied tenths,
    # R13 is the selected digit. This fixture is not an assumed customer I/O map.
    from winproladder_mcp.native_state import status

    ladder = program(
        {"type": "arithmetic", "operation": "div", "sa": "R0", "sb": 10, "destination": "R2"},
        {"type": "arithmetic", "operation": "div", "sa": "R10", "sb": 10, "destination": "R11"},
    )
    ladder.networks += [status("R3", 0, 3, 0), status("R3", 5, 8, 1)]
    ladder.networks += program(
        {"type": "move_word", "source": "R11", "destination": "R13", "enable": "M0"},
        {"type": "move_word", "source": "R12", "destination": "R13", "enable": "M1"},
    ).networks
    ladder.networks += [
        Network(condition="M0", coils=[{"address": 0}]),
        Network(condition="M1", coils=[{"address": 1}]),
    ]
    ladder.networks += program(
        {"type": "accumulative_timer", "unit_ms": 10, "cv": "R0", "pv": "R1"}
    ).networks
    scans = []
    for i in range(30):
        phase = i % 10
        expected = {"Y0": phase < 4, "Y1": 5 <= phase < 9}
        if phase < 4 or 5 <= phase < 9:
            expected["R13"] = number // 10 if phase < 4 else number % 10
        scans.append({"expected": expected})
    case = AcceptanceCase(
        name=f"{number // 10}.{number % 10}: 40ms on/10ms off",
        initial={"R10": number, "R1": 1000},
        scan_ms=10,
        scans=scans,
    )
    result = strict_service(tmp_path).generate(
        "display.ldr", ladder, [case], io_contract=IOContract(inputs=[], outputs=["Y0", "Y1"])
    )
    assert result["compiled_acceptance"]["passed"]
    assert not result["layout"]["helper_devices"]
