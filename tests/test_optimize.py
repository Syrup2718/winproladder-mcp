import hashlib
import itertools
import random
from pathlib import Path

import pytest

from winproladder_mcp.ir import Ladder, decode_network
from winproladder_mcp.layout import expressions, lower_ladder, requires_lowering
from winproladder_mcp.ldr import parse
from winproladder_mcp.logic import Expr, evaluate, expression_text, parse_expression
from winproladder_mcp.optimize import simplify


@pytest.mark.parametrize(
    "source,expected",
    [
        ("X0 AND X0 AND TRUE", "X0"),
        ("X0 OR (X0 AND X1)", "X0"),
        ("X0 AND (X0 OR X1)", "X0"),
        ("(X0 AND X1) OR (X1 AND X0 AND X2)", "X0 AND X1"),
        ("X0 AND NOT X0", "FALSE"),
        ("X0 OR NOT X0", "TRUE"),
        ("(X0 AND X1) OR (X0 AND X2)", "X0 AND (X1 OR X2)"),
        ("(X0 OR X1) AND (X0 OR X2)", "X0 OR (X1 AND X2)"),
    ],
)
def test_identities(source, expected):
    assert simplify(parse_expression(source)) == simplify(parse_expression(expected))


def test_random_trees_exhaustive_truth_tables():
    rng = random.Random(107)

    def tree(depth):
        if not depth or rng.random() < 0.3:
            return rng.choice(
                [Expr("true"), Expr("false")]
                + [Expr("contact", f"X{i}", nc) for i in range(4) for nc in (False, True)]
            )
        return Expr(rng.choice(["and", "or"]), items=(tree(depth - 1), tree(depth - 1)))

    for _ in range(500):
        original = tree(5)
        reduced = simplify(original)
        assert simplify(reduced) == reduced
        ladder = Ladder.model_validate(
            {"networks": [{"condition": expression_text(original), "coils": [{"address": 0}]}]}
        )
        lowered, _ = lower_ladder(ladder)
        assert all(not requires_lowering(e) for n in lowered.networks for e in expressions(n))
        for values in itertools.product((False, True), repeat=4):
            state = dict(zip([f"X{i}" for i in range(4)], values, strict=True))
            assert evaluate(original, state) == evaluate(reduced, state)
            expected = evaluate(original, state)
            for network in lowered.networks:
                value = evaluate(expressions(network)[0], state)
                coil = network.coils[0]
                state[f"{coil.device}{coil.address}"] = value
            assert state["Y0"] == expected


@pytest.mark.parametrize(
    "condition",
    [
        "X0 AND (X1 OR X2)",
        "X0 OR (X1 AND X2)",
        "X0 AND X1 AND (X2 OR (X3 AND X4))",  # CH01 p.14
        "(X0 AND X1) OR (X0 AND X2)",
    ],
)
def test_manual_reordering_needs_no_helpers(condition):
    source = Ladder.model_validate(
        {"networks": [{"condition": condition, "coils": [{"address": 0}]}]}
    )
    lowered, report = lower_ladder(source)
    assert report["helper_devices"] == []
    assert len(lowered.networks) == 1
    assert all(not requires_lowering(e) for e in expressions(lowered.networks[0]))


def test_user_confirmed_baseline_and_optimized_size():
    fixtures = Path(__file__).parent / "fixtures"
    baseline = (fixtures / "traffic_light-connected-verified.ldr").read_bytes()
    assert hashlib.sha256(baseline).hexdigest() == (
        "a4694aa8db73737ada925742ebc6ba164aee52e56137bd5ae201017c203b3b94"
    )
    original = parse((fixtures / "traffic_light-dangling.ldr").read_bytes())
    source = Ladder(networks=[decode_network(r.payload) for r in reversed(original.records)])
    _, report = lower_ladder(source)
    assert report["metrics"]["networks_after"] < len(parse(baseline).records)
    assert len(report["helper_devices"]) < 13


def test_traffic_complete_timing_cycle_and_skip():
    from winproladder_mcp.timing import timed_simulate

    raw = (Path(__file__).parent / "fixtures/traffic_light-dangling.ldr").read_bytes()
    source = Ladder(networks=[decode_network(r.payload) for r in reversed(parse(raw).records)])
    lowered, _ = lower_ladder(source)
    for scans in (
        [{"X0": True}] * 256,
        [{"X0": True, "X1": i in {1, 20, 110, 210}} for i in range(256)],
    ):
        old = timed_simulate(source, scans, {}, 100)
        new = timed_simulate(lowered, scans, {}, 100)
        for a, b in zip(old, new, strict=True):
            assert all(b[k] == v for k, v in a.items())
        assert any(s["Y0"] for s in old)
        assert any(s["Y1"] for s in old)
        assert any(s["Y2"] for s in old)
