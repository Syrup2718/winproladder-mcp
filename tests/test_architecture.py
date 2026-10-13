"""Architecture constraints cannot be bypassed by lowering or alternate file tools."""

import asyncio
import json

import pytest

from winproladder_mcp.architecture import ArchitecturePolicy, architecture_report
from winproladder_mcp.ir import Ladder, Network
from winproladder_mcp.server import build_server
from winproladder_mcp.service import Service


def strict_workspace(root):
    (root / ".winproladder-policy.json").write_text('{"forbid_m_to_m": true}')
    return Service(root)


def ladder(condition, device="M", address=1):
    return Ladder.model_validate(
        {"networks": [{"condition": condition, "coils": [{"device": device, "address": address}]}]}
    )


@pytest.mark.parametrize("condition", ["M0", "NOT M0", "M1", "X0 OR M0", "M0 AND X1"])
def test_rejects_copies_self_holds_and_mixed_inputs_before_writing(tmp_path, condition):
    service = strict_workspace(tmp_path)
    with pytest.raises(ValueError, match="M-to-M"):
        service.generate("rejected.ldr", ladder(condition))
    assert not (tmp_path / "artifacts/rejected.ldr").exists()


@pytest.mark.parametrize("mode", ["normal", "set", "reset"])
def test_coil_modes_cannot_bypass_policy(mode):
    program = ladder("M0")
    program.networks[0].coils[0].mode = mode
    assert not architecture_report(program, ArchitecturePolicy(forbid_m_to_m=True))["valid"]


@pytest.mark.parametrize(
    "network",
    [
        {
            "block": {"type": "timer", "address": 0, "preset": 1, "enable": "M0"},
            "coils": [{"device": "M", "address": 1}],
        },
        {
            "action": {
                "type": "compare",
                "sa": "R0",
                "sb": "R1",
                "enable": "M0",
                "equal": [{"device": "M", "address": 1}],
            }
        },
    ],
)
def test_function_blocks_do_not_hide_m_to_m(network):
    program = Ladder.model_validate({"networks": [network]})
    report = architecture_report(program, ArchitecturePolicy(forbid_m_to_m=True))
    assert report["m_to_m_networks"] == [{"network": 0, "reads": ["M0"], "writes": ["M1"]}]


def test_rejects_helpers_introduced_by_lowering(tmp_path):
    service = strict_workspace(tmp_path)
    program = ladder("(M0 AND M1) OR (M2 AND M3)", "Y", 0)
    assert architecture_report(program, ArchitecturePolicy(forbid_m_to_m=True))["valid"]
    with pytest.raises(ValueError, match="M-to-M"):
        service.generate("hidden-helper.ldr", program)
    assert not (tmp_path / "artifacts/hidden-helper.ldr").exists()


def test_allows_unconditional_comparison_to_output_without_helpers(tmp_path):
    service = strict_workspace(tmp_path)
    program = Ladder.model_validate(
        {
            "networks": [
                {
                    "action": {
                        "type": "compare",
                        "sa": "R0",
                        "sb": "R1",
                        "equal": [{"device": "M", "address": 0}],
                    }
                },
                {"condition": "M0", "coils": [{"address": 0}]},
                {"block": {"type": "timer", "address": 0, "preset": 4, "enable": "M0"}},
            ]
        }
    )
    result = service.generate("allowed.ldr", program)
    assert result["architecture"]["valid"]
    assert result["architecture"]["m_to_m_networks"] == []
    assert result["layout"]["helper_devices"] == []


def test_policy_reloads_and_covers_export_edit_and_direct_write(tmp_path):
    service = Service(tmp_path)
    original = service.generate("old.ldr", ladder("M0"))
    strict_workspace(tmp_path)
    # Inspection of old programs remains available.
    assert service.read(original["path"])["ladder"]
    with pytest.raises(ValueError, match="M-to-M"):
        service.export(original["path"], "copy.ldr")
    with pytest.raises(ValueError, match="M-to-M"):
        service.write("direct.ldr", service.load(original["path"]))
    with pytest.raises(ValueError, match="M-to-M"):
        service.edit(
            original["path"],
            "edit.ldr",
            "insert",
            1,
            Network(condition="X0", coils=[{"address": 0}]),
            True,
        )
    assert sorted(p.name for p in (tmp_path / "artifacts").glob("*.ldr")) == ["old.ldr"]


@pytest.mark.parametrize("content", ["{", '{"forbid_m_to_m":"false"}', '{"typo":true}'])
def test_invalid_policy_cannot_silently_disable_check(tmp_path, content):
    (tmp_path / ".winproladder-policy.json").write_text(content)
    with pytest.raises(ValueError):
        Service(tmp_path).generate("invalid.ldr", ladder("X0", "Y", 0))


def test_tool_preview_and_guide_expose_live_workspace_policy(tmp_path):
    strict_workspace(tmp_path)
    server = build_server(tmp_path)

    async def run():
        guide = await server.call_tool("get_design_guide", {})
        # FastMCP returns content plus structured data for dict results.
        guide_data = guide[1] if isinstance(guide, tuple) else json.loads(guide[0].text)
        assert guide_data["architecture_policy"] == {
            "forbid_m_to_m": True,
            "allow_function_m_to_m": False,
        }
        preview = await server.call_tool("validate_ladder", {"ladder": ladder("M0").model_dump()})
        data = preview[1] if isinstance(preview, tuple) else json.loads(preview[0].text)
        assert not data["valid"]
        assert data["architecture"]["m_to_m_networks"]

    asyncio.run(run())
