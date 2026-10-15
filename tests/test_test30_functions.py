"""Independent GUI-export oracles and memory/label boundary checks."""

from pathlib import Path

import pytest

from winproladder_mcp.instruction_catalog import TEST30_PAYLOADS
from winproladder_mcp.io_contract import IOContract
from winproladder_mcp.ir import (
    Ladder,
    Network,
    ProcessFunction,
    SampleFlow,
    compile_network,
    decode_network,
    validation,
)
from winproladder_mcp.service import Service

ROOT = Path(__file__).resolve().parents[1]


def sample():
    return Ladder.model_validate_json((ROOT / "examples/test30_functions.json").read_text())


def test_export_roundtrip_and_evidence(tmp_path):
    p = sample()
    assert p.profile == "FBs-32MC-test30"
    assert [n.action.target for n in p.networks[4:]] == ["A", "B1", "JY1", "1WX"]
    assert [compile_network(n).hex() for n in p.networks] == list(TEST30_PAYLOADS.values())
    for n in p.networks:
        assert decode_network(compile_network(n)) == n
        assert decode_network(compile_network(n)[:-1]) is None
    assert [e["source"] for e in validation(p)["instruction_evidence"]] == [
        f"test30.ldr N{i:03}" for i in range(8)
    ]
    (tmp_path / ".winproladder-policy.json").write_text(
        '{"forbid_m_to_m":true,"allow_function_m_to_m":true}'
    )
    result = Service(tmp_path).generate(
        "test30.ldr", p, io_contract=IOContract(inputs=["X1"], outputs=[])
    )
    assert Path(result["path"]).read_bytes() == (ROOT / "samples/test30.ldr").read_bytes()
    assert not result["layout"]["helper_devices"]


@pytest.mark.parametrize("target", ["A", "B1", "JY1", "1WX", "AB12", "ABCDEF", "abc123", "9Z9Z9Z"])
def test_alphanumeric_labels(target):
    n = Network(action=SampleFlow(type="lbl", target=target))
    assert decode_network(compile_network(n)) == n
    assert validation(Ladder(networks=[n]))["valid"]
    assert not validation(Ladder(networks=[n, n]))["valid"]
    with pytest.raises(ValueError):
        SampleFlow(type="jmp", target=target)


@pytest.mark.parametrize("target", ["ABCDEFG", "中文", "A B", "A_1", "A\n", "", "\uff21", "A\x00B"])
def test_invalid_labels(target):
    with pytest.raises(ValueError):
        SampleFlow(type="lbl", target=target)


@pytest.mark.parametrize(
    "index,updates",
    [
        (1, {"length": 0}),
        (1, {"length": 512}),
        (1, {"file_base": "F8192"}),
        (1, {"pulse": True}),
        (1, {"source": "WX0"}),
        (2, {"length": 129}),
        (2, {"bank": 0}),
        (2, {"offset": 1}),
        (2, {"pulse": None}),
        (2, {"work": "R19"}),
        (2, {"work": "D1"}),
        (2, {"work": "D4095"}),
        (3, {"destination": "D3990"}),
        (3, {"pulse": True}),
        (0, {"group": 1}),
        (0, {"destination": "D4000"}),
        (0, {"length": 2}),
        (0, {"read_mode": "X1"}),
    ],
)
def test_rejected_forms(index, updates):
    fields = sample().networks[index].action.model_dump()
    fields.update(updates)
    with pytest.raises(ValueError):
        ProcessFunction.model_validate(fields)


def test_memory_footprints_and_mutable_operands():
    p = sample()
    wr = p.networks[2].action
    assert wr.source_devices() == {f"R{i}" for i in range(20)} | {"D1", "R2900", "R2901"}
    assert wr.destination_devices() == {"D1", "R2900", "R2901"}
    rd = p.networks[3].action
    assert rd.destination_devices() == {f"R{i}" for i in range(2, 22)} | {"D10"}
    for index in (1, 2, 3):
        fields = p.networks[index].action.model_dump()
        fields["length"] = 1
        n = Network(action=ProcessFunction.model_validate(fields))
        assert decode_network(compile_network(n)) == n
    fields = p.networks[1].action.model_dump()
    fields.update(read_mode="X2", source="D100", file_base="F8191", length=1)
    n = Network(action=ProcessFunction.model_validate(fields))
    assert decode_network(compile_network(n)) == n
    assert "D100" in n.action.destination_devices()


@pytest.mark.parametrize("target", ["HSC0I", "HSTAI", "INT0", "1MSI", "100MS"])
def test_reserved_interrupt_labels(target):
    n = Network(action=SampleFlow(type="lbl", target=target))
    assert not validation(Ladder(networks=[n]))["valid"]


def test_work_area_conflict_is_rejected():
    p = sample()
    other = Network(action=ProcessFunction(type="system_status", group=0, destination="R200"))
    # STAT's unknown hardware-dependent extent is only a possible overlap.
    assert validation(Ladder(networks=[p.networks[2], other]))["valid"]
    other = Network(
        action=ProcessFunction(
            type="memory_pack_read", bank=1, offset=0, destination="R2901", pointer="D100", length=1
        )
    )
    assert not validation(Ladder(networks=[p.networks[2], other]))["valid"]
