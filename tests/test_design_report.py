from winproladder_mcp.control import ControlSpec, control_ladder
from winproladder_mcp.service import Service


def test_preexisting_report_never_overwritten_and_ldr_still_returned(tmp_path):
    service = Service(tmp_path)
    service.output.mkdir()
    report = service.output / "candidate.ldr.design.json"
    report.write_text("user-owned report", encoding="utf-8")
    ladder, design = control_ladder(
        ControlSpec(
            signal="X0",
            output=0,
            stop="X1",
            reset="X2",
            reverse="X3",
            requirement="toggle",
            kind="toggle",
        )
    )
    result = service.generate_design("candidate.ldr", ladder, design)
    assert "design_report_warning" in result
    assert (service.output / "candidate.ldr").is_file()
    assert report.read_text(encoding="utf-8") == "user-owned report"
