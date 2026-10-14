from pathlib import Path

import pytest

from winproladder_mcp.analysis import device_references
from winproladder_mcp.architecture import ArchitecturePolicy, architecture_report
from winproladder_mcp.instruction_catalog import TEST23_PAYLOADS
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
from winproladder_mcp.matrix_functions import CONTROLS, STATUS
from winproladder_mcp.service import Service
from winproladder_mcp.timing import timed_simulate

ROOT = Path(__file__).resolve().parents[1]
POLICY = ArchitecturePolicy(forbid_m_to_m=True, allow_function_m_to_m=True)


def sample():
    return Ladder.model_validate(Service(ROOT).read("samples/test23.ldr")["ladder"])


def test_full_original_generation(tmp_path):
    (tmp_path / ".winproladder-policy.json").write_text(POLICY.model_dump_json())
    p = sample()
    assert [compile_network(n).hex() for n in p.networks] == list(TEST23_PAYLOADS.values())
    report = validation(p)
    assert report["valid"]
    assert [e["source"] for e in report["instruction_evidence"]] == [
        f"test23.ldr N{i:03}" for i in range(8)
    ]
    result = Service(tmp_path).generate(
        "matrix.ldr", p, io_contract=IOContract(inputs=["X1", "X2", "X7", "X8"], outputs=[])
    )
    assert Path(result["path"]).read_bytes() == (ROOT / "samples/test23.ldr").read_bytes()
    assert not result["layout"]["helper_devices"]


def test_full_matrix_spans_and_dynamic_length_reference():
    d = device_references(list(enumerate(sample().networks)))["devices"]
    assert d["R5004"]["reads"] == [0] and d["R5024"]["writes"] == [0]
    assert "R5025" not in d
    assert d["D52"]["reads"] == [2, 3] and d["D72"]["writes"] == [2]
    assert d["R1"]["reads"] == [1, 4, 6]
    assert d["R355"]["reads"] == [4] and d["R356"]["reads"] == []
    assert d["R365"]["writes"] == [4] and "R366" not in d
    assert d["R203"]["writes"] == [4, 7] and d["R204"]["writes"] == [4]
    # L is words, not bits: MBRD L=5 sees only R0..R4, not 80 words.
    assert 6 in d["R4"]["reads"] and 6 not in d["R5"]["reads"]


@pytest.mark.parametrize("index", range(8))
def test_native_controls_status_and_runtime_boundary(index):
    n = sample().networks[index]
    for name in CONTROLS[n.action.type]:
        setattr(n.action, name, "M30 AND TRUE")
    for name in STATUS[n.action.type]:
        setattr(n.action, name, [Coil(device="M", address=31)])
    p = Ladder(networks=[n])
    lowered, report = lower_ladder(p)
    decoded = Ladder(networks=[decode_network(compile_network(lowered.networks[0]))])
    assert not report["helper_devices"]
    for candidate in [p, lowered, decoded]:
        assert architecture_report(candidate, POLICY)["valid"]
        if STATUS[n.action.type]:
            assert not architecture_report(candidate, ArchitecturePolicy(forbid_m_to_m=True))[
                "valid"
            ]
    for name in CONTROLS[n.action.type]:
        assert getattr(decoded.networks[0].action, name) == "M30"
    with pytest.raises(ValueError):
        simulate(decoded, [{}], {})
    with pytest.raises(ValueError):
        timed_simulate(decoded, [{}], {}, 10)


@pytest.mark.parametrize("field", ["enable", "input_bit", "increment", "clear"])
@pytest.mark.parametrize("expression", ["TRUE", "FALSE", "X4", "NOT X4", "X4 AND M10", "X4 OR M10"])
def test_four_input_pin_separation(field, expression):
    n = sample().networks[7]
    setattr(n.action, field, expression)
    decoded = decode_network(compile_network(n))
    assert decoded is not None
    for name in CONTROLS[n.action.type]:
        assert parse_expression(getattr(decoded.action, name)) == parse_expression(
            getattr(n.action, name)
        )
    assert compile_network(decoded) == compile_network(n)


@pytest.mark.parametrize(
    "index,field,value",
    [
        (0, "length", 1),
        (0, "length", 257),
        (0, "source", "R3838"),
        (0, "source_b", "D4093"),
        (0, "destination", "R3840"),
        (1, "length_register", "R0"),
        (2, "length", "R1"),
        (4, "length", 5),
        (4, "length_register", None),
        (4, "length_register", "R3840"),
        (4, "source", "D3841"),
        (4, "destination", "R7900"),
        (5, "pointer", "R3840"),
        (6, "destination", "R0"),
        (7, "source", "R0"),
        (7, "pointer", "R3840"),
        (7, "destination", "D4094"),
        (0, "pulse", True),
        (7, "mode", 1),
        (0, "input_bit", "X2"),
    ],
)
def test_unencoded_forms_and_range_checks(index, field, value):
    data = sample().networks[index].action.model_dump()
    data[field] = value
    with pytest.raises(ValueError):
        ProcessFunction.model_validate(data)


@pytest.mark.parametrize("index", range(8))
def test_maximum_spans_and_in_place_operations(index):
    n = sample().networks[index]
    data = n.action.model_dump()
    if index != 4:
        data["length"] = 256
    for field, value in [("source", "D0"), ("source_b", "R5000"), ("destination", "D0")]:
        if data[field] is not None:
            data[field] = value
    if index == 4:
        data["length_register"] = "D3000"
    n.action = ProcessFunction.model_validate(data)
    assert decode_network(compile_network(n)).action == n.action


def test_status_contract_and_truncated_payloads(tmp_path):
    p = sample()
    p.networks[6].action.output = [Coil(device="Y", address=19)]
    io = IOContract(inputs=["X1", "X2", "X7", "X8"], outputs=[])
    with pytest.raises(ValueError):
        Service(tmp_path).generate("missing.ldr", p, io_contract=io)
    assert not (tmp_path / "artifacts/missing.ldr").exists()
    for raw in TEST23_PAYLOADS.values():
        assert decode_network(bytes.fromhex(raw)[:-1]) is None
