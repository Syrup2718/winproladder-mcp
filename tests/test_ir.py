from itertools import product
from pathlib import Path

import pytest
from pydantic import ValidationError

from winproladder_mcp.ir import (
    Coil,
    Contact,
    Ladder,
    Network,
    Step,
    UnsupportedInstruction,
    compile_network,
    decode_network,
    simulate,
    start_stop,
    validation,
)
from winproladder_mcp.ldr import parse


def test_exact_import_verified_start_stop() -> None:
    ladder = start_stop()
    assert compile_network(ladder.networks[0]) == bytes.fromhex("4100a0009001c100")
    assert validation(ladder)["import_verified"] is True
    assert validation(start_stop(False))["import_verified"] is False
    for start, stop, previous in product([False, True], repeat=3):
        value = simulate(ladder, [{"X0": start, "X1": stop}], {"Y0": previous})[0]["Y0"]
        assert value == (not stop and (start or previous))
        if stop:
            assert value is False


def test_start_stop_scan_sequence() -> None:
    scans = [
        (False, False),
        (True, False),
        (False, False),
        (False, True),
        (False, False),
        (True, True),
    ]
    outputs = [
        state["Y0"]
        for state in simulate(
            start_stop(), [{"X0": start, "X1": stop} for start, stop in scans], {}
        )
    ]
    assert outputs == [False, True, True, False, False, False]


def test_decoded_subset_reencodes_exactly() -> None:
    count = 0
    for path in (Path(__file__).parents[1] / "samples").glob("*.ldr"):
        for record in parse(path.read_bytes()).records:
            network = decode_network(record.payload)
            if network is not None:
                count += 1
                assert compile_network(network) == record.payload
    assert count >= 20


@pytest.mark.parametrize(
    "payload", ["e0014000c101", "4fe8fd8101010392", "50028003f102", "40006001e200c100", "41"]
)
def test_unsupported_stays_whole_opaque(payload: str) -> None:
    assert decode_network(bytes.fromhex(payload)) is None


def test_invalid_ir_and_addresses() -> None:
    with pytest.raises(ValidationError):
        Contact(device="X", address=True)
    with pytest.raises(ValidationError):
        Ladder.model_validate({"networks": [], "raw": "00"})
    for network in [
        Network(),
        Network(empty=True, coils=[Coil(address=0)]),
        Network(
            steps=[Step(op="and", contact=Contact(device="X", address=0))], coils=[Coil(address=0)]
        ),
        Network(
            steps=[Step(op="load", contact=Contact(device="M", address=256))],
            coils=[Coil(address=0)],
        ),
    ]:
        with pytest.raises(UnsupportedInstruction):
            compile_network(network)
    ladder = start_stop()
    ladder.networks[0].steps[1].contact.address = 256
    assert validation(ladder)["valid"] is False
