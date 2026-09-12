import pytest

from winproladder_mcp.ir import compile_network, decode_network
from winproladder_mcp.system import SystemSpec, system_ladder
from winproladder_mcp.timing import timed_simulate


def test_independent_toggles_get_distinct_state_and_outputs():
    spec = SystemSpec(
        requirement="two buttons",
        controls=[
            {"requirement": "first", "kind": "toggle", "signal": "X0"},
            {"requirement": "second", "kind": "toggle", "signal": "X1"},
        ],
    )
    ladder, design = system_ladder(spec)
    assert design["resources"]["output"] == [0, 1]
    trace = timed_simulate(ladder, [{"X0": True}, {}, {"X1": True}, {}], {}, 10)
    assert [(s["Y0"], s["Y1"]) for s in trace] == [
        (True, False),
        (True, False),
        (True, True),
        (True, True),
    ]
    for n in ladder.networks:
        raw = compile_network(n)
        assert compile_network(decode_network(raw)) == raw


def test_reserve_later_explicit_output_before_automatic_allocation():
    spec = SystemSpec(
        requirement="allocate",
        controls=[
            {"requirement": "auto", "kind": "star_delta"},
            {"requirement": "explicit", "kind": "start_stop", "output": 0},
        ],
    )
    _, design = system_ladder(spec)
    assert design["controls"][0]["resolved_spec"]["output"] == 1


def test_explicit_overlap_rejected():
    spec = SystemSpec(
        requirement="bad",
        controls=[
            {"requirement": "first", "kind": "star_delta", "output": 0},
            {"requirement": "second", "kind": "start_stop", "output": 2},
        ],
    )
    with pytest.raises(ValueError, match="overlap"):
        system_ladder(spec)
