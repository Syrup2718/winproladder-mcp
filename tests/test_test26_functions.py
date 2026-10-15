"""FUN50..57: export oracle, dynamic byte lengths, shift pins and decode spans."""

from pathlib import Path

import pytest

from winproladder_mcp.analysis import device_references
from winproladder_mcp.architecture import ArchitecturePolicy, architecture_report
from winproladder_mcp.instruction_catalog import TEST26_PAYLOADS
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
from winproladder_mcp.shift_functions import CONTROLS, STATUS
from winproladder_mcp.timing import timed_simulate

ROOT = Path(__file__).resolve().parents[1]
POLICY = ArchitecturePolicy(forbid_m_to_m=True, allow_function_m_to_m=True)
IO = IOContract(inputs=[f"X{i}" for i in range(16)], outputs=["Y0", "Y2"])


def sample():
    return Ladder.model_validate(Service(ROOT).read("samples/test26.ldr")["ladder"])


def test_original_byte_generation(tmp_path):
    (tmp_path / ".winproladder-policy.json").write_text(POLICY.model_dump_json())
    p = sample()
    assert [compile_network(n).hex() for n in p.networks] == list(TEST26_PAYLOADS.values())
    assert [e["source"] for e in validation(p)["instruction_evidence"]] == [
        f"test26.ldr N{i:03}" for i in range(8)
    ]
    result = Service(tmp_path).generate("test26.ldr", p, io_contract=IO)
    assert Path(result["path"]).read_bytes() == (ROOT / "samples/test26.ldr").read_bytes()
    assert not result["layout"]["helper_devices"]


def test_parameters_match_screenshot():
    a = [n.action for n in sample().networks]
    assert (a[0].source, a[0].length_register, a[0].destination) == ("R1000", "R999", "R1500")
    assert (a[1].destination, a[1].count, a[1].enable, a[1].input_bit) == ("R22", 2, "M3", "TRUE")
    assert a[1].output == [Coil(device="Y", address=0)]
    assert (a[2].destination, a[2].length_register, a[2].enable, a[2].input_bit) == (
        "R23",
        "R1",
        "M1",
        "TRUE",
    )
    assert a[2].output == [Coil(device="M", address=2)]
    assert (a[3].destination, a[3].length_register) == ("R5000", "D22")
    assert (a[4].destination, a[4].count) == ("D22", 9)
    assert (a[5].source, a[5].destination) == ("R60", "R70")
    assert (a[6].source, a[6].destination) == ("R40", "R46")
    assert (a[7].source, a[7].source_index, a[7].bit_length, a[7].destination) == (
        "WX0",
        3,
        5,
        "R2",
    )


def test_full_spans_and_in_place_reads():
    d = device_references(list(enumerate(sample().networks)))["devices"]
    assert d["R1127"]["reads"] == [0] and "R1128" not in d
    assert d["R1755"]["writes"] == [0] and "R1756" not in d
    assert not d["R1500"]["reads"]  # BDIST clears the destination high bytes.
    assert d["R999"]["reads"] == [0] and not d["R999"]["writes"]
    for name, index in [("R22", 1), ("R23", 2), ("R5000", 3), ("D22", 4)]:
        assert index in d[name]["reads"] and index in d[name]["writes"]
    assert d["D22"]["reads"] == [3, 4]
    assert d["R1"]["reads"] == [2]
    assert d["R2"]["writes"] == [7] and d["R3"]["writes"] == [7] and "R4" not in d
    assert all(d[f"X{i}"]["reads"] == [7] for i in range(16))


@pytest.mark.parametrize("index", range(8))
@pytest.mark.parametrize(
    "expression", ["TRUE", "FALSE", "M30", "NOT X4", "X4 AND M10", "X4 OR M10"]
)
def test_each_input_pin_status_and_policy(index, expression):
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
def test_runtime_not_claimed(index):
    p = Ladder(networks=[sample().networks[index]])
    with pytest.raises(ValueError):
        simulate(p, [{}], {})
    with pytest.raises(ValueError):
        timed_simulate(p, [{}], {}, 10)


@pytest.mark.parametrize(
    "index,field,value",
    [
        (0, "length_register", None),
        (0, "length_register", "R3840"),
        (0, "source", "D3969"),
        (0, "source", "R3840"),
        (0, "destination", "D3841"),
        (0, "count", 2),
        (0, "error", [{"device": "M", "address": 1}]),
        (1, "count", 0),
        (1, "count", 17),
        (1, "count", True),
        (1, "count", None),
        (1, "length_register", "R1"),
        (2, "count", 2),
        (2, "length_register", None),
        (3, "input_bit", "X0"),
        (4, "destination", "R3840"),
        (4, "count", 17),
        (5, "source", "1"),
        (5, "destination", "WX0"),
        (6, "count", 1),
        (7, "source_index", 16),
        (7, "source_index", None),
        (7, "bit_length", 0),
        (7, "bit_length", 9),
        (7, "bit_length", None),
        (7, "bit_length", "R1"),
        (7, "destination_index", 1),
        (7, "destination", "D4095"),
        (0, "pulse", True),
        (1, "bit_length", 1),
    ],
)
def test_invalid_and_unencoded_forms(index, field, value):
    data = sample().networks[index].action.model_dump()
    data[field] = value
    with pytest.raises(ValueError):
        ProcessFunction.model_validate(data)


@pytest.mark.parametrize("index", [1, 4])
@pytest.mark.parametrize("count", [1, 16])
def test_shift_count_bounds(index, count):
    n = sample().networks[index]
    data = n.action.model_dump()
    data.update(count=count, destination="D4095")
    n.action = ProcessFunction.model_validate(data)
    assert decode_network(compile_network(n)).action == n.action


@pytest.mark.parametrize(
    "source,start,bits,expected",
    [
        ("R0", 15, 8, {"R0", "R1"}),
        ("R3839", 15, 8, {"R3839"}),
        ("R8071", 15, 8, {"R8071"}),
        ("D4095", 15, 8, {"D4095"}),
        ("T254", 15, 8, {"T254", "T255"}),
        ("T255", 15, 8, {"T255"}),
        ("WX0", 15, 8, {"WX0", *(f"X{i}" for i in range(32))}),
    ],
)
def test_decod_cross_word_and_bank_end_clipping(source, start, bits, expected):
    n = sample().networks[7]
    data = n.action.model_dump()
    data.update(source=source, source_index=start, bit_length=bits, destination="D4080")
    n.action = ProcessFunction.model_validate(data)
    assert n.action.source_devices() == expected
    assert n.action.destination_devices() == {f"D{i}" for i in range(4080, 4096)}
    assert decode_network(compile_network(n)).action == n.action


@pytest.mark.parametrize(
    "bits,words", [(1, 1), (2, 1), (3, 1), (4, 1), (5, 2), (6, 4), (7, 8), (8, 16)]
)
def test_decod_power_of_two_width(bits, words):
    n = sample().networks[7]
    data = n.action.model_dump()
    data.update(source="R0", source_index=0, bit_length=bits, destination="D0")
    n.action = ProcessFunction.model_validate(data)
    assert len(n.action.destination_devices()) == words
    assert decode_network(compile_network(n)).action == n.action


def test_bdist_maximum_spans():
    n = sample().networks[0]
    data = n.action.model_dump()
    data.update(source="D3968", destination="R7816", length_register="D0")
    n.action = ProcessFunction.model_validate(data)
    assert "D4095" in n.action.source_devices()
    assert "R8071" in n.action.destination_devices()
    assert decode_network(compile_network(n)).action == n.action


def test_contract_and_truncation(tmp_path):
    for field, missing in [("inputs", "X15"), ("outputs", "Y0"), ("outputs", "Y2")]:
        io = IO.model_copy(update={field: [x for x in getattr(IO, field) if x != missing]})
        with pytest.raises(ValueError):
            Service(tmp_path).generate("bad.ldr", sample(), io_contract=io)
    assert not (tmp_path / "artifacts/bad.ldr").exists()
    for raw in TEST26_PAYLOADS.values():
        assert decode_network(bytes.fromhex(raw)[:-1]) is None


def test_new_fields_do_not_leak_into_old_instructions():
    with pytest.raises(ValueError):
        ProcessFunction(type="nibble_unite", source="R0", destination="R10", count=5)
    with pytest.raises(ValueError):
        ProcessFunction(type="move_word", source="R0", destination="R10", bit_length=1)
