import asyncio

import pytest

from winproladder_mcp.architecture import ArchitecturePolicy, enforce_architecture
from winproladder_mcp.ir import Coil, Ladder, Network, compile_network, decode_network
from winproladder_mcp.logic import bit_address, device_name
from winproladder_mcp.manual_reference import analyze_rtc_snapshot, manual_reference
from winproladder_mcp.registers import decode_register, encode_register, register_span
from winproladder_mcp.server import build_server


def snapshot():
    return dict(zip([f"R{i}" for i in range(4128, 4135)], [59, 30, 8, 7, 10, 26, 3], strict=True))


@pytest.mark.parametrize(
    "name,hex_word", [("R5000", "2800"), ("R8071", "3ffe"), ("D4000", "5f40"), ("D4095", "5ffe")]
)
def test_manual_bank_boundaries(name, hex_word):
    assert encode_register(name).hex() == hex_word
    assert decode_register(bytes.fromhex(hex_word)) == name
    assert register_span(name, 1, writable=True) == {name}


@pytest.mark.parametrize("name", ["R3839", "R8071", "D4095"])
def test_double_word_end_boundary(name):
    with pytest.raises(ValueError, match="boundary"):
        register_span(name, 2)


def test_ordinary_m_max_and_policy():
    assert bit_address("M1911") == 0xF87
    assert device_name(0xF87) == "M1911"
    net = Network(condition="M1911", coils=[Coil(device="M", address=1000)])
    decoded = decode_network(compile_network(net))
    for n in [net, decoded]:
        with pytest.raises(ValueError, match="M-to-M"):
            enforce_architecture(Ladder(networks=[n]), ArchitecturePolicy(forbid_m_to_m=True))
    for address in ["M1912", "M1952", "M2001", "M2008"]:
        with pytest.raises(ValueError):
            bit_address(address)
    with pytest.raises(ValueError):
        encode_register("R4128")


def test_rtc_packed_bytes_not_hhmm():
    values = snapshot()
    values["R4135"] = 8 * 256 + 30
    result = analyze_rtc_snapshot(values)
    assert result["packed_consistent"] and result["minute_of_day"] == 510
    assert result["expected_R4135"] == 2078
    values["R4135"] = 830
    assert not analyze_rtc_snapshot(values)["packed_consistent"]


@pytest.mark.parametrize(
    "register,value",
    [
        ("R4128", 60),
        ("R4129", -1),
        ("R4130", 24),
        ("R4131", 0),
        ("R4132", 13),
        ("R4133", 100),
        ("R4134", 7),
        ("R4128", True),
    ],
)
def test_rtc_ranges(register, value):
    values = snapshot()
    values[register] = value
    with pytest.raises(ValueError):
        analyze_rtc_snapshot(values)


def test_rtc_calendar_and_unknown_century():
    values = snapshot()
    values.update(R4132=2, R4131=30)
    with pytest.raises(ValueError, match="month/day"):
        analyze_rtc_snapshot(values)
    values["R4131"] = 29
    assert "century" in analyze_rtc_snapshot(values)["calendar_validation"]
    values["R0"] = 1
    with pytest.raises(ValueError):
        analyze_rtc_snapshot(values)


def test_rtc_tools_and_manual_editions(tmp_path):
    async def run():
        server = build_server(tmp_path)
        ref = await server.call_tool("get_manual_reference", {})
        result = await server.call_tool("inspect_rtc_snapshot", {"registers": snapshot()})
        assert "R4135" in str(ref) and "2078" in str(result)

    asyncio.run(run())
    assert manual_reference()["limits"]["D_manual_editions"] == {
        "basic": [0, 3071],
        "advanced": [0, 4095],
    }
