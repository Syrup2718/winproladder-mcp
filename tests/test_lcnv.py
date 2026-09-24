"""FUN33 evidence, constrained inference, profile preservation and real MCP delivery."""

import asyncio
import base64
import json
import sys
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from winproladder_mcp.analysis import device_references
from winproladder_mcp.ir import (
    Ladder,
    LinearConversion,
    Network,
    compile_network,
    decode_network,
    validation,
)
from winproladder_mcp.layout import lower_ladder
from winproladder_mcp.ldr import Document, parse
from winproladder_mcp.registers import decode_register, encode_register
from winproladder_mcp.service import Service
from winproladder_mcp.timing import timed_simulate

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "samples/test6.ldr"


def conversion(**overrides):
    return LinearConversion.model_validate(
        {"source": "R3840", "table": "R2001", "destination": "D1000", **overrides}
    )


def test_sample_matches_screenshot_and_rebuilds_identically(tmp_path):
    result = Service(ROOT).read("samples/test6.ldr")
    ladder = Ladder.model_validate(result["ladder"])
    assert ladder.profile == "FBs-24MA" and len(ladder.networks) == 13
    for i in range(5):
        block = ladder.networks[2 * i].action
        assert isinstance(block, LinearConversion)
        assert (block.mode, block.source, block.table, block.destination, block.length) == (
            0,
            f"R{3840 + i}",
            f"R{2001 + 5 * i}",
            f"D{1000 + i}",
            1,
        )
    report = validation(ladder)
    assert [e["status"] for e in report["instruction_evidence"]] == ["observed_export"] * 5
    assert report["instruction_evidence"][4]["operand_labels"] == "inferred"
    generated = Service(tmp_path).generate("rebuilt.ldr", ladder)
    assert Path(generated["path"]).read_bytes() == SAMPLE.read_bytes()
    assert generated["profile"] == "FBs-24MA"


@pytest.mark.parametrize(
    "name,hex_value",
    [
        ("R0", "0a00"),
        ("R1", "0a02"),
        ("R2001", "19a2"),
        ("R2006", "19ac"),
        ("R3840", "0100"),
        ("R3843", "0106"),
        ("D1000", "47d0"),
        ("D1003", "47d6"),
    ],
)
def test_word_operands_against_independent_sample_values(name, hex_value):
    assert encode_register(name) == bytes.fromhex(hex_value)
    assert decode_register(bytes.fromhex(hex_value)) == name


@pytest.mark.parametrize(
    "mode,length,table_words", [(0, 64, 4), (1, 64, 256), (2, 64, 3), (3, 64, 192)]
)
def test_inferred_modes_lengths_and_full_resource_spans(mode, length, table_words):
    action = conversion(mode=mode, length=length, source="R100", table="R1000", destination="D0")
    assert action.table_words == table_words
    network = Network(action=action)
    raw = compile_network(network)
    assert int.from_bytes(raw[4:6], "big") == mode
    assert raw[-2:] == b"\x00\x40"
    assert compile_network(decode_network(raw)) == raw
    report = validation(Ladder(networks=[network]))
    assert report["instruction_evidence"][0]["status"] == "inferred_variant"
    references = device_references([(0, network)])
    assert references["devices"][f"R{1000 + table_words - 1}"]["reads"] == [0]
    assert f"R{1000 + table_words}" not in references["devices"]
    assert references["devices"]["D63"]["writes"] == [0]
    assert "D64" not in references["devices"]


@pytest.mark.parametrize(
    "options",
    [
        {"mode": 4},
        {"mode": True},
        {"length": 0},
        {"length": 65},
        {"length": "R0"},
        {"source": "R3903", "length": 2},
        {"source": "R3839", "length": 2},
        {"table": "R3837"},
        {"destination": "R3840"},
        {"table": "R3840"},
        {"destination": "D3999", "length": 2},
        {"source": "R5000"},
        {"source": "D4000"},
        {"source": "R00"},
        {"source": "@R0"},
        {"pulse": True},
    ],
)
def test_unsupported_operands_and_cross_bank_spans_rejected(options):
    with pytest.raises(ValueError):
        conversion(**options)


@pytest.mark.parametrize("offset,value", [(3, 0x7D), (5, 4), (7, 1), (13, 0), (13, 65)])
def test_unknown_or_invalid_payloads_stay_opaque(offset, value):
    raw = bytearray.fromhex("4fe8f57c0000010019a247d00001")
    raw[offset] = value
    assert decode_network(bytes(raw)) is None


def test_lcnv_helpers_keep_profile_and_no_invented_physical_io():
    ladder = Ladder(
        profile="FBs-24MA",
        networks=[Network(action=conversion(enable="(X1 OR X2) AND (X3 OR X5)"))],
    )
    lowered, layout = lower_ladder(ladder)
    assert lowered.profile == "FBs-24MA" and layout["helper_devices"]
    devices = device_references(list(enumerate(lowered.networks)))["devices"]
    assert {d for d in devices if d.startswith(("X", "Y"))} == {"X1", "X2", "X3", "X5"}
    with pytest.raises(ValueError, match="cannot execute"):
        timed_simulate(lowered, [{}], {}, 10)


def test_edit_preserves_new_header_and_unknown_headers_remain_opaque(tmp_path):
    (tmp_path / "sample.ldr").write_bytes(SAMPLE.read_bytes())
    service = Service(tmp_path)
    edited = service.edit(
        "sample.ldr",
        "edited.ldr",
        "replace",
        0,
        Network(action=conversion(destination="D1010")),
        True,
    )
    before = parse(SAMPLE.read_bytes())
    after = parse(Path(edited["path"]).read_bytes())
    assert after.header == before.header
    assert after.records[:-1] == before.records[:-1]
    header = bytearray(before.header)
    header[176] ^= 1
    (tmp_path / "unknown.ldr").write_bytes(
        Document(bytes(header), before.records, before.tail).encode()
    )
    assert service.read("unknown.ldr")["ladder"] is None
    with pytest.raises(ValueError, match="header"):
        service.edit("unknown.ldr", "denied.ldr", "delete", 1, None, True)


def test_real_mcp_reads_generates_and_downloads_test6(tmp_path):
    (tmp_path / "test6.ldr").write_bytes(SAMPLE.read_bytes())

    async def run():
        params = StdioServerParameters(
            command=sys.executable, args=["-m", "winproladder_mcp.server", "--root", str(tmp_path)]
        )
        async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
            await session.initialize()
            decoded = await session.call_tool("read_ldr", {"path": "test6.ldr"})
            assert not decoded.isError
            ladder = json.loads(decoded.content[0].text)["ladder"]
            generated = await session.call_tool(
                "generate_ldr",
                {
                    "output_name": "roundtrip.ldr",
                    "ladder": ladder,
                    "io_contract": {"inputs": [], "outputs": []},
                },
            )
            assert not generated.isError, generated.content
            result = generated.structuredContent
            resource = await session.read_resource(result["artifact"]["uri"])
            assert base64.b64decode(resource.contents[0].blob) == SAMPLE.read_bytes()

    asyncio.run(run())
