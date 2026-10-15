from pathlib import Path

import pytest

from winproladder_mcp.analysis import device_references
from winproladder_mcp.architecture import ArchitecturePolicy, enforce_architecture
from winproladder_mcp.instruction_catalog import TEST19_PAYLOADS
from winproladder_mcp.io_contract import IOContract
from winproladder_mcp.ir import (
    AccumulativeTimer,
    Coil,
    Ladder,
    Network,
    SampleCall,
    TemperatureControl,
    compile_network,
    decode_network,
    simulate,
    validation,
)
from winproladder_mcp.layout import lower_ladder
from winproladder_mcp.ldr import parse
from winproladder_mcp.service import Service
from winproladder_mcp.timing import timed_simulate

ROOT = Path(__file__).resolve().parents[1]
IO = IOContract(inputs=["X5"], outputs=["Y0", "Y2", "Y3", "Y4", "Y24"])


def sample():
    return Ladder.model_validate(Service(ROOT).read("samples/test19.ldr")["ladder"])


def test_forensic_roundtrip_and_evidence():
    ladder = sample()
    assert [compile_network(n).hex() for n in ladder.networks] == list(TEST19_PAYLOADS.values())
    report = validation(ladder)
    evidence = {e["network_index"]: e for e in report["instruction_evidence"]}
    for i in [0, 2, 4, 5, 6]:
        assert evidence[i]["source"] == f"test19.ldr N{i:03}"
        assert evidence[i]["status"] == "observed_export"
        assert not evidence[i]["gui_import_verified"]
    assert any("CALL" in e for e in report["errors"])


def test_subset_generate_and_full_rejection(tmp_path):
    (tmp_path / ".winproladder-policy.json").write_text('{"forbid_m_to_m":true}')
    service = Service(tmp_path)
    with pytest.raises(ValueError, match="M-to-M"):
        service.generate("full.ldr", sample(), io_contract=IO)
    assert not (tmp_path / "artifacts/full.ldr").exists()
    ladder = sample()
    ladder.networks = [ladder.networks[i] for i in [4, 6]]
    result = service.generate("subset.ldr", ladder, io_contract=IO)
    doc = parse(Path(result["path"]).read_bytes())
    assert [r.payload.hex() for r in reversed(doc.records)] == [TEST19_PAYLOADS[i] for i in [4, 6]]
    assert doc.header == parse((ROOT / "samples/test19.ldr").read_bytes()).header
    assert doc.editable and result["architecture"]["valid"]
    assert not result["layout"]["helper_devices"]


@pytest.mark.parametrize(
    "index,field,pin",
    [
        (4, "timing", "done"),
        (4, "timing", "not_done"),
        (4, "enable", "done"),
        (4, "enable", "not_done"),
        (6, "enable", "error"),
        (6, "enable", "alarm"),
        (6, "heat_cool", "error"),
        (6, "heat_cool", "alarm"),
    ],
)
def test_both_inputs_and_statuses_enforce_policy(index, field, pin):
    n = sample().networks[index]
    setattr(n.action, field, "M10")
    setattr(n.action, pin, [Coil(device="M", address=11)])
    lowered = lower_ladder(Ladder(networks=[n]))[0].networks[0]
    for candidate in [n, lowered, decode_network(compile_network(lowered))]:
        with pytest.raises(ValueError, match="M-to-M"):
            enforce_architecture(
                Ladder(networks=[candidate]), ArchitecturePolicy(forbid_m_to_m=True)
            )


@pytest.mark.parametrize("index", [2, 4, 5, 6])
def test_boolean_lowering_preserves_both_pins(index):
    n = sample().networks[index]
    n.action.enable = "X5 AND TRUE"
    if isinstance(n.action, AccumulativeTimer):
        n.action.timing = "X6 OR FALSE"
    else:
        n.action.heat_cool = "FALSE"
    lowered, report = lower_ladder(Ladder(networks=[n]))
    a = decode_network(compile_network(lowered.networks[0])).action
    assert a.enable == "X5" and not report["helper_devices"]
    assert a.timing == "X6" if isinstance(a, AccumulativeTimer) else a.heat_cool == "FALSE"


def test_units_cv_word_and_spans():
    ladder = sample()
    assert [ladder.networks[i].action.unit_ms for i in [2, 4, 5]] == [10, 100, 1000]
    assert ladder.networks[2].action.cv == "T255"
    refs = device_references(list(enumerate(ladder.networks)))
    assert refs["devices"]["T255"] == {"reads": [2], "writes": [2]}
    for d in ["D223", "D226", "R103", "R106", "R109", "R123"]:
        assert refs["devices"][d]["reads"] == [6]
    for d in ["Y2", "Y3", "Y4", "R112", "R123"]:
        assert refs["devices"][d]["writes"] == [6]
    assert "R124" not in refs["devices"] and "Y5" not in refs["devices"]
    assert not refs["complete"] and refs["reference_uncertainties"][0]["network"] == 6


@pytest.mark.parametrize(
    "field,value",
    [
        ("start", 32),
        ("start", 30),
        ("zones", 0),
        ("zones", 33),
        ("output", "Y254"),
        ("output", "X0"),
        ("work", "D4088"),
        ("setpoint", "D4094"),
        ("destination", "R3838"),
        ("integral", "R3840"),
        ("work", "R102"),
        ("mode", 1),
    ],
)
def test_tpctl_invalid_or_unencoded_parameters(field, value):
    data = sample().networks[6].action.model_dump()
    data[field] = value
    with pytest.raises(ValueError):
        TemperatureControl.model_validate(data)


def test_manual_upper_limits_are_not_sample_limits():
    data = sample().networks[6].action.model_dump()
    data.update(start=31, zones=1, output="Y255", work="D4087", destination="R8071")
    action = TemperatureControl.model_validate(data)
    assert len(action.work_devices()) == 9
    assert decode_network(compile_network(Network(action=action))).action == action


@pytest.mark.parametrize(
    "field,value",
    [
        ("cv", "T256"),
        ("cv", "R3904"),
        ("pv", 100),
        ("unit_ms", 1),
        ("cv", "WY0"),
    ],
)
def test_timer_codec_boundary(field, value):
    data = sample().networks[4].action.model_dump()
    data[field] = value
    with pytest.raises(ValueError):
        AccumulativeTimer.model_validate(data)


def test_timer_cv_ir_bank_is_instruction_specific():
    from winproladder_mcp.registers import encode_word

    data = sample().networks[4].action.model_dump()
    data["cv"] = "R3903"
    action = AccumulativeTimer.model_validate(data)
    assert decode_network(compile_network(Network(action=action))).action == action
    with pytest.raises(ValueError):
        encode_word("R3903", writable=True)


def test_exclusive_work_across_networks_and_implicit_io(tmp_path):
    ladder = sample()
    ladder.networks = [ladder.networks[4], ladder.networks[6]]
    ladder.networks[0].action.pv = "R123"
    assert any("exclusive WR R123" in e for e in validation(ladder)["errors"])
    ladder.networks[0].action.pv = "R253"
    with pytest.raises(ValueError, match=r"Undeclared.*Y3.*Y4"):
        Service(tmp_path).generate(
            "missing.ldr",
            ladder,
            io_contract=IOContract(inputs=["X5"], outputs=["Y0", "Y2", "Y24"]),
        )


def test_call_no_generation_or_unknown_target_guess(tmp_path):
    with pytest.raises(ValueError, match=r"CALL.*unresolved"):
        Service(tmp_path).generate(
            "call.ldr",
            Ladder(networks=[Network(action=SampleCall(type="call"))]),
            io_contract=IOContract(inputs=[], outputs=[]),
        )
    assert decode_network(bytes.fromhex(TEST19_PAYLOADS[0].replace("672e", "672f"))) is None
    assert not (tmp_path / "artifacts/call.ldr").exists()


@pytest.mark.parametrize("index", [0, 2, 4, 5, 6])
def test_no_runtime_simulation_claim(index):
    ladder = sample()
    ladder.networks = [ladder.networks[index]]
    with pytest.raises(ValueError):
        simulate(ladder, [{}], {})
    if index in {4, 5}:
        trace = timed_simulate(ladder, [{}], {}, 10)
        assert trace[0][ladder.networks[0].action.cv] == 0
    else:
        with pytest.raises(ValueError):
            timed_simulate(ladder, [{}], {}, 10)
