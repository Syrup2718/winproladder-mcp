from pathlib import Path

import pytest

from winproladder_mcp.ir import (
    Coil,
    Counter,
    Ladder,
    Network,
    Timer,
    UnsupportedInstruction,
    block_catalog,
    compile_network,
    decode_network,
    simulate,
    start_stop,
    validation,
)
from winproladder_mcp.ldr import parse


@pytest.mark.parametrize("network,payload,source", block_catalog())
def test_block_matches_independent_sample(network: Network, payload: bytes, source: str) -> None:
    filename, number = source.split()
    doc = parse((Path(__file__).parents[1] / "samples" / filename).read_bytes())
    record = list(reversed(doc.records))[int(number[1:])]
    assert compile_network(network) == record.payload == payload
    assert decode_network(record.payload) == network
    report = validation(Ladder(networks=[network]))
    assert report["valid"]
    assert report["import_verified"] is False
    assert report["block_evidence"] == [
        {"network_index": 0, "source": source, "status": "observed_export"}
    ]


@pytest.mark.parametrize(
    "network",
    [
        Network(block=Timer(address=256, preset=257)),
        Network(block=Timer(address=1, preset=256), coils=[Coil(address=256)]),
        Network(block=Counter(address=256, preset=16)),
        Network(block=Counter(address=0, preset=10), condition="X0"),
        Network(block=Timer(address=1, preset=256), empty=True),
    ],
)
def test_invalid_inferred_parameters(network: Network) -> None:
    with pytest.raises(UnsupportedInstruction):
        compile_network(network)


def test_mutated_block_stays_opaque() -> None:
    assert decode_network(bytes.fromhex("4fe8fd8001010393")) is None
    assert decode_network(bytes.fromhex("4fe87fe8f941000b0592")) is None


def test_no_silent_boolean_block_simulation() -> None:
    with pytest.raises(UnsupportedInstruction, match="cannot execute"):
        simulate(Ladder(networks=[Network(block=Timer(address=1, preset=256))]), [{}], {})


@pytest.mark.parametrize("initial,inputs", [({"Y00": True}, [{}]), ({}, [{"X00": True}])])
def test_noncanonical_device_names_rejected(
    initial: dict[str, bool], inputs: list[dict[str, bool]]
) -> None:
    with pytest.raises(ValueError, match="canonical"):
        simulate(start_stop(), inputs, initial)
