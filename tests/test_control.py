from typing import get_args

import pytest

from winproladder_mcp.control import ControlKind, ControlSpec, control_ladder
from winproladder_mcp.ir import compile_network, decode_network
from winproladder_mcp.timing import timed_simulate


@pytest.mark.parametrize("kind", get_args(ControlKind))
def test_all_controls_roundtrip(kind):
    ladder, design = control_ladder(
        ControlSpec(
            signal="X0",
            output=0,
            stop="X1",
            reset="X2",
            reverse="X3",
            requirement="customer draft",
            kind=kind,
        )
    )
    assert "signal" not in design["defaults_used"]
    for n in ladder.networks:
        raw = compile_network(n)
        decoded = decode_network(raw)
        assert decoded is not None
        assert compile_network(decoded) == raw


@pytest.mark.parametrize(
    "kind,expected",
    [
        ("toggle", [False, True, True, True, False, False]),
        ("rising_edge", [False, True, False, False, True, False]),
        ("falling_edge", [False, False, False, True, False, True]),
        ("set_reset", [False, True, True, True, True, True]),
    ],
)
def test_stateful_controls(kind, expected):
    ladder, _ = control_ladder(
        ControlSpec(
            signal="X0",
            output=0,
            stop="X1",
            reset="X2",
            reverse="X3",
            requirement="test",
            kind=kind,
        )
    )
    scans = [{}, {"X0": True}, {"X0": True}, {}, {"X0": True}, {}]
    assert [s["Y0"] for s in timed_simulate(ladder, scans, {}, 10)] == expected


def test_set_reset_priority():
    ladder, _ = control_ladder(
        ControlSpec(
            signal="X0",
            output=0,
            stop="X1",
            reset="X2",
            reverse="X3",
            requirement="test",
            kind="set_reset",
        )
    )
    assert not timed_simulate(ladder, [{"X0": True, "X2": True}], {}, 10)[0]["Y0"]


@pytest.mark.parametrize(
    "kind,expected",
    [
        ("on_delay", [False, False, False, True, False, False, False]),
        ("off_delay", [False, True, True, True, True, True, False]),
        ("pulse", [False, True, True, False, False, False, False]),
    ],
)
def test_timer_controls(kind, expected):
    ladder, _ = control_ladder(
        ControlSpec(
            signal="X0",
            output=0,
            stop="X1",
            reset="X2",
            reverse="X3",
            requirement="test",
            kind=kind,
            delay_ms=30,
        )
    )
    scans = [{}, {"X0": True}, {"X0": True}, {"X0": True}, {}, {}, {}]
    assert [s["Y0"] for s in timed_simulate(ladder, scans, {}, 10)] == expected


def test_star_delta_no_overlap_and_stop():
    ladder, _ = control_ladder(
        ControlSpec(
            signal="X0",
            output=0,
            stop="X1",
            reset="X2",
            reverse="X3",
            requirement="test",
            kind="star_delta",
            delay_ms=30,
            gap_ms=20,
        )
    )
    trace = timed_simulate(ladder, [{"X0": True}] + [{}] * 6 + [{"X1": True}], {}, 10)
    assert all(not (s["Y1"] and s["Y2"]) for s in trace)
    assert any(s["Y1"] for s in trace)
    assert any(s["Y2"] for s in trace)
    assert not any(trace[-1][name] for name in ["Y0", "Y1", "Y2"])
