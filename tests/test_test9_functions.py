"""test9 byte oracles, implicit MC policy dependencies and complete-region delivery."""

import asyncio
import base64
import json
import sys
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from winproladder_mcp.architecture import ArchitecturePolicy, architecture_report
from winproladder_mcp.ir import (
    Differential,
    Ladder,
    MasterControl,
    MasterEnd,
    Network,
    UpDownCounter,
    compile_network,
    decode_network,
    simulate,
    validation,
)
from winproladder_mcp.layout import lower_ladder
from winproladder_mcp.ldr import Document, parse
from winproladder_mcp.service import Service
from winproladder_mcp.timing import timed_simulate

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "samples/test9.ldr"


def sample_ladder():
    return Ladder.model_validate(Service(ROOT).read("samples/test9.ldr")["ladder"])


def test_all_sample9_operands_and_payloads():
    ladder = sample_ladder()
    assert len(ladder.networks) == 8
    ns = ladder.networks
    assert ns[0].action == MasterControl(number=0, enable="M0")
    assert ns[1].branch_encoding == "test9_or"
    assert ns[2].block.preset == 100 and ns[2].block.enable == "NOT T1"
    assert ns[3].action == MasterEnd(number=0)
    assert ns[4].action == MasterControl(number=2, enable="M1")
    assert ns[5].action == Differential(type="difu", destination="M100")
    assert ns[6].action == Differential(type="difd", destination="M101")
    assert ns[7].action == UpDownCounter(cv="R200", preset=100, pulse="X1", up="X2", clear="X3")
    for network, record in zip(ns, reversed(parse(SAMPLE.read_bytes()).records), strict=True):
        assert compile_network(network) == record.payload
    assert compile_network(ns[7]).hex() == "400160026003f10000640b90"
    assert validation(ladder)["errors"] == ["N004: MC 2 missing MCE 2"]


def test_implicit_mc_policy_and_fragment_export_rejected(tmp_path):
    (tmp_path / ".winproladder-policy.json").write_text('{"forbid_m_to_m":true}')
    (tmp_path / "test9.ldr").write_bytes(SAMPLE.read_bytes())
    service = Service(tmp_path)
    ladder = sample_ladder()
    report = service.architecture(ladder, enforce=False)
    assert report["m_to_m_networks"] == [
        {"network": 5, "reads": ["M1"], "writes": ["M100"]},
        {"network": 6, "reads": ["M1"], "writes": ["M101"]},
    ]
    assert service.read("test9.ldr")["ladder"] is not None
    with pytest.raises(ValueError, match="M-to-M"):
        service.export("test9.ldr", "forbidden-copy.ldr")
    assert not (tmp_path / "artifacts/forbidden-copy.ldr").exists()
    # Appending the missing end does not fix the forbidden control dependency.
    ladder.networks.append(Network(action=MasterEnd(number=2)))
    assert validation(ladder)["valid"]
    with pytest.raises(ValueError, match="M-to-M"):
        service.generate("still-forbidden.ldr", ladder)


def test_mc0_exact_region_no_helpers_or_timing_changes(tmp_path):
    (tmp_path / ".winproladder-policy.json").write_text('{"forbid_m_to_m":true}')
    ladder = sample_ladder()
    ladder.networks = ladder.networks[:4]
    source = parse(SAMPLE.read_bytes())
    expected = Document(source.header, source.records[-4:], source.tail).encode()
    emitted = Service(tmp_path).generate("mc0.ldr", ladder)
    assert Path(emitted["path"]).read_bytes() == expected
    assert emitted["architecture"]["valid"]
    assert emitted["layout"]["helper_devices"] == []
    assert emitted["timer_settings"]["timers"][0]["preset_ticks"] == 100
    assert compile_network(ladder.networks[1]).hex() == "4201910061009201e422c100"


def test_mce_ends_implicit_dependency_but_nested_scope_cannot_hide_it():
    ladder = Ladder(
        networks=[
            Network(action=MasterControl(number=0, enable="M0")),
            Network(action=MasterControl(number=2, enable="TRUE")),
            Network(action=Differential(type="difu", destination="M100")),
            Network(action=MasterEnd(number=2)),
            Network(action=MasterEnd(number=0)),
            Network(action=Differential(type="difd", destination="M101")),
        ]
    )
    policy = ArchitecturePolicy(forbid_m_to_m=True)
    assert architecture_report(ladder, policy)["m_to_m_networks"] == [
        {"network": 2, "reads": ["M0"], "writes": ["M100"]}
    ]
    assert not validation(ladder)["valid"]  # Nested generation deliberately unsupported.


@pytest.mark.parametrize(
    "action",
    [
        Differential(type="difu", destination="M100", trigger="M0"),
        Differential(type="difd", destination="M101", trigger="NOT M1"),
    ],
)
def test_pulse_function_cannot_hide_m_to_m(action):
    ladder = Ladder(networks=[Network(action=action)])
    assert not architecture_report(ladder, ArchitecturePolicy(forbid_m_to_m=True))["valid"]


@pytest.mark.parametrize(
    "actions",
    [
        [MasterControl(number=2)],
        [MasterEnd(number=2)],
        [MasterControl(number=0), MasterEnd(number=2)],
        [
            MasterControl(number=0),
            MasterEnd(number=0),
            MasterControl(number=0),
            MasterEnd(number=0),
        ],
    ],
)
def test_incomplete_and_duplicate_master_regions_rejected(actions):
    assert not validation(Ladder(networks=[Network(action=a) for a in actions]))["valid"]


def test_udctr_inferred_inputs_preserve_direct_clear_polarity():
    action = UpDownCounter(
        cv="D200", preset=42, pulse="X1 AND NOT X2", up="FALSE", clear="X3 OR X4"
    )
    ladder, _ = lower_ladder(Ladder(networks=[Network(action=action)]))
    n = ladder.networks[-1]
    decoded = decode_network(compile_network(n))
    assert decoded.action.up == "FALSE"
    assert decoded.action.clear == "(X3 OR X4)"
    assert compile_network(decoded) == compile_network(n)
    for invalid in ["R3840", "D4000"]:
        with pytest.raises(ValueError):
            UpDownCounter(cv=invalid, preset=100, pulse="X1", up="X2", clear="X3")


@pytest.mark.parametrize(
    "payload",
    [
        "4810fc880080",
        "fc890080",
        "4fe8f8f70001",
        "400160026003f10100640b90",
        "400160026003f10000640b916ffcc100",
        "42016100e422c100",
    ],
)
def test_unknown_variants_remain_opaque(payload):
    assert decode_network(bytes.fromhex(payload)) is None


def test_new_actions_do_not_claim_runtime_simulation():
    for ladder in [
        Ladder(networks=sample_ladder().networks[:4]),
        Ladder(networks=sample_ladder().networks[5:]),
    ]:
        with pytest.raises(ValueError, match="cannot execute"):
            simulate(ladder, [{}], {})
        with pytest.raises(ValueError, match="cannot execute"):
            timed_simulate(ladder, [{}], {}, 10)


def test_native_parallel_boolean_truth_table_without_helpers():
    from itertools import product

    n = sample_ladder().networks[1]
    lowered, report = lower_ladder(Ladder(networks=[n]))
    assert report["helper_devices"] == []
    assert compile_network(lowered.networks[0]) == compile_network(n)
    for t, y in product([False, True], repeat=2):
        state = simulate(lowered, [{}], {"T1": t, "Y0": y})[0]
        assert state["Y0"] == (t != y)


def test_real_mcp_strict_policy_delivery_and_rejection(tmp_path):
    (tmp_path / ".winproladder-policy.json").write_text('{"forbid_m_to_m":true}')
    (tmp_path / "test9.ldr").write_bytes(SAMPLE.read_bytes())

    async def run():
        params = StdioServerParameters(
            command=sys.executable, args=["-m", "winproladder_mcp.server", "--root", str(tmp_path)]
        )
        async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
            await session.initialize()
            r = await session.call_tool("read_ldr", {"path": "test9.ldr"})
            ladder = json.loads(r.content[0].text)["ladder"]
            denied = await session.call_tool(
                "generate_ldr",
                {
                    "ladder": ladder,
                    "output_name": "denied.ldr",
                    "io_contract": {"inputs": ["X1", "X2", "X3"], "outputs": ["Y0"]},
                },
            )
            assert denied.isError
            ladder["networks"] = ladder["networks"][:4]
            r = await session.call_tool(
                "generate_ldr",
                {
                    "ladder": ladder,
                    "output_name": "allowed.ldr",
                    "io_contract": {"inputs": [], "outputs": ["Y0"]},
                },
            )
            assert not r.isError, r.content
            downloaded = await session.read_resource(r.structuredContent["artifact"]["uri"])
            doc = parse(base64.b64decode(downloaded.contents[0].blob))
            assert [r.encode() for r in doc.records] == [
                r.encode() for r in parse(SAMPLE.read_bytes()).records[-4:]
            ]

    asyncio.run(run())
