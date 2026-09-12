import pytest

from winproladder_mcp.ir import Ladder
from winproladder_mcp.timing import timed_simulate


def timer(address=0, preset=3):
    return Ladder.model_validate(
        {
            "networks": [
                {
                    "block": {
                        "type": "timer",
                        "address": address,
                        "preset": preset,
                        "enable": "X0",
                    },
                    "coils": [{"address": 0}],
                }
            ]
        }
    )


def test_timer_threshold_reset_restart():
    trace = timed_simulate(timer(), [{"X0": True}] * 3 + [{}] + [{"X0": True}], {}, 10)
    assert [s["Y0"] for s in trace] == [False, False, True, False, False]


def test_counter_counts_edges_and_reset_wins():
    ladder = Ladder.model_validate(
        {
            "networks": [
                {
                    "block": {
                        "type": "counter",
                        "address": 0,
                        "preset": 2,
                        "pulse": "X0",
                        "clear": "X1",
                    },
                    "coils": [{"address": 0}],
                }
            ]
        }
    )
    trace = timed_simulate(
        ladder,
        [{"X0": True}, {"X0": True}, {}, {"X0": True}, {"X0": True, "X1": True}, {"X0": True}],
        {},
        10,
    )
    assert [s["Y0"] for s in trace] == [False, False, False, True, False, False]


@pytest.mark.parametrize("period", [True, 0, -1, 60001, 1.5])
def test_invalid_scan_duration(period):
    with pytest.raises(ValueError):
        timed_simulate(timer(), [], {}, period)


def test_unknown_timer_configuration_rejected():
    with pytest.raises(ValueError, match="configuration"):
        timed_simulate(timer(50), [], {}, 10)


def test_initial_timer_state_rejected():
    with pytest.raises(ValueError, match="start reset"):
        timed_simulate(timer(), [], {"T0": True}, 10)


@pytest.mark.parametrize("preset,period", [(1, 1), (3, 7), (100, 20), (32767, 60000)])
def test_timer_different_scan_periods(preset, period):
    import math

    scans = math.ceil(preset * 10 / period)
    trace = timed_simulate(timer(preset=preset), [{"X0": True}] * scans, {}, period)
    assert all(not state["Y0"] for state in trace[:-1])
    assert trace[-1]["Y0"]


def test_duplicate_timer_writers_rejected():
    ladder = timer()
    ladder.networks.append(ladder.networks[0].model_copy(deep=True))
    with pytest.raises(ValueError, match="single writer"):
        timed_simulate(ladder, [], {}, 10)


@pytest.mark.parametrize("scan", [{"Y0": True}, {"X00": True}, {"X0": 1}])
def test_invalid_timed_inputs(scan):
    with pytest.raises(ValueError):
        timed_simulate(timer(), [scan], {}, 10)


def test_timer_can_drive_later_network_and_inverted_coil():
    ladder = timer(preset=1)
    ladder.networks.append(
        Ladder.model_validate(
            {"networks": [{"condition": "T0", "coils": [{"address": 1, "inverted": True}]}]}
        ).networks[0]
    )
    trace = timed_simulate(ladder, [{"X0": True}, {}], {}, 10)
    assert [(s["Y0"], s["Y1"]) for s in trace] == [(True, False), (False, True)]


def test_timed_acceptance_generation(tmp_path):
    from winproladder_mcp.acceptance import AcceptanceCase
    from winproladder_mcp.service import Service

    case = AcceptanceCase.model_validate(
        {
            "name": "30ms delay",
            "scan_ms": 10,
            "scans": [
                {"inputs": {"X0": True}, "expected": {"Y0": False}},
                {"inputs": {"X0": True}, "expected": {"Y0": False}},
                {"inputs": {"X0": True}, "expected": {"Y0": True}},
            ],
        }
    )
    assert Service(tmp_path).generate("timed.ldr", timer(), [case])["acceptance"]["passed"]
