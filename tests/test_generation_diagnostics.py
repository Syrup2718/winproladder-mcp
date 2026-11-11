"""Generation failures are classified without weakening the established write gates."""

import asyncio
import itertools
import sys
from typing import Any

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import winproladder_mcp.service as service_module
from winproladder_mcp.generation_diagnostics import GENERATION_CODES, GenerationFailure
from winproladder_mcp.io_contract import IOContract
from winproladder_mcp.ir import Ladder, Network, simulate
from winproladder_mcp.server import build_server
from winproladder_mcp.service import Service


def diagnostic(result: Any) -> dict[str, Any]:
    assert result.isError
    assert result.structuredContent is not None
    data = result.structuredContent
    assert data["error"]["written"] is False
    assert data["error"]["generation_code"] == data["diagnosis"]["code"]
    assert data["diagnosis"]["artifact_created"] is False
    assert data["diagnosis"]["original_request_preserved"] is True
    return data["diagnosis"]


def generate_arguments(name: str, ladder: dict[str, Any]) -> dict[str, Any]:
    return {
        "output_name": name,
        "ladder": ladder,
        "io_contract": {"inputs": [], "outputs": []},
    }


def test_public_generation_failure_categories_and_locations(tmp_path):
    async def run():
        server = build_server(tmp_path)
        cases = [
            (
                "invalid.ldr",
                {"networks": []},
                "INVALID_IR",
                None,
                None,
            ),
            (
                "instruction.ldr",
                {"networks": [{"action": {"type": "unknown_func"}}]},
                "UNSUPPORTED_INSTRUCTION",
                0,
                "unknown_func",
            ),
            (
                "operand.ldr",
                {
                    "networks": [
                        {
                            "action": {
                                "type": "arithmetic",
                                "operation": "sub",
                                "sa": "R0",
                                "sb": "R1",
                                "destination": "R2",
                            }
                        }
                    ]
                },
                "UNSUPPORTED_OPERAND",
                0,
                "arithmetic",
            ),
            (
                "structure.ldr",
                {
                    "networks": [
                        {"action": {"type": "for", "count": 2}},
                        {"action": {"type": "for", "count": 3}},
                        {"action": {"type": "next"}},
                        {"action": {"type": "next"}},
                    ]
                },
                "UNSUPPORTED_NETWORK_STRUCTURE",
                1,
                "for",
            ),
            (
                "evidence.ldr",
                {"networks": [{"action": {"type": "call"}}]},
                "MISSING_ENCODING_EVIDENCE",
                0,
                "call",
            ),
        ]
        for name, ladder, code, network, instruction in cases:
            result = await server.call_tool("generate_ldr", generate_arguments(name, ladder))
            report = diagnostic(result)
            assert report["code"] == code
            assert report["network_index"] == network
            assert report["instruction"] == instruction
            if code == "UNSUPPORTED_OPERAND":
                assert report["operands"]["sb"] == "R1"
            if code == "MISSING_ENCODING_EVIDENCE":
                assert "Original WinProLadder-exported .ldr" in report["missing_evidence"]
            assert report["verified_alternative"] is None
            assert report["recovery"]["policy_bypassed"] is False
            assert not (tmp_path / "artifacts" / name).exists()

    asyncio.run(run())


def test_existing_policy_code_is_preserved_with_generation_diagnosis(tmp_path):
    (tmp_path / ".winproladder-policy.json").write_text(
        '{"forbid_m_to_m":true,"allow_function_m_to_m":true}', encoding="utf-8"
    )

    async def run():
        server = build_server(tmp_path)
        result = await server.call_tool(
            "generate_ldr",
            {
                "output_name": "policy.ldr",
                "ladder": {
                    "networks": [{"condition": "M0", "coils": [{"device": "M", "address": 1}]}]
                },
                "io_contract": {"inputs": [], "outputs": []},
            },
        )
        report = diagnostic(result)
        assert result.structuredContent["error"]["code"] == "ARCHITECTURE_POLICY_VIOLATION"
        assert report["code"] == "UNSUPPORTED_NETWORK_STRUCTURE"
        assert report["stage"] == "source_validation"
        assert not (tmp_path / "artifacts/policy.ldr").exists()

    asyncio.run(run())


def test_import_unverified_is_explicit_and_never_claims_gui_verification(tmp_path):
    ladder = Ladder(networks=[Network(condition="X0", coils=[{"address": 0}])])
    with pytest.raises(GenerationFailure) as caught:
        Service(tmp_path).create(
            "candidate.ldr",
            ladder,
            io_contract=IOContract(inputs=["X0"], outputs=["Y0"]),
        )
    report = caught.value.diagnostic
    assert report.code == "IMPORT_UNVERIFIED"
    assert report.stage == "import_verification"
    assert report.safe_to_retry
    assert report.validation_levels["gui_import"] == "not_verified"
    assert report.validation_levels["physical_plc"] == "not_verified"
    assert not (tmp_path / "artifacts/candidate.ldr").exists()


def test_encoder_failure_is_diagnostic_and_fail_closed(tmp_path, monkeypatch):
    def broken_encoder(_network):
        raise ValueError("Encoder internal failure")

    monkeypatch.setattr(service_module, "compile_network", broken_encoder)
    ladder = Ladder(networks=[Network(condition="X0", coils=[{"address": 0}])])
    with pytest.raises(GenerationFailure) as caught:
        Service(tmp_path).generate(
            "broken.ldr",
            ladder,
            io_contract=IOContract(inputs=["X0"], outputs=["Y0"]),
        )
    report = caught.value.diagnostic
    assert report.code == "ENCODING_FAILURE"
    assert report.stage == "encoding"
    assert report.network_index is None
    assert not (tmp_path / "artifacts/broken.ldr").exists()


def test_emitted_byte_validation_failure_is_diagnostic_and_fail_closed(tmp_path, monkeypatch):
    monkeypatch.setattr(service_module, "decode_network", lambda _payload: None)
    ladder = Ladder(networks=[Network(condition="X0", coils=[{"address": 0}])])
    with pytest.raises(GenerationFailure) as caught:
        Service(tmp_path).generate(
            "invalid-bytes.ldr",
            ladder,
            io_contract=IOContract(inputs=["X0"], outputs=["Y0"]),
        )
    report = caught.value.diagnostic
    assert report.code == "ARTIFACT_VALIDATION_FAILURE"
    assert report.stage == "artifact_validation"
    assert report.validation_levels["emitted_bytes"] == "failed"
    assert not (tmp_path / "artifacts/invalid-bytes.ldr").exists()


def test_existing_boolean_recovery_is_reported_and_semantically_equivalent(tmp_path):
    source = Ladder(networks=[Network(condition="X0 AND TRUE", coils=[{"address": 0}])])
    service = Service(tmp_path)
    result = service.generate(
        "recovered.ldr",
        source,
        io_contract=IOContract(inputs=["X0"], outputs=["Y0"]),
    )
    recovery = result["generation_recovery"]
    assert recovery["status"] == "recovered"
    assert recovery["applied"] == ["boolean_simplification"]
    assert recovery["policy_bypassed"] is False
    assert recovery["unverified_encoding_substitution"] is False

    emitted = Ladder.model_validate(service.read(result["path"])["ladder"])
    scans = [{"X0": False}, {"X0": True}, {"X0": False}]
    assert simulate(source, scans, {}) == simulate(emitted, scans, {})

    connected = Ladder(
        networks=[Network(condition="(X0 AND X1) OR (X2 AND X3)", coils=[{"address": 1}])]
    )
    connected_result = service.generate(
        "connected.ldr",
        connected,
        io_contract=IOContract(inputs=["X0", "X1", "X2", "X3"], outputs=["Y1"]),
    )
    connected_recovery = connected_result["generation_recovery"]
    assert "verified_connected_layout_lowering" in connected_recovery["applied"]
    connected_emitted = Ladder.model_validate(service.read(connected_result["path"])["ladder"])
    truth_table = [
        {f"X{index}": value for index, value in enumerate(values)}
        for values in itertools.product((False, True), repeat=4)
    ]
    assert [scan["Y1"] for scan in simulate(connected, truth_table, {})] == [
        scan["Y1"] for scan in simulate(connected_emitted, truth_table, {})
    ]


def test_capabilities_list_exact_diagnostic_scope(tmp_path):
    async def run():
        server = build_server(tmp_path)
        result = await server.call_tool("get_capabilities", {"detail": True})
        data = result[1] if isinstance(result, tuple) else result.structuredContent
        assert data is not None
        scope = data["generation_failure_diagnostics"]
        assert scope["codes"] == list(GENERATION_CODES)
        assert scope["defensive_only"] == [
            "ENCODING_FAILURE",
            "ARTIFACT_VALIDATION_FAILURE",
        ]
        assert "guess opcode or binary layout" in scope["never"]

    asyncio.run(run())


def test_validate_ladder_returns_all_non_writing_diagnostics(tmp_path):
    async def run():
        server = build_server(tmp_path)
        result = await server.call_tool(
            "validate_ladder",
            {
                "ladder": {
                    "networks": [
                        {"action": {"type": "for", "count": 2}},
                        {"action": {"type": "for", "count": 3}},
                    ]
                }
            },
        )
        data = result[1] if isinstance(result, tuple) else result.structuredContent
        assert data is not None and not data["valid"]
        assert data["diagnostics"]
        assert {item["code"] for item in data["diagnostics"]} == {"UNSUPPORTED_NETWORK_STRUCTURE"}
        assert all(item["artifact_created"] is False for item in data["diagnostics"])
        assert not (tmp_path / "artifacts").exists()

    asyncio.run(run())


def test_generation_diagnosis_survives_real_stdio_transport(tmp_path):
    async def run():
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "winproladder_mcp.server", "--root", str(tmp_path)],
        )
        async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "generate_ldr",
                generate_arguments(
                    "wire.ldr",
                    {"networks": [{"action": {"type": "unknown_func"}}]},
                ),
            )
            report = diagnostic(result)
            assert report["code"] == "UNSUPPORTED_INSTRUCTION"
            assert report["network_index"] == 0
            assert report["instruction"] == "unknown_func"
            assert not (tmp_path / "artifacts/wire.ldr").exists()

    asyncio.run(asyncio.wait_for(run(), timeout=30))
