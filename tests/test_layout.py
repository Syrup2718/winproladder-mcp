import itertools
import random
from pathlib import Path

import pytest

from winproladder_mcp.ir import Ladder, compile_network, decode_network, simulate
from winproladder_mcp.layout import expressions, lower_ladder, requires_lowering, safe_ladder
from winproladder_mcp.ldr import parse
from winproladder_mcp.logic import contacts, parse_expression
from winproladder_mcp.service import Service
from winproladder_mcp.timing import timed_simulate


@pytest.mark.parametrize(
    "expression",
    [
        "X0 AND ((M11 AND NOT T1) OR (M10 AND (T0 OR X1)) "
        "OR (NOT M10 AND NOT M11 AND NOT M12 AND X1))",
        "Y2 AND (X4 OR X5 OR (X6 AND NOT X7))",
        "(X0 OR X1) AND (X2 OR X3)",
        "FALSE",
        "X0 OR FALSE",
        "X0 AND NOT (X1 OR (X2 AND X3))",
    ],
)
def test_all_branch_shapes_are_flat_and_equivalent(expression):
    source = Ladder.model_validate(
        {"networks": [{"condition": expression, "coils": [{"address": 9}]}]}
    )
    fixed, report = lower_ladder(source)
    assert report["normalized_networks"] == [0]
    assert all(not requires_lowering(e) for n in fixed.networks for e in expressions(n))
    names = sorted(contacts(parse_expression(expression)))
    for values in itertools.product((False, True), repeat=len(names)):
        state = dict(zip(names, values, strict=True))
        inputs = {k: v for k, v in state.items() if k.startswith("X")}
        a = simulate(source, [inputs], state)[0]
        b = simulate(fixed, [inputs], state)[0]
        assert a["Y9"] == b["Y9"]
    assert safe_ladder(fixed) == fixed


def test_whole_customer_file_fixed_and_original_devices_unchanged(tmp_path):
    raw = (Path(__file__).parent / "fixtures/traffic_light-dangling.ldr").read_bytes()
    before = parse(raw)
    source = Ladder(networks=[decode_network(r.payload) for r in reversed(before.records)])
    result = Service(tmp_path).generate("traffic.ldr", source)
    assert result["layout_normalized_networks"] == [6, 7, 8]
    after = parse((tmp_path / "artifacts/traffic.ldr").read_bytes())
    fixed = Ladder(networks=[decode_network(r.payload) for r in reversed(after.records)])
    assert before.header == after.header and before.tail == after.tail
    assert all(not requires_lowering(e) for n in fixed.networks for e in expressions(n))
    rng = random.Random(53)
    scans = [{"X0": rng.random() < 0.95, "X1": rng.random() < 0.15} for _ in range(256)]
    a, b = timed_simulate(source, scans, {}, 100), timed_simulate(fixed, scans, {}, 100)
    for old, new in zip(a, b, strict=True):
        assert all(new[k] == v for k, v in old.items())
    assert all(compile_network(decode_network(r.payload)) == r.payload for r in after.records)


def test_helpers_avoid_existing_memory_and_input_model_unchanged():
    ladder = Ladder.model_validate(
        {
            "networks": [
                {"condition": "M255 AND (X0 OR X1)", "coils": [{"device": "M", "address": 254}]}
            ]
        }
    )
    original = ladder.model_dump()
    _, report = lower_ladder(ladder)
    assert set(report["helper_devices"]).isdisjoint({"M254", "M255"})
    assert ladder.model_dump() == original


def test_all_recipe_families_are_connected_and_preserve_original_devices():
    from typing import get_args

    from winproladder_mcp.control import ControlKind, ControlSpec, control_ladder
    from winproladder_mcp.layout import needs_lowering
    from winproladder_mcp.sequence import SequenceSpec, sequence_ladder

    programs = [
        control_ladder(ControlSpec(requirement="layout", kind=kind))[0]
        for kind in get_args(ControlKind)
    ]
    programs.append(
        sequence_ladder(
            SequenceSpec(
                requirement="full length",
                steps=[{"name": str(i), "ticks": 1, "outputs": [i]} for i in range(16)],
            )
        )[0]
    )
    rng = random.Random(91)
    scans = [{f"X{i}": rng.random() < 0.25 for i in range(7)} for _ in range(128)]
    for source in programs:
        fixed, _ = lower_ladder(source)
        assert all(
            not needs_lowering(n, i, e)
            for n in fixed.networks
            for i, e in enumerate(expressions(n))
        )
        old_trace, new_trace = (
            timed_simulate(source, scans, {}, 10),
            timed_simulate(fixed, scans, {}, 10),
        )
        for old, new in zip(old_trace, new_trace, strict=True):
            assert all(new[k] == v for k, v in old.items())


def test_memory_exhaustion_rejected_before_writing(tmp_path):
    source = Ladder.model_validate(
        {
            "networks": [{"condition": "(X0 OR X3) AND (X1 OR X2)", "coils": [{"address": 0}]}]
            + [{"condition": f"M{i}", "coils": [{"address": 1}]} for i in range(256)]
        }
    )
    with pytest.raises(ValueError, match="No free"):
        Service(tmp_path).generate("must-not-exist.ldr", source)
    assert not (tmp_path / "artifacts/must-not-exist.ldr").exists()


def test_edit_uses_same_layout_without_reusing_existing_helpers(tmp_path):
    from winproladder_mcp.ir import Network

    service = Service(tmp_path)
    original = Ladder.model_validate(
        {"networks": [{"condition": "M0", "coils": [{"device": "M", "address": 1}]}]}
    )
    service.generate("source.ldr", original)
    edited = service.edit(
        "artifacts/source.ldr",
        "edited.ldr",
        "insert",
        0,
        Network(condition="(X0 OR X3) AND (X1 OR X2)", coils=[{"address": 0}]),
        True,
    )
    after = parse(Path(edited["path"]).read_bytes())
    networks = [decode_network(r.payload) for r in reversed(after.records)]
    assert len(networks) == 3
    assert networks[0].coils[0].address == 2
    assert compile_network(networks[-1]) == compile_network(original.networks[0])
