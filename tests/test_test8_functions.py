"""test8 is the independent oracle that disproves the FUN15/16 probe A."""

import asyncio
import base64
import json
import sys
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from winproladder_mcp.analysis import device_references
from winproladder_mcp.io_contract import IOContract
from winproladder_mcp.ir import (
    Bitwise,
    Coil,
    Compare,
    Counter,
    Ladder,
    Network,
    RegisterStep,
    Timer,
    compile_network,
    decode_network,
    simulate,
    validation,
)
from winproladder_mcp.layout import lower_ladder, memory_used
from winproladder_mcp.service import Service
from winproladder_mcp.timing import timed_simulate

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "samples/test8.ldr"


def test_test8_screenshot_semantics_and_exact_rebuild(tmp_path):
    ladder = Ladder.model_validate(Service(ROOT).read("samples/test8.ldr")["ladder"])
    assert len(ladder.networks) == 7
    assert ladder.profile == "FBs-24MA-test7"
    ns = ladder.networks
    assert ns[0].action == RegisterStep(type="increment", destination="R100", enable="TRUE")
    assert ns[1].action == RegisterStep(type="decrement", destination="D200", enable="TRUE")
    assert ns[2].edge.kind == "falling" and ns[2].edge.input == "X0"
    assert ns[2].coils == [Coil(address=0, mode="reset")]
    assert ns[3].direct_rail and ns[3].coils == [Coil(address=2, inverted=True)]
    assert ns[4].direct_rail and ns[4].coils == [Coil(address=3, mode="set")]
    cmp = ns[5].action
    assert isinstance(cmp, Compare) and (cmp.sa, cmp.sb) == ("R3840", "R3841")
    assert (cmp.equal[0].address, cmp.greater[0].address, cmp.less[0].address) == (100, 101, 102)
    assert ns[6].action == Bitwise(
        operation="and", sa="R3844", sb="D120", destination="D150", enable="TRUE"
    )
    assert compile_network(ns[0]).hex() == "4fe8f4960ac8"
    assert compile_network(ns[1]).hex() == "4fe8f4984190"
    assert compile_network(ns[5]).hex() == "4fe87fe8f46a0100010200006ffcc8746ffdc8756ffec876"
    assert compile_network(ns[6]).hex() == "4fe8f4c6010840f0412c"
    report = validation(ladder)
    assert [e["status"] for e in report["instruction_evidence"]] == ["observed_export"] * 7
    result = Service(tmp_path).generate(
        "rebuilt.ldr", ladder, io_contract=IOContract(inputs=["X0"], outputs=["Y0", "Y2", "Y3"])
    )
    assert Path(result["path"]).read_bytes() == SAMPLE.read_bytes()
    assert result["layout"]["helper_devices"] == []
    refs = device_references(list(enumerate(ns)))["devices"]
    assert refs["R100"] == {"reads": [0], "writes": [0]}
    assert refs["D200"] == {"reads": [1], "writes": [1]}
    assert refs["M100"] == {"reads": [], "writes": [5]}
    assert refs["D120"] == {"reads": [6], "writes": []}
    assert refs["D150"] == {"reads": [], "writes": [6]}
    assert {d for d in refs if d.startswith(("X", "Y", "M"))} == {
        "X0",
        "Y0",
        "Y2",
        "Y3",
        "M100",
        "M101",
        "M102",
    }


def test_cmp_outputs_participate_in_memory_allocation_and_io_contract(tmp_path):
    cmp = Compare(
        sa="R3840",
        sb="R3841",
        equal=[Coil(device="M", address=100)],
        greater=[Coil(device="M", address=101)],
        less=[Coil(device="M", address=102)],
        enable="(X0 OR X1) AND (X2 OR X3)",
    )
    ladder = Ladder(networks=[Network(action=cmp)])
    assert memory_used(ladder) == {100, 101, 102}
    lowered, report = lower_ladder(ladder, reserved=set(range(100)))
    assert report["helper_devices"] == ["M103"]
    assert "M103" in lowered.symbols
    for n in lowered.networks:
        assert compile_network(decode_network(compile_network(n))) == compile_network(n)
    physical = Ladder(networks=[Network(action=Compare(sa="R0", sb="R1", equal=[Coil(address=0)]))])
    with pytest.raises(ValueError):
        Service(tmp_path).generate(
            "denied.ldr", physical, io_contract=IOContract(inputs=[], outputs=[])
        )
    assert not (tmp_path / "artifacts/denied.ldr").exists()


@pytest.mark.parametrize(
    "mode,initial,expected",
    [
        ("set", False, [False, True, True, True]),
        ("reset", True, [True, False, False, False]),
    ],
)
def test_set_reset_hold_when_rung_false(mode, initial, expected):
    ladder = Ladder(networks=[Network(condition="X0", coils=[Coil(address=0, mode=mode)])])
    scans = [{}, {"X0": True}, {}, {}]
    boolean = simulate(ladder, scans, {"Y0": initial})
    assert [s["Y0"] for s in boolean] == expected
    assert [s["Y0"] for s in timed_simulate(ladder, scans, {"Y0": initial}, 10)] == expected


def test_set_reset_scan_order_and_edge_reset():
    ladder = Ladder(
        networks=[
            Network(condition="X0", coils=[Coil(address=0, mode="set")]),
            Network(condition="X1", coils=[Coil(address=0, mode="reset")]),
        ]
    )
    trace = simulate(ladder, [{"X0": True}, {}, {"X0": True, "X1": True}, {}], {})
    assert [s["Y0"] for s in trace] == [True, True, False, False]
    edge = decode_network(bytes.fromhex("e00050000100"))
    trace = simulate(Ladder(networks=[edge]), [{"X0": True}, {"X0": True}, {}, {}], {"Y0": True})
    assert [s["Y0"] for s in trace] == [True, True, False, False]
    rail = Ladder(
        networks=[
            decode_network(bytes.fromhex("4febd102")),
            decode_network(bytes.fromhex("4feb1103")),
        ]
    )
    assert [(s["Y2"], s["Y3"]) for s in simulate(rail, [{}, {}], {"Y2": True})] == [
        (False, True)
    ] * 2


@pytest.mark.parametrize("address,device", [(0, "Y"), (255, "Y"), (0, "M"), (255, "M")])
def test_inferred_set_reset_address_variants(address, device):
    for mode in ["set", "reset"]:
        network = Network(condition="X0", coils=[Coil(device=device, address=address, mode=mode)])
        raw = compile_network(network)
        assert compile_network(decode_network(raw)) == raw


@pytest.mark.parametrize(
    "payload",
    [
        "4fe8f46a40c8",
        "4fe8f46c40ca",  # Disproved old probe, never reinterpret as INC/DEC.
        "4fe8f4970ac8",
        "4fe8f4cb010840f0412c",  # F4CA is XOR since test10; this variant is unknown.
        "4fe87fe8f46a0100010200016ffcc874",  # Unknown reserved word.
        "4fe87fe8f46a0100010200006ffac874",  # Unknown status selector.
        "4fe87fe8f46a0100010200006ffdc8746ffdc875",  # Duplicate status output.
        "4fe87fe8f46a0100010200006ffcc8746ffe",  # Missing output coil.
        "4fe87fe8f46a0100010200006ffcc000",  # X cannot be an output.
    ],
)
def test_unconfirmed_and_malformed_payloads_stay_opaque(payload):
    assert decode_network(bytes.fromhex(payload)) is None


@pytest.mark.parametrize("block_type", [Timer, Counter])
@pytest.mark.parametrize("preset", [0xF46A, 0xF4C6])
def test_opcode_looking_literal_does_not_steal_timer_counter_decode(block_type, preset):
    network = Network(block=block_type(address=1, preset=preset), coils=[Coil(address=0)])
    raw = compile_network(network)
    assert compile_network(decode_network(raw)) == raw


def test_invalid_modes_operands_and_rail_combinations():
    for mode in ["set", "reset"]:
        with pytest.raises(ValueError):
            Coil(address=0, mode=mode, inverted=True)
    with pytest.raises(ValueError):
        RegisterStep(type="increment", destination="R3840")
    with pytest.raises(ValueError):
        Compare(sa="R0", sb=5)
    with pytest.raises(ValueError):
        Compare(sa="R0", sb="R1", equal=[Coil(address=0, mode="set")])
    with pytest.raises(ValueError):
        Bitwise(operation="xor", sa="R0", sb="R1", destination="R2")
    with pytest.raises(ValueError):
        compile_network(Network(condition="X0", direct_rail=True, coils=[Coil(address=0)]))
    with pytest.raises(ValueError):
        compile_network(
            Network(action=RegisterStep(type="increment", destination="R0"), direct_rail=True)
        )


def test_new_register_actions_refuse_boolean_runtime_claims():
    for action in [
        RegisterStep(type="increment", destination="R100"),
        Compare(sa="R0", sb="R1"),
        Bitwise(operation="and", sa="R0", sb="R1", destination="D0"),
    ]:
        ladder = Ladder(networks=[Network(action=action)])
        with pytest.raises(ValueError, match="cannot execute"):
            simulate(ladder, [{}], {})
        with pytest.raises(ValueError, match="cannot execute"):
            timed_simulate(ladder, [{}], {}, 10)


def test_real_mcp_test8_read_generate_download(tmp_path):
    (tmp_path / "test8.ldr").write_bytes(SAMPLE.read_bytes())

    async def run():
        params = StdioServerParameters(
            command=sys.executable, args=["-m", "winproladder_mcp.server", "--root", str(tmp_path)]
        )
        async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("read_ldr", {"path": "test8.ldr"})
            assert not result.isError
            ladder = json.loads(result.content[0].text)["ladder"]
            result = await session.call_tool(
                "generate_ldr",
                {
                    "output_name": "rebuilt.ldr",
                    "ladder": ladder,
                    "io_contract": {"inputs": ["X0"], "outputs": ["Y0", "Y2", "Y3"]},
                },
            )
            assert not result.isError, result.content
            resource = await session.read_resource(result.structuredContent["artifact"]["uri"])
            assert base64.b64decode(resource.contents[0].blob) == SAMPLE.read_bytes()

    asyncio.run(run())
