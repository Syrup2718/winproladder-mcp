"""Original GUI export oracle plus boundary, pin, policy and physical IO checks."""

from pathlib import Path

import pytest

from winproladder_mcp.analysis import device_references
from winproladder_mcp.architecture import ArchitecturePolicy, architecture_report
from winproladder_mcp.instruction_catalog import TEST24_PAYLOADS
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
from winproladder_mcp.service import Service
from winproladder_mcp.timing import timed_simulate
from winproladder_mcp.transfer_functions import CONTROLS, STATUS

ROOT = Path(__file__).resolve().parents[1]
POLICY = ArchitecturePolicy(forbid_m_to_m=True, allow_function_m_to_m=True)
IO = IOContract(inputs=["X0", "X2", "X6", "X9", "X11"], outputs=[f"Y{i}" for i in range(8, 24)])


def sample():
    return Ladder.model_validate(Service(ROOT).read("samples/test24.ldr")["ladder"])


def test_original_generation_and_evidence(tmp_path):
    (tmp_path / ".winproladder-policy.json").write_text(POLICY.model_dump_json())
    p = sample()
    assert [compile_network(n).hex() for n in p.networks] == list(TEST24_PAYLOADS.values())
    report = validation(p)
    assert report["valid"]
    assert [e["source"] for e in report["instruction_evidence"]] == [
        f"test24.ldr N{i:03}" for i in range(8)
    ]
    result = Service(tmp_path).generate("test24.ldr", p, io_contract=IO)
    assert Path(result["path"]).read_bytes() == (ROOT / "samples/test24.ldr").read_bytes()
    assert not result["layout"]["helper_devices"]


def test_decoded_parameters_match_screenshot():
    a = [n.action for n in sample().networks]
    assert (a[0].source, a[0].destination, a[0].length) == ("R2", "R2", 5)
    assert (a[0].enable, a[0].input_bit, a[0].left) == ("X0", "X0", "FALSE")
    assert (a[1].source, a[1].destination, a[1].length) == ("R12", "R12", 5)
    assert (a[2].source, a[2].destination, a[2].length, a[2].ones) == ("R100", "R100", 10, "M3")
    assert a[2].zero == [Coil(device="M", address=6)]
    assert (a[3].source, a[3].destination, a[3].length, a[3].ascending) == (
        "R122",
        "R155",
        4,
        "TRUE",
    )
    assert (a[4].destination, a[4].length, a[4].ones) == ("R111", 2, "FALSE")
    assert (a[5].source, a[5].destination) == ("R11", "R20")
    assert (a[6].source, a[6].destination) == ("R5", "WY8")
    assert (a[7].trigger, a[7].bit_destination) == ("X11", "M10")


def test_word_spans_and_toggle_read_modify_write():
    d = device_references(list(enumerate(sample().networks)))["devices"]
    assert d["R6"]["writes"] == [0] and "R7" not in d
    assert d["R109"]["reads"] == [2] and "R110" not in d
    assert d["R100"]["writes"] == [2] and not d["R101"]["writes"]
    assert d["R158"]["writes"] == [3] and "R159" not in d
    assert d["R112"]["writes"] == [4] and "R113" not in d
    assert all(d[f"Y{i}"]["writes"] == [6] for i in range(8, 24))
    assert "Y7" not in d and "Y24" not in d
    assert d["M10"]["reads"] == [7] and d["M10"]["writes"] == [7]


@pytest.mark.parametrize("index", range(8))
def test_control_status_wiring_and_policy(index):
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
        if STATUS[n.action.type] or n.action.type == "toggle_bit":
            assert not architecture_report(candidate, ArchitecturePolicy(forbid_m_to_m=True))[
                "valid"
            ]
    for name in CONTROLS[n.action.type]:
        assert getattr(decoded.networks[0].action, name) == "M30"
    with pytest.raises(ValueError):
        simulate(decoded, [{}], {})
    with pytest.raises(ValueError):
        timed_simulate(decoded, [{}], {}, 10)


@pytest.mark.parametrize("index", range(8))
@pytest.mark.parametrize("expression", ["TRUE", "FALSE", "X4", "NOT X4", "X4 AND M10", "X4 OR M10"])
def test_each_control_separately(index, expression):
    for field in CONTROLS[sample().networks[index].action.type]:
        n = sample().networks[index]
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
        (1, "destination", "D4093"),
        (2, "destination", "R3840"),
        (3, "length", 128),
        (3, "length", 1),
        (4, "length", 0),
        (4, "length", 512),
        (4, "destination", "D4095"),
        (5, "source", "10"),
        (5, "destination", "WX0"),
        (5, "destination", "D3072"),
        (6, "destination", "WY7"),
        (6, "source", "R3848"),
        (7, "bit_destination", "X0"),
        (7, "bit_destination", "M1000"),
        (7, "enable", "X0"),
        (7, "length", 2),
        (0, "pulse", True),
        (0, "length_register", "R1"),
        (2, "ascending", "X0"),
        (5, "trigger", "X0"),
    ],
)
def test_invalid_or_unencoded_forms(index, field, value):
    data = sample().networks[index].action.model_dump()
    data[field] = value
    with pytest.raises(ValueError):
        ProcessFunction.model_validate(data)


@pytest.mark.parametrize("index,length", [(0, 256), (1, 256), (2, 256), (3, 127), (4, 1), (4, 511)])
def test_lengths_and_non_sample_operands(index, length):
    n = sample().networks[index]
    data = n.action.model_dump()
    data.update(length=length, destination="D3500")
    if data["source"] is not None:
        data["source"] = "R5000"
    n.action = ProcessFunction.model_validate(data)
    assert decode_network(compile_network(n)).action == n.action
    assert len(n.action.destination_devices()) == (1 if index == 2 else length)


def test_wy8_contract_checks_entire_word_before_writing(tmp_path):
    for missing in [8, 16, 23]:
        io = IO.model_copy(update={"outputs": [x for x in IO.outputs if x != f"Y{missing}"]})
        with pytest.raises(ValueError):
            Service(tmp_path).generate("bad.ldr", sample(), io_contract=io)
    assert not (tmp_path / "artifacts/bad.ldr").exists()


def test_payload_truncations_rejected():
    for raw in TEST24_PAYLOADS.values():
        payload = bytes.fromhex(raw)
        assert decode_network(payload[:-1]) is None
