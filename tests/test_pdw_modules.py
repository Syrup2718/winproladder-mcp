"""Synthetic module records only: no local sample paths, initialization blobs or private data."""

import asyncio
import sys

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from test_pdw import synthetic_template

from winproladder_mcp.io_contract import IOContract
from winproladder_mcp.ir import Coil, Ladder, Network
from winproladder_mcp.ldr import FOOTER
from winproladder_mcp.pdw_modules import parse_modules, select_modules
from winproladder_mcp.pdw_project import (
    MODEL_PROFILES,
    TAIL_START,
    PdwSection,
    Record,
    build,
    parse,
)
from winproladder_mcp.service import Service


def fake_module(name, seed=0):
    return name.encode("ascii").ljust(16, b"\0") + bytes((i + seed) % 256 for i in range(60))


def module_template(model="FBs-40MC", payload=None):
    project = parse(synthetic_template())
    prefix = bytearray(project.raw[:TAIL_START])
    prefix[160:176] = model.encode("ascii").ljust(16, b"\0")
    modules = fake_module("FBs-TESTA") + fake_module("FBs-TESTB", 9) if payload is None else payload
    records = [
        Record(r.tag, modules, r.checksum) if r.tag == 0x1040 else r for r in project.records
    ]
    return bytes(prefix) + b"".join(r.encode() for r in records) + FOOTER


@pytest.mark.parametrize("model", list(MODEL_PROFILES))
def test_model_and_module_preservation(model):
    raw = module_template(model)
    original = parse(raw)
    assert original.model == model
    assert [m["name"] for m in original.describe()["modules"]] == ["FBs-TESTA", "FBs-TESTB"]
    output, _ = build(
        raw, [bytes.fromhex("4000c100")], [PdwSection(network_index=0, name="AREA")], [""], []
    )
    assert output[:256] == raw[:256]
    assert parse(output).module_payload == original.module_payload


def test_select_order_duplicates_and_exact_parameters():
    a, b = fake_module("FBs-TESTA"), fake_module("FBs-TESTB", 9)
    selected = select_modules([a, b], ["FBs-TESTB", "FBs-TESTA", "FBs-TESTB"])
    assert selected == b + a + b
    raw, _ = build(
        module_template(),
        [bytes.fromhex("4000c100")],
        [PdwSection(network_index=0, name="AREA")],
        [""],
        [],
        selected,
    )
    assert parse(raw).module_payload == selected
    assert len(parse(raw).describe()["modules"]) == 3
    removed, _ = build(
        raw, [bytes.fromhex("4000c100")], [PdwSection(network_index=0, name="AREA")], [""], [], b""
    )
    assert parse(removed).describe()["modules"] == []


def test_unknown_conflicting_and_malformed_records():
    with pytest.raises(ValueError, match="no supplied"):
        select_modules([fake_module("FBs-TESTA")], ["FBs-UNSEEN"])
    with pytest.raises(ValueError, match="conflicting"):
        select_modules([fake_module("FBs-TESTA"), fake_module("FBs-TESTA", 1)], ["FBs-TESTA"])
    assert select_modules([fake_module("FBs-TESTA")] * 2, ["FBs-TESTA"]) == fake_module("FBs-TESTA")
    for payload in [b"bad", b"?" * 76, b"FBs-X\0\xff" + b"\0" * 69, b"x" * 16 + b"\0" * 60]:
        with pytest.raises(ValueError):
            parse_modules(payload)
    with pytest.raises(ValueError, match="implementation limit"):
        select_modules([], ["FBs-TESTA"] * 257)
    raw = module_template()
    project = parse(raw)
    wrong = [Record(r.tag, r.payload, b"\x01\0") if r.tag == 0x1040 else r for r in project.records]
    with pytest.raises(ValueError, match="trailer"):
        parse(raw[:TAIL_START] + b"".join(r.encode() for r in wrong) + FOOTER)


def test_service_catalogs_profiles_io_and_preservation(tmp_path):
    original = module_template()
    (tmp_path / "main.pdw").write_bytes(original)
    (tmp_path / "catalog.pdw").write_bytes(module_template("FBs-20MC", fake_module("FBs-TESTC", 7)))
    service = Service(tmp_path)
    ladder = Ladder(
        profile="FBs-40MC-test27", networks=[Network(condition="X0", coils=[Coil(address=0)])]
    )
    contract = IOContract(inputs=["X0"], outputs=["Y0"])
    preserved = service.generate_project_pdw("preserved.pdw", "main.pdw", ladder, contract)
    assert [m["name"] for m in preserved["project"]["modules"]] == ["FBs-TESTA", "FBs-TESTB"]
    selected = service.generate_project_pdw(
        "selected.pdw",
        "main.pdw",
        ladder,
        contract,
        module_order=["FBs-TESTC", "FBs-TESTA", "FBs-TESTC"],
        module_template_paths=["catalog.pdw"],
    )
    assert [m["name"] for m in selected["project"]["modules"]] == [
        "FBs-TESTC",
        "FBs-TESTA",
        "FBs-TESTC",
    ]
    assert selected["io_contract"]["used"] == ["X0", "Y0"]
    assert selected["project"]["model"] == "FBs-40MC"
    with pytest.raises(ValueError, match="explicit"):
        service.generate_project_pdw(
            "bad.pdw", "main.pdw", ladder, contract, module_template_paths=["catalog.pdw"]
        )
    wrong = ladder.model_copy(update={"profile": "FBs-20MC"})
    with pytest.raises(ValueError, match="profile"):
        service.generate_project_pdw("bad.pdw", "main.pdw", wrong, contract)
    with pytest.raises(ValueError, match="no supplied"):
        service.generate_project_pdw(
            "bad.pdw", "main.pdw", ladder, contract, module_order=["FBs-UNKNOWN"]
        )
    with pytest.raises(ValueError, match="Undeclared"):
        service.generate_project_pdw(
            "bad.pdw", "main.pdw", ladder, IOContract(inputs=[], outputs=[])
        )
    assert not (tmp_path / "artifacts/bad.pdw").exists()


def test_module_selection_mcp(tmp_path):
    (tmp_path / "main.pdw").write_bytes(module_template())

    async def run():
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "winproladder_mcp.server", "--root", str(tmp_path), "--compact-responses"],
        )
        async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
            await session.initialize()
            inspected = await session.call_tool("inspect_pdw", {"path": "main.pdw"})
            assert not inspected.isError, inspected.content
            assert len(inspected.structuredContent["modules"]) == 2
            result = await session.call_tool(
                "generate_project_pdw",
                {
                    "output_name": "output.pdw",
                    "template_path": "main.pdw",
                    "ladder": {
                        "profile": "FBs-40MC-test27",
                        "networks": [{"condition": "X0", "coils": [{"address": 0}]}],
                    },
                    "io_contract": {"inputs": ["X0"], "outputs": ["Y0"]},
                    "module_order": ["FBs-TESTB", "FBs-TESTB", "FBs-TESTA"],
                },
            )
            assert not result.isError, result.content
            assert [m["name"] for m in result.structuredContent["project"]["modules"]] == [
                "FBs-TESTB",
                "FBs-TESTB",
                "FBs-TESTA",
            ]

    asyncio.run(run())
