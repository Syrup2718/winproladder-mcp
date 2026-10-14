from pathlib import Path

import pytest

from winproladder_mcp.analysis import device_references
from winproladder_mcp.architecture import ArchitecturePolicy, architecture_report
from winproladder_mcp.instruction_catalog import TEST22_PAYLOADS
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
from winproladder_mcp.service import Service
from winproladder_mcp.table_functions import CONTROLS, STATUS
from winproladder_mcp.timing import timed_simulate

ROOT = Path(__file__).resolve().parents[1]
POLICY = ArchitecturePolicy(forbid_m_to_m=True, allow_function_m_to_m=True)


def sample():
    return Ladder.model_validate(Service(ROOT).read("samples/test22.ldr")["ladder"])


def contract():
    return IOContract(
        inputs=["X0", "X2", "X3", "X5", "X7"], outputs=[f"Y{i}" for i in range(5, 15)]
    )


def test_full_generation_matches_original_including_empty_record(tmp_path):
    (tmp_path / ".winproladder-policy.json").write_text(POLICY.model_dump_json())
    ladder = sample()
    assert ladder.networks[-1].empty
    assert [compile_network(n).hex() for n in ladder.networks] == list(TEST22_PAYLOADS.values())
    report = validation(ladder)
    assert report["valid"]
    assert [e["source"] for e in report["instruction_evidence"]] == [
        f"test22.ldr N{i:03}" for i in range(8)
    ]
    result = Service(tmp_path).generate("tables.ldr", ladder, io_contract=contract())
    assert Path(result["path"]).read_bytes() == (ROOT / "samples/test22.ldr").read_bytes()
    assert not result["layout"]["helper_devices"]


def test_complete_spans_and_system_flag():
    r = device_references(list(enumerate(sample().networks)))
    assert r["complete"]
    d = r["devices"]
    assert d["R219"]["reads"] == [7] and "R220" not in d
    assert d["R203"]["writes"] == [2] and d["R204"]["writes"] == []
    assert d["R11"]["writes"] == [3, 5]  # OW and queue's tenth element.
    assert d["R111"]["writes"] == [6] and "R112" not in d
    assert d["R1"]["writes"] == [3, 4, 5]  # Ordinary table words plus queue Pr.
    assert d["M1975"]["reads"] == [7]
    assert all(d[f"Y{i}"]["writes"] == [7] for i in range(5, 15))
    assert "Y15" not in d


@pytest.mark.parametrize("index", range(8))
def test_controls_status_policy_lowering_and_runtime_boundary(index):
    n = sample().networks[index]
    for control in CONTROLS[n.action.type]:
        setattr(n.action, control, "M25 AND TRUE")
    for pin in STATUS[n.action.type]:
        setattr(n.action, pin, [Coil(device="M", address=26)])
    if n.action.type == "block_compare":
        n.action.bit_destination = "M100"
    ladder = Ladder(networks=[n])
    lowered, report = lower_ladder(ladder)
    decoded = Ladder(networks=[decode_network(compile_network(lowered.networks[0]))])
    assert not report["helper_devices"]
    for candidate in [ladder, lowered, decoded]:
        assert architecture_report(candidate, POLICY)["valid"]
        if STATUS[n.action.type]:
            assert not architecture_report(candidate, ArchitecturePolicy(forbid_m_to_m=True))[
                "valid"
            ]
    for control in CONTROLS[n.action.type]:
        assert getattr(decoded.networks[0].action, control) == "M25"
    with pytest.raises(ValueError):
        simulate(decoded, [{}], {})
    with pytest.raises(ValueError):
        timed_simulate(decoded, [{}], {}, 10)


def test_implicit_bkcmp_bits_enforce_policy_without_status_coils(tmp_path):
    n = sample().networks[7]
    n.action.enable = "M10"
    n.action.bit_destination = "M990"
    ladder = Ladder(networks=[n])
    for candidate in [
        ladder,
        lower_ladder(ladder)[0],
        Ladder(networks=[decode_network(compile_network(n))]),
    ]:
        assert architecture_report(candidate, POLICY)["valid"]
        report = architecture_report(candidate, ArchitecturePolicy(forbid_m_to_m=True))
        assert not report["valid"]
        assert set(report["m_to_m_networks"][0]["writes"]) == {f"M{i}" for i in range(990, 1000)}
    io = contract()
    io.outputs.remove("Y14")
    with pytest.raises(ValueError):
        Service(tmp_path).generate("missing.ldr", sample(), io_contract=io)
    assert not (tmp_path / "artifacts/missing.ldr").exists()


@pytest.mark.parametrize(
    "index,field,value",
    [
        (0, "length", 1),
        (0, "length", 257),
        (0, "value", 32768),
        (0, "value", -32769),
        (0, "value", True),
        (0, "value", "R20"),
        (0, "pointer", "R3840"),
        (0, "source", "R3839"),
        (1, "destination", "D4090"),
        (2, "destination", "R3840"),
        (2, "value", None),
        (3, "output_word", "R3840"),
        (3, "input_word", "20"),
        (4, "destination", "R3839"),
        (5, "destination", "R3840"),
        (5, "pointer", "R3840"),
        (6, "destination", "D4090"),
        (6, "value", 1),
        (7, "source", "D4080"),
        (7, "bit_destination", "Y250"),
        (7, "bit_destination", "M991"),
        (7, "bit_destination", "S0"),
        (7, "bit_destination", "X0"),
        (7, "length", 0),
        (7, "length", 257),
        (3, "push", "X0"),
        (5, "left", "X0"),
        (1, "pulse", True),
        (7, "mode", 1),
    ],
)
def test_invalid_spans_and_unencoded_forms(index, field, value):
    data = sample().networks[index].action.model_dump()
    data[field] = value
    with pytest.raises(ValueError):
        ProcessFunction.model_validate(data)


@pytest.mark.parametrize("index", range(8))
def test_maximum_length_and_other_direct_banks(index):
    data = sample().networks[index].action.model_dump()
    data["length"] = 256
    if data["source"] is not None:
        data["source"] = "D0"
    if data["destination"] is not None:
        data["destination"] = "R5000"
    if data["bit_destination"] is not None:
        data["bit_destination"] = "Y0"
    n = sample().networks[index]
    n.action = ProcessFunction.model_validate(data)
    raw = compile_network(n)
    assert decode_network(raw).action == n.action
    assert bytes.fromhex("00ff") in raw


@pytest.mark.parametrize("index", [0, 2])
@pytest.mark.parametrize("value", [-32768, -1, 0, 32767])
def test_signed_constant_variants_are_roundtrippable(index, value):
    n = sample().networks[index]
    n.action.value = value
    assert decode_network(compile_network(n)).action.value == value


def test_read_only_compare_and_one_group_bkcmp():
    n = sample().networks[1]
    data = n.action.model_dump()
    data.update(source="R3840", destination="R3850")
    n.action = ProcessFunction.model_validate(data)
    assert decode_network(compile_network(n)).action == n.action
    n = sample().networks[7]
    data = n.action.model_dump()
    data.update(length=1, bit_destination="Y255", source="D4094")
    n.action = ProcessFunction.model_validate(data)
    assert n.action.source_devices() == {"R2", "D4094", "D4095", "M1975"}
    assert n.action.destination_devices() == {"Y255"}
    assert decode_network(compile_network(n)).action == n.action


def test_unknown_and_truncated_forms_not_misdecoded():
    for raw in list(TEST22_PAYLOADS.values())[:8]:
        assert decode_network(bytes.fromhex(raw)[:-1]) is None
    for index, old, new in [(0, "f50c", "f40c"), (2, "f5f8", "f4f8")]:
        assert decode_network(bytes.fromhex(TEST22_PAYLOADS[index].replace(old, new))) is None
