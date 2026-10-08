from pathlib import Path

import pytest

from winproladder_mcp.analysis import device_references
from winproladder_mcp.architecture import ArchitecturePolicy, enforce_architecture
from winproladder_mcp.io_contract import IOContract
from winproladder_mcp.ir import (
    Coil,
    FloatOperation,
    ImmediateIO,
    Ladder,
    Network,
    compile_network,
    decode_network,
    simulate,
    validation,
)
from winproladder_mcp.layout import lower_ladder, memory_used
from winproladder_mcp.service import Service
from winproladder_mcp.timing import timed_simulate

ROOT = Path(__file__).resolve().parents[1]
PAYLOADS = [
    "4fe8f47f001000001b5c515a6ffcc827",
    "4fe8f67f001100000f78400000000f8c",
    "4fe8f47f001200000aca0acc",
    "4fe8f47f001300000ace0ad2",
    "4fe8f47f0014000028003ffc",
    "4fe8f4e80000000a",
]


def sample():
    return Ladder.model_validate(Service(ROOT).read("samples/test14.ldr")["ladder"])


def test_exact_export_and_io_contract(tmp_path):
    ladder = sample()
    assert [compile_network(n).hex() for n in ladder.networks] == PAYLOADS
    assert ladder.networks[0].action.error == [Coil(device="M", address=23)]
    assert ladder.networks[1].action.sa == "R700"  # Sy exponent
    assert ladder.networks[1].action.sb == 2.0  # Sx base
    assert ladder.networks[5].action == ImmediateIO(start="X0", count=10)
    assert all(e["status"] == "observed_export" for e in validation(ladder)["instruction_evidence"])
    (tmp_path / ".winproladder-policy.json").write_text('{"forbid_m_to_m":true}')
    svc = Service(tmp_path)
    with pytest.raises(ValueError, match="Undeclared physical I/O"):
        svc.generate("denied.ldr", ladder, io_contract=IOContract(inputs=["X0"], outputs=[]))
    assert not (tmp_path / "artifacts/denied.ldr").exists()
    result = svc.generate(
        "test14.ldr",
        ladder,
        io_contract=IOContract(inputs=[f"X{i}" for i in range(10)], outputs=[]),
    )
    assert Path(result["path"]).read_bytes() == (ROOT / "samples/test14.ldr").read_bytes()
    assert result["layout"]["helper_devices"] == []
    refs = device_references(list(enumerate(ladder.networks)))["devices"]
    assert all(refs[f"X{i}"]["reads"] == [5] for i in range(10))
    assert refs["M23"]["writes"] == [0] and memory_used(ladder) == {23}
    assert refs["R8071"]["writes"] == [4] and refs["R701"]["reads"] == [1]


def test_error_coils_cannot_bypass_policy(tmp_path):
    ladder = sample()
    ladder.networks[0].action.enable = "M0"
    for variant in [
        ladder,
        lower_ladder(ladder)[0],
        Ladder(networks=[decode_network(compile_network(ladder.networks[0]))]),
    ]:
        with pytest.raises(ValueError, match="M-to-M"):
            enforce_architecture(variant, ArchitecturePolicy(forbid_m_to_m=True))
    (tmp_path / ".winproladder-policy.json").write_text('{"forbid_m_to_m":true}')
    with pytest.raises(ValueError, match="M-to-M"):
        Service(tmp_path).generate(
            "bad.ldr",
            ladder,
            io_contract=IOContract(inputs=[f"X{i}" for i in range(10)], outputs=[]),
        )


@pytest.mark.parametrize("operation", ["log", "pow", "asin", "acos", "atan"])
def test_new_operations_variants_and_limits(operation):
    kwargs = {"sb": 2} if operation == "pow" else {}
    net = Network(
        action=FloatOperation(
            operation=operation, sa=0.5, destination="D3998", error=[Coil(address=0)], **kwargs
        )
    )
    assert decode_network(compile_network(net)) == net
    with pytest.raises(ValueError, match="D3999"):
        FloatOperation(operation=operation, sa="R0", destination="D3999", **kwargs)


@pytest.mark.parametrize(
    "operation,value", [("log", 0), ("log", -1), ("asin", -1.1), ("acos", 1.1)]
)
def test_constant_domain(operation, value):
    with pytest.raises(ValueError):
        FloatOperation(operation=operation, sa=value, destination="R0")


@pytest.mark.parametrize("operation", ["add", "div", "sqrt", "ln", "sin"])
def test_inferred_previous_float_err_forms(operation):
    kwargs = {"sb": "R2"} if operation in {"add", "div"} else {}
    n = Network(
        action=FloatOperation(
            operation=operation,
            sa="R0",
            destination="R4",
            error=[Coil(device="M", address=1911)],
            **kwargs,
        )
    )
    assert decode_network(compile_network(n)) == n
    assert (
        validation(Ladder(networks=[n]))["instruction_evidence"][0]["status"] == "inferred_variant"
    )


@pytest.mark.parametrize("kwargs", [{"mode": "set"}, {"mode": "reset"}, {"inverted": True}])
def test_invalid_error_coils(kwargs):
    with pytest.raises(ValueError):
        FloatOperation(
            operation="log", sa="R0", destination="R2", error=[Coil(address=0, **kwargs)]
        )


@pytest.mark.parametrize(
    "start,count", [("X35", 2), ("Y23", 2), ("M0", 1), ("X0", 0), ("X0", 37), ("X0", True)]
)
def test_imdio_limits(start, count):
    with pytest.raises(ValueError):
        ImmediateIO(start=start, count=count)


def test_imdio_output_span():
    n = Network(action=ImmediateIO(start="Y20", count=4, enable="X0"))
    assert decode_network(compile_network(n)) == n
    refs = device_references([(0, n)])["devices"]
    assert all(refs[f"Y{i}"] == {"reads": [0], "writes": [0]} for i in range(20, 24))
    assert refs["X0"]["reads"] == [0]


def test_no_runtime_model_or_unknown_flag_acceptance():
    for n in sample().networks:
        with pytest.raises(ValueError, match="cannot execute"):
            simulate(Ladder(networks=[n]), [{}], {})
        with pytest.raises(ValueError, match="cannot execute"):
            timed_simulate(Ladder(networks=[n]), [{}], {}, 10)
    for raw in [
        PAYLOADS[0].replace("6ffc", "6ffd"),
        "4fe8f4e800000025",
        "4fe8f47f001500001b5c515a",
        "4fe8f57f000c0bbc6ffcc827",
    ]:
        assert decode_network(bytes.fromhex(raw)) is None
