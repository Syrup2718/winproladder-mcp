"""Independent test28 export oracles, hardware footprints and rejected unsafe forms."""

import string
from pathlib import Path

import pytest

from winproladder_mcp.analysis import device_references
from winproladder_mcp.architecture import ArchitecturePolicy, architecture_report
from winproladder_mcp.conversion_functions import decode_ascii, encode_ascii
from winproladder_mcp.instruction_catalog import TEST28_PAYLOADS
from winproladder_mcp.io_contract import IOContract
from winproladder_mcp.ir import (
    Coil,
    Ladder,
    Network,
    ProcessFunction,
    compile_network,
    decode_network,
    simulate,
    validation,
)
from winproladder_mcp.ldr import parse
from winproladder_mcp.logic import parse_expression
from winproladder_mcp.optimize import simplify
from winproladder_mcp.pulse_functions import CONTROLS, STATUS
from winproladder_mcp.service import Service

ROOT = Path(__file__).resolve().parents[1]
POLICY = ArchitecturePolicy(forbid_m_to_m=True, allow_function_m_to_m=True)


def sample():
    return Ladder.model_validate(Service(ROOT).read("samples/test28.ldr")["ladder"])


def test_export_oracles():
    p = sample()
    assert p.profile == "FBs-40MA-test12"
    assert [compile_network(n).hex() for n in p.networks] == list(TEST28_PAYLOADS.values())
    for n in p.networks:
        assert decode_network(compile_network(n)) == n
    assert p.networks[7].action.text == "SYRUP IS CAT"
    assert [p.networks[i].action.target for i in (1, 3, 5)] == ["8"] * 3
    report = validation(p)
    assert not report["valid"]
    errors = " ".join(report["errors"])
    assert all(word in errors for word in ("CALL", "JMP", "PWM", "TDSP"))
    refs = device_references(list(enumerate(p.networks)))
    assert not refs["complete"]
    assert any("TDSP" in x["reason"] for x in refs["reference_uncertainties"])
    assert all(4 in refs["devices"][f"R{i}"]["writes"] for i in (10, 11, 12))
    assert refs["devices"]["X0"]["reads"] == [0, 4]
    assert all(refs["devices"][f"R{i}"]["writes"] == [7] for i in range(1234, 1240))


def test_confirmed_subset_generation(tmp_path):
    (tmp_path / ".winproladder-policy.json").write_text(POLICY.model_dump_json())
    p = sample()
    indexes = [0, 1, 4, 7]
    p.networks = [p.networks[i] for i in indexes]
    r = Service(tmp_path).generate(
        "subset.ldr",
        p,
        io_contract=IOContract(inputs=["X0", "X1", "X2", "X10"], outputs=["Y0", "Y1"]),
    )
    actual = list(reversed(parse(Path(r["path"]).read_bytes()).records))
    assert [x.payload.hex() for x in actual] == [TEST28_PAYLOADS[i] for i in indexes]
    assert not r["layout"]["helper_devices"]
    with pytest.raises(ValueError):
        Service(tmp_path).generate(
            "full.ldr",
            sample(),
            io_contract=IOContract(
                inputs=["X0", "X1", "X2", "X10", "X11", "X12"], outputs=["Y0", "Y1"]
            ),
        )
    assert not (tmp_path / "artifacts/full.ldr").exists()


@pytest.mark.parametrize("index", [0, 2, 4, 6])
@pytest.mark.parametrize(
    "expression", ["TRUE", "FALSE", "M30", "NOT X4", "X4 OR M10", "X4 AND M10"]
)
def test_control_and_status_wiring(index, expression):
    for pin in CONTROLS[sample().networks[index].action.type]:
        n = sample().networks[index]
        setattr(n.action, pin, expression)
        for j, status in enumerate(STATUS[n.action.type]):
            setattr(n.action, status, [Coil(device="M", address=40 + j)])
        decoded = decode_network(compile_network(n))
        assert decoded is not None
        assert compile_network(decoded) == compile_network(n)
        for control in CONTROLS[n.action.type]:
            assert simplify(parse_expression(getattr(decoded.action, control))) == simplify(
                parse_expression(getattr(n.action, control))
            )
        for status in STATUS[n.action.type]:
            assert getattr(decoded.action, status) == getattr(n.action, status)
        assert architecture_report(Ladder(networks=[n]), POLICY)["valid"]


@pytest.mark.parametrize(
    "index,field,value",
    [
        (0, "mode", 1),
        (0, "frequency", "R3840"),
        (0, "forward_output", "X0"),
        (0, "reverse_output", "Y0"),
        (0, "pulse", True),
        (2, "on_ms", -1),
        (2, "period_ms", 0),
        (2, "physical_output", "Y16"),
        (4, "physical_input", "X8"),
        (4, "sample_ms", 0),
        (4, "sample_ms", 32768),
        (4, "destination", "R3838"),
        (6, "source", "R0"),
        (6, "display_number", 2),
        (0, "on_ms", 1),
        (4, "display_on", "X0"),
    ],
)
def test_unencoded_forms(index, field, value):
    data = sample().networks[index].action.model_dump()
    data[field] = value
    with pytest.raises(ValueError):
        ProcessFunction.model_validate(data)


def test_pwm_boundaries_and_single_use(tmp_path):
    n = sample().networks[2]
    for on, period in ((0, 1), (1, 1), (32767, 32767)):
        data = n.action.model_dump()
        data.update(on_ms=on, period_ms=period)
        good = Network(action=ProcessFunction.model_validate(data))
        assert validation(Ladder(networks=[good]))["valid"]
        assert decode_network(compile_network(good)) == good
        assert not validation(Ladder(networks=[good, good]))["valid"]
    assert not validation(Ladder(networks=[sample().networks[0]] * 2))["valid"]
    with pytest.raises(ValueError):
        Service(tmp_path).generate(
            "missing.ldr",
            Ladder(networks=[sample().networks[4]]),
            io_contract=IOContract(inputs=["X10"], outputs=[]),
        )


@pytest.mark.parametrize(
    "text", ["A", "AB", "ABCDEF", "SYRUP IS CAT", "hello123", " A ", "123456789012"]
)
def test_ascii_general_strings(text):
    raw = encode_ascii(text)
    assert decode_ascii(raw) == text
    # Independent bit reconstruction into the original character sequence.
    flags = int.from_bytes(raw[:2], "big")
    pairs = [((raw[2 + 2 * i] << 1) | ((flags >> i) & 1), raw[3 + 2 * i]) for i in range(6)]
    assert bytes(x for pair in pairs for x in pair).rstrip(b"\0") == text.encode()
    a = ProcessFunction(type="ascii_literal", text=text, destination="R100")
    assert len(a.destination_devices()) == (len(text) + 1) // 2
    n = Network(action=a)
    assert decode_network(compile_network(n)) == n


def test_ascii_oracles_and_character_bits():
    assert encode_ascii("ABCDEF").hex() == "0007204221442246000000000000"
    assert encode_ascii("SYRUP IS CAT").hex() == "0029295929552820245310432054"
    for c in string.ascii_letters + string.digits + " ":
        for position in range(12):
            text = "A" * position + c + "B" * (11 - position)
            assert decode_ascii(encode_ascii(text)) == text
    for text in ("", "A" * 13, "中文", "A\x00B", "A\n", "A!"):
        with pytest.raises(ValueError):
            encode_ascii(text)
    for i in range(8):
        assert decode_network(bytes.fromhex(TEST28_PAYLOADS[i])[:-1]) is None


@pytest.mark.parametrize("index", [0, 2, 4, 6, 7])
def test_no_execution_model(index):
    with pytest.raises(ValueError):
        simulate(Ladder(networks=[sample().networks[index]]), [{}], {})
