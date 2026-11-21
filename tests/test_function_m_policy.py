import json

import pytest

from winproladder_mcp.architecture import ArchitecturePolicy, architecture_report
from winproladder_mcp.io_contract import IOContract
from winproladder_mcp.ir import Ladder, Network, compile_network, decode_network
from winproladder_mcp.layout import lower_ladder
from winproladder_mcp.service import Service

POLICY = ArchitecturePolicy(forbid_m_to_m=True, allow_function_m_to_m=True)


def workspace(path):
    (path / ".winproladder-policy.json").write_text(json.dumps(POLICY.model_dump()))
    return Service(path)


@pytest.mark.parametrize(
    "data",
    [
        {
            "block": {"type": "timer", "address": 1, "preset": 10, "enable": "M0"},
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
        {"action": {"type": "difu", "trigger": "M0", "destination": "M1"}},
        {"action": {"type": "difd", "trigger": "M0", "destination": "M1"}},
    ],
)
def test_native_results_allowed_at_all_stages(tmp_path, data):
    ladder = Ladder(networks=[Network.model_validate(data)])
    lowered = lower_ladder(ladder)[0]
    emitted = Ladder(networks=[decode_network(compile_network(n)) for n in lowered.networks])
    for candidate in [ladder, lowered, emitted]:
        report = architecture_report(candidate, POLICY)
        assert report["valid"] and not report["m_to_m_networks"]
        assert report["allowed_function_m_to_m"][0]["writes"] == ["M1"]
    result = workspace(tmp_path).generate(
        "function.ldr", ladder, io_contract=IOContract(inputs=[], outputs=[])
    )
    assert result["architecture"]["valid"]


@pytest.mark.parametrize("mode", ["normal", "set", "reset"])
def test_plain_copy_still_rejected(tmp_path, mode):
    ladder = Ladder(
        networks=[Network(condition="M0", coils=[{"device": "M", "address": 1, "mode": mode}])]
    )
    with pytest.raises(ValueError, match="M-to-M"):
        workspace(tmp_path).generate("copy.ldr", ladder)
    assert not (tmp_path / "artifacts/copy.ldr").exists()


def test_function_does_not_whitelist_adjacent_copy_or_mc_region(tmp_path):
    service = workspace(tmp_path)
    ladder = Ladder.model_validate(
        {
            "networks": [
                {"action": {"type": "mc", "number": 0, "enable": "M0"}},
                {"condition": "TRUE", "coils": [{"device": "M", "address": 1}]},
                {"action": {"type": "mce", "number": 0}},
            ]
        }
    )
    assert not architecture_report(ladder, POLICY)["valid"]
    with pytest.raises(ValueError, match="M-to-M"):
        service.generate("mc_copy.ldr", ladder)


def test_automatic_helpers_still_rejected(tmp_path):
    ladder = Ladder(
        networks=[
            Network(condition="(M0 AND M1) OR (M2 AND M3)", coils=[{"device": "Y", "address": 0}])
        ]
    )
    with pytest.raises(ValueError, match="M-to-M"):
        workspace(tmp_path).generate("helper.ldr", ladder)


def test_function_and_plain_duplicate_pin_not_exempt():
    n = Network.model_validate(
        {
            "action": {
                "type": "compare",
                "sa": "R0",
                "sb": "R1",
                "enable": "M0",
                "equal": [{"device": "M", "address": 1}],
            },
            "coils": [{"device": "M", "address": 1}],
        }
    )
    assert not architecture_report(Ladder(networks=[n]), POLICY)["valid"]
