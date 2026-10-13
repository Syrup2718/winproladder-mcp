from pathlib import Path

import pytest

from winproladder_mcp.analysis import device_references
from winproladder_mcp.architecture import ArchitecturePolicy, architecture_report
from winproladder_mcp.instruction_catalog import TEST21_PAYLOADS
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
from winproladder_mcp.timing import timed_simulate

ROOT = Path(__file__).resolve().parents[1]
POLICY = ArchitecturePolicy(forbid_m_to_m=True, allow_function_m_to_m=True)


def sample():
    return Ladder.model_validate(Service(ROOT).read("samples/test21.ldr")["ladder"])


def test_original_full_generation_and_evidence(tmp_path):
    (tmp_path / ".winproladder-policy.json").write_text(POLICY.model_dump_json())
    ladder = sample()
    assert [compile_network(n).hex() for n in ladder.networks] == list(TEST21_PAYLOADS.values())
    report = validation(ladder)
    assert report["valid"]
    assert [e["source"] for e in report["instruction_evidence"]] == [
        f"test21.ldr N{i:03}" for i in range(5)
    ]
    result = Service(tmp_path).generate(
        "table.ldr", ladder, io_contract=IOContract(inputs=["X0", "X5"], outputs=[])
    )
    assert Path(result["path"]).read_bytes() == (ROOT / "samples/test21.ldr").read_bytes()
    assert not result["layout"]["helper_devices"]


def test_clear_anchor_corrects_old_inversion():
    ladder = sample()
    assert ladder.networks[0].action.clear == "FALSE"
    assert ladder.networks[1].action.clear == "FALSE"
    assert ladder.networks[2].action.clear == "X5"
    for value, token in [("X5", "6005"), ("NOT X5", "7005"), ("TRUE", "6fe8"), ("FALSE", "7fe8")]:
        n = ladder.networks[2].model_copy(deep=True)
        n.action.clear = value
        raw = compile_network(n)
        assert raw.hex().startswith("48146fe8" + token)
        assert decode_network(raw).action.clear == value


def test_entire_table_spans_and_swap_writes():
    refs = device_references(list(enumerate(sample().networks)))
    assert refs["complete"]
    d = refs["devices"]
    assert d["R1"]["reads"] == [0] and d["R10"]["writes"] == [0]
    assert "R11" not in d
    assert d["R9"]["reads"] == [0] and d["R9"]["writes"] == [0]
    assert d["R29"]["reads"] == [1] and d["R39"]["writes"] == [1]
    assert d["R127"]["reads"] == [3] and d["R148"]["writes"] == [3]
    assert d["R109"]["reads"] == [2, 4] and d["R109"]["writes"] == [4]
    assert d["R209"]["reads"] == [4] and d["R209"]["writes"] == [4]


@pytest.mark.parametrize("index", range(5))
def test_lowering_policy_and_no_execution_claim(index):
    from winproladder_mcp.process_functions import CONTROLS, STATUS

    n = sample().networks[index]
    for control in CONTROLS[n.action.type]:
        setattr(n.action, control, "M20 AND TRUE")
    if STATUS[n.action.type]:
        n.action.done = [Coil(device="M", address=21)]
    ladder = Ladder(networks=[n])
    lowered, report = lower_ladder(ladder)
    assert not report["helper_devices"]
    decoded = Ladder(networks=[decode_network(compile_network(lowered.networks[0]))])
    for candidate in [ladder, lowered, decoded]:
        assert architecture_report(candidate, POLICY)["valid"]
        if STATUS[n.action.type]:
            assert not architecture_report(candidate, ArchitecturePolicy(forbid_m_to_m=True))[
                "valid"
            ]
    for control in CONTROLS[n.action.type]:
        assert getattr(decoded.networks[0].action, control) == "M20"
    with pytest.raises(ValueError):
        simulate(decoded, [{}], {})
    with pytest.raises(ValueError):
        timed_simulate(decoded, [{}], {}, 10)


@pytest.mark.parametrize(
    "index,field,value",
    [
        (0, "length", 1),
        (0, "length", 2049),
        (0, "length", "R2"),
        (0, "source", "R3839"),
        (0, "destination", "R3840"),
        (1, "pointer", "R3840"),
        (1, "source", "D4090"),
        (1, "destination", "R8070"),
        (3, "length", 257),
        (4, "length", 257),
        (4, "source", "R3840"),
        (3, "pointer", "R10"),
        (3, "clear", "X0"),
        (4, "pulse", True),
        (0, "source", "V"),
        (0, "mode", 1),
        (0, "length", True),
    ],
)
def test_reject_bad_spans_modes_and_unused_fields(index, field, value):
    data = sample().networks[index].action.model_dump()
    data[field] = value
    with pytest.raises(ValueError):
        ProcessFunction.model_validate(data)


@pytest.mark.parametrize("index,maximum", [(0, 2048), (1, 2048), (3, 256), (4, 256)])
def test_manual_maxima_and_inferred_addresses(index, maximum):
    data = sample().networks[index].action.model_dump()
    data.update(source="D0", destination="R5000", length=maximum)
    action = ProcessFunction.model_validate(data)
    n = sample().networks[index]
    n.action = action
    raw = compile_network(n)
    assert (maximum - 1).to_bytes(2, "big") in raw
    assert decode_network(raw).action == action
    assert len(action.source_devices()) >= maximum


def test_unknown_forms_remain_opaque_and_status_contract(tmp_path):
    for raw in TEST21_PAYLOADS.values():
        assert decode_network(bytes.fromhex(raw)[:-1]) is None
    n = sample().networks[3]
    data = n.action.model_dump()
    data["done"] = [{"device": "M", "address": 20}]
    with pytest.raises(ValueError):
        ProcessFunction.model_validate(data)
    with pytest.raises(ValueError):
        Service(tmp_path).generate(
            "bad.ldr", sample(), io_contract=IOContract(inputs=["X0"], outputs=[])
        )
    assert not (tmp_path / "artifacts/bad.ldr").exists()
