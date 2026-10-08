from pathlib import Path

import pytest

from winproladder_mcp.analysis import device_references
from winproladder_mcp.architecture import ArchitecturePolicy, enforce_architecture
from winproladder_mcp.io_contract import IOContract
from winproladder_mcp.ir import (
    PID,
    Coil,
    Divide48,
    HighSpeedCounter,
    Ladder,
    Network,
    SumWords,
    Watchdog,
    compile_network,
    decode_network,
    simulate,
    validation,
)
from winproladder_mcp.layout import lower_ladder
from winproladder_mcp.service import Service
from winproladder_mcp.timing import timed_simulate

ROOT = Path(__file__).resolve().parents[1]
PAYLOADS = [
    "4000f5d1005a",
    "48e4f4f2",
    "4fe8f4e50000",
    "4fe8f7e7010000000000",
    "481280077fe86fe8f51700640b900ba40bb80bcc6ffcc1006ffdc1016ffec102",
    "4fe87fe8f46c0a180a2a0a2c6ffcc815",
    "4fe8f5c000160a2c0a2e",
]


def sample():
    return Ladder.model_validate(Service(ROOT).read("samples/test16.ldr")["ladder"])


def test_sample_and_references(tmp_path):
    ladder = sample()
    assert [compile_network(n).hex() for n in ladder.networks] == PAYLOADS
    assert all(e["status"] == "observed_export" for e in validation(ladder)["instruction_evidence"])
    (tmp_path / ".winproladder-policy.json").write_text('{"forbid_m_to_m":true}')
    result = Service(tmp_path).generate(
        "test16.ldr",
        ladder,
        io_contract=IOContract(inputs=["X0", "X7"], outputs=["Y0", "Y1", "Y2"]),
    )
    assert Path(result["path"]).read_bytes() == (ROOT / "samples/test16.ldr").read_bytes()
    assert result["architecture"]["valid"] and not result["layout"]["helper_devices"]
    refs = device_references(list(enumerate(ladder.networks)))["devices"]
    for name in ["R12", "R13", "R14", "R21", "R22", "R23"]:
        assert 5 in refs[name]["reads"]
    assert refs["R24"]["writes"] == [5]
    assert refs["R43"]["reads"] == [6]
    assert refs["R234"]["writes"] == [4] and refs["R234"]["reads"] == [4]
    assert refs["R207"]["reads"] == [4] and refs["R226"]["reads"] == [4]
    assert refs["R4097"]["writes"] == [2]
    assert refs["HSC0.PV"]["writes"] == [3]


@pytest.mark.parametrize("field", ["enable", "bumpless", "direction"])
@pytest.mark.parametrize("pin", ["error", "high", "low"])
def test_pid_policy_all_input_and_status_pins(field, pin):
    action = PID(interval=100, setting="R200", destination="R210", parameters="R220", work="R230")
    setattr(action, field, "M10")
    setattr(action, pin, [Coil(device="M", address=20)])
    n = Network(action=action)
    for candidate in [
        n,
        lower_ladder(Ladder(networks=[n]))[0].networks[0],
        decode_network(compile_network(n)),
    ]:
        with pytest.raises(ValueError, match="M-to-M"):
            enforce_architecture(
                Ladder(networks=[candidate]), ArchitecturePolicy(forbid_m_to_m=True)
            )


@pytest.mark.parametrize("field", ["enable", "unsigned_when"])
@pytest.mark.parametrize("pin", ["zero", "error"])
def test_div48_policy(field, pin):
    a = Divide48(sa="R0", sb="R3", destination="R6")
    setattr(a, field, "M10")
    setattr(a, pin, [Coil(device="M", address=20)])
    n = Network(action=a)
    for candidate in [
        n,
        lower_ladder(Ladder(networks=[n]))[0].networks[0],
        decode_network(compile_network(n)),
    ]:
        with pytest.raises(ValueError, match="M-to-M"):
            enforce_architecture(
                Ladder(networks=[candidate]), ArchitecturePolicy(forbid_m_to_m=True)
            )


@pytest.mark.parametrize("field", ["sa", "sb", "destination"])
def test_div48_full_width(field):
    args = dict(sa="R0", sb="R3", destination="R6")
    args[field] = "D4094"
    with pytest.raises(ValueError, match="span"):
        Divide48(**args)
    args[field] = "D4093"
    n = Network(action=Divide48(**args))
    assert compile_network(decode_network(compile_network(n))) == compile_network(n)


@pytest.mark.parametrize("setting", [0, 49, 51, 121, 900])
def test_wdt_discrete_units(setting):
    with pytest.raises(ValueError):
        Watchdog(type="wdt", setting=setting)


@pytest.mark.parametrize("count", [0, 512])
def test_sum_count_range(count):
    with pytest.raises(ValueError):
        SumWords(source="R0", count=count, destination="R600")


def test_sum_span_boundary():
    with pytest.raises(ValueError, match="span"):
        SumWords(source="D4090", count=7, destination="R0")
    a = SumWords(source="D4090", count=6, destination="R0")
    assert decode_network(compile_network(Network(action=a))).action == a


def test_pid_work_exclusive_and_io(tmp_path):
    ladder = sample()
    ladder.networks.append(Network(action=SumWords(source="R234", count=1, destination="R300")))
    assert not validation(ladder)["valid"]
    assert any("exclusive WR R234" in e for e in validation(ladder)["errors"])
    with pytest.raises(ValueError):
        Service(tmp_path).generate(
            "bad.ldr", sample(), io_contract=IOContract(inputs=["X0"], outputs=["Y0", "Y1", "Y2"])
        )
    assert not (tmp_path / "artifacts/bad.ldr").exists()


@pytest.mark.parametrize("interval", [0, 3001])
def test_pid_interval_bounds(interval):
    with pytest.raises(ValueError):
        PID(interval=interval, setting="R0", destination="R10", parameters="R20", work="R30")


def test_unknown_counter_forms_stay_opaque():
    for raw in ["4fe8f4e50001", "4fe8f7e7000000000000", "4fe8f7e7010000000001"]:
        assert decode_network(bytes.fromhex(raw)) is None
    with pytest.raises(ValueError):
        HighSpeedCounter(type="hsctr", counter="HSC1")


@pytest.mark.parametrize("index", range(7))
def test_no_runtime_simulation_claim(index):
    ladder = sample()
    ladder.networks = [ladder.networks[index]]
    with pytest.raises(ValueError):
        simulate(ladder, [{}], {})
    with pytest.raises(ValueError):
        timed_simulate(ladder, [{}], {}, 10)


def test_changed_pid_inputs_survive_lowering():
    a = PID(
        enable="X0 AND TRUE",
        bumpless="X1 AND TRUE",
        direction="X2 AND TRUE",
        interval=3000,
        setting="D4000",
        destination="D4010",
        parameters="D4020",
        work="D4030",
        error=[Coil(address=0)],
        high=[Coil(address=1)],
        low=[Coil(address=2)],
    )
    lowered, report = lower_ladder(Ladder(networks=[Network(action=a)]))
    assert not report["helper_devices"]
    decoded = decode_network(compile_network(lowered.networks[0])).action
    assert (decoded.enable, decoded.bumpless, decoded.direction) == ("X0", "X1", "X2")
