from pathlib import Path

import pytest

from winproladder_mcp.analysis import device_references
from winproladder_mcp.io_contract import IOContract
from winproladder_mcp.ir import (
    FloatOperation,
    Ladder,
    Network,
    compile_network,
    decode_network,
    simulate,
    validation,
)
from winproladder_mcp.service import Service
from winproladder_mcp.timing import timed_simulate

ROOT = Path(__file__).resolve().parents[1]
PAYLOADS = [
    "4fe8f47f00091b5c1b5e",
    "4fe8f47f000a3ffe5ffc",
    "4fe8f57f000b007b0bbc",
    "4fe8f47f000c0bbc",
    "4fe8f47f000d0a00",
    "4fe8f47f000e00000a2c0ac4",
    "4fe8f47f000f00003f7040f6",
]


def sample():
    return Ladder.model_validate(Service(ROOT).read("samples/test13.ldr")["ladder"])


def test_screenshot_and_exact_rebuild(tmp_path):
    ladder = sample()
    assert ladder.profile == "FBs-44MN-test13"
    assert [n.action.operation for n in ladder.networks] == [
        "sin",
        "cos",
        "tan",
        "neg",
        "abs",
        "ln",
        "exp",
    ]
    assert [compile_network(n).hex() for n in ladder.networks] == PAYLOADS
    assert ladder.networks[1].action.sa == "R8071"
    assert ladder.networks[2].action.sa == 123
    assert all(e["status"] == "observed_export" for e in validation(ladder)["instruction_evidence"])
    (tmp_path / ".winproladder-policy.json").write_text('{"forbid_m_to_m":true}')
    result = Service(tmp_path).generate(
        "test13.ldr", ladder, io_contract=IOContract(inputs=[], outputs=[])
    )
    assert Path(result["path"]).read_bytes() == (ROOT / "samples/test13.ldr").read_bytes()
    assert result["architecture"]["valid"] and result["layout"]["helper_devices"] == []
    refs = device_references(list(enumerate(ladder.networks)))["devices"]
    assert refs["R8071"]["reads"] == [1] and "R8072" not in refs
    assert refs["D4095"]["writes"] == [1]
    for r in ["R222", "R223"]:
        assert refs[r]["reads"] == [3] and refs[r]["writes"] == [2, 3]
    for r in ["R0", "R1"]:
        assert refs[r]["reads"] == [4] and refs[r]["writes"] == [4]


@pytest.mark.parametrize("operation", ["sin", "cos", "tan"])
@pytest.mark.parametrize("angle", [-18000, -123, 0, 18000])
def test_signed_angle_constants(operation, angle):
    net = Network(action=FloatOperation(operation=operation, sa=angle, destination="R0"))
    raw = compile_network(net)
    assert raw[2:4].hex() == "f57f"
    assert int.from_bytes(raw[6:8], "big", signed=True) == angle
    assert decode_network(raw) == net


@pytest.mark.parametrize("angle", [-18001, 18001, 1.23, 123.000001, True, float("inf")])
def test_invalid_angle_literals(angle):
    with pytest.raises(ValueError):
        FloatOperation(operation="sin", sa=angle, destination="R0")


@pytest.mark.parametrize("operation", ["neg", "abs"])
def test_in_place_forms_and_boundary(operation):
    for destination in ["R8070", "D4094"]:
        n = Network(action=FloatOperation(operation=operation, destination=destination))
        assert len(compile_network(n)) == 8 and decode_network(compile_network(n)) == n
    for kwargs in [{"sa": "R0"}, {"sb": 1}, {"destination": "R8071"}]:
        with pytest.raises(ValueError):
            FloatOperation.model_validate({"operation": operation, "destination": "R0", **kwargs})


@pytest.mark.parametrize("operation", ["ln", "exp"])
def test_log_exp_limits_and_constant_form(operation):
    n = Network(action=FloatOperation(operation=operation, sa=1.5, destination="D3998"))
    assert decode_network(compile_network(n)) == n
    for kwargs in [{"sa": "D3999"}, {"destination": "D3999"}, {"sa": "D4094"}]:
        with pytest.raises(ValueError, match="D3999"):
            FloatOperation.model_validate(
                {"operation": operation, "sa": "R0", "destination": "R2", **kwargs}
            )
    for value in [0, -1, 1e-100]:
        with pytest.raises(ValueError):
            FloatOperation(operation="ln", sa=value, destination="R0")


@pytest.mark.parametrize(
    "raw",
    [
        "4fe8f67f00091b5c1b5e",  # invalid second-operand flag
        "4fe8f57f000c0bbc",  # in-place constant flag
        "4fe8f47f000c0bbc0bbe",  # extra operand
        "4fe8f47f001500003f7040f6",  # unimplemented neighbor
    ],
)
def test_unknown_forms_stay_opaque(raw):
    assert decode_network(bytes.fromhex(raw)) is None


def test_runtime_still_explicitly_unsupported():
    for net in sample().networks:
        ladder = Ladder(networks=[net])
        with pytest.raises(ValueError, match="cannot execute"):
            simulate(ladder, [{}], {})
        with pytest.raises(ValueError, match="cannot execute"):
            timed_simulate(ladder, [{}], {}, 10)
