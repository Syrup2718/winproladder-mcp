"""test29 independent ASC and single-digit LBL export oracles."""

from pathlib import Path

import pytest

from winproladder_mcp.conversion_functions import encode_ascii
from winproladder_mcp.instruction_catalog import TEST29_PAYLOADS
from winproladder_mcp.io_contract import IOContract
from winproladder_mcp.ir import (
    Ladder,
    Network,
    SampleFlow,
    compile_network,
    decode_network,
    validation,
)
from winproladder_mcp.service import Service

ROOT = Path(__file__).resolve().parents[1]


def sample():
    return Ladder.model_validate(Service(ROOT).read("samples/test29.ldr")["ladder"])


def test_original_roundtrip_and_evidence(tmp_path):
    p = sample()
    assert p.profile == "FBs-32MN-test29"
    assert [n.action.text for n in p.networks[:2]] == ["1234567890GH", "IJKLMNOUTWXZ"]
    assert [n.action.target for n in p.networks[2:]] == list("023456")
    assert [compile_network(n).hex() for n in p.networks] == list(TEST29_PAYLOADS.values())
    assert [x["source"] for x in validation(p)["instruction_evidence"]] == [
        f"test29.ldr N{i:03}" for i in range(8)
    ]
    (tmp_path / ".winproladder-policy.json").write_text(
        '{"forbid_m_to_m":true,"allow_function_m_to_m":true}'
    )
    r = Service(tmp_path).generate("test29.ldr", p, io_contract=IOContract(inputs=[], outputs=[]))
    assert Path(r["path"]).read_bytes() == (ROOT / "samples/test29.ldr").read_bytes()
    assert not r["layout"]["helper_devices"]


@pytest.mark.parametrize("target", list("0123456789"))
def test_digit_label(target):
    n = Network(action=SampleFlow(type="lbl", target=target))
    assert compile_network(n) == bytes([0xEF, ord(target)]) + bytes(6)
    assert decode_network(compile_network(n)) == n
    assert validation(Ladder(networks=[n]))["valid"]
    assert not validation(Ladder(networks=[n, n]))["valid"]


@pytest.mark.parametrize("target", ["", "1234567", "A_", "-1", "\uff11", "1\n", 1])
def test_unencoded_label_forms(target):
    with pytest.raises(ValueError):
        SampleFlow(type="lbl", target=target)


@pytest.mark.parametrize("target", list("02345679"))
def test_labels_do_not_unlock_jumps(target):
    with pytest.raises(ValueError):
        SampleFlow(type="jmp", target=target)


def test_ascii_independent_digit_and_letter_oracles():
    assert encode_ascii("1234567890GH").hex() == "003f183219341a361b381c302348"
    assert encode_ascii("IJKLMNOUTWXZ").hex() == "000f244a254c264e27552a572c5a"
    p = sample()
    assert p.networks[0].action.destination_devices() == {f"R{i}" for i in range(5555, 5561)}
    assert p.networks[1].action.destination_devices() == {f"D{i}" for i in range(111, 117)}
    for raw in TEST29_PAYLOADS.values():
        assert decode_network(bytes.fromhex(raw)[:-1]) is None
