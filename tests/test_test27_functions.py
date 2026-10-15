"""FUN06/58..64 independent export oracles, conversion spans and mode boundaries."""

from pathlib import Path

import pytest

from winproladder_mcp.analysis import device_references
from winproladder_mcp.architecture import ArchitecturePolicy, architecture_report
from winproladder_mcp.conversion_functions import CONTROLS, STATUS
from winproladder_mcp.instruction_catalog import TEST27_PAYLOADS
from winproladder_mcp.io_contract import IOContract
from winproladder_mcp.ir import (
    Coil,
    Ladder,
    ProcessFunction,
    compile_network,
    decode_network,
    simulate,
    validation,
)
from winproladder_mcp.layout import lower_ladder
from winproladder_mcp.logic import parse_expression
from winproladder_mcp.optimize import simplify
from winproladder_mcp.service import Service
from winproladder_mcp.timing import timed_simulate

ROOT = Path(__file__).resolve().parents[1]
POLICY = ArchitecturePolicy(forbid_m_to_m=True, allow_function_m_to_m=True)
IO = IOContract(
    inputs=["X0", "X1", "X5", "X6", "X11", "X12", "X13", "X14"],
    outputs=[f"Y{i}" for i in range(16)],
)


def sample():
    return Ladder.model_validate(Service(ROOT).read("samples/test27.ldr")["ladder"])


def test_original_generation(tmp_path):
    (tmp_path / ".winproladder-policy.json").write_text(POLICY.model_dump_json())
    p = sample()
    assert p.profile == "FBs-40MC-test27"
    assert [compile_network(n).hex() for n in p.networks] == list(TEST27_PAYLOADS.values())
    assert [e["source"] for e in validation(p)["instruction_evidence"]] == [
        f"test27.ldr N{i:03}" for i in range(8)
    ]
    result = Service(tmp_path).generate("test27.ldr", p, io_contract=IO)
    assert Path(result["path"]).read_bytes() == (ROOT / "samples/test27.ldr").read_bytes()
    assert not result["layout"]["helper_devices"]


def test_screenshot_parameters_and_footprints():
    p = sample()
    a = [n.action for n in p.networks]
    assert (a[0].source, a[0].source_index, a[0].count, a[0].destination, a[0].high_priority) == (
        "R0",
        9,
        36,
        "WY0",
        "TRUE",
    )
    assert (a[1].source, a[1].count, a[1].destination) == ("R0", 0, "R100")
    assert (a[2].text, a[2].destination) == ("ABCDEF", "R200")
    assert (a[3].source, a[3].destination) == ("R20", "R50")
    assert (a[4].source, a[4].destination) == ("R5000", "R5100")
    assert simplify(parse_expression(a[4].enable)) == simplify(
        parse_expression("(X0 OR X6) AND M1")
    )
    assert (a[5].count, a[6].count) == (3, 1)
    assert [getattr(a[7], x) for x in CONTROLS[a[7].type]] == ["X11", "X12", "X13", "X14"]
    d = device_references(list(enumerate(p.networks)))["devices"]
    assert d["R2"]["reads"] == [0] and "R3" not in d
    assert all(d[f"Y{i}"]["writes"] == [0] for i in range(16))
    assert d["R100"]["reads"] == [1] and d["R100"]["writes"] == [1]
    assert d["R202"]["writes"] == [2] and "R203" not in d
    assert d["R22"]["reads"] == [3] and d["R51"]["writes"] == [3]
    assert d["R5001"]["reads"] == [4] and d["R5102"]["writes"] == [4]
    assert d["R1002"]["reads"] == [5] and "R1003" not in d
    assert d["R1100"]["reads"] == [5] and d["R1100"]["writes"] == [5]
    assert d["R1400"]["reads"] == [6] and d["R1400"]["writes"] == [6]
    assert d["R110"]["reads"] == [7] and d["R110"]["writes"] == [7]


@pytest.mark.parametrize("index", range(8))
@pytest.mark.parametrize(
    "expression", ["TRUE", "FALSE", "M30", "NOT X4", "X4 AND M10", "X4 OR M10"]
)
def test_independent_pins_status_and_policy(index, expression):
    for control in CONTROLS[sample().networks[index].action.type]:
        n = sample().networks[index]
        setattr(n.action, control, expression)
        for offset, name in enumerate(STATUS[n.action.type]):
            setattr(n.action, name, [Coil(device="M", address=31 + offset)])
        p = Ladder(networks=[n])
        lowered, report = lower_ladder(p)
        decoded = Ladder(networks=[decode_network(compile_network(lowered.networks[0]))])
        assert not report["helper_devices"]
        for candidate in [p, lowered, decoded]:
            assert architecture_report(candidate, POLICY)["valid"]
        for name in CONTROLS[n.action.type]:
            assert simplify(
                parse_expression(getattr(decoded.networks[0].action, name))
            ) == simplify(parse_expression(getattr(n.action, name)))
        for name in STATUS[n.action.type]:
            assert getattr(decoded.networks[0].action, name) == getattr(n.action, name)
        assert compile_network(decoded.networks[0]) == compile_network(lowered.networks[0])
        if STATUS[n.action.type] and "M" in expression:
            assert not architecture_report(decoded, ArchitecturePolicy(forbid_m_to_m=True))["valid"]


@pytest.mark.parametrize("index", range(8))
def test_runtime_boundary(index):
    p = Ladder(networks=[sample().networks[index]])
    with pytest.raises(ValueError):
        simulate(p, [{}], {})
    with pytest.raises(ValueError):
        timed_simulate(p, [{}], {}, 10)


@pytest.mark.parametrize(
    "index,field,value",
    [
        (0, "count", 1),
        (0, "count", 257),
        (0, "source_index", 16),
        (0, "source_index", None),
        (0, "destination", "WX0"),
        (1, "count", 4),
        (1, "count", None),
        (1, "count", True),
        (2, "text", "ABCDEG"),
        (2, "text", ""),
        (2, "text", None),
        (2, "destination", "R3838"),
        (2, "source", "R0"),
        (3, "source", "D4094"),
        (3, "destination", "R3839"),
        (4, "source", "D4095"),
        (4, "destination", "R8070"),
        (5, "count", 0),
        (5, "count", 512),
        (5, "length_register", "R1"),
        (6, "count", 0),
        (6, "error", [{"device": "M", "address": 1}]),
        (7, "destination", "D3072"),
        (7, "destination", "R3840"),
        (7, "count", 1),
        (7, "pulse", True),
        (1, "high_priority", "X0"),
        (0, "bit_length", 5),
        (0, "destination_index", 1),
        (7, "text", "ABCDEF"),
    ],
)
def test_invalid_and_unencoded_forms(index, field, value):
    data = sample().networks[index].action.model_dump()
    data[field] = value
    with pytest.raises(ValueError):
        ProcessFunction.model_validate(data)


@pytest.mark.parametrize(
    "source,expected", [("R0", 17), ("R3839", 1), ("D4095", 1), ("T250", 6), ("WX0", 257)]
)
def test_encod_maximum_span_and_clipping(source, expected):
    n = sample().networks[0]
    data = n.action.model_dump()
    data.update(source=source, source_index=15, count=256, destination="R100")
    n.action = ProcessFunction.model_validate(data)
    assert len(n.action.source_devices()) == expected
    assert decode_network(compile_network(n)).action == n.action


@pytest.mark.parametrize(
    "count,words,preserve", [(0, 1, True), (1, 1, False), (2, 2, True), (3, 2, False)]
)
def test_seven_segment_count_semantics(count, words, preserve):
    n = sample().networks[1]
    data = n.action.model_dump()
    data.update(count=count)
    n.action = ProcessFunction.model_validate(data)
    assert len(n.action.destination_devices()) == words
    assert ("R100" in n.action.source_devices()) == preserve
    assert decode_network(compile_network(n)).action == n.action


@pytest.mark.parametrize("index", [5, 6])
@pytest.mark.parametrize("count", [1, 4, 5, 511])
def test_hex_ascii_full_spans(index, count):
    n = sample().networks[index]
    data = n.action.model_dump()
    data.update(source="D0", destination="R5000", count=count)
    n.action = ProcessFunction.model_validate(data)
    expected = (count + 3) // 4 if index == 5 else count
    assert len(n.action.destination_devices()) == expected
    assert decode_network(compile_network(n)).action == n.action


def test_unknown_literal_and_hms_selector_rejected():
    raw = bytes.fromhex(TEST27_PAYLOADS[2])
    assert decode_network(raw.replace(bytes.fromhex("2042"), bytes.fromhex("2043"))) is None
    raw = bytes.fromhex(TEST27_PAYLOADS[4])
    assert decode_network(raw.replace(bytes.fromhex("f4dd0000"), bytes.fromhex("f4dd0001"))) is None


def test_contract_truncation_and_field_leaks(tmp_path):
    for field, missing in [("inputs", "X14"), ("inputs", "X6"), ("outputs", "Y15")]:
        io = IO.model_copy(update={field: [x for x in getattr(IO, field) if x != missing]})
        with pytest.raises(ValueError):
            Service(tmp_path).generate("bad.ldr", sample(), io_contract=io)
    assert not (tmp_path / "artifacts/bad.ldr").exists()
    for raw in TEST27_PAYLOADS.values():
        assert decode_network(bytes.fromhex(raw)[:-1]) is None
    for data in [
        dict(type="shift_left", destination="R0", count=0),
        dict(type="move_word", source="R0", destination="R1", text="ABCDEF"),
    ]:
        with pytest.raises(ValueError):
            ProcessFunction.model_validate(data)
