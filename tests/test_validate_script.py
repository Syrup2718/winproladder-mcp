"""The shared validator preserves diagnostics for successful and failed checks."""

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("project_validate", ROOT / "scripts" / "validate.py")
assert SPEC is not None and SPEC.loader is not None
validate = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = validate
SPEC.loader.exec_module(validate)


def execute(tmp_path, steps, *, root=None):
    return validate.execute_validation(
        root or tmp_path,
        "test",
        steps=steps,
        output_root=tmp_path / "validation-results",
        echo=False,
    )


def test_validation_success_writes_machine_readable_result_and_log(tmp_path):
    step = validate.Step("success", (sys.executable, "-c", "print('ok')"))

    code, latest = execute(tmp_path, [step])

    assert code == 0
    result = json.loads(latest.read_text(encoding="utf-8"))
    assert result["passed"]
    assert result["status"] == "passed"
    assert result["passed_steps"] == 1
    log = Path(result["steps"][0]["log"])
    assert log.is_file()
    assert "ok" in log.read_text(encoding="utf-8")


def test_failure_still_runs_later_steps_and_redacts_json_and_logs(tmp_path):
    secret = "should-never-appear"
    steps = [
        validate.Step(
            "failed-step",
            (
                sys.executable,
                "-c",
                f"print('TOKEN={secret}'); raise SystemExit(3)",
            ),
        ),
        validate.Step("later-step", (sys.executable, "-c", "print('still ran')")),
    ]

    code, latest = execute(tmp_path, steps)

    assert code == 1
    result = json.loads(latest.read_text(encoding="utf-8"))
    assert result["status"] == "failed"
    assert result["failed_steps"] == 1
    assert result["passed_steps"] == 1
    assert [step["status"] for step in result["steps"]] == ["failed", "passed"]
    saved = latest.read_text(encoding="utf-8") + "".join(
        Path(step["log"]).read_text(encoding="utf-8") for step in result["steps"]
    )
    assert secret not in saved
    assert "<redacted>" in saved
    assert "still ran" in saved


def test_quick_and_full_plans_contain_the_required_checks(tmp_path):
    quick = validate.validation_steps(ROOT, "quick", tmp_path)
    full = validate.validation_steps(ROOT, "full", tmp_path)

    assert [step.name for step in quick] == ["format", "lint", "mypy", "tests"]
    assert [step.name for step in full] == [
        "format",
        "lint",
        "mypy",
        "tests-with-coverage",
        "mcp-self-check",
        "workspace-audit",
    ]
    coverage = next(step for step in full if step.name == "tests-with-coverage")
    assert "--cov-fail-under=90" in coverage.command
    audit = next(step for step in full if step.name == "workspace-audit")
    assert "--check" in audit.command


def test_ci_uses_shared_validation_once_per_os_and_retains_failure_logs():
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert workflow.count("validation: quick") == 2
    assert workflow.count("validation: full") == 1
    assert "scripts/validate.py --${{ matrix.validation }}" in workflow
    assert "if: failure()" in workflow
    assert "path: tmp/validation" in workflow


def test_isolated_format_error_fails_validation(tmp_path):
    source = tmp_path / "bad_format.py"
    source.write_text("value=  1\n", encoding="utf-8")
    step = validate.Step(
        "format",
        (sys.executable, "-m", "ruff", "format", "--check", str(source)),
    )

    code, latest = execute(tmp_path, [step])

    assert code == 1
    assert json.loads(latest.read_text(encoding="utf-8"))["steps"][0]["status"] == "failed"


def test_isolated_lint_error_fails_validation(tmp_path):
    source = tmp_path / "bad_lint.py"
    source.write_text("import os\n", encoding="utf-8")
    step = validate.Step(
        "lint",
        (sys.executable, "-m", "ruff", "check", str(source)),
    )

    code, latest = execute(tmp_path, [step])

    assert code == 1
    assert json.loads(latest.read_text(encoding="utf-8"))["steps"][0]["status"] == "failed"


def test_isolated_test_failure_fails_validation(tmp_path):
    test_file = tmp_path / "test_deliberate_failure.py"
    test_file.write_text("def test_failure():\n    assert False\n", encoding="utf-8")
    step = validate.Step(
        "tests",
        (sys.executable, "-m", "pytest", "-q", str(test_file)),
    )

    code, latest = execute(tmp_path, [step])

    assert code == 1
    assert json.loads(latest.read_text(encoding="utf-8"))["steps"][0]["status"] == "failed"


def test_isolated_coverage_below_90_fails_validation(tmp_path):
    package = tmp_path / "samplepkg"
    package.mkdir()
    (package / "__init__.py").write_text(
        "def covered():\n"
        "    return 1\n\n"
        "def uncovered(value):\n"
        "    if value > 10:\n"
        "        return value + 1\n"
        "    if value > 5:\n"
        "        return value - 1\n"
        "    return 0\n",
        encoding="utf-8",
    )
    test_file = tmp_path / "test_samplepkg.py"
    test_file.write_text(
        "from samplepkg import covered\n\ndef test_covered():\n    assert covered() == 1\n",
        encoding="utf-8",
    )
    step = validate.Step(
        "tests-with-coverage",
        (
            sys.executable,
            "-m",
            "pytest",
            "-q",
            str(test_file),
            "--cov=samplepkg",
            "--cov-report=term",
            "--cov-fail-under=90",
        ),
    )

    code, latest = execute(tmp_path, [step])

    assert code == 1
    result = json.loads(latest.read_text(encoding="utf-8"))
    assert result["steps"][0]["returncode"] != 0
    log = Path(result["steps"][0]["log"]).read_text(encoding="utf-8").lower()
    assert "required test coverage of 90%" in log
