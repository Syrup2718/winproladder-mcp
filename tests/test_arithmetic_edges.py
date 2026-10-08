"""Independent test7 byte oracles, resource accounting, native edges and MCP delivery."""

import asyncio
import base64
import json
import sys
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from winproladder_mcp.analysis import device_references
from winproladder_mcp.control import ControlSpec, control_ladder
from winproladder_mcp.io_contract import IOContract
from winproladder_mcp.ir import (
    Arithmetic,
    Coil,
    EdgeContact,
    Ladder,
    Network,
    compile_network,
    decode_network,
    simulate,
    validation,
)
from winproladder_mcp.layout import lower_ladder
from winproladder_mcp.ldr import Document, parse
from winproladder_mcp.service import Service
from winproladder_mcp.system import SystemSpec, system_ladder
from winproladder_mcp.timing import timed_simulate

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "samples/test7.ldr"


def arithmetic(**overrides):
    return Arithmetic.model_validate(
        {"operation": "add", "sa": "R3840", "sb": 5, "destination": "D100", **overrides}
    )


def test_screenshot_operands_byte_oracles_and_identical_file(tmp_path):
    decoded = Service(ROOT).read("samples/test7.ldr")
    ladder = Ladder.model_validate(decoded["ladder"])
    assert ladder.profile == "FBs-24MA-test7"
    assert ladder.networks[0].edge == EdgeContact(kind="rising", input="X0")
    expected = [
        ("add", "R3840", 5, "D100", "4fe87fe8f6620100000540c8"),
        ("sub", "D100", 1, "D101", "4fe87fe8f66440c8000140ca"),
        ("mul", "D102", 2, "D103", "4fe87fe8f66640cc000240ce"),
        ("div", "R3841", 20, "D105", "4fe87fe8f6680102001440d2"),
    ]
    for network, (op, sa, sb, dest, raw) in zip(ladder.networks[1:], expected, strict=True):
        a = network.action
        assert isinstance(a, Arithmetic)
        assert (a.operation, a.sa, a.sb, a.destination) == (op, sa, sb, dest)
        assert compile_network(network).hex() == raw
    report = validation(ladder)
    assert [e["status"] for e in report["instruction_evidence"]] == ["observed_export"] * 5
    result = Service(tmp_path).generate(
        "rebuilt.ldr", ladder, io_contract=IOContract(inputs=["X0"], outputs=["Y1"])
    )
    assert Path(result["path"]).read_bytes() == SAMPLE.read_bytes()
    assert result["layout"]["helper_devices"] == []
    assert result["artifact_validation"]["decoded_networks"] == 5
    refs = device_references(list(enumerate(ladder.networks)))["devices"]
    assert refs["D104"]["writes"] == [3]  # High product word.
    assert refs["D106"]["writes"] == [4]  # Remainder, not an unused word.
    assert refs["D102"]["reads"] == [3]
    assert {d for d in refs if d.startswith(("X", "Y", "M"))} == {"X0", "Y1"}


@pytest.mark.parametrize("operation", ["add", "sub", "mul", "div"])
def test_inferred_conditions_registers_and_constant_address_collision(operation):
    # 0x0100 could also mean R3840: Sb is always a literal for this opcode family.
    network = Network(
        action=arithmetic(
            operation=operation,
            sa="D3999",
            sb=256,
            destination="R3838",
            enable="(X1 OR X2) AND (X3 OR X5)",
            unsigned_when="X6 AND NOT X7",
        )
    )
    ladder, layout = lower_ladder(Ladder(networks=[network]))
    for n in ladder.networks:
        assert compile_network(decode_network(compile_network(n))) == compile_network(n)
    assert ladder.networks[-1].action.sb == 256
    assert validation(ladder)["instruction_evidence"][0]["status"] == "inferred_variant"
    devices = device_references(list(enumerate(ladder.networks)))["devices"]
    assert {d for d in devices if d.startswith(("X", "Y"))} == {"X1", "X2", "X3", "X5", "X6", "X7"}
    assert all(d in ladder.symbols for d in layout["helper_devices"])


@pytest.mark.parametrize(
    "options",
    [
        {"sa": 3840},
        {"sa": "@R0"},
        {"sb": "R1"},
        {"sb": True},
        {"sb": -1},
        {"sb": 32768},
        {"destination": "R3840"},
        {"operation": "mul", "destination": "R3839"},
        {"operation": "div", "destination": "D4095"},
        {"operation": "div", "sb": 0},
        {"operation": "mov"},
        {"pulse": True},
        {"width": 32},
        {"flags": {"zero": "Y0"}},
    ],
)
def test_unestablished_forms_and_invalid_operands_rejected(options):
    with pytest.raises(ValueError):
        arithmetic(**options)


@pytest.mark.parametrize(
    "raw",
    [
        "4fe87fe8f66a0100000540c8",  # Incrementing opcode cannot establish FUN15.
        "4fe87fe8f4620100000540c8",  # Register/register hypothesis is not enabled.
        "4fe87fe8f6620100ffff40c8",  # Negative constant encoding not established.
        "4fe87fe8f6680100000040c8",  # Zero divisor.
        "4fe87fe8f6620100000540c8c100",  # Connected status outputs unknown.
        "e00040008001c100",  # Compound native edge rung unknown.
        "e0004100c100",  # Edge device bank extrapolation deliberately unsupported.
    ],
)
def test_unconfirmed_encodings_remain_opaque(raw):
    assert decode_network(bytes.fromhex(raw)) is None


def test_arithmetic_not_misrepresented_as_simulated():
    ladder = Ladder(networks=[Network(action=arithmetic())])
    with pytest.raises(ValueError, match="cannot execute"):
        simulate(ladder, [{}], {})
    with pytest.raises(ValueError, match="cannot execute"):
        timed_simulate(ladder, [{}], {}, 10)


@pytest.mark.parametrize("initial_x0", [False, True])
def test_native_edges_have_one_scan_pulses_and_no_memory_helpers(tmp_path, initial_x0):
    ladder = Ladder(
        networks=[
            Network(edge=EdgeContact(kind="rising", input="X0"), coils=[Coil(address=1)]),
            Network(edge=EdgeContact(kind="falling", input="X0"), coils=[Coil(address=3)]),
        ]
    )
    result = Service(tmp_path).generate("edges.ldr", ladder)
    assert result["layout"]["helper_devices"] == []
    states = [True, True, False, False, True]
    expected = [
        (not initial_x0, False),
        (False, False),
        (False, True),
        (False, False),
        (True, False),
    ]
    scans = [{"X0": value} for value in states]
    boolean = simulate(ladder, scans, {"X0": initial_x0})
    timed = timed_simulate(ladder, scans, {"X0": initial_x0}, 10)
    assert [(s["Y1"], s["Y3"]) for s in boolean] == expected
    assert timed == boolean


def test_native_edge_sample_and_exclusivity():
    assert (
        compile_network(
            Network(edge=EdgeContact(kind="falling", input="X1"), coils=[Coil(address=3)])
        ).hex()
        == "e0005001c103"
    )
    with pytest.raises(ValueError):
        EdgeContact(kind="rising", input="X256")
    for extra in ({"empty": True}, {"condition": "X0"}, {"action": arithmetic()}):
        with pytest.raises(ValueError, match="own network"):
            compile_network(
                Network(
                    edge=EdgeContact(kind="rising", input="X0"), coils=[Coil(address=1)], **extra
                )
            )


def test_native_edge_recipes_and_system_do_not_allocate_m():
    controls = [
        ControlSpec(requirement=kind, kind=kind, signal="X0", output=i)
        for i, kind in enumerate(["rising_edge", "falling_edge"])
    ]
    ladder, report = system_ladder(SystemSpec(requirement="edges", controls=controls))
    assert len(ladder.networks) == 2
    assert all(n.edge is not None for n in ladder.networks)
    assert report["resources"]["memory"] == []
    assert ladder.symbols == {}
    for spec in controls:
        gated, _ = control_ladder(spec.model_copy(update={"reset": "X1"}))
        assert all(n.edge is None for n in gated.networks)
        trace = simulate(gated, [{}, {"X0": True, "X1": True}, {"X0": True}, {}], {})
        assert not trace[1][f"Y{spec.output}"]


def test_test7_header_preserved_on_edit_and_unknown_metadata_rejected(tmp_path):
    original = SAMPLE.read_bytes()
    (tmp_path / "test7.ldr").write_bytes(original)
    service = Service(tmp_path)
    changed = service.edit(
        "test7.ldr", "changed.ldr", "replace", 1, Network(action=arithmetic(sb=10)), True
    )
    before = parse(original)
    after = parse(Path(changed["path"]).read_bytes())
    assert after.header == before.header
    assert after.header[176:178] == bytes.fromhex("1040")
    header = bytearray(before.header)
    header[177] = 0x41
    (tmp_path / "unknown.ldr").write_bytes(
        Document(bytes(header), before.records, before.tail).encode()
    )
    assert service.read("unknown.ldr")["ladder"] is None


def test_real_mcp_test7_delivery_and_io_guard(tmp_path):
    (tmp_path / "test7.ldr").write_bytes(SAMPLE.read_bytes())

    async def run():
        params = StdioServerParameters(
            command=sys.executable, args=["-m", "winproladder_mcp.server", "--root", str(tmp_path)]
        )
        async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
            await session.initialize()
            decoded = await session.call_tool("read_ldr", {"path": "test7.ldr"})
            assert not decoded.isError
            ladder = json.loads(decoded.content[0].text)["ladder"]
            arguments = {
                "output_name": "roundtrip.ldr",
                "ladder": ladder,
                "io_contract": {"inputs": ["X0"], "outputs": ["Y1"]},
            }
            generated = await session.call_tool("generate_ldr", arguments)
            assert not generated.isError, generated.content
            resource = await session.read_resource(generated.structuredContent["artifact"]["uri"])
            assert base64.b64decode(resource.contents[0].blob) == SAMPLE.read_bytes()
            arguments.update(output_name="denied.ldr", io_contract={"inputs": [], "outputs": []})
            denied = await session.call_tool("generate_ldr", arguments)
            assert denied.isError
            assert not (tmp_path / "artifacts/denied.ldr").exists()

    asyncio.run(run())
