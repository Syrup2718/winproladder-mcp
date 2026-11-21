import itertools
import random

import pytest

from winproladder_mcp.ir import Ladder
from winproladder_mcp.layout import expressions, lower_ladder, requires_lowering
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
