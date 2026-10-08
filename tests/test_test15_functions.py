from pathlib import Path

import pytest

from winproladder_mcp.analysis import device_references
from winproladder_mcp.architecture import ArchitecturePolicy, enforce_architecture
from winproladder_mcp.io_contract import IOContract
from winproladder_mcp.ir import (
    Coil,
    Ladder,
    Network,
    PeripheralIO,
    compile_network,
    decode_network,
    simulate,
    validation,
)
from winproladder_mcp.layout import lower_ladder, memory_used
from winproladder_mcp.service import Service
from winproladder_mcp.timing import timed_simulate

ROOT = Path(__file__).resolve().parents[1]
PAYLOADS = [
    "4fe8f4ea000011d00810",
    "4fe8f6ec000a01051360087421706ffcc81a",
    "4fe8f6ee00010103023e138c6ffcc81b",
    "4fe8f6fc0388017800002172",
    "4fe8f6fa000a011400025ffe402c6ffcc81c",
]


def sample():
    return Ladder.model_validate(Service(ROOT).read("samples/test15.ldr")["ladder"])


def contract():
    return IOContract(
        inputs=[f"X{i}" for i in range(18)],
        outputs=[f"Y{i}" for i in [*range(3, 9), 20, 21, *range(120, 128)]],
    )


def test_exact_sample_roundtrip(tmp_path):
    ladder = sample()
    assert [compile_network(n).hex() for n in ladder.networks] == PAYLOADS
    assert [n.action.type for n in ladder.networks] == ["tkey", "hkey", "dsw", "7sgdl", "muxi"]
    assert ladder.networks[2].action.destination == "R3999"
    assert ladder.networks[3].action.source == "V"
    assert all(e["status"] == "observed_export" for e in validation(ladder)["instruction_evidence"])
    (tmp_path / ".winproladder-policy.json").write_text('{"forbid_m_to_m":true}')
    result = Service(tmp_path).generate("test15.ldr", ladder, io_contract=contract())
    assert Path(result["path"]).read_bytes() == (ROOT / "samples/test15.ldr").read_bytes()
    assert result["architecture"]["valid"] and result["layout"]["helper_devices"] == []
    refs = device_references(list(enumerate(ladder.networks)))["devices"]
    assert refs["V"]["reads"] == [3] and refs["R3999"]["writes"] == [2]
    assert refs["R1223"] == {"reads": [2], "writes": [2]}
    assert refs["D4095"]["writes"] == [4] and "D4096" not in refs
    assert refs["Y127"]["writes"] == [3] and refs["X17"]["reads"] == [4]
    assert set(range(10)) | set(range(100, 116)) <= memory_used(ladder)


@pytest.mark.parametrize("index", range(5))
def test_implicit_kl_and_status_m_policy(index):
    ladder = sample()
    n = ladder.networks[index]
    if index == 3:
        n.action.done = [Coil(device="M", address=200)]
    n.action.enable = "M1911"
    for candidate in [
        n,
        lower_ladder(Ladder(networks=[n]))[0].networks[0],
        decode_network(compile_network(n)),
    ]:
        with pytest.raises(ValueError, match="M-to-M"):
            enforce_architecture(
                Ladder(networks=[candidate]), ArchitecturePolicy(forbid_m_to_m=True)
            )


@pytest.mark.parametrize("missing", ["X9", "X17", "Y8", "Y127", "Y21"])
def test_undeclared_span_rejected(tmp_path, missing):
    io = contract()
    (io.inputs if missing.startswith("X") else io.outputs).remove(missing)
    with pytest.raises(ValueError, match="Undeclared physical I/O"):
        Service(tmp_path).generate("denied.ldr", sample(), io_contract=io)


@pytest.mark.parametrize("rows,words", [(2, 1), (3, 2), (4, 2), (5, 3), (8, 4)])
def test_muxi_result_width(rows, words):
    action = PeripheralIO(
        type="muxi",
        input="X240",
        output="Y240",
        rows=rows,
        destination=f"D{4096 - words}",
        work="D22",
    )
    assert len(action.destination_devices()) == words
    assert len(action.input_devices()) == 8 and len(action.output_devices()) == rows
    n = Network(action=action)
    assert decode_network(compile_network(n)) == n
    if words > 1:
        with pytest.raises(ValueError):
            PeripheralIO.model_validate({**action.model_dump(), "destination": "D4095"})


@pytest.mark.parametrize(
    "index,changes",
    [
        (0, {"input": "X241"}),
        (0, {"key_start": "M1897"}),
        (1, {"work": "R3840"}),
        (1, {"rows": 2}),
        (1, {"done": [{"address": 0}]}),
        (2, {"work": "D4095"}),
        (2, {"input": "M0"}),
        (3, {"mode": 4}),
        (3, {"mode": True}),
        (3, {"work": "V"}),
        (4, {"rows": 1}),
        (4, {"rows": 9}),
        (4, {"rows": True}),
    ],
)
def test_invalid_operands(index, changes):
    with pytest.raises(ValueError):
        PeripheralIO.model_validate({**sample().networks[index].action.model_dump(), **changes})


def test_workspace_register_exclusivity():
    ladder = sample()
    ladder.networks[3].action.work = "R1223"
    assert any("exclusive WR R1223" in e for e in validation(ladder)["errors"])
    n = sample().networks[1].action
    with pytest.raises(ValueError, match="WR"):
        PeripheralIO.model_validate({**n.model_dump(), "work": "R1200"})


def test_second_status_and_unknown_forms():
    for index, field in [(1, "function_pressed"), (2, "error"), (0, "pressed")]:
        n = sample().networks[index]
        setattr(n.action, field, [Coil(address=50)])
        assert decode_network(compile_network(n)) == n
    for raw in [
        PAYLOADS[0] + "6ffec100",
        PAYLOADS[3] + "6ffdc100",
        PAYLOADS[4][:-4],
        PAYLOADS[0].replace("f4ea", "f4eb"),
    ]:
        assert decode_network(bytes.fromhex(raw)) is None


def test_simulation_explicitly_unsupported():
    for n in sample().networks:
        with pytest.raises(ValueError, match="cannot execute"):
            simulate(Ladder(networks=[n]), [{}], {})
        with pytest.raises(ValueError, match="cannot execute"):
            timed_simulate(Ladder(networks=[n]), [{}], {}, 10)
