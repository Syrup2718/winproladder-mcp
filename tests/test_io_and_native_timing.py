"""Physical wiring must follow the request; elapsed time must not invent an input."""

import asyncio
from pathlib import Path

import pytest

from winproladder_mcp.analysis import device_references
from winproladder_mcp.control import ControlSpec, control_ladder
from winproladder_mcp.io_contract import IOContract
from winproladder_mcp.ir import Coil, Ladder, Network, Timer, decode_network
from winproladder_mcp.ldr import parse
from winproladder_mcp.sequence import SequenceSpec, sequence_ladder
from winproladder_mcp.server import build_server
from winproladder_mcp.service import Service
from winproladder_mcp.system import SystemSpec, system_ladder
from winproladder_mcp.timing import timed_simulate


def devices(ladder):
    return set(device_references(list(enumerate(ladder.networks)))["devices"])


@pytest.mark.parametrize("extra", ["X4", "Y74"])
def test_customer_io_contract_rejects_undeclared_reads_and_writes(tmp_path, extra):
    ladder = Ladder(networks=[Network(condition=extra, coils=[Coil(address=71)])])
    with pytest.raises(ValueError, match=f"Undeclared physical I/O: {extra}"):
        Service(tmp_path).generate(
            "rejected.ldr", ladder, io_contract=IOContract(inputs=["X1"], outputs=["Y71"])
        )
    assert not (tmp_path / "artifacts").exists()


def test_false_lowering_never_adds_x0(tmp_path):
    result = Service(tmp_path).generate(
        "false.ldr",
        Ladder(networks=[Network(condition="FALSE", coils=[Coil(address=71)])]),
        io_contract=IOContract(inputs=[], outputs=["Y71"]),
    )
    assert result["io_contract"]["used"] == ["Y71"]
    decoded = Ladder.model_validate(Service(tmp_path).read(result["path"])["ladder"])
    assert devices(decoded) == {"Y71"}
    assert not timed_simulate(decoded, [{}], {"Y71": True}, 10)[0]["Y71"]


def test_no_default_physical_control_assignments():
    with pytest.raises(ValueError, match="signal"):
        ControlSpec(requirement="timer", kind="on_delay")
    spec = ControlSpec(
        requirement="X1 delays Y71", kind="on_delay", signal="X1", output=71, delay_ms=3000
    )
    ladder, _ = control_ladder(spec)
    assert devices(ladder) == {"X1", "Y71", "T0"}
    assert ladder.networks[0].block.preset == 300


def test_system_allocation_does_not_hide_missing_stop_condition():
    spec = SystemSpec(
        requirement="motor",
        controls=[
            {"requirement": "start stop", "kind": "start_stop", "signal": "X1", "output": 71}
        ],
    )
    with pytest.raises(ValueError, match="requires explicit stop"):
        system_ladder(spec)


def test_native_three_and_five_seconds_without_clock_or_snapshot_copies(tmp_path):
    spec = SequenceSpec(
        requirement="X1 starts Y71 3s then Y72 5s",
        start="X1",
        steps=[
            {"name": "pump A", "outputs": [71], "ticks": 30},
            {"name": "pump B", "outputs": [72], "ticks": 50},
        ],
    )
    ladder, design = sequence_ladder(spec)
    assert spec.clock is None and design["effective_timeout_ticks"] == [None, None]
    assert [n.block.preset for n in ladder.networks if isinstance(n.block, Timer)] == [300, 500]
    assert not ({f"M{i}" for i in range(64, 80)} & devices(ladder))
    assert all(d in ladder.symbols for d in devices(ladder) if d.startswith("M"))
    result = Service(tmp_path).generate_design(
        "native.ldr", ladder, design, io_contract=IOContract(inputs=["X1"], outputs=["Y71", "Y72"])
    )
    doc = parse(Path(result["path"]).read_bytes())
    emitted = Ladder(networks=[decode_network(r.payload) for r in reversed(doc.records)])
    trace = timed_simulate(emitted, [{"X1": True}] + [{}] * 80, {}, 100)
    assert [(s["Y71"], s["Y72"]) for s in trace] == (
        [(True, False)] * 30 + [(False, True)] * 50 + [(False, False)]
    )
    assert {d for d in devices(emitted) if d.startswith(("X", "Y"))} == {"X1", "Y71", "Y72"}
    assert all(d in result["symbols"] for d in devices(emitted) if d.startswith("M"))


def test_native_pause_preserves_time_without_silent_external_clock(tmp_path):
    (tmp_path / ".winproladder-policy.json").write_text(
        '{"forbid_m_to_m":true,"allow_function_m_to_m":true}'
    )
    spec = SequenceSpec(
        requirement="pause retains elapsed time",
        start="X1",
        pause="X3",
        steps=[{"name": "pump", "outputs": [71], "ticks": 3}],
    )
    ladder, design = sequence_ladder(spec)
    result = Service(tmp_path).generate_design(
        "paused.ldr",
        ladder,
        design,
        io_contract=IOContract(inputs=["X1", "X3"], outputs=["Y71"]),
    )
    emitted = Ladder.model_validate(Service(tmp_path).read(result["path"])["ladder"])
    trace = timed_simulate(emitted, [{"X1": True}, {}, {"X3": True}, {}, {}], {}, 100)
    assert [s["Y71"] for s in trace] == [True, True, False, True, False]
    assert [s["R2"] for s in trace] == [0, 10, 10, 20, 30]
    assert design["timing_mode"] == "native_accumulative_10ms"
    assert not result["layout"]["helper_devices"]


def test_mcp_generation_requires_separate_customer_io_contract(tmp_path):
    server = build_server(tmp_path)

    async def run():
        tools = {t.name: t for t in await server.list_tools()}
        for name in (
            "generate_ldr",
            "create_ldr",
            "generate_control_ldr",
            "generate_system_ldr",
            "generate_sequence_ldr",
        ):
            assert "io_contract" in tools[name].inputSchema["required"]
        result = await server.call_tool(
            "generate_ldr",
            {
                "output_name": "wrong.ldr",
                "io_contract": {"inputs": ["X1"], "outputs": ["Y71"]},
                "ladder": {"networks": [{"condition": "X4", "coils": [{"address": 71}]}]},
            },
        )
        assert "Undeclared physical I/O" in str(result)

    # FastMCP's direct call API raises on errors (stdio converts them to isError).
    with pytest.raises(Exception, match="Undeclared physical I/O"):
        asyncio.run(run())
    assert not (tmp_path / "artifacts").exists()
