"""test12 export oracle, binary32 constants, expanded banks and compare-output policy."""

import math
import struct
from pathlib import Path

import pytest

from winproladder_mcp.analysis import device_references
from winproladder_mcp.architecture import ArchitecturePolicy, enforce_architecture
from winproladder_mcp.floating import float_span
from winproladder_mcp.io_contract import IOContract
from winproladder_mcp.ir import (
    Coil,
    FloatCompare,
    FloatOperation,
    FloatZoneCompare,
    Ladder,
    Network,
    compile_network,
    decode_network,
    simulate,
    validation,
)
from winproladder_mcp.layout import lower_ladder, memory_used
from winproladder_mcp.ldr import parse
from winproladder_mcp.logic import bit_address, device_name
from winproladder_mcp.service import Service, default_header
from winproladder_mcp.timing import timed_simulate

ROOT = Path(__file__).resolve().parents[1]
PAYLOADS = [
    "4fe8f57f000540c0624e00005ffc3f70",
    "4fe8f57f000642cc666600001a966ffcc1006ffdc88b6ffec847",
    "4fe8f57f00073ffeb85200000a1e27fc6ffcc1016ffdc8136ffecbf7",
    "4fe8f47f0008000040f60b94",
]


def sample():
    return Ladder.model_validate(Service(ROOT).read("samples/test12.ldr")["ladder"])


def test_test12_screenshot_and_exact_regeneration(tmp_path):
    ladder = sample()
    assert ladder.profile == "FBs-40MA-test12"
    ns = ladder.networks
    assert ns[0].action == FloatOperation(
        operation="div", sa=6.0120001, sb="D4094", destination="R8000"
    )
    assert ns[1].action == FloatCompare(
        sa=102.2,
        sb="R2123",
        equal=[Coil(address=0)],
        greater=[Coil(device="M", address=123)],
        less=[Coil(device="M", address=55)],
    )
    assert ns[2].action == FloatZoneCompare(
        source="R3838",
        upper=1.99,
        lower="R15",
        within=[Coil(address=1)],
        above=[Coil(device="M", address=3)],
        below=[Coil(device="M", address=999)],
    )
    assert ns[3].action == FloatOperation(operation="sqrt", sa="D123", destination="R202")
    assert [compile_network(n).hex() for n in ns] == PAYLOADS
    assert [e["status"] for e in validation(ladder)["instruction_evidence"]] == [
        "observed_export"
    ] * 4
    (tmp_path / ".winproladder-policy.json").write_text('{"forbid_m_to_m":true}')
    result = Service(tmp_path).generate(
        "test12.ldr", ladder, io_contract=IOContract(inputs=[], outputs=["Y0", "Y1"])
    )
    assert Path(result["path"]).read_bytes() == (ROOT / "samples/test12.ldr").read_bytes()
    assert result["layout"]["helper_devices"] == [] and result["architecture"]["valid"]
    assert parse(Path(result["path"]).read_bytes()).header == default_header("FBs-40MA-test12")


def test_double_word_and_high_m_references():
    ladder = sample()
    refs = device_references(list(enumerate(ladder.networks)))["devices"]
    for d in ["D4094", "D4095"]:
        assert refs[d]["reads"] == [0]
    for d in ["R8000", "R8001"]:
        assert refs[d]["writes"] == [0]
    for d in ["R3838", "R3839", "R15", "R16"]:
        assert refs[d]["reads"] == [2]
    assert refs["M999"]["writes"] == [2]
    assert memory_used(ladder) == {3, 55, 123, 999}
    assert bit_address("M999") == 0xBF7 and device_name(0xBF7) == "M999"
    assert compile_network(Network(condition="M999", coils=[Coil(address=0)])).hex() == "4bf7c100"
    for name in ["M1912", "X256", "Y999"]:
        with pytest.raises(ValueError):
            bit_address(name)


@pytest.mark.parametrize("index", [1, 2])
def test_float_status_outputs_cannot_bypass_m_policy(index, tmp_path):
    ladder = sample()
    ladder.networks[index].action.enable = "M999"
    for variant in [ladder, lower_ladder(ladder)[0]]:
        with pytest.raises(ValueError, match="M-to-M"):
            enforce_architecture(variant, ArchitecturePolicy(forbid_m_to_m=True))
    (tmp_path / ".winproladder-policy.json").write_text('{"forbid_m_to_m":true}')
    with pytest.raises(ValueError, match="M-to-M"):
        Service(tmp_path).generate(
            "denied.ldr", ladder, io_contract=IOContract(inputs=[], outputs=["Y0", "Y1"])
        )
    with pytest.raises(ValueError, match="M-to-M"):
        enforce_architecture(
            Ladder(networks=[decode_network(compile_network(ladder.networks[index]))]),
            ArchitecturePolicy(forbid_m_to_m=True),
        )


@pytest.mark.parametrize(
    "sa,sb,flag",
    [("R0", "R2", "f47f"), (1.5, "R2", "f57f"), ("R0", 1.5, "f67f"), (1.5, 2.5, "f77f")],
)
def test_float_constant_flags_inferred_and_roundtrip(sa, sb, flag):
    n = Network(action=FloatOperation(operation="add", sa=sa, sb=sb, destination="R4"))
    raw = compile_network(n)
    assert raw[2:4].hex() == flag
    assert decode_network(raw) == n
    assert (
        validation(Ladder(networks=[n]))["instruction_evidence"][0]["status"] == "inferred_variant"
    )


@pytest.mark.parametrize(
    "value,expected",
    [
        (6.0120001, "40c0624e"),
        (102.2, "42cc6666"),
        (1.99, "3ffeb852"),
        (0.0, "00000000"),
        (-0.0, "80000000"),
    ],
)
def test_binary32_precision_and_signed_zero(value, expected):
    n = Network(action=FloatCompare(sa=value, sb="R0"))
    raw = compile_network(n)
    assert raw[6:10].hex() == expected
    decoded = decode_network(raw)
    assert compile_network(decoded) == raw
    assert struct.pack(">f", decoded.action.sa).hex() == expected
    if value == 0:
        assert math.copysign(1, decoded.action.sa) == math.copysign(1, value)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf"), 1e100, True])
def test_invalid_float_literals_rejected(value):
    with pytest.raises(ValueError):
        FloatCompare(sa=value, sb="R0")


@pytest.mark.parametrize("source", ["R3839", "R8071", "R3840", "R4999", "R8072", "D4095", "D4096"])
def test_float_bank_boundaries(source):
    with pytest.raises(ValueError):
        float_span(source, 2)


def test_new_float_banks_and_zero_division():
    assert float_span("R8070", 2) == {"R8070", "R8071"}
    assert float_span("D4094", 2) == {"D4094", "D4095"}
    assert float_span("R5000", 2) == {"R5000", "R5001"}
    for v in [0.0, -0.0, 1e-100]:
        with pytest.raises(ValueError, match="division by zero"):
            FloatOperation(operation="div", sa="R0", sb=v, destination="R2")
    with pytest.raises(ValueError):
        FloatOperation(operation="sqrt", sa=-1.0, destination="R0")
    with pytest.raises(ValueError):
        FloatOperation(operation="f_to_i", sa=1.5, destination="R0")


@pytest.mark.parametrize(
    "raw",
    [
        "4fe8f57f00067fc0000000000a00",  # NaN
        "4fe8f47f000600010a0000000a02",  # register prefix corruption
        "4fe8f57f00073ffeb85200000a1e27fc6fffc101",  # ERR flag not supported
        "4fe8f47f0009000040f60b94",  # unknown FSQR neighbor
        "4fe8f67f0008000040f60b94",  # illegal second constant flag on unary
    ],
)
def test_unknown_or_invalid_forms_remain_opaque(raw):
    assert decode_network(bytes.fromhex(raw)) is None


def test_native_functions_still_refuse_runtime_simulation():
    for n in sample().networks:
        with pytest.raises(ValueError, match="cannot execute"):
            simulate(Ladder(networks=[n]), [{}], {})
        with pytest.raises(ValueError, match="cannot execute"):
            timed_simulate(Ladder(networks=[n]), [{}], {}, 10)
