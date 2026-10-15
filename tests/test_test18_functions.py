from pathlib import Path

import pytest

from winproladder_mcp.analysis import device_references
from winproladder_mcp.architecture import ArchitecturePolicy, enforce_architecture
from winproladder_mcp.io_contract import IOContract
from winproladder_mcp.ir import (
    PID,
    AnalogConversion,
    BitAccess,
    Coil,
    Ladder,
    Network,
    SampleFlow,
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
    "4fe86811f55a000601000de8",
    "ef31000000000000",
    "4fe86812f55e011e0004286428740b8e402e",
    "4fe8f78ca7fe188000000000",
    "4fe8f4ba0a1400026ffcc100",
    "4fe86814f544000f0a18",
]


def sample():
    return Ladder.model_validate(Service(ROOT).read("samples/test18.ldr")["ladder"])


def test_exact_roundtrip(tmp_path):
    ladder = sample()
    assert [compile_network(n).hex() for n in ladder.networks] == PAYLOADS
    assert len(validation(ladder)["instruction_evidence"]) == 6
    assert all(e["status"] == "observed_export" for e in validation(ladder)["instruction_evidence"])
    (tmp_path / ".winproladder-policy.json").write_text('{"forbid_m_to_m":true}')
    r = Service(tmp_path).generate(
        "out.ldr", ladder, io_contract=IOContract(inputs=[], outputs=["Y0"])
    )
    assert Path(r["path"]).read_bytes() == (ROOT / "samples/test18.ldr").read_bytes()
    assert not r["layout"]["helper_devices"] and r["architecture"]["valid"]


def test_all_potential_spans():
    refs = device_references(list(enumerate(sample().networks)))["devices"]
    assert refs["R3845"]["reads"] == [0] and refs["R505"]["writes"] == [0]
    assert refs["R3858"]["reads"] == [2] and refs["D26"]["writes"] == [2]
    assert refs["R5312"]["reads"] == [2] and "R5313" not in refs
    assert refs["R199"]["reads"] == [2] and refs["M2"]["reads"] == [2]
    assert refs["M1919"]["reads"] == [4]
    assert refs["R12"] == {"reads": [5], "writes": [5]}


@pytest.mark.parametrize(
    "index,field,pin",
    [
        (2, "enable", "overflow"),
        (2, "selector", "overflow"),
        (4, "enable", "output"),
        (4, "enable", "error"),
        (5, "enable", "error"),
        (5, "input_bit", "error"),
    ],
)
def test_all_control_inputs_and_statuses_policy(index, field, pin):
    n = sample().networks[index]
    setattr(n.action, field, "M10")
    setattr(n.action, pin, [Coil(device="M", address=11)])
    for candidate in [
        n,
        lower_ladder(Ladder(networks=[n]))[0].networks[0],
        decode_network(compile_network(n)),
    ]:
        with pytest.raises(ValueError, match="M-to-M"):
            enforce_architecture(
                Ladder(networks=[candidate]), ArchitecturePolicy(forbid_m_to_m=True)
            )


@pytest.mark.parametrize("index", [0, 2, 4, 5])
def test_variants_and_lowering(index):
    n = sample().networks[index]
    n.action.enable = "X0 AND TRUE"
    if isinstance(n.action, AnalogConversion):
        n.action.selector = "X1 AND TRUE"
        n.action.destination = "D100"
    elif n.action.type == "bitwr":
        n.action.input_bit = "X1 AND TRUE"
    lowered, report = lower_ladder(Ladder(networks=[n]))
    assert not report["helper_devices"]
    decoded = decode_network(compile_network(lowered.networks[0]))
    assert decoded.action.enable == "X0"
    assert compile_network(decoded) == compile_network(lowered.networks[0])
    assert validation(lowered)["instruction_evidence"][0]["status"] == "inferred_variant"


@pytest.mark.parametrize("index", [0, 2, 5])
def test_false_secondary_needs_no_helper(index):
    n = sample().networks[index]
    setattr(n.action, "input_bit" if index == 5 else "selector", "FALSE")
    lowered, report = lower_ladder(Ladder(networks=[n]))
    assert not report["helper_devices"]
    assert decode_network(compile_network(lowered.networks[0])) is not None


@pytest.mark.parametrize("bit", [-1, 16, 31])
@pytest.mark.parametrize("kind", ["bitrd", "bitwr"])
def test_16bit_index_limits(bit, kind):
    with pytest.raises(ValueError):
        BitAccess(type=kind, word="R0", bit=bit, input_bit="TRUE" if kind == "bitwr" else None)


def test_span_limits_and_manual_bank():
    with pytest.raises(ValueError, match="span"):
        AnalogConversion(type="adcnv", polarity=0, source="R3900", count=6, destination="R0")
    args = dict(
        type="mlc",
        source="R0",
        count=1,
        destination="D3999",
        x_table="D3745",
        y_table="R100",
        table_length="R1",
    )
    AnalogConversion(**args)
    args["x_table"] = "D3746"
    with pytest.raises(ValueError, match="D3999"):
        AnalogConversion(**args)
    with pytest.raises(ValueError):
        BitAccess(type="bitwr", word="R3840", bit=0, input_bit="TRUE")


def test_dynamic_table_intersects_exclusive_work():
    n = sample().networks[2]
    pid = PID(interval=10, setting="R0", destination="R10", parameters="R20", work="R5310")
    assert any(
        "exclusive WR R5310" in e
        for e in validation(Ladder(networks=[n, Network(action=pid)]))["errors"]
    )


@pytest.mark.parametrize(
    "change", ["move", "delete_label", "duplicate", "change_operand", "profile"]
)
def test_unresolved_jump_cannot_relocate(tmp_path, change):
    ladder = sample()
    if change == "move":
        ladder.networks[0], ladder.networks[2] = ladder.networks[2], ladder.networks[0]
    elif change == "delete_label":
        ladder.networks.pop(1)
    elif change == "duplicate":
        ladder.networks.append(Network(action=SampleFlow(type="lbl")))
    elif change == "profile":
        ladder.profile = "FBn-26MC-test17"
    else:
        ladder.networks[4].action.word = "R11"
    assert not validation(ladder)["valid"]
    with pytest.raises(ValueError):
        Service(tmp_path).generate(
            "denied.ldr", ladder, io_contract=IOContract(inputs=[], outputs=["Y0"])
        )
    assert not (tmp_path / "artifacts/denied.ldr").exists()


def test_edit_jump_program_is_guarded(tmp_path):
    (tmp_path / "sample.ldr").write_bytes((ROOT / "samples/test18.ldr").read_bytes())
    with pytest.raises(ValueError, match="JMP"):
        Service(tmp_path).edit("sample.ldr", "denied.ldr", "delete", 0, None, True)
    from winproladder_mcp.service import default_header

    raw = (ROOT / "samples/test18.ldr").read_bytes()
    (tmp_path / "other.ldr").write_bytes(default_header("FBn-26MC-test17") + raw[256:])
    with pytest.raises(ValueError, match="JMP"):
        Service(tmp_path).edit(
            "other.ldr", "denied_profile.ldr", "replace", 0, sample().networks[0], True
        )


@pytest.mark.parametrize("index", range(6))
def test_no_runtime_simulation(index):
    ladder = sample()
    ladder.networks = [ladder.networks[index]]
    with pytest.raises(ValueError):
        simulate(ladder, [{}], {})
    with pytest.raises(ValueError):
        timed_simulate(ladder, [{}], {}, 10)


def test_missing_output_io(tmp_path):
    with pytest.raises(ValueError, match="Undeclared"):
        Service(tmp_path).generate(
            "denied.ldr", sample(), io_contract=IOContract(inputs=[], outputs=[])
        )


def test_unknown_jump_or_label_stays_opaque():
    assert decode_network(bytes.fromhex(PAYLOADS[3].replace("a7fe", "a7ff"))) is None
    assert decode_network(bytes.fromhex("ef32010000000000")) is None
