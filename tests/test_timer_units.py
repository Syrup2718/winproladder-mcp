"""Public timer-unit regression tests using synthetic project-owned programs."""

from winproladder_mcp.analysis import describe, timer_settings
from winproladder_mcp.control import ControlSpec, control_ladder
from winproladder_mcp.io_contract import IOContract
from winproladder_mcp.ir import Ladder, Network, Timer
from winproladder_mcp.service import Service
from winproladder_mcp.timing import timed_simulate


def test_preset_ten_means_100ms_for_declared_timer_bank():
    ladder = Ladder(
        networks=[
            Network(block=Timer(address=address, preset=10, enable="TRUE")) for address in range(3)
        ]
    )
    report = timer_settings(list(enumerate(ladder.networks)))
    assert not report["configuration_verified"]
    assert [
        (t["device"], t["preset_ticks"], t["assumed_time_base_ms"], t["nominal_duration_ms"])
        for t in report["timers"]
    ] == [("T0", 10, 10, 100), ("T1", 10, 10, 100), ("T2", 10, 10, 100)]


def test_generation_reports_encoded_ticks_and_duration_separately(tmp_path):
    ladder, _ = control_ladder(
        ControlSpec(
            requirement="Y0 after 100 ms", kind="on_delay", signal="TRUE", output=0, delay_ms=100
        )
    )
    result = Service(tmp_path).generate(
        "100ms.ldr", ladder, io_contract=IOContract(inputs=[], outputs=["Y0"])
    )
    assert result["timer_settings"]["timers"][0]["preset_ticks"] == 10
    assert result["timer_settings"]["timers"][0]["nominal_duration_ms"] == 100
    assert "preset=10 ticks, nominal_duration=100 ms" in describe(ladder.networks[0])
    emitted = Ladder.model_validate(Service(tmp_path).read(result["path"])["ladder"])
    trace = timed_simulate(emitted, [{}] * 10, {}, 10)
    assert [s["Y0"] for s in trace] == [False] * 9 + [True]


def test_unknown_timer_allocation_is_not_reported_as_known_duration():
    report = timer_settings([(0, Network(block=Timer(address=50, preset=10)))])
    assert report["timers"][0]["assumed_time_base_ms"] is None
    assert report["timers"][0]["nominal_duration_ms"] is None
