"""All PDW fixtures are synthetic. Never read/copy private project samples in CI."""

import asyncio
import base64
import itertools
import sys
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import BlobResourceContents, EmbeddedResource

from winproladder_mcp.acceptance import AcceptanceCase
from winproladder_mcp.io_contract import IOContract
from winproladder_mcp.pdw import (
    MAGIC,
    PERIOD,
    SIZE,
    START,
    TAIL_START,
    PdwRung,
    parse,
    replace_rungs,
)
from winproladder_mcp.pdw_project import unit, word_sum
from winproladder_mcp.service import Service


def synthetic_template(count=1):
    """Construct only documented framing/required fields with an artificial XOR mask."""
    raw = bytearray(TAIL_START)
    raw[: len(MAGIC)] = MAGIC
    raw[160:168] = b"FBs-60MC"
    raw[START - 4 : START] = bytes.fromhex("0a1800a0")
    raw[0xA122:0xA126] = bytes.fromhex("0b180061")
    plain = bytearray(b"\xff" * SIZE)
    plain[:8] = b"FBS40003"
    plain[0xC8:0xCA] = b"\x28\xff" if count == 1 else b"\x30\xff"
    plain[0xCA:0xCC] = (1 if count == 1 else 0x102).to_bytes(2, "big")
    plain[0x100:0x106] = bytes.fromhex("40004000004f")
    words = count * 2
    plain[0x106:0x10A] = words.to_bytes(2, "little") + bytes((255 - words, 0x4E))
    plain[0x10A:0x110] = b"\x00\x02" + (0x202 + words * 2).to_bytes(2, "little") * 2
    plain[0x11E:0x120] = b"\xfe\xff"
    plain[0x112:0x116] = bytes.fromhex("ffa700a8")
    plain[0x200 : 0x200 + count * 4] = bytes.fromhex("4000c100") * count
    # Make the artificial header consistent with the newly validated full checksum,
    # while retaining the legacy sampled checksum field used by the old API.
    correction = (
        int.from_bytes(plain[0xC8:0xCA], "little") - (word_sum(plain[0x100:0x200]) - 24)
    ) & 65535
    plain[0x120:0x122] = ((65535 + correction) & 65535).to_bytes(2, "little")
    mask = bytes((i * 37 + i // 256) % 256 for i in range(PERIOD))
    raw[START : START + SIZE] = bytes(x ^ mask[i % PERIOD] for i, x in enumerate(plain))
    secondary = bytearray(b"\xff" * 0x6100)
    secondary[0x5FFE] = 0
    raw[0xA126 : 0xA126 + 0x6100] = bytes(x ^ mask[i % PERIOD] for i, x in enumerate(secondary))
    raw += unit(0x200, "MAIN0001").encode()
    raw += unit(0x202 + count * 4, "SUB00001").encode()
    for tag, size in [(0x1050, 32528), (0x1040, 0), (0x1042, 188)]:
        raw += tag.to_bytes(2, "little") + size.to_bytes(2, "little") + b"\0" * (size + 2)
    return bytes(raw) + bytes.fromhex("ffff00000000")


@pytest.mark.parametrize("count", [1, 2])
def test_all_sampled_address_polarity_combinations(count):
    template = synthetic_template(count)
    choices = [
        PdwRung(input=x, output=y, normally_closed=nc)
        for x, y, nc in itertools.product(["X0", "X1"], ["Y0", "Y1", "Y2"], [False, True])
    ]
    for combo in itertools.product(choices, repeat=count):
        result = replace_rungs(template, list(combo))
        assert list(parse(result).rungs) == list(combo)
        assert len(result) == len(template)
        assert result[:START] == template[:START]
        assert result[START + SIZE :] == template[START + SIZE :]
        assert replace_rungs(result, list(parse(template).rungs)) == template


@pytest.mark.parametrize(
    "offset",
    [
        160,
        START - 4,
        START,
        START + 0xCA,
        START + 0x106,
        START + 0x10C,
        START + 0x300,
        0xA126 + 0x10,
        TAIL_START,
    ],
)
def test_corrupt_or_unsupported_templates_rejected(offset):
    raw = bytearray(synthetic_template())
    raw[offset] ^= 1
    with pytest.raises(ValueError):
        parse(bytes(raw))


def test_reject_annotations_topology_truncation_and_schema():
    template = synthetic_template()
    with pytest.raises(ValueError, match="rung count"):
        replace_rungs(template, [PdwRung(input="X0", output="Y0")] * 2)
    for raw in [template[:20], template[:-1], template + b"extra"]:
        with pytest.raises(ValueError):
            parse(raw)
    raw = bytearray(template)
    raw[START + 0x11E] ^= 1
    with pytest.raises(ValueError, match="annotations"):
        parse(bytes(raw))
    for args in [
        {"input": "M0", "output": "Y0"},
        {"input": "X2", "output": "Y0"},
        {"input": "X0", "output": "Y0", "normally_closed": 1},
        {"input": "X0", "output": "Y0", "comment": "ignored?"},
    ]:
        with pytest.raises(ValueError):
            PdwRung.model_validate(args)


def test_service_io_acceptance_no_overwrite_and_scope(tmp_path):
    (tmp_path / "template.pdw").write_bytes(synthetic_template())
    service = Service(tmp_path)
    rungs = [PdwRung(input="X0", output="Y1", normally_closed=True)]
    contract = IOContract(inputs=["X0"], outputs=["Y1"])
    acceptance = [
        AcceptanceCase.model_validate(
            {
                "name": "NC truth table",
                "scans": [
                    {"inputs": {"X0": False}, "expected": {"Y1": True}},
                    {"inputs": {"X0": True}, "expected": {"Y1": False}},
                ],
            }
        )
    ]
    result = service.generate_pdw("test.pdw", "template.pdw", rungs, contract, acceptance)
    assert result["compiled_acceptance"]["passed"]
    assert result["verification"]["gui"].startswith("not verified")
    assert service.inspect_pdw("artifacts/test.pdw")["rungs"] == [r.model_dump() for r in rungs]
    with pytest.raises(FileExistsError):
        service.generate_pdw("test.pdw", "template.pdw", rungs, contract)
    with pytest.raises(ValueError, match="Undeclared"):
        service.generate_pdw("bad.pdw", "template.pdw", rungs, IOContract(inputs=[], outputs=[]))
    for name in ["../escape.pdw", "wrong.ldr"]:
        with pytest.raises(ValueError):
            service.generate_pdw(name, "template.pdw", rungs, contract)
    with pytest.raises(ValueError, match="inside workspace"):
        service.load_pdw(str(Path(__file__).resolve()))
    acceptance[0].scans[0].expected["Y1"] = False
    with pytest.raises(ValueError, match="acceptance failed"):
        service.generate_pdw("failed.pdw", "template.pdw", rungs, contract, acceptance)
    assert not (tmp_path / "artifacts/failed.pdw").exists()


def test_stdio_pdw_generation_and_binary_delivery(tmp_path):
    (tmp_path / "template.pdw").write_bytes(synthetic_template())

    async def run():
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "winproladder_mcp.server", "--root", str(tmp_path), "--compact-responses"],
        )
        async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
            await session.initialize()
            caps = await session.call_tool("get_capabilities", {})
            assert caps.structuredContent["pdw"]["template_required"]
            args = {
                "output_name": "demo.pdw",
                "template_path": "template.pdw",
                "rungs": [{"input": "X0", "output": "Y1"}],
                "io_contract": {"inputs": ["X0"], "outputs": ["Y1"]},
            }
            generated = await session.call_tool("generate_pdw", args)
            assert not generated.isError, generated.content
            metadata = generated.structuredContent
            expected = (tmp_path / "artifacts/demo.pdw").read_bytes()
            fetched = await session.call_tool("get_pdw_artifact", {"output_name": "demo.pdw"})
            assert not fetched.isError
            embedded = next(c for c in fetched.content if isinstance(c, EmbeddedResource))
            assert isinstance(embedded.resource, BlobResourceContents)
            assert base64.b64decode(embedded.resource.blob) == expected
            resource = (await session.read_resource(metadata["artifact"]["uri"])).contents[0]
            assert base64.b64decode(resource.blob) == expected
            inspect = await session.call_tool("inspect_pdw", {"path": "artifacts/demo.pdw"})
            assert not inspect.isError
            assert inspect.structuredContent["rungs"][0]["output"] == "Y1"
            assert (await session.call_tool("generate_pdw", args)).isError
            assert (
                await session.call_tool("get_pdw_artifact", {"output_name": "../template.pdw"})
            ).isError

    asyncio.run(run())
