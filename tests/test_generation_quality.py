import pytest

from winproladder_mcp.capabilities import (
    capability_summary,
    instruction_capabilities,
    instruction_families,
)
from winproladder_mcp.control import ControlSpec, control_ladder
from winproladder_mcp.generation_quality import writer_report
from winproladder_mcp.io_contract import IOContract
from winproladder_mcp.ir import Coil, Ladder, Network
from winproladder_mcp.service import Service


def test_instruction_capabilities_are_queryable_without_full_document():
    summary = capability_summary()
    families = instruction_families()
    assert summary["instruction_family_count"] == len(families)
    assert summary["instruction_discovery"]["detail_tool"] == "get_instruction_capabilities"
    assert "schema" not in summary and "design_guide" not in summary
    selected = instruction_capabilities(families[0]["family"])
    assert selected["family"] == families[0]["family"]
    with pytest.raises(ValueError, match="Unknown instruction family"):
        instruction_capabilities("missing")


def test_generation_discloses_missing_acceptance_and_can_require_it(tmp_path):
    service = Service(tmp_path)
    ladder = Ladder(networks=[Network(condition="X0", coils=[Coil(address=0)])])
    contract = IOContract(inputs=["X0"], outputs=["Y0"])
    result = service.generate("candidate.ldr", ladder, io_contract=contract)
    assert result["behavior_verification"] == {
        "level": "not_run",
        "required": False,
        "passed": False,
        "source_checked": False,
        "emitted_checked": False,
        "warning": "No executable acceptance cases were supplied.",
    }
    with pytest.raises(ValueError, match="acceptance cases are required"):
        service.generate(
            "denied.ldr", ladder, io_contract=contract, require_acceptance=True
        )
    assert not (tmp_path / "artifacts/denied.ldr").exists()


def test_strict_writer_policy_rejects_normal_duplicates_but_reports_set_reset(tmp_path):
    duplicate = Ladder(
        networks=[
            Network(condition="X0", coils=[Coil(address=0)]),
            Network(condition="X1", coils=[Coil(address=0)]),
        ]
    )
    with pytest.raises(ValueError, match="Strict single-writer policy failed"):
        writer_report(duplicate, strict=True)
    set_reset = Ladder(
        networks=[
            Network(condition="X0", coils=[Coil(address=0, mode="set")]),
            Network(condition="X1", coils=[Coil(address=0, mode="reset")]),
        ]
    )
    report = writer_report(set_reset, strict=True)
    assert report["valid"]
    assert "Y0" in report["multiple_writers"]
    assert not report["strict_violations"]


@pytest.mark.parametrize("kind", ["off_delay", "pulse"])
def test_stateful_control_recipes_use_distinct_entry_and_updated_status_bits(kind):
    ladder, _ = control_ladder(
        ControlSpec(kind=kind, requirement="single writer", signal="X0", output=0)
    )
    report = writer_report(ladder, strict=True)
    assert report["valid"]
    assert "M0" not in report["multiple_writers"]
    assert ladder.symbols["M3"] == "Control state at scan entry"
