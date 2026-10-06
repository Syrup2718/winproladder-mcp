"""Independent test10 byte oracle, operand typing, I/O aliases and native status outputs."""

from pathlib import Path

import pytest

from winproladder_mcp.analysis import device_references
from winproladder_mcp.architecture import ArchitecturePolicy, enforce_architecture
from winproladder_mcp.io_contract import IOContract
from winproladder_mcp.ir import (
    Coil,
    ExclusiveLogic,
    Ladder,
    Network,
    Timer,
    WordConversion,
    ZoneCompare,
    compile_network,
    decode_network,
    simulate,
    validation,
)
from winproladder_mcp.layout import lower_ladder, memory_used
from winproladder_mcp.ldr import parse
from winproladder_mcp.registers import decode_word, encode_word
from winproladder_mcp.service import Service
from winproladder_mcp.timing import timed_simulate

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "samples/test10.ldr"
PAYLOADS = [
    "4fe8f4ca13a442580adc",
    "4fe8f4cc0b9a03920bd2",
    "4fe8f7da0064fff601006ffcc1006ffdc1016ffec102",
    "4fe8f5a6014d0bbc",
    "4fe8f4a408000820",
]


def sample():
    return Ladder.model_validate(Service(ROOT).read("samples/test10.ldr")["ladder"])


def test_test10_screenshot_and_exact_bytes(tmp_path):
    ladder = sample()
    assert ladder.networks[0].action == ExclusiveLogic(
        operation="xor", sa="R1234", sb="D300", destination="R110"
    )
    assert ladder.networks[1].action == ExclusiveLogic(
        operation="xnr", sa="R205", sb="T1", destination="R233"
    )
    assert ladder.networks[2].action == ZoneCompare(
        source="R3840",
        upper=100,
        lower=-10,
        within=[Coil(address=0)],
        above=[Coil(address=1)],
        below=[Coil(address=2)],
    )
    assert ladder.networks[3].action == WordConversion(
        operation="to_bcd", source=333, destination="R222"
    )
    assert ladder.networks[4].action == WordConversion(
        operation="to_bin", source="WX0", destination="WY0"
    )
    assert [compile_network(n).hex() for n in ladder.networks] == PAYLOADS
    assert [r.payload.hex() for r in reversed(parse(SAMPLE.read_bytes()).records)] == PAYLOADS
    assert [v["status"] for v in validation(ladder)["instruction_evidence"]] == [
        "observed_export"
    ] * 5
    (tmp_path / ".winproladder-policy.json").write_text('{"forbid_m_to_m":true}')
    result = Service(tmp_path).generate(
        "roundtrip.ldr",
        ladder,
        io_contract=IOContract(
            inputs=[f"X{i}" for i in range(16)], outputs=[f"Y{i}" for i in range(16)]
        ),
    )
    assert Path(result["path"]).read_bytes() == SAMPLE.read_bytes()
    assert result["layout"]["helper_devices"] == []
    assert result["architecture"]["valid"]


def test_grouped_io_references_and_overlap_are_explicit(tmp_path):
    ladder = sample()
    report = device_references(list(enumerate(ladder.networks)))
    refs = report["devices"]
    assert refs["T1"] == {"reads": [1], "writes": []}
    assert refs["WX0"]["reads"] == [4] and refs["WY0"]["writes"] == [4]
    for i in range(16):
        assert refs[f"X{i}"]["reads"] == [4]
        assert refs[f"Y{i}"]["writes"] == ([2, 4] if i < 3 else [4])
    assert report["multiple_writers"] == {f"Y{i}": [2, 4] for i in range(3)}
    with pytest.raises(ValueError, match="Undeclared physical I/O"):
        Service(tmp_path).generate(
            "denied.ldr", ladder, io_contract=IOContract(inputs=[], outputs=["Y0", "Y1", "Y2"])
        )
    assert not (tmp_path / "artifacts/denied.ldr").exists()


@pytest.mark.parametrize(
    "upper,lower,expected", [(32767, -32768, "7fff8000"), (0, 0, "00000000"), (-1, -10, "fffffff6")]
)
def test_zone_signed_order_and_boundaries(upper, lower, expected):
    network = Network(action=ZoneCompare(source="D100", upper=upper, lower=lower))
    raw = compile_network(network)
    assert raw[4:8].hex() == expected
    assert decode_network(raw) == network


def test_zone_status_policy_and_reservation(tmp_path):
    n = Network(
        action=ZoneCompare(source="R100", lower=-1, upper=1, within=[Coil(device="M", address=100)])
    )
    good = Ladder(networks=[n])
    assert memory_used(good) == {100}
    assert enforce_architecture(good, ArchitecturePolicy(forbid_m_to_m=True))["valid"]
    assert decode_network(compile_network(n)) == n
    n.action.enable = "M0"
    with pytest.raises(ValueError, match="M-to-M"):
        enforce_architecture(good, ArchitecturePolicy(forbid_m_to_m=True))
    (tmp_path / ".winproladder-policy.json").write_text('{"forbid_m_to_m":true}')
    with pytest.raises(ValueError, match="M-to-M"):
        Service(tmp_path).generate(
            "denied.ldr", good, io_contract=IOContract(inputs=[], outputs=[])
        )


@pytest.mark.parametrize(
    "name,raw", [("T0", "0390"), ("T1", "0392"), ("T255", "058e"), ("WX0", "0800"), ("WY0", "0820")]
)
def test_word_banks_are_distinct_from_contacts(name, raw):
    assert encode_word(name).hex() == raw
    assert decode_word(bytes.fromhex(raw)) == name


@pytest.mark.parametrize("name", ["WX1", "WY16", "WM0", "T256", "T01", "C1", "X0"])
def test_unconfirmed_word_banks_rejected(name):
    with pytest.raises(ValueError):
        encode_word(name)


@pytest.mark.parametrize("name", ["WX0", "T1", "R3840"])
def test_protected_word_destinations_rejected(name):
    with pytest.raises(ValueError):
        WordConversion(operation="to_bin", source="R100", destination=name)


@pytest.mark.parametrize(
    "data",
    [
        {"operation": "to_bcd", "source": "R100"},
        {"operation": "to_bcd", "source": -1},
        {"operation": "to_bcd", "source": 10000},
        {"operation": "to_bcd", "source": True},
        {"operation": "to_bin", "source": 333},
    ],
)
def test_unsupported_conversion_forms_rejected(data):
    with pytest.raises(ValueError):
        WordConversion(destination="R222", **data)


def test_zone_invalid_forms_rejected():
    for values in [
        {"upper": 1, "lower": 2},
        {"upper": 32768, "lower": 0},
        {"upper": 0, "lower": -32769},
        {"upper": True, "lower": 0},
        {"upper": 1, "lower": 0, "within": [Coil(address=0, mode="set")]},
    ]:
        with pytest.raises(ValueError):
            ZoneCompare(source="R100", **values)


@pytest.mark.parametrize(
    "raw",
    [
        "4fe8f4cb13a442580adc",  # unsupported modifier
        "4fe8f4cc0b9a03920bd26ffcc100",  # unconfirmed D=0 wiring
        "4fe8f7da0064fff601006fffc100",  # unconfirmed ERR wiring
        "4fe8f7da0064fff601006ffc",  # empty status output
        "4fe8f7da0064fff601006ffcc1006ffcc101",  # duplicate output selector
        "4fe8f4a408000800",  # input destination
        "4fe8f4a408010820",  # unsupported grouped word
        "4fe8f4a6014d0bbc",  # unconfirmed register BCD opcode
    ],
)
def test_unknown_forms_remain_opaque(raw):
    assert decode_network(bytes.fromhex(raw)) is None


@pytest.mark.parametrize("preset", [0xF4CA, 0xF4CC, 0xF7DA, 0xF5A6, 0xF4A4])
def test_opcode_looking_timer_literal_not_misparsed(preset):
    n = Network(block=Timer(address=1, preset=preset, enable="TRUE"))
    assert decode_network(compile_network(n)) == n


def test_new_functions_lower_and_refuse_unsupported_runtime():
    original = sample()
    lowered, layout = lower_ladder(original)
    assert layout["helper_devices"] == []
    assert [compile_network(n).hex() for n in lowered.networks] == PAYLOADS
    for n in original.networks:
        with pytest.raises(ValueError, match="cannot execute"):
            simulate(Ladder(networks=[n]), [{}], {})
        with pytest.raises(ValueError, match="cannot execute"):
            timed_simulate(Ladder(networks=[n]), [{}], {}, 10)


def test_previous_xor_hypothesis_is_now_supported_as_inferred_variant():
    raw = bytes.fromhex("4fe8f4ca010840f0412c")
    n = decode_network(raw)
    assert n.action == ExclusiveLogic(operation="xor", sa="R3844", sb="D120", destination="D150")
    assert compile_network(n) == raw
    assert validation(Ladder(networks=[n]))["instruction_evidence"][0]["status"] == (
        "inferred_variant"
    )
