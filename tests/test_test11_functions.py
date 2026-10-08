"""test11 byte oracle: comparison position, grouped M policy, float widths and header."""

from pathlib import Path

import pytest

from winproladder_mcp.analysis import device_references
from winproladder_mcp.architecture import ArchitecturePolicy, enforce_architecture
from winproladder_mcp.io_contract import IOContract
from winproladder_mcp.ir import (
    Coil,
    ComparisonContact,
    FloatOperation,
    Ladder,
    Network,
    Timer,
    compile_network,
    decode_network,
    simulate,
    validation,
)
from winproladder_mcp.layout import lower_ladder, memory_used
from winproladder_mcp.ldr import Document, Record, parse
from winproladder_mcp.registers import encode_comparison_word
from winproladder_mcp.service import Service, default_header, header_profile
from winproladder_mcp.timing import timed_simulate

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "samples/test11.ldr"
PAYLOADS = [
    "f47f00150a0428def47f002208850902f47f002341bc03940101",
    "f47f00180eb00f78f47f002503f40c58f67f0026059400641103",
    "4fe8f47f000000000aca0aca",
    "4fe8f47f00010acc40ce",
    "4fe8f47f000200000ad0000044560ac6",
    "4fe8f47f000300000a1200000a140acc",
    "4fe8f47f000400000a0000000a020a04",
]


def sample():
    return Ladder.model_validate(Service(ROOT).read("samples/test11.ldr")["ladder"])


def test_test11_exact_sample_semantics_and_generation(tmp_path):
    ladder = sample()
    assert ladder.profile == "FBs-32MA-test11"
    ns = ladder.networks
    assert [(c.operation, c.sa, c.sb) for c in ns[0].comparison_chain] == [
        ("eq", "R2", "R5111"),
        ("gt", "WS0", "WM0"),
        ("lt", "D222", "T2"),
    ]
    assert ns[0].coils == [Coil(address=1, mode="reset")]
    assert [(c.operation, c.sa, c.sb) for c in ns[1].comparison_chain] == [
        ("ne", "R600", "R700"),
        ("ge", "T50", "R300"),
        ("le", "C2", 100),
    ]
    assert ns[1].coils == [Coil(address=3, mode="set")]
    assert [
        (n.action.operation, n.action.sa, n.action.sb, n.action.destination) for n in ns[2:]
    ] == [
        ("i_to_f", "R101", None, "R101"),
        ("f_to_i", "R102", None, "D103"),
        ("add", "R104", "D555", "R99"),
        ("sub", "R9", "R10", "R102"),
        ("mul", "R0", "R1", "R2"),
    ]
    assert [compile_network(n).hex() for n in ns] == PAYLOADS
    assert [r.payload.hex() for r in reversed(parse(SAMPLE.read_bytes()).records)] == PAYLOADS
    evidence = validation(ladder)["instruction_evidence"]
    assert len(evidence) == 7 and all(e["status"] == "observed_export" for e in evidence)
    (tmp_path / ".winproladder-policy.json").write_text('{"forbid_m_to_m":true}')
    result = Service(tmp_path).generate(
        "roundtrip.ldr", ladder, io_contract=IOContract(inputs=[], outputs=["Y1", "Y3"])
    )
    assert Path(result["path"]).read_bytes() == SAMPLE.read_bytes()
    assert result["layout"]["helper_devices"] == []
    assert result["architecture"]["valid"]
    rebuilt = Service(tmp_path).read("artifacts/roundtrip.ldr")["ladder"]
    assert Ladder.model_validate(rebuilt) == ladder


def test_float_word_spans_and_overlaps():
    refs = device_references(list(enumerate(sample().networks)))
    assert refs["devices"]["R102"] == {"reads": [3], "writes": [2, 5]}
    assert refs["devices"]["R103"] == {"reads": [3], "writes": [5]}
    assert refs["devices"]["R100"]["writes"] == [4]
    assert refs["devices"]["D556"]["reads"] == [4]
    assert refs["devices"]["R11"]["reads"] == [5]
    assert refs["devices"]["R1"]["reads"] == [6]
    assert refs["devices"]["R2"] == {"reads": [0, 6], "writes": [6]}
    assert refs["devices"]["R3"]["writes"] == [6]
    assert refs["multiple_writers"] == {"R102": [2, 5]}


def test_grouped_m_policy_source_lowered_and_raw_export(tmp_path):
    ladder = sample()
    assert memory_used(ladder) == set(range(16))
    policy = ArchitecturePolicy(forbid_m_to_m=True)
    assert enforce_architecture(ladder, policy)["valid"]
    refs = device_references(list(enumerate(ladder.networks)))["devices"]
    for i in range(16):
        assert refs[f"M{i}"]["reads"] == [0]
    ladder.networks[0].coils = [Coil(device="M", address=100, mode="reset")]
    for variant in [ladder, lower_ladder(ladder)[0]]:
        with pytest.raises(ValueError, match="M-to-M"):
            enforce_architecture(variant, policy)
    (tmp_path / ".winproladder-policy.json").write_text('{"forbid_m_to_m":true}')
    svc = Service(tmp_path)
    with pytest.raises(ValueError, match="M-to-M"):
        svc.generate("denied.ldr", ladder, io_contract=IOContract(inputs=[], outputs=["Y3"]))
    raw = parse(SAMPLE.read_bytes())
    records = list(raw.records)
    records[-1] = Record.create(compile_network(ladder.networks[0]))
    (tmp_path / "forbidden.ldr").write_bytes(
        Document(raw.header, tuple(records), raw.tail).encode()
    )
    with pytest.raises(ValueError, match="M-to-M"):
        svc.export("forbidden.ldr", "denied-export.ldr")
    assert not (tmp_path / "artifacts/denied-export.ldr").exists()


@pytest.mark.parametrize(
    "operation,sa,sb,dest",
    [
        ("i_to_f", "R0", None, "R3839"),
        ("f_to_i", "R3839", None, "R1"),
        ("add", "D4095", "R0", "D0"),
        ("sub", "R0", "D4095", "R1"),
        ("mul", "R0", "R1", "D4095"),
        ("add", "R3840", "R0", "R2"),
        ("i_to_f", "T1", None, "R0"),
        ("f_to_i", "R8071", None, "R0"),
        ("add", "R0", None, "R2"),
        ("i_to_f", "R0", "R1", "R2"),
    ],
)
def test_float_unsupported_or_crossing_operands(operation, sa, sb, dest):
    with pytest.raises(ValueError):
        FloatOperation(operation=operation, sa=sa, sb=sb, destination=dest)


@pytest.mark.parametrize(
    "operation,sa,sb,dest",
    [
        ("i_to_f", "R3839", None, "D3998"),
        ("f_to_i", "R3838", None, "D3999"),
        ("add", "R3838", "D3998", "R3838"),
        ("sub", "R0", "R1", "R2"),
        ("mul", "D0", "D2", "D4"),
    ],
)
def test_valid_float_boundaries_and_inferred_enable(operation, sa, sb, dest):
    n = Network(
        action=FloatOperation(operation=operation, sa=sa, sb=sb, destination=dest, enable="X0")
    )
    assert decode_network(compile_network(n)) == n
    assert (
        validation(Ladder(networks=[n]))["instruction_evidence"][0]["status"] == "inferred_variant"
    )


@pytest.mark.parametrize("name", ["WS1", "WM16", "C3", "R4999", "R8072"])
def test_unconfirmed_compare_banks_not_extrapolated(name):
    with pytest.raises(ValueError):
        encode_comparison_word(name)


@pytest.mark.parametrize(
    "first,later",
    [("gt", "lt"), ("lt", "ge"), ("ge", "le"), ("le", "lt"), ("eq", "eq"), ("ne", "ne")],
)
def test_inferred_comparison_positions_roundtrip(first, later):
    n = Network(
        comparison_chain=[
            ComparisonContact(operation=first, sa="R0", sb="R1"),
            ComparisonContact(operation=later, sa="R2", sb="R3"),
        ],
        coils=[Coil(address=0)],
    )
    report = validation(Ladder(networks=[n]))
    assert report["valid"]
    assert report["instruction_evidence"][0]["status"] == "inferred_variant"
    assert decode_network(compile_network(n)) == n


@pytest.mark.parametrize("value", [-1, 32768, True])
def test_compare_constant_bounds_rejected(value):
    with pytest.raises(ValueError):
        ComparisonContact(operation="le", sa="C2", sb=value)


def test_mixed_logic_rejected_and_io_checked(tmp_path):
    n = sample().networks[0]
    n.condition = "X0"
    assert not validation(Ladder(networks=[n]))["valid"]
    with pytest.raises(ValueError, match="Undeclared physical I/O"):
        Service(tmp_path).generate(
            "denied.ldr", sample(), io_contract=IOContract(inputs=[], outputs=["Y1"])
        )


@pytest.mark.parametrize(
    "raw",
    [
        "4fe8f47f000900000a0000000a020a04",  # unsupported subcode; FDIV known by test12
        "4fe8f47f000000010aca0aca",  # unknown extra word
        "4fe8f47f000200000ad0000144560ac6",
        "4fe8f47f00010acc40ce6ffcc100",  # ERR wiring
        "f47f001b0a0428de0101",  # outside inferred first-position family
        "f47f00150a040902f67f002209020064c100",  # unobserved constant gt
        "f47f00150a0428def47f002208850902f47f002341bc0394",  # missing coil
    ],
)
def test_unknown_extension_forms_stay_opaque(raw):
    assert decode_network(bytes.fromhex(raw)) is None


def test_header_unknown_fields_and_runtime_rejection():
    header = parse(SAMPLE.read_bytes()).header
    assert header == default_header("FBs-32MA-test11")
    assert header[160:168] == b"FBs-32MA" and header[176:178] == bytes.fromhex("1040")
    bad = bytearray(header)
    bad[178] = 1
    assert header_profile(bytes(bad)) is None
    for n in sample().networks:
        for run in [
            lambda n=n: simulate(Ladder(networks=[n]), [{}], {}),
            lambda n=n: timed_simulate(Ladder(networks=[n]), [{}], {}, 10),
        ]:
            with pytest.raises(ValueError, match="cannot execute"):
                run()
    n = Network(block=Timer(address=1, preset=0xF47F, enable="TRUE"))
    assert decode_network(compile_network(n)) == n


@pytest.mark.parametrize(
    "op,first,series",
    [
        ("eq", "0015", "0021"),
        ("gt", "0016", "0022"),
        ("lt", "0017", "0023"),
        ("ne", "0018", "0024"),
        ("ge", "0019", "0025"),
        ("le", "001a", "0026"),
    ],
)
def test_all_comparison_position_probe_bytes(op, first, series):
    # Explicit hypothesis oracle, not an independent WinProLadder export.
    n = Network(
        comparison_chain=[
            ComparisonContact(operation=op, sa="R600", sb="R700"),
            ComparisonContact(operation=op, sa="R600", sb="R700"),
        ],
        coils=[Coil(address=1)],
    )
    expected = bytes.fromhex(f"f47f{first}0eb00f78f47f{series}0eb00f78c101")
    assert compile_network(n) == expected
    assert decode_network(expected) == n


def test_first_constant_comparison_still_rejected():
    n = Network(
        comparison_chain=[ComparisonContact(operation="le", sa="C2", sb=100)],
        coils=[Coil(address=1)],
    )
    assert not validation(Ladder(networks=[n]))["valid"]
