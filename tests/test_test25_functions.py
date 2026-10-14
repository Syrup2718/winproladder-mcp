"""FUN42..49 export oracles, packing footprints and strict mode boundaries."""

from pathlib import Path

import pytest

from winproladder_mcp.analysis import device_references
from winproladder_mcp.architecture import ArchitecturePolicy, architecture_report
from winproladder_mcp.instruction_catalog import TEST25_PAYLOADS
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
from winproladder_mcp.packing_functions import STATUS
from winproladder_mcp.service import Service
from winproladder_mcp.timing import timed_simulate

ROOT = Path(__file__).resolve().parents[1]
POLICY = ArchitecturePolicy(forbid_m_to_m=True, allow_function_m_to_m=True)
IO = IOContract(inputs=[f"X{i}" for i in range(16)], outputs=[f"Y{i}" for i in range(16)])


def sample():
    return Ladder.model_validate(Service(ROOT).read("samples/test25.ldr")["ladder"])


def test_original_byte_generation(tmp_path):
    (tmp_path / ".winproladder-policy.json").write_text(POLICY.model_dump_json())
    p = sample()
    assert [compile_network(n).hex() for n in p.networks] == list(TEST25_PAYLOADS.values())
    assert [e["source"] for e in validation(p)["instruction_evidence"]] == [
        f"test25.ldr N{i:03}" for i in range(8)
    ]
    result = Service(tmp_path).generate("test25.ldr", p, io_contract=IO)
    assert Path(result["path"]).read_bytes() == (ROOT / "samples/test25.ldr").read_bytes()
    assert not result["layout"]["helper_devices"]


def test_parameters_match_screenshot():
    a = [n.action for n in sample().networks]
    assert (a[0].source, a[0].source_index, a[0].destination, a[0].destination_index) == (
        "WX0",
        11,
        "R0",
        7,
    )
    assert (a[1].source_index, a[1].destination_index) == (2, 1)
    assert (a[2].source_index, a[2].destination_index) == (1, 1)
    assert (a[3].source, a[3].destination) == ("R111", "R222")
    assert a[4].destination == "R100"
    assert (a[5].source, a[5].count, a[5].destination) == ("R22", 3, "WY0")
    assert (a[6].source, a[6].count, a[6].destination) == ("WX0", 2, "R100")
    assert (a[7].source, a[7].length_register, a[7].destination) == ("R2000", "R999", "R5000")


def test_full_spans_and_partial_word_preservation():
    d = device_references(list(enumerate(sample().networks)))["devices"]
    for name, index in [("R0", 0), ("R20", 1), ("R42", 2), ("R111", 3), ("R222", 3)]:
        assert index in d[name]["reads"] and index in d[name]["writes"]
    assert d["R100"]["reads"] == [4] and d["R100"]["writes"] == [4, 6]
    assert d["R101"]["writes"] == [6] and "R102" not in d
    assert d["R24"]["reads"] == [5] and "R25" not in d
    assert all(d[f"Y{i}"]["writes"] == [5] for i in range(16))
    assert all(d[f"X{i}"]["reads"] == [0, 6] for i in range(16))
    assert d["R999"]["reads"] == [7] and not d["R999"]["writes"]
    assert d["R2255"]["reads"] == [7] and "R2256" not in d
    assert d["R5127"]["writes"] == [7] and "R5128" not in d


@pytest.mark.parametrize("index", range(8))
@pytest.mark.parametrize(
    "expression", ["TRUE", "FALSE", "M30", "NOT X4", "X4 AND M10", "X4 OR M10"]
)
def test_conditions_status_and_policy(index, expression):
    n = sample().networks[index]
    n.action.enable = expression
    for name in STATUS[n.action.type]:
        setattr(n.action, name, [Coil(device="M", address=31)])
    p = Ladder(networks=[n])
    lowered, report = lower_ladder(p)
    decoded = Ladder(networks=[decode_network(compile_network(lowered.networks[0]))])
    assert not report["helper_devices"]
    for candidate in [p, lowered, decoded]:
        assert architecture_report(candidate, POLICY)["valid"]
    assert simplify(parse_expression(decoded.networks[0].action.enable)) == simplify(
        parse_expression(expression)
    )
    assert compile_network(decoded.networks[0]) == compile_network(lowered.networks[0])
    if STATUS[n.action.type] and "M" in expression:
        assert not architecture_report(decoded, ArchitecturePolicy(forbid_m_to_m=True))["valid"]


@pytest.mark.parametrize("index", range(8))
def test_no_unverified_runtime(index):
    p = Ladder(networks=[sample().networks[index]])
    with pytest.raises(ValueError):
        simulate(p, [{}], {})
    with pytest.raises(ValueError):
        timed_simulate(p, [{}], {}, 10)


@pytest.mark.parametrize(
    "index,field,value",
    [
        (0, "source_index", -1),
        (0, "destination_index", 16),
        (0, "source_index", None),
        (0, "source_index", True),
        (1, "source_index", 4),
        (2, "destination_index", 2),
        (3, "source", "WX0"),
        (3, "destination", "R3840"),
        (4, "destination", "T1"),
        (4, "source", "R0"),
        (5, "count", 0),
        (5, "count", 5),
        (5, "count", "R1"),
        (5, "source", "D4094"),
        (5, "destination", "WX0"),
        (6, "destination", "R3839"),
        (6, "source", "12"),
        (7, "source", "R3840"),
        (7, "source", "D3841"),
        (7, "destination", "D3969"),
        (7, "length_register", "R3840"),
        (7, "length_register", None),
        (7, "count", 2),
        (7, "length", 10),
        (7, "error", [{"device": "M", "address": 1}]),
        (0, "pulse", True),
        (0, "ones", "X1"),
        (5, "source_index", 1),
    ],
)
def test_reject_invalid_and_unencoded_forms(index, field, value):
    data = sample().networks[index].action.model_dump()
    data[field] = value
    with pytest.raises(ValueError):
        ProcessFunction.model_validate(data)


@pytest.mark.parametrize("index,high", [(0, 15), (1, 3), (2, 1)])
def test_index_boundaries(index, high):
    for start, end in [(0, high), (high, 0)]:
        n = sample().networks[index]
        data = n.action.model_dump()
        data.update(source_index=start, destination_index=end, source="D4095", destination="D4095")
        n.action = ProcessFunction.model_validate(data)
        assert decode_network(compile_network(n)).action == n.action


@pytest.mark.parametrize("index", [5, 6])
@pytest.mark.parametrize("count", [1, 4])
def test_nibble_count_spans(index, count):
    n = sample().networks[index]
    data = n.action.model_dump()
    data.update(source="D0", destination="R5000", count=count)
    n.action = ProcessFunction.model_validate(data)
    assert decode_network(compile_network(n)).action == n.action
    assert len(n.action.source_devices()) == (count if index == 5 else 1)
    assert len(n.action.destination_devices()) == (1 if index == 5 else count)


def test_dynamic_maximum_bank_boundary():
    n = sample().networks[7]
    data = n.action.model_dump()
    data.update(source="D3840", destination="R7944", length_register="D0")
    n.action = ProcessFunction.model_validate(data)
    assert decode_network(compile_network(n)).action == n.action
    assert "D4095" in n.action.source_devices()
    assert "R8071" in n.action.destination_devices()


def test_full_word_contract_and_truncations(tmp_path):
    for field, missing in [("inputs", "X15"), ("outputs", "Y15"), ("outputs", "Y12")]:
        io = IO.model_copy(update={field: [x for x in getattr(IO, field) if x != missing]})
        with pytest.raises(ValueError):
            Service(tmp_path).generate("bad.ldr", sample(), io_contract=io)
    assert not (tmp_path / "artifacts/bad.ldr").exists()
    for raw in TEST25_PAYLOADS.values():
        assert decode_network(bytes.fromhex(raw)[:-1]) is None
