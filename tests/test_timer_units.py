"""Regression evidence from the user's three-light 100 ms cycle file."""

import hashlib
from pathlib import Path

from winproladder_mcp.analysis import describe, timer_settings
from winproladder_mcp.control import ControlSpec, control_ladder
from winproladder_mcp.io_contract import IOContract
from winproladder_mcp.ir import Ladder, Network, Timer
from winproladder_mcp.service import Service
from winproladder_mcp.timing import timed_simulate

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = "tests/fixtures/Y0_Y1_Y2_100ms_cycle.ldr"


def test_user_file_preset_ten_means_100ms_under_sampled_time_base():
    assert hashlib.sha256((ROOT / FIXTURE).read_bytes()).hexdigest() == (
        "cc6904494143a986df9e8971cdd0c27f07337c1ba957da5cfab1e3f32a601396"
    )
    read = Service(ROOT).read(FIXTURE)
    report = read["timer_settings"]
    assert not report["configuration_verified"]
    assert [
        (t["device"], t["preset_ticks"], t["assumed_time_base_ms"], t["nominal_duration_ms"])
        for t in report["timers"]
    ] == [("T0", 10, 10, 100), ("T1", 10, 10, 100), ("T2", 10, 10, 100)]
    ladder = Ladder.model_validate(read["ladder"])
    trace = timed_simulate(ladder, [{}] * 100, {}, 10)
    for scan, state in enumerate(trace):
        assert [i for i in range(3) if state[f"Y{i}"]] == [(scan // 10) % 3]
    analyzed = Service(ROOT).analyze(FIXTURE)
    assert analyzed["timer_settings"] == report
    assert set(analyzed["references"]["devices"]) == {"Y0", "Y1", "Y2", "T0", "T1", "T2"}


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
