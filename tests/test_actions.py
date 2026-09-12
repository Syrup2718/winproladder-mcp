from pathlib import Path

import pytest

from winproladder_mcp.analysis import device_references
from winproladder_mcp.ir import (
    Ladder,
    Network,
    compile_network,
    decode_network,
    simulate,
    validation,
)
from winproladder_mcp.ldr import parse
from winproladder_mcp.service import Service


def test_test5_round_trip():
    raw = (Path(__file__).parents[1] / "samples/test5.ldr").read_bytes()
    document = parse(raw)
    networks = [decode_network(r.payload) for r in reversed(document.records)]
    assert all(n is not None for n in networks)
    ladder = Ladder(networks=networks)
    assert validation(ladder)["valid"]
    for record, network in zip(reversed(document.records), networks, strict=True):
        assert compile_network(network) == record.payload
    refs = device_references(list(enumerate(networks)))
    assert refs["devices"]["R0"]["reads"] == [1]
    assert refs["devices"]["R2"]["writes"] == [1]


def test_generate_test5_identical(tmp_path):
    raw = (Path(__file__).parents[1] / "samples/test5.ldr").read_bytes()
    ladder = Ladder(networks=[decode_network(r.payload) for r in reversed(parse(raw).records)])
    service = Service(tmp_path)
    service.generate("test5-generated.ldr", ladder)
    assert (tmp_path / "artifacts/test5-generated.ldr").read_bytes() == raw
    with pytest.raises(ValueError, match="missing NEXT"):
        service.edit("artifacts/test5-generated.ldr", "invalid.ldr", "delete", 6, None, True)


@pytest.mark.parametrize(
    "actions",
    [
        [{"type": "next"}],
        [{"type": "for", "count": 10}],
        [{"type": "break"}],
        [
            {"type": "for", "count": 2},
            {"type": "for", "count": 3},
            {"type": "next"},
            {"type": "next"},
        ],
    ],
)
def test_invalid_loops(actions):
    assert not validation(Ladder(networks=[Network(action=a) for a in actions]))["valid"]


def test_register_limits_and_action_exclusivity():
    with pytest.raises(ValueError):
        Network(action={"type": "register_or", "sa": 256, "sb": 0, "destination": 1})
    with pytest.raises(ValueError):
        compile_network(Network(action={"type": "next"}, condition="X0"))
    for address in (0, 1, 127, 128, 255):
        network = Network(
            action={"type": "register_or", "sa": address, "sb": 0, "destination": address}
        )
        assert compile_network(decode_network(compile_network(network))) == compile_network(network)


def test_actions_not_boolean_simulated():
    with pytest.raises(ValueError, match="cannot execute"):
        simulate(
            Ladder(
                networks=[
                    Network(action={"type": "register_or", "sa": 0, "sb": 1, "destination": 2})
                ]
            ),
            [{}],
            {},
        )
