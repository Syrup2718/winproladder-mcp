from pathlib import Path

import pytest

from winproladder_mcp.analysis import device_references
from winproladder_mcp.architecture import ArchitecturePolicy, enforce_architecture
from winproladder_mcp.io_contract import IOContract
from winproladder_mcp.ir import (
    PID,
    Coil,
    Divide48,
    IntegerFunction,
    Ladder,
    Network,
    compile_network,
    decode_network,
    simulate,
    validation,
)
from winproladder_mcp.layout import lower_ladder
from winproladder_mcp.service import Service
from winproladder_mcp.timing import timed_simulate

ROOT = Path(__file__).resolve().parents[1]
PAYLOADS = [
    "4fe8f47427fa0a0057f46ffcc819",
    "4fe8f5c0000c0ac80af6",
    "4fe8f4e244b0432040dc",
    "4fe8f49c1a680a02",
    "4fe8f49a0a18",
    "4fe8f49e0ba2",
    "4fe8f4b90a04",
    "4fe8f77500080bb80bbc",
]


def sample():
    return Ladder.model_validate(Service(ROOT).read("samples/test17.ldr")["ladder"])


def test_sample_roundtrip_and_evidence(tmp_path):
    ladder = sample()
    assert [compile_network(n).hex() for n in ladder.networks] == PAYLOADS
    assert len(validation(ladder)["instruction_evidence"]) == 8
    assert all(
        e["source"].startswith("test17.ldr") for e in validation(ladder)["instruction_evidence"]
    )
    (tmp_path / ".winproladder-policy.json").write_text('{"forbid_m_to_m":true}')
    result = Service(tmp_path).generate(
        "test17.ldr", ladder, io_contract=IOContract(inputs=[], outputs=[])
    )
    assert Path(result["path"]).read_bytes() == (ROOT / "samples/test17.ldr").read_bytes()
    assert result["architecture"]["valid"] and not result["layout"]["helper_devices"]


def test_runtime_mean_spans_and_ext_width():
    report = device_references(list(enumerate(sample().networks)))
    refs = report["devices"]
    assert refs["D655"]["reads"] == [2] and "D656" not in refs
    assert refs["D600"]["reads"] == [2]
    assert refs["R2"]["reads"] == [0, 6] and refs["R3"]["writes"] == [6]
    assert refs["R3839"]["reads"] == [0]
    assert refs["D3068"]["writes"] == [0]
    assert not report["complete"]
    assert report["reference_uncertainties"][0]["network"] == 7


@pytest.mark.parametrize(
    "source,valid", [("D3840", True), ("D3841", False), ("R3584", True), ("R3585", False)]
)
def test_mean_maximum_span(source, valid):
    args = dict(type="mean", source=source, count="D0", destination="R0")
    if not valid:
        with pytest.raises(ValueError, match="span"):
            IntegerFunction(**args)
    else:
        a = IntegerFunction(**args)
        assert decode_network(compile_network(Network(action=a))).action == a


@pytest.mark.parametrize("kind", ["ext", "crc16"])
def test_two_word_destination(kind):
    args = dict(type=kind, destination="D4095")
    if kind == "crc16":
        args.update(source="R0", count=8, mode=1)
    with pytest.raises(ValueError, match="span"):
        IntegerFunction(**args)


@pytest.mark.parametrize(
    "index,pin", [(0, "zero"), (0, "error"), (2, "error"), (3, "error"), (7, "zero"), (7, "error")]
)
def test_status_architecture_in_three_stages(index, pin):
    n = sample().networks[index]
    n.action.enable = "M100"
    setattr(n.action, pin, [Coil(device="M", address=101)])
    for candidate in [
        n,
        lower_ladder(Ladder(networks=[n]))[0].networks[0],
        decode_network(compile_network(n)),
    ]:
        with pytest.raises(ValueError, match="M-to-M"):
            enforce_architecture(
                Ladder(networks=[candidate]), ArchitecturePolicy(forbid_m_to_m=True)
            )


def test_dynamic_mean_conflicts_with_pid_work():
    ladder = Ladder(
        networks=[
            Network(
                action=IntegerFunction(type="mean", source="D400", count="R0", destination="R1")
            ),
            Network(
                action=PID(
                    interval=1, setting="R100", destination="R200", parameters="R300", work="D650"
                )
            ),
        ]
    )
    assert any("exclusive WR D650" in e for e in validation(ladder)["errors"])


def test_div48_single_pin_preserved_after_lowering():
    a = Divide48(encoding="single_input", enable="X0 AND TRUE", sa="R0", sb="R3", destination="D0")
    lowered, report = lower_ladder(Ladder(networks=[Network(action=a)]))
    assert not report["helper_devices"]
    decoded = decode_network(compile_network(lowered.networks[0])).action
    assert decoded.encoding == "single_input" and decoded.enable == "X0"
    with pytest.raises(ValueError, match="no U/S"):
        Divide48(encoding="single_input", unsigned_when="X1", sa="R0", sb="R3", destination="R6")


@pytest.mark.parametrize("index", range(8))
def test_runtime_not_claimed(index):
    ladder = sample()
    ladder.networks = [ladder.networks[index]]
    with pytest.raises(ValueError):
        simulate(ladder, [{}], {})
    with pytest.raises(ValueError):
        timed_simulate(ladder, [{}], {}, 10)


@pytest.mark.parametrize("index", range(2, 8))
def test_operand_and_enable_variants(index):
    n = sample().networks[index]
    n.action.enable = "X0 AND (X1 OR X2)"
    n.action.destination = "D1000"
    decoded = decode_network(compile_network(n))
    assert decoded is not None
    assert compile_network(decoded) == compile_network(n)
    assert (
        validation(Ladder(networks=[n]))["instruction_evidence"][0]["status"] == "inferred_variant"
    )


def test_unsupported_forms_are_rejected():
    for kwargs in [
        dict(type="mean", source="R0", count=2, destination="R300"),
        dict(type="crc16", source="R0", count=8, mode=0, destination="R300"),
        dict(type="neg", source="R0", destination="R1"),
        dict(type="ext", destination="R1", error=[Coil(address=0)]),
    ]:
        with pytest.raises(ValueError):
            IntegerFunction(**kwargs)


def test_crc_status_wrong_tail_opaque():
    assert decode_network(bytes.fromhex(PAYLOADS[-1] + "6ffec100")) is None
