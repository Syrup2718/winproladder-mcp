import pytest

from winproladder_mcp.acceptance import AcceptanceCase, check_acceptance
from winproladder_mcp.design import design_guide
from winproladder_mcp.ir import start_stop
from winproladder_mcp.service import Service


def cases():
    return [AcceptanceCase.model_validate(c) for c in design_guide()["acceptance_example"]]


def test_acceptance_pass_and_generate(tmp_path):
    result = Service(tmp_path).generate("accepted.ldr", start_stop(), cases())
    assert result["acceptance"]["passed"]
    assert (tmp_path / "artifacts/accepted.ldr").is_file()


def test_failed_acceptance_never_writes(tmp_path):
    tests = cases()
    tests[0].scans[0].expected["Y0"] = True
    with pytest.raises(ValueError, match="no file written"):
        Service(tmp_path).generate("bad.ldr", start_stop(), tests)
    assert not (tmp_path / "artifacts").exists()


def test_stop_polarity_difference_detected():
    assert not check_acceptance(start_stop(False), cases())["passed"]


@pytest.mark.parametrize("name", ["X00", "R0", "X256", "__import__"])
def test_invalid_expected_device(name):
    tests = cases()
    tests[0].scans[0].expected = {name: False}
    with pytest.raises(ValueError):
        check_acceptance(start_stop(), tests)


def test_empty_cases_not_silent_success():
    with pytest.raises(ValueError):
        check_acceptance(start_stop(), [])
