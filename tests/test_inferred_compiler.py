import random
from collections.abc import Callable
from itertools import product
from pathlib import Path

import pytest

from winproladder_mcp.design import design_guide
from winproladder_mcp.ir import (
    Coil,
    Counter,
    Ladder,
    Network,
    Timer,
    compile_network,
    decode_network,
    simulate,
    validation,
)
from winproladder_mcp.ldr import parse
from winproladder_mcp.logic import bit_address, parse_expression


@pytest.mark.parametrize(
    "file,index,condition,output",
    [
        ("test.ldr", 5, "(NOT X6 OR X8) AND X7 AND (X9 OR X10)", 6),
        ("test4.ldr", 7, "Y2 AND (X4 OR X5 OR (X6 AND NOT X7))", 9),
    ],
)
def test_branch_compiler_matches_exports(
    file: str, index: int, condition: str, output: int
) -> None:
    doc = parse((Path(__file__).parents[1] / "samples" / file).read_bytes())
    expected = list(reversed(doc.records))[index].payload
    assert compile_network(Network(condition=condition, coils=[Coil(address=output)])) == expected


def execute_words(payload: bytes, state: dict[int, bool]) -> bool:
    """Independent VM for test purposes, not the production decoder/evaluator."""
    accumulator = False
    stack = []
    for i in range(0, len(payload), 2):
        word = int.from_bytes(payload[i : i + 2], "big")
        if word == 0xE200:
            accumulator = stack.pop() and accumulator
        elif word == 0xE443:
            accumulator = stack.pop() or accumulator
        else:
            operation = word >> 13
            active = state.get(word & 0xFFF, False)
            if word & 0x1000:
                active = not active
            if operation == 2:
                accumulator = active
            elif operation == 3:
                stack.append(accumulator)
                accumulator = active
            elif operation == 4:
                accumulator = accumulator and active
            elif operation == 5:
                accumulator = accumulator or active
            elif operation == 6:
                assert not stack
                return not accumulator if word & 0x1000 else accumulator
            else:
                raise AssertionError(hex(word))
    raise AssertionError("Missing coil")


def test_random_trees_against_independent_vm() -> None:
    rng = random.Random(3278)
    names = ["X0", "X1", "Y2", "M240"]
    addresses = [0, 1, 0x102, 0x900]

    def tree(depth: int) -> tuple[str, Callable[[dict[str, bool]], bool]]:
        if depth == 0 or rng.random() < 0.25:
            name = rng.choice(names)
            return name, lambda state: state[name]
        left, lf = tree(depth - 1)
        if rng.random() < 0.2:
            return f"NOT ({left})", lambda state: not lf(state)
        right, rf = tree(depth - 1)
        if rng.random() < 0.5:
            return f"({left} AND {right})", lambda state: lf(state) and rf(state)
        return f"({left} OR {right})", lambda state: lf(state) or rf(state)

    for _ in range(150):
        expression, expected = tree(4)
        payload = compile_network(Network(condition=expression, coils=[Coil(address=0)]))
        for values in product([False, True], repeat=4):
            state = dict(zip(names, values, strict=True))
            encoded_state = dict(zip(addresses, values, strict=True))
            assert execute_words(payload, encoded_state) == expected(state), expression


@pytest.mark.parametrize(
    "expression",
    [
        "__import__('os').system('echo bad')",
        "X0.__class__",
        "X0[0]",
        "X0 + X1",
        "X00",
        "X256",
        "M999",
        "R0",
        "X0 and",
        "(" * 1000 + "X0" + ")" * 1000,
    ],
)
def test_reject_unsupported_or_executable_expression(expression: str) -> None:
    with pytest.raises(ValueError):
        parse_expression(expression)


def test_device_page_carry_and_not_precedence() -> None:
    assert bit_address("M239") == 0x8FF
    assert bit_address("M240") == 0x900
    assert compile_network(
        Network(condition="M240", coils=[Coil(device="M", address=255)])
    ) == bytes.fromhex("4900c90f")
    ladder = Ladder(networks=[Network(condition="!X0 AND X1 OR Y2", coils=[Coil(address=0)])])
    assert simulate(ladder, [{"X0": True, "X1": False}], {"Y2": True})[0]["Y0"] is True


def test_inferred_blocks_accept_new_parameters_and_conditions() -> None:
    for block in [
        Timer(address=10, preset=300, enable="X0 AND NOT X1"),
        Counter(address=5, preset=256, pulse="X0", clear="X1 OR M0"),
    ]:
        network = Network(block=block, coils=[Coil(address=2)])
        payload = compile_network(network)
        decoded = decode_network(payload)
        assert decoded is not None
        assert compile_network(decoded) == payload
        report = validation(Ladder(networks=[network]))
        assert report["valid"]
        assert not report["import_verified"]


def test_generated_interlock_both_start_forward_priority() -> None:
    example = design_guide()["examples"]["interlocked_forward_reverse_forward_priority"]
    ladder = Ladder.model_validate(example)
    trace = simulate(ladder, [{"X0": True, "X1": True}, {}, {"X2": True}, {"X1": True}, {}], {})
    assert [(x["Y0"], x["Y1"]) for x in trace] == [
        (True, False),
        (True, False),
        (False, False),
        (False, True),
        (False, True),
    ]


def test_all_sample_decoding_coverage() -> None:
    count = 0
    for path in (Path(__file__).parents[1] / "samples").glob("*.ldr"):
        for record in parse(path.read_bytes()).records:
            decoded = decode_network(record.payload)
            if decoded is not None:
                assert compile_network(decoded) == record.payload
                count += 1
    # Twelve exports; decoding does not imply structural/policy validity.
    assert count == 87


def test_flat_chains_keep_node_limit_without_consuming_branch_depth() -> None:
    expression = " AND ".join(f"X{i}" for i in range(128))
    network = Network(condition=expression, coils=[Coil(address=0)])
    payload = compile_network(network)
    assert len(payload) == 2 * 129
    decoded = decode_network(payload)
    assert decoded is not None
    assert compile_network(decoded) == payload
    with pytest.raises(ValueError, match="256 nodes"):
        parse_expression(expression + " AND X128")
    with pytest.raises(ValueError, match="depth 32"):
        parse_expression("NOT " * 33 + "X0")
