from winproladder_mcp.ir import compile_network, decode_network
from winproladder_mcp.sequence import SequenceSpec, sequence_ladder
from winproladder_mcp.timing import timed_simulate


def test_pause_preserves_ticks_without_false_resume_edge():
    spec = SequenceSpec(
        start="X0",
        pause="X1",
        reset="X2",
        abort="X3",
        clock="X4",
        requirement="pause resume",
        steps=[{"name": "mix", "ticks": 3, "outputs": [0]}],
    )
    ladder, _ = sequence_ladder(spec)
    scans = [
        {"X0": True},
        {"X4": True},
        {},
        {"X1": True, "X4": True},
        {"X4": True},
        {},
        {"X4": True},
        {},
        {"X4": True},
    ]
    trace = timed_simulate(ladder, scans, {}, 10)
    assert trace[2]["Y0"]
    assert not trace[3]["Y0"]
    assert trace[4]["Y0"] and not trace[4]["M5"]
    assert trace[6]["Y0"] and not trace[6]["M5"]
    assert trace[8]["M5"] and not trace[8]["Y0"]
    for n in ladder.networks:
        raw = compile_network(n)
        decoded = decode_network(raw)
        assert decoded is not None
        assert compile_network(decoded) == raw


def test_zero_time_steps_do_not_cascade_in_one_scan():
    ladder, _ = sequence_ladder(
        SequenceSpec(
            start="X0",
            pause="X1",
            reset="X2",
            abort="X3",
            clock="X4",
            requirement="three stages",
            steps=[{"name": str(i), "ticks": 0, "outputs": [i]} for i in range(3)],
        )
    )
    trace = timed_simulate(ladder, [{"X0": True}, {}, {}, {}, {}], {}, 10)
    assert [next((i for i in range(3) if s[f"Y{i}"]), -1) for s in trace] == [0, 1, 2, -1, -1]


def test_abort_latches_until_reset():
    ladder, _ = sequence_ladder(
        SequenceSpec(
            start="X0",
            pause="X1",
            reset="X2",
            abort="X3",
            clock="X4",
            requirement="abort",
            steps=[{"name": "mix", "outputs": [0]}],
        )
    )
    trace = timed_simulate(
        ladder,
        [{"X0": True}, {"X3": True}, {}, {"X0": True}, {"X2": True}, {}, {"X0": True}],
        {},
        10,
    )
    assert [s["Y0"] for s in trace] == [True, False, False, False, False, False, True]


def test_missing_completion_feedback_times_out():
    spec = SequenceSpec(
        start="X0",
        pause="X1",
        reset="X2",
        abort="X3",
        clock="X4",
        requirement="wait for level",
        steps=[
            {
                "name": "fill",
                "outputs": [0],
                "ticks": 1,
                "complete_when": "X5",
                "timeout_ticks": 2,
            }
        ],
    )
    ladder, _ = sequence_ladder(spec)
    trace = timed_simulate(ladder, [{"X0": True}, {"X4": True}, {}, {"X4": True}], {}, 10)
    assert trace[1]["Y0"] and not trace[1]["M6"]
    assert not trace[-1]["Y0"] and trace[-1]["M6"]


def test_completion_wins_same_tick_as_timeout():
    spec = SequenceSpec(
        start="X0",
        pause="X1",
        reset="X2",
        abort="X3",
        clock="X4",
        requirement="complete at limit",
        steps=[
            {
                "name": "fill",
                "outputs": [0],
                "ticks": 1,
                "complete_when": "X5",
                "timeout_ticks": 1,
            }
        ],
    )
    ladder, _ = sequence_ladder(spec)
    final = timed_simulate(ladder, [{"X0": True}, {"X4": True, "X5": True}], {}, 10)[-1]
    assert final["M5"] and not final["M6"] and not final["Y0"]


def test_restart_immediately_after_completion():
    ladder, _ = sequence_ladder(
        SequenceSpec(
            start="X0",
            pause="X1",
            reset="X2",
            abort="X3",
            clock="X4",
            requirement="restart",
            steps=[
                {
                    "name": "step",
                    "ticks": 0,
                    "outputs": [0],
                }
            ],
        )
    )
    trace = timed_simulate(ladder, [{"X0": True}, {}, {"X0": True}], {}, 10)
    assert [s["Y0"] for s in trace] == [True, False, True]


def test_sixteen_steps_compile_and_complete_without_cascade():
    ladder, _ = sequence_ladder(
        SequenceSpec(
            start="X0",
            pause="X1",
            reset="X2",
            abort="X3",
            clock="X4",
            requirement="maximum",
            steps=[{"name": str(i), "ticks": 0, "outputs": [i]} for i in range(16)],
        )
    )
    for n in ladder.networks:
        assert decode_network(compile_network(n)) is not None
    trace = timed_simulate(ladder, [{"X0": True}] + [{}] * 16, {}, 10)
    for i, state in enumerate(trace[:-1]):
        assert [j for j in range(16) if state[f"Y{j}"]] == [i]
    assert trace[-1]["M5"]
