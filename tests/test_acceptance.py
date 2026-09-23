import pytest

from winproladder_mcp.acceptance import AcceptanceCase, check_acceptance
from winproladder_mcp.design import design_guide
from winproladder_mcp.ir import Coil, Ladder, Network, start_stop
from winproladder_mcp.service import Service


def cases():
    return [AcceptanceCase.model_validate(c) for c in design_guide()["acceptance_example"]]


def test_acceptance_pass_and_generate(tmp_path):
    result = Service(tmp_path).generate("accepted.ldr", start_stop(), cases())
    assert result["acceptance"]["passed"]
    assert result["compiled_acceptance"]["passed"]
    assert result["artifact_validation"]["crc_valid"]
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


@pytest.mark.parametrize("wrong_device", [False, True])
def test_emitted_logic_is_checked_before_write(tmp_path, monkeypatch, wrong_device):
    """A code generation regression must not produce a falsely accepted artifact."""
    from winproladder_mcp import service

    compile_original = service.compile_network

    def wrong_output(network):
        changed = network.model_copy(deep=True)
        changed.coils = [Coil(address=1 if wrong_device else 0, inverted=not wrong_device)]
        return compile_original(changed)

    monkeypatch.setattr(service, "compile_network", wrong_output)
    message = "Undeclared physical I/O: Y1" if wrong_device else "Compiled acceptance failed"
    with pytest.raises(ValueError, match=message):
        Service(tmp_path).generate("wrong.ldr", start_stop(), cases())
    assert not (tmp_path / "artifacts").exists()


def test_acceptance_of_lowered_branch_reads_actual_bytes(tmp_path):
    ladder = Ladder(
        networks=[Network(condition="(X0 OR X1) AND (X2 OR X3)", coils=[Coil(address=0)])]
    )
    expectations = [
        AcceptanceCase.model_validate(
            {
                "name": "both branches required",
                "scans": [
                    {"inputs": {"X0": True}, "expected": {"Y0": False}},
                    {"inputs": {"X0": True, "X3": True}, "expected": {"Y0": True}},
                ],
            }
        )
    ]
    result = Service(tmp_path).generate("branches.ldr", ladder, expectations)
    assert result["layout"]["helper_devices"]
    assert result["compiled_acceptance"]["passed"]
    assert result["artifact_validation"]["decoded_networks"] > 1
