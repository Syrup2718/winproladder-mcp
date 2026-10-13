from pathlib import Path

import pytest

from winproladder_mcp.analysis import device_references
from winproladder_mcp.architecture import ArchitecturePolicy, architecture_report
from winproladder_mcp.instruction_catalog import TEST20_PAYLOADS
from winproladder_mcp.io_contract import IOContract
from winproladder_mcp.ir import (
    Coil,
    Ladder,
    Network,
    ProcessFunction,
    compile_network,
    decode_network,
    simulate,
    validation,
)
from winproladder_mcp.layout import lower_ladder
from winproladder_mcp.ldr import parse
from winproladder_mcp.process_functions import CONTROLS, STATUS
from winproladder_mcp.service import Service
from winproladder_mcp.timing import timed_simulate

ROOT = Path(__file__).resolve().parents[1]
POLICY = ArchitecturePolicy(forbid_m_to_m=True, allow_function_m_to_m=True)


def sample():
    return Ladder.model_validate(Service(ROOT).read("samples/test20.ldr")["ladder"])


def test_original_payloads_and_conflict_diagnosis():
    ladder = sample()
    assert [compile_network(n).hex() for n in ladder.networks] == list(TEST20_PAYLOADS.values())
    assert architecture_report(ladder, POLICY)["valid"]
    report = validation(ladder)
    assert report["errors"] == [
        f"N002: exclusive WR R{i} also used by networks [3]" for i in [15, 16, 17]
    ]
    assert [e["source"] for e in report["instruction_evidence"]] == [
        f"test20.ldr N{i:03}" for i in range(4)
    ]


def test_generate_subsets_preserves_user_io_and_full_conflict_rejected(tmp_path):
    (tmp_path / ".winproladder-policy.json").write_text(POLICY.model_dump_json())
    service = Service(tmp_path)
    contract = IOContract(inputs=["X1", "X2"], outputs=["Y0", "Y12"])
    with pytest.raises(ValueError, match="exclusive WR R15"):
        service.generate("full.ldr", sample(), io_contract=contract)
    assert not (tmp_path / "artifacts/full.ldr").exists()
    for indices in [[0, 1, 2], [3]]:
        ladder = sample()
        ladder.networks = [ladder.networks[i] for i in indices]
        result = service.generate(f"subset{indices[0]}.ldr", ladder, io_contract=contract)
        doc = parse(Path(result["path"]).read_bytes())
        assert [r.payload.hex() for r in reversed(doc.records)] == [
            TEST20_PAYLOADS[i] for i in indices
        ]
        assert doc.editable and not result["layout"]["helper_devices"]


@pytest.mark.parametrize("index", range(4))
def test_lowering_all_inputs_and_no_runtime_claim(index):
    n = sample().networks[index]
    for name in CONTROLS[n.action.type]:
        setattr(n.action, name, "X5 AND TRUE")
    lowered, report = lower_ladder(Ladder(networks=[n]))
    decoded = decode_network(compile_network(lowered.networks[0]))
    assert not report["helper_devices"]
    for name in CONTROLS[n.action.type]:
        assert getattr(decoded.action, name) == "X5"
    with pytest.raises(ValueError):
        simulate(lowered, [{}], {})
    with pytest.raises(ValueError):
        timed_simulate(lowered, [{}], {}, 10)


@pytest.mark.parametrize("index", range(4))
def test_all_input_status_pairs_follow_both_policy_modes(index):
    original = sample().networks[index]
    for name in CONTROLS[original.action.type]:
        for pin in STATUS[original.action.type]:
            n = original.model_copy(deep=True)
            setattr(n.action, name, "M20")
            setattr(n.action, pin, [Coil(device="M", address=21)])
            for candidate in [
                n,
                lower_ladder(Ladder(networks=[n]))[0].networks[0],
                decode_network(compile_network(n)),
            ]:
                ladder = Ladder(networks=[candidate])
                assert architecture_report(ladder, POLICY)["valid"]
                assert not architecture_report(ladder, ArchitecturePolicy(forbid_m_to_m=True))[
                    "valid"
                ]


def test_full_spans_and_uncertainty():
    r = device_references(list(enumerate(sample().networks)))
    d = r["devices"]
    assert d["R5008"]["writes"] == [0] and "R5009" not in d
    assert d["D113"]["writes"] == [1] and d["T20"]["writes"] == [1]
    assert d["M1974"]["reads"] == [1]
    assert d["R18"]["writes"] == [2] and d["R17"]["writes"] == [2, 3]
    assert d["R3904"]["writes"] == [2] and d["R50"]["writes"] == [3]
    assert not r["complete"] and r["reference_uncertainties"][0]["network"] == 0


@pytest.mark.parametrize(
    "index,field,value",
    [
        (0, "mode", 0),
        (0, "pulse", False),
        (0, "work", "R8065"),
        (1, "timer", "T256"),
        (1, "timer", "R20"),
        (1, "destination", "D4095"),
        (1, "lower", "D113"),
        (2, "work", "D3997"),
        (2, "maximum", "D4000"),
        (2, "work", "R3965"),
        (2, "target", "R3840"),
        (2, "target", "R16"),
        (3, "length", 1),
        (3, "length", 2049),
        (3, "destination", "R3835"),
        (3, "pointer", "R3840"),
        (3, "pulse", True),
        (2, "pause", "X0"),
    ],
)
def test_operand_and_mode_boundaries(index, field, value):
    data = sample().networks[index].action.model_dump()
    data[field] = value
    with pytest.raises(ValueError):
        ProcessFunction.model_validate(data)


def test_inferred_or_bank_and_max_table_length():
    n = sample().networks[2]
    n.action.destination = "R3967"
    assert decode_network(compile_network(n)).action.destination == "R3967"
    n = sample().networks[3]
    n.action.length = 2048
    n.action.destination = "D0"
    raw = compile_network(n)
    assert bytes.fromhex("07ff") in raw
    assert decode_network(raw).action.length == 2048
    assert len(n.action.destination_devices()) == 2049


def test_unknown_form_words_stay_opaque():
    for index, old, new in [
        (0, "f103", "f102"),
        (1, "f8160000", "f8160001"),
        (2, "f47e0000", "f47e0001"),
    ]:
        assert decode_network(bytes.fromhex(TEST20_PAYLOADS[index].replace(old, new))) is None


def test_ramp_timer_and_work_cannot_be_reused():
    n = sample().networks[1]
    other = Network.model_validate({"block": {"type": "timer", "address": 20, "preset": 10}})
    assert any(
        "exclusive RAMP Tn T20" in e for e in validation(Ladder(networks=[n, other]))["errors"]
    )
    other = sample().networks[3]
    other.action.source = "D113"
    assert any("exclusive WR D113" in e for e in validation(Ladder(networks=[n, other]))["errors"])


def test_table_clear_polarity_is_separate_from_increment():
    n = sample().networks[3]
    assert n.action.clear == "FALSE" and n.action.increment == "TRUE"
    assert compile_network(n).hex().startswith("4fe86fe87fe8")
    n.action.clear = "TRUE"
    raw = compile_network(n)
    assert raw.hex().startswith("4fe86fe86fe8")
    assert decode_network(raw).action.clear == "TRUE"
