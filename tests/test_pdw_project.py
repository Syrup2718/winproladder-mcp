"""Synthetic PDW project regressions; no machine-specific or private sample access."""

import asyncio
import base64
import sys

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import EmbeddedResource
from test_pdw import synthetic_template

from winproladder_mcp.acceptance import AcceptanceCase
from winproladder_mcp.component_comments import ComponentComment
from winproladder_mcp.io_contract import IOContract
from winproladder_mcp.ir import Coil, Ladder, Network, Timer, decode_network
from winproladder_mcp.pdw_project import PdwSection, build, parse
from winproladder_mcp.service import Service


def cycle_ladder():
    return Ladder(
        profile="FBs-60MC-test16",
        networks=[
            Network(
                condition="X0 AND ((NOT Y1 AND NOT Y2 AND NOT T0) OR T2)", coils=[Coil(address=0)]
            ),
            Network(condition="X0 AND (Y1 OR T0) AND NOT T1", coils=[Coil(address=1)]),
            Network(condition="X0 AND (Y2 OR T1) AND NOT T2", coils=[Coil(address=2)]),
            *(Network(block=Timer(address=i, preset=10, enable=f"X0 AND Y{i}")) for i in range(3)),
        ],
    )


def acceptance():
    scans = []
    for enabled, count in [(False, 3), (True, 60), (False, 4), (True, 60)]:
        for t in range(count):
            scans.append(
                {
                    "inputs": {"X0": enabled},
                    "expected": {f"Y{i}": enabled and i == (t // 10) % 3 for i in range(3)},
                }
            )
    return [AcceptanceCase.model_validate({"name": "cycle restart", "scan_ms": 10, "scans": scans})]


def test_variable_program_sections_unicode_and_comments(tmp_path):
    template = synthetic_template()
    (tmp_path / "template.pdw").write_bytes(template)
    ladder = cycle_ladder()
    ladder.networks[0].comment = "中文網路\r\n第二行"
    result = Service(tmp_path).generate_project_pdw(
        "cycle.pdw",
        "template.pdw",
        ladder,
        IOContract(inputs=["X0"], outputs=["Y0", "Y1", "Y2"]),
        acceptance(),
        sections=[
            PdwSection(network_index=0, name="AREA", comment="NOTE", embed_comment=True),
            PdwSection(network_index=3, name="計時區", comment="計時設定\r\n測試"),
        ],
        comments=[
            ComponentComment(ref=f"Y{i}", comment=t, description="中文說明")
            for i, t in enumerate(["RED", "YELLOW", "GREEN"])
        ],
        require_acceptance=True,
    )
    assert result["compiled_acceptance"]["passed"]
    description = Service(tmp_path).inspect_pdw("artifacts/cycle.pdw")
    assert [u["name"] for u in description["units"]] == ["AREA", "計時區", "SUB00001"]
    assert description["network_comments"][0]["comment"] == ladder.networks[0].comment
    assert description["component_comments"][2]["description"] == "中文說明"
    assert description["integrity"]["header_checksum"]
    assert description["rungs"] is None
    from pathlib import Path

    emitted = parse(Path(result["path"]).read_bytes())
    assert emitted.program.startswith(b"\xf0\x7f\x07\x2dSECT:AREA:NOTE")
    for offset in result["network_offsets"]:
        assert offset in range(0x200, 0x200 + len(emitted.program))
    with pytest.raises(FileExistsError):
        Service(tmp_path).generate_project_pdw(
            "cycle.pdw",
            "template.pdw",
            ladder,
            IOContract(inputs=["X0"], outputs=["Y0", "Y1", "Y2"]),
        )


@pytest.mark.parametrize("offset", [0x1023A, 0x1022C, 0x122 + 0x120, 0x122 + 0xCA, 0x122 + 0x203])
def test_reject_integrity_mutations_previously_accepted(offset):
    raw = bytearray(synthetic_template())
    raw[offset] ^= 1
    with pytest.raises(ValueError):
        parse(bytes(raw))


def test_metadata_limits_and_duplicates():
    template = synthetic_template()
    payload = bytes.fromhex("4000c100")
    for sections in [
        [],
        [PdwSection(network_index=1, name="A")],
        [PdwSection(network_index=0, name="A"), PdwSection(network_index=0, name="B")],
        [PdwSection(network_index=0, name="A", embed_comment=True)],
    ]:
        with pytest.raises(ValueError):
            build(template, [payload], sections, [""], [])
    with pytest.raises(ValueError, match="Duplicate"):
        build(
            template,
            [payload],
            [PdwSection(network_index=0, name="A")],
            [""],
            [ComponentComment(ref="Y0", comment="A"), ComponentComment(ref="Y0", comment="B")],
        )
    with pytest.raises(ValueError, match="CP950"):
        build(template, [payload], [PdwSection(network_index=0, name="😀")], [""], [])
    with pytest.raises(ValueError, match="extent"):
        build(template, [payload] * 1100, [PdwSection(network_index=0, name="A")], [""] * 1100, [])


def test_name_memory_disagreement_rejected():
    raw, _ = build(
        synthetic_template(),
        [bytes.fromhex("4000c100")],
        [PdwSection(network_index=0, name="A")],
        [""],
        [ComponentComment(ref="Y0", comment="RED")],
    )
    changed = bytearray(raw)
    changed[0xA126 + 0x5FFB] ^= 1
    with pytest.raises(ValueError, match="disagree"):
        parse(bytes(changed))


def test_opaque_instruction_inspection_not_semantic_success():
    raw, _ = build(
        synthetic_template(),
        [bytes.fromhex("f67f0000deadbeef")],
        [PdwSection(network_index=0, name="A")],
        [""],
        [],
    )
    project = parse(raw)
    assert project.describe()["func199_candidate_addresses"] == [0x200]
    assert decode_network(project.program) is None


def test_source_checks_and_no_output_on_failure(tmp_path):
    (tmp_path / "template.pdw").write_bytes(synthetic_template())
    service = Service(tmp_path)
    ladder = cycle_ladder()
    contract = IOContract(inputs=["X0"], outputs=["Y0", "Y1", "Y2"])
    with pytest.raises(ValueError, match="Undeclared"):
        service.generate_project_pdw(
            "bad.pdw", "template.pdw", ladder, IOContract(inputs=[], outputs=[])
        )
    with pytest.raises(ValueError, match="acceptance"):
        service.generate_project_pdw(
            "bad.pdw", "template.pdw", ladder, contract, require_acceptance=True
        )
    ladder.networks[1].coils = [Coil(address=0)]
    with pytest.raises(ValueError):
        service.generate_project_pdw("bad.pdw", "template.pdw", ladder, contract)
    assert not (tmp_path / "artifacts/bad.pdw").exists()


def test_project_tool_stdio(tmp_path):
    (tmp_path / "template.pdw").write_bytes(synthetic_template())

    async def run():
        params = StdioServerParameters(
            command=sys.executable, args=["-m", "winproladder_mcp.server", "--root", str(tmp_path)]
        )
        async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "generate_project_pdw",
                {
                    "output_name": "project.pdw",
                    "template_path": "template.pdw",
                    "ladder": cycle_ladder().model_dump(),
                    "io_contract": {"inputs": ["X0"], "outputs": ["Y0", "Y1", "Y2"]},
                    "acceptance": [a.model_dump() for a in acceptance()],
                    "require_acceptance": True,
                    "comments": [{"ref": "Y0", "comment": "紅燈"}],
                    "sections": [{"network_index": 0, "name": "測試區", "comment": "測試\r\n說明"}],
                },
            )
            assert not result.isError, result.content
            embedded = next(c for c in result.content if isinstance(c, EmbeddedResource))
            raw = base64.b64decode(embedded.resource.blob)
            assert parse(raw).describe()["component_comments"][0]["comment"] == "紅燈"

    asyncio.run(run())
