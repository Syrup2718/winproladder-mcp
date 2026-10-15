"""Verify real MCP generation, decoded behavior, and file delivery; retain a GUI manifest.

Run with the installed project Python, e.g.:
    python scripts/verify_release.py --root C:/Fatek/winproladder-mcp
Each run uses a new directory and never replaces an earlier release's evidence.
"""

import argparse
import asyncio
import base64
import hashlib
import itertools
import json
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from winproladder_mcp.ldr import FOOTER, parse


def acceptance(
    name: str,
    inputs: list[dict[str, bool]],
    expected: list[dict[str, bool]],
    scan_ms: int | None = 10,
) -> list[dict[str, Any]]:
    case: dict[str, Any] = {
        "name": name,
        "scans": [
            {"inputs": state, "expected": outputs}
            for state, outputs in zip(inputs, expected, strict=True)
        ],
    }
    if scan_ms is not None:
        case["scan_ms"] = scan_ms
    return [case]


def release_cases() -> list[dict[str, Any]]:
    """Customer-level scenarios with expected behavior independent of the compiler."""
    cases: list[dict[str, Any]] = []

    def control(
        kind: str,
        requirement: str,
        inputs: list[dict[str, bool]],
        outputs: list[bool] | list[dict[str, bool]],
        **options: Any,
    ) -> None:
        expected = [{"Y0": value} if isinstance(value, bool) else value for value in outputs]
        cases.append(
            {
                "id": kind,
                "requirement": requirement,
                "tool": "generate_control_ldr",
                "arguments": {
                    "spec": {
                        "kind": kind,
                        "requirement": requirement,
                        "signal": "X0",
                        "output": 0,
                        **(
                            {"stop": "X1"}
                            if kind in {"start_stop", "forward_reverse", "star_delta"}
                            else {}
                        ),
                        **({"reset": "X2"} if kind in {"set_reset", "toggle", "counter"} else {}),
                        **({"reverse": "X3"} if kind == "forward_reverse" else {}),
                        **options,
                    },
                    "acceptance": acceptance(requirement, inputs, expected),
                },
            }
        )

    control(
        "start_stop",
        "X0 starts and latches Y0; X1 stops and has priority over start.",
        [{}, {"X0": True}, {}, {"X1": True}, {"X0": True, "X1": True}, {}],
        [False, True, True, False, False, False],
    )
    control(
        "set_reset",
        "X0 sets Y0, X2 resets it, and reset wins simultaneous commands.",
        [{}, {"X0": True}, {}, {"X2": True}, {"X0": True, "X2": True}, {}],
        [False, True, True, False, False, False],
    )
    edge_inputs = [{}, {"X0": True}, {"X0": True}, {}, {"X0": True}, {}, {"X2": True}]
    control(
        "toggle",
        "Toggle Y0 once per press of X0; holding the button must not repeat; X2 clears.",
        edge_inputs,
        [False, True, True, True, False, False, False],
    )
    control(
        "rising_edge",
        "Y0 pulses for one scan on the rising edge of X0.",
        edge_inputs,
        [False, True, False, False, True, False, False],
    )
    control(
        "falling_edge",
        "Y0 pulses for one scan on the falling edge of X0.",
        edge_inputs,
        [False, False, False, True, False, True, False],
    )
    timer_inputs = [{}, {"X0": True}, {"X0": True}, {"X0": True}, {}, {}, {}]
    control(
        "on_delay",
        "Y0 turns on after X0 stays high for 30 ms and resets when X0 drops.",
        timer_inputs,
        [False, False, False, True, False, False, False],
        delay_ms=30,
    )
    control(
        "off_delay",
        "Y0 starts immediately with X0 and remains on for 30 ms after X0 drops.",
        timer_inputs,
        [False, True, True, True, True, True, False],
        delay_ms=30,
    )
    control(
        "pulse",
        "An X0 rising edge starts a 30 ms Y0 pulse; holding X0 does not retrigger.",
        timer_inputs,
        [False, True, True, False, False, False, False],
        delay_ms=30,
    )
    control(
        "counter",
        "Y0 turns on at the second X0 rising edge; X2 clears even if X0 is high.",
        [{}, {"X0": True}, {"X0": True}, {}, {"X0": True}, {"X0": True, "X2": True}],
        [False, False, False, False, True, False],
        count=2,
    )
    control(
        "forward_reverse",
        "Y0 forward and Y1 reverse exclude each other; X1 stops; simultaneous starts favor forward",
        [
            {},
            {"X0": True, "X3": True},
            {"X3": True},
            {"X1": True},
            {"X3": True},
            {"X0": True},
            {"X1": True},
        ],
        [
            {"Y0": False, "Y1": False},
            {"Y0": True, "Y1": False},
            {"Y0": True, "Y1": False},
            {"Y0": False, "Y1": False},
            {"Y0": False, "Y1": True},
            {"Y0": False, "Y1": True},
            {"Y0": False, "Y1": False},
        ],
    )
    control(
        "star_delta",
        "Start main Y0 and star Y1, wait 30 ms, leave a 20 ms gap, then delta Y2; X1 stops.",
        [{"X0": True}, {}, {}, {}, {}, {"X1": True}],
        [
            {"Y0": True, "Y1": True, "Y2": False},
            {"Y0": True, "Y1": True, "Y2": False},
            {"Y0": True, "Y1": False, "Y2": False},
            {"Y0": True, "Y1": False, "Y2": True},
            {"Y0": True, "Y1": False, "Y2": True},
            {"Y0": False, "Y1": False, "Y2": False},
        ],
        delay_ms=30,
        gap_ms=20,
    )
    requirement = "Two independent start/stop motors Y0 and Y1; keep stops independent."
    cases.append(
        {
            "id": "independent_motors",
            "requirement": requirement,
            "tool": "generate_system_ldr",
            "arguments": {
                "spec": {
                    "requirement": requirement,
                    "controls": [
                        {
                            "kind": "start_stop",
                            "requirement": "Motor A",
                            "output": 0,
                            "signal": "X0",
                            "stop": "X1",
                        },
                        {
                            "kind": "start_stop",
                            "requirement": "Motor B",
                            "output": 1,
                            "signal": "X2",
                            "stop": "X3",
                        },
                    ],
                },
                "acceptance": acceptance(
                    requirement,
                    [{}, {"X0": True}, {"X2": True}, {"X1": True}, {}, {"X3": True}],
                    [
                        {"Y0": False, "Y1": False},
                        {"Y0": True, "Y1": False},
                        {"Y0": True, "Y1": True},
                        {"Y0": False, "Y1": True},
                        {"Y0": False, "Y1": True},
                        {"Y0": False, "Y1": False},
                    ],
                ),
            },
        }
    )
    requirement = "Mix Y0 for three X4 clock ticks then drain Y1 for one; pause retains ticks."
    sequence_inputs = [
        {"X0": True},
        {"X4": True},
        {},
        {"X1": True, "X4": True},
        {"X4": True},
        {},
        {"X4": True},
        {},
        {"X4": True},
        {},
        {"X4": True},
    ]
    cases.append(
        {
            "id": "pause_resume_sequence",
            "requirement": requirement,
            "tool": "generate_sequence_ldr",
            "arguments": {
                "spec": {
                    "requirement": requirement,
                    "start": "X0",
                    "pause": "X1",
                    "clock": "X4",
                    "steps": [
                        {"name": "mix", "ticks": 3, "outputs": [0]},
                        {"name": "drain", "ticks": 1, "outputs": [1]},
                    ],
                },
                "acceptance": acceptance(
                    requirement,
                    sequence_inputs,
                    [
                        {"Y0": index < 8 and index != 3, "Y1": index in (8, 9), "M5": index == 10}
                        for index in range(len(sequence_inputs))
                    ],
                ),
            },
        }
    )
    truth_inputs = [
        {f"X{i}": value for i, value in enumerate(bits)}
        for bits in itertools.product((False, True), repeat=7)
    ]
    truth_expected = []
    for state in truth_inputs:
        value = state["X0"] and any(state[f"X{i}"] for i in range(1, 7))
        truth_expected.append({"Y0": value, "Y1": not value})
    requirement = "Connected permissives with normal and inverted outputs."
    cases.append(
        {
            "id": "connected_boolean",
            "requirement": requirement,
            "tool": "generate_ldr",
            "arguments": {
                "ladder": {
                    "networks": [
                        {
                            "condition": "X0 AND (X1 OR X2 OR X3 OR X4 OR X5 OR X6)",
                            "coils": [{"address": 0}, {"address": 1, "inverted": True}],
                        }
                    ]
                },
                "acceptance": acceptance(
                    "All 128 input combinations", truth_inputs, truth_expected, scan_ms=None
                ),
            },
        }
    )
    requirement = "Timer T0 needs 30 ms permission; C0 counts two edges; Y2 requires both done."
    cases.append(
        {
            "id": "custom_timer_counter",
            "requirement": requirement,
            "tool": "generate_ldr",
            "arguments": {
                "ladder": {
                    "networks": [
                        {
                            "block": {
                                "type": "timer",
                                "address": 0,
                                "preset": 3,
                                "enable": "X0 AND (X1 OR X2)",
                            },
                            "coils": [{"address": 0}],
                        },
                        {
                            "block": {
                                "type": "counter",
                                "address": 0,
                                "preset": 2,
                                "pulse": "X3",
                                "clear": "X4",
                            },
                            "coils": [{"address": 1}],
                        },
                        {"condition": "T0 AND C0", "coils": [{"address": 2}]},
                    ]
                },
                "acceptance": acceptance(
                    requirement,
                    [
                        {},
                        {"X0": True, "X1": True, "X3": True},
                        {"X0": True, "X2": True, "X3": True},
                        {"X0": True, "X2": True},
                        {"X0": True, "X1": True, "X3": True},
                        {"X0": True, "X1": True, "X3": True, "X4": True},
                        {},
                    ],
                    [
                        {"Y0": False, "Y1": False, "Y2": False},
                        {"Y0": False, "Y1": False, "Y2": False},
                        {"Y0": False, "Y1": False, "Y2": False},
                        {"Y0": True, "Y1": False, "Y2": False},
                        {"Y0": True, "Y1": True, "Y2": True},
                        {"Y0": True, "Y1": False, "Y2": False},
                        {"Y0": False, "Y1": False, "Y2": False},
                    ],
                ),
            },
        }
    )
    cases.append(
        {
            "id": "native_timer_sequence",
            "requirement": "X1 starts Y71 for 3s then Y72 for 5s",
            "tool": "generate_sequence_ldr",
            "arguments": {
                "spec": {
                    "requirement": "X1 starts Y71 for 3s then Y72 for 5s",
                    "start": "X1",
                    "steps": [
                        {"name": "first pump", "outputs": [71], "ticks": 30},
                        {"name": "second pump", "outputs": [72], "ticks": 50},
                    ],
                },
                "acceptance": acceptance(
                    "native T durations",
                    [{"X1": True}] + [{}] * 8,
                    [{"Y71": i < 3, "Y72": 3 <= i < 8} for i in range(9)],
                    1000,
                ),
            },
        }
    )
    # The scenario's independent input/output observations define permitted wiring.
    for case in cases:
        scans = [s for a in case["arguments"]["acceptance"] for s in a["scans"]]
        case["arguments"]["io_contract"] = {
            "inputs": sorted({d for s in scans for d in s["inputs"] if d.startswith("X")}),
            "outputs": sorted({d for s in scans for d in s["expected"] if d.startswith("Y")}),
        }
    cases.append(
        {
            "id": "native_pause_resume",
            "requirement": "retain elapsed time without an external clock",
            "tool": "generate_sequence_ldr",
            "arguments": {
                "spec": {
                    "requirement": "native pause",
                    "start": "X0",
                    "pause": "X1",
                    "reset": "X2",
                    "steps": [{"name": "mix", "outputs": [0], "ticks": 3}],
                    "tick_ms": 10,
                },
                "io_contract": {"inputs": ["X0", "X1", "X2"], "outputs": ["Y0"]},
                "acceptance": acceptance(
                    "pause then resume",
                    [{"X0": True}, {}, {"X1": True}, {}, {}, {"X2": True}],
                    [{"Y0": v} for v in [True, True, False, True, False, False]],
                ),
            },
        }
    )
    return cases


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def result_json(result: Any) -> dict[str, Any]:
    require(not result.isError, f"MCP tool failed: {result.content}")
    require(bool(result.content), "MCP returned no content")
    data = json.loads(result.content[0].text)
    require(isinstance(data, dict), "Expected JSON object in first text content")
    return data


async def verify_artifact(
    session: ClientSession, result: dict[str, Any], raw: bytes
) -> dict[str, Any]:
    artifact = result["artifact"]
    uri = artifact["uri"]
    resource = await session.read_resource(uri)
    require(len(resource.contents) == 1, f"Expected one binary resource for {uri}")
    blob = resource.contents[0]
    downloaded = base64.b64decode(blob.blob, validate=True)
    require(downloaded == raw, f"resources/read bytes differ from generated file: {uri}")
    require(blob.mimeType == "application/octet-stream", f"Unexpected resource MIME: {uri}")
    fetched = await session.call_tool("get_ldr_artifact", {"output_name": artifact["name"]})
    metadata = result_json(fetched)
    require(metadata["sha256"] == result["sha256"], "Artifact download hash mismatch")
    embedded = [item for item in fetched.content if item.type == "resource"]
    require(len(embedded) == 1, "get_ldr_artifact did not return one embedded file")
    require(
        base64.b64decode(embedded[0].resource.blob, validate=True) == raw,
        "get_ldr_artifact bytes differ from generated file",
    )
    return {"uri": uri, "resource_read": True, "embedded_download": True, "size": len(raw)}


async def verify_case(
    session: ClientSession, case: dict[str, Any], output: Path, index: int
) -> dict[str, Any]:
    arguments = {"output_name": f"{index:02d}_{case['id']}.ldr", **case["arguments"]}
    tool_result = await session.call_tool(case["tool"], arguments)
    result = result_json(tool_result)
    path = Path(result["path"])
    require(path.resolve() == output / arguments["output_name"], "Output escaped release directory")
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    require(result["sha256"] == digest, "Generated hash does not match file bytes")
    require(result["size"] == len(raw), "Generated file size mismatch")
    document = parse(raw, strict_crc=True)
    require(bool(document.records) and document.tail == FOOTER, "Unexpected LDR framing")
    require(document.encode() == raw, "LDR parser changed file bytes on roundtrip")
    require(all(record.crc_valid for record in document.records), "Invalid record CRC")
    require(result["acceptance"]["passed"] is True, "Source requirement acceptance failed")
    links = [item for item in tool_result.content if item.type == "resource_link"]
    require(len(links) == 1, "Generation must return a directly usable MCP ResourceLink")
    require(str(links[0].uri) == result["artifact"]["uri"], "ResourceLink URI mismatch")
    download = await verify_artifact(session, result, raw)

    inspected = result_json(await session.call_tool("inspect_ldr", {"path": str(path)}))
    require(inspected["sha256"] == digest, "MCP inspection hash mismatch")
    require(all(item["crc_valid"] for item in inspected["records"]), "MCP reports invalid CRC")
    decoded = result_json(await session.call_tool("read_ldr", {"path": str(path)}))
    require(decoded["ladder"] is not None, "Generated file contains opaque networks")
    require(decoded["sha256"] == digest, "MCP read hash mismatch")
    analysis = result_json(await session.call_tool("analyze_ldr", {"path": str(path)}))
    require(
        analysis["decoded_count"] == len(document.records), "Incomplete generated-file analysis"
    )

    replayed = []
    for scenario in arguments["acceptance"]:
        simulation = {
            "ladder": decoded["ladder"],
            "inputs": [scan["inputs"] for scan in scenario["scans"]],
            "initial": scenario.get("initial", {}),
        }
        if "scan_ms" in scenario:
            simulation["scan_ms"] = scenario["scan_ms"]
        trace = result_json(await session.call_tool("simulate_ladder", simulation))["trace"]
        for scan_index, (scan, state) in enumerate(zip(scenario["scans"], trace, strict=True)):
            for device, expected in scan["expected"].items():
                require(
                    state.get(device, False) == expected,
                    f"Decoded {case['id']} scan {scan_index}: {device} expected {expected}",
                )
        replayed.append({"name": scenario["name"], "scans": len(trace), "passed": True})

    if "design" in result:
        require(bool(result["design"]["assumptions"]), "Design must disclose defaults/assumptions")
        report = Path(result["design_report"])
        stored = json.loads(report.read_text(encoding="utf-8"))
        require(stored["sha256"] == digest, "Companion design report hash mismatch")
    return {
        "id": case["id"],
        "requirement": case["requirement"],
        "request": {"tool": case["tool"], "arguments": arguments},
        "result": result,
        "path": str(path),
        "sha256": digest,
        "size": len(raw),
        "networks": len(document.records),
        "crc_valid": True,
        "decoded_behavior": replayed,
        "delivery": download,
        "gui_import": {"status": "pending", "sha256": digest},
    }


async def verify_rejections(
    session: ClientSession, first: dict[str, Any], output: Path
) -> dict[str, bool]:
    path = Path(first["path"])
    before = path.read_bytes()
    duplicate = await session.call_tool(first["request"]["tool"], first["request"]["arguments"])
    require(duplicate.isError, "Duplicate generation unexpectedly overwrote an existing file")
    require(path.read_bytes() == before, "Duplicate generation changed existing bytes")
    invalid_name = "rejected_behavior.ldr"
    failed = await session.call_tool(
        "generate_ldr",
        {
            "output_name": invalid_name,
            "io_contract": {"inputs": [], "outputs": ["Y0"]},
            "ladder": {"networks": [{"condition": "FALSE", "coils": [{"address": 0}]}]},
            "acceptance": acceptance("An impossible requirement", [{}], [{"Y0": True}]),
        },
    )
    require(failed.isError, "A failing acceptance case was not rejected")
    require(not (output / invalid_name).exists(), "Failed acceptance left an LDR file")
    for name, tool, arguments, reason in [
        (
            "undeclared_input.ldr",
            "generate_ldr",
            {
                "io_contract": {"inputs": ["X1"], "outputs": ["Y71"]},
                "ladder": {"networks": [{"condition": "X4", "coils": [{"address": 71}]}]},
            },
            "Undeclared physical I/O: X4",
        ),
        (
            "undeclared_output.ldr",
            "generate_control_ldr",
            {
                "io_contract": {"inputs": ["X1"], "outputs": ["Y71"]},
                "spec": {
                    "requirement": "Y71 only",
                    "kind": "on_delay",
                    "signal": "X1",
                    "output": 72,
                },
            },
            "Undeclared physical I/O: Y72",
        ),
        (
            "unsupported_time_resolution.ldr",
            "generate_sequence_ldr",
            {
                "io_contract": {"inputs": ["X1", "X3"], "outputs": ["Y71"]},
                "spec": {
                    "requirement": "reject sub-10ms native timing",
                    "tick_ms": 1,
                    "start": "X1",
                    "pause": "X3",
                    "steps": [{"name": "pump", "outputs": [71], "ticks": 1}],
                },
            },
            "multiple of 10 ms",
        ),
    ]:
        rejected = await session.call_tool(tool, {"output_name": name, **arguments})
        require(
            rejected.isError and reason in str(rejected.content),
            f"Expected specific rejection for {name}",
        )
        require(not (output / name).exists(), f"Rejected request left {name}")
    return {
        "overwrite_rejected_and_bytes_preserved": True,
        "failed_acceptance_writes_no_file": True,
        "undeclared_input_rejected": True,
        "undeclared_output_rejected": True,
        "unsupported_resolution_rejected_without_clock_substitution": True,
    }


async def verify_release(root: Path) -> Path:
    root = root.resolve(strict=True)
    run_id = f"release-{datetime.now(UTC):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}"
    output = root / "artifacts" / run_id
    output.mkdir(parents=True, exist_ok=False)
    manifest_path = output / "manifest.json"
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "run_id": run_id,
        "created_at": datetime.now(UTC).isoformat(),
        "status": "running",
        "workspace": str(root),
        "output_directory": str(output),
        "python": sys.executable,
        "scope": "Actual stdio MCP, binary integrity, decoded scan model, and artifact delivery; "
        "GUI import and PLC runtime are separate verification steps.",
        "cases": [],
    }

    def save_manifest() -> None:
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    save_manifest()
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "winproladder_mcp.server", "--root", str(root), "--output-dir", str(output)],
    )
    try:
        async with stdio_client(parameters) as (read, write), ClientSession(read, write) as session:
            initialized = await session.initialize()
            manifest["server"] = initialized.serverInfo.model_dump(mode="json")
            manifest["tools"] = [tool.name for tool in (await session.list_tools()).tools]
            require(
                "get_ldr_artifact" in manifest["tools"], "MCP artifact delivery tool is missing"
            )
            guide = result_json(await session.call_tool("get_design_guide", {}))
            cases = release_cases()
            recipes = {
                case["arguments"]["spec"]["kind"]
                for case in cases
                if case["tool"] == "generate_control_ldr"
            }
            require(
                recipes == set(guide["control_recipes"]["kinds"]),
                "Release scenarios do not cover the server's advertised recipe set",
            )
            for index, case in enumerate(cases, 1):
                manifest["active_case"] = case["id"]
                save_manifest()
                checked = await verify_case(session, case, output, index)
                manifest["cases"].append(checked)
                save_manifest()
                print(
                    f"PASS {case['id']}: {checked['networks']} networks {checked['sha256']}",
                    flush=True,
                )
            manifest["rejections"] = await verify_rejections(session, manifest["cases"][0], output)
        manifest.pop("active_case", None)
        manifest["status"] = "passed"
    except BaseException as error:
        manifest["status"] = "failed"
        manifest["error"] = repr(error)
        raise
    finally:
        manifest["finished_at"] = datetime.now(UTC).isoformat()
        save_manifest()
        print(f"MANIFEST {manifest_path}", flush=True)
    return manifest_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--timeout", type=int, default=180, help="Entire run timeout in seconds")
    args = parser.parse_args()
    asyncio.run(asyncio.wait_for(verify_release(args.root), timeout=args.timeout))


if __name__ == "__main__":
    main()
