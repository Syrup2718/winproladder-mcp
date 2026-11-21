"""Run reproducible project checks and retain redacted machine-readable diagnostics."""

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TextIO

SECRET_ASSIGNMENT = re.compile(
    r"(?i)\b(api[_-]?key|authorization|credential|password|secret|token)\b"
    r"(\s*[=:]\s*)([^\s,;]+)"
)
SECRET_JSON_ASSIGNMENT = re.compile(
    r'(?i)("(?:api[_-]?key|authorization|credential|password|secret|token)"\s*:\s*")'
    r'((?:\\.|[^"\\])*)(")'
)
SECRET_TOKEN = re.compile(
    r"(?i)\b(bearer\s+)[A-Za-z0-9._~+/=-]+|"
    r"\b(?:github_pat_|gh[opsu]_|sk-)[A-Za-z0-9_-]{8,}"
)


@dataclass(frozen=True)
class Step:
    name: str
    command: tuple[str, ...]


def redact(text: str) -> str:
    """Remove common credential forms without recording environment variables."""

    text = SECRET_JSON_ASSIGNMENT.sub(r"\1<redacted>\3", text)
    text = SECRET_ASSIGNMENT.sub(r"\1\2<redacted>", text)

    def replace_token(match: re.Match[str]) -> str:
        prefix = match.group(1)
        return f"{prefix}<redacted>" if prefix else "<redacted>"

    return SECRET_TOKEN.sub(replace_token, text)


def _timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds")


def _write_json(path: Path, payload: dict[str, object]) -> None:
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    with temporary.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    temporary.replace(path)


def _display_command(command: tuple[str, ...]) -> str:
    return redact(shlex.join(command))


def _run_step(step: Step, root: Path, log: TextIO, *, echo: bool) -> int:
    command_text = _display_command(step.command)
    log.write(f"COMMAND: {command_text}\n")
    log.flush()
    if echo:
        print(f"[{step.name}] {command_text}", flush=True)
    try:
        process = subprocess.Popen(
            step.command,
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )
    except OSError as error:
        message = redact(f"Unable to start command: {error}\n")
        log.write(message)
        if echo:
            print(message, end="", file=sys.stderr, flush=True)
        return 127
    assert process.stdout is not None
    for line in process.stdout:
        safe_line = redact(line)
        log.write(safe_line)
        log.flush()
        if echo:
            print(safe_line, end="", flush=True)
    return process.wait()


def validation_steps(root: Path, mode: str, run_dir: Path) -> list[Step]:
    python = sys.executable
    steps = [
        Step("format", (python, "-m", "ruff", "format", "--check", ".")),
        Step("lint", (python, "-m", "ruff", "check", ".")),
        Step("mypy", (python, "-m", "mypy")),
    ]
    if mode == "quick":
        # No reliable affected-test selector exists, so quick still runs the full suite.
        steps.append(Step("tests", (python, "-m", "pytest", "-q")))
        return steps
    if mode != "full":
        raise ValueError(f"Unknown validation mode: {mode}")
    coverage_report = run_dir / "coverage.json"
    audit_report = run_dir / "workspace-audit.json"
    steps.extend(
        [
            Step(
                "tests-with-coverage",
                (
                    python,
                    "-m",
                    "pytest",
                    "-q",
                    "--cov=winproladder_mcp",
                    "--cov-report=term-missing",
                    f"--cov-report=json:{coverage_report}",
                    "--cov-fail-under=90",
                ),
            ),
            Step(
                "mcp-self-check",
                (python, "-m", "winproladder_mcp.setup", "check"),
            ),
            Step(
                "workspace-audit",
                (
                    python,
                    str(root / "scripts" / "audit_workspace.py"),
                    "--root",
                    str(root),
                    "--output",
                    str(audit_report),
                    "--check",
                ),
            ),
        ]
    )
    return steps


def execute_validation(
    root: Path,
    mode: str,
    *,
    steps: list[Step] | None = None,
    output_root: Path | None = None,
    echo: bool = True,
) -> tuple[int, Path]:
    """Execute every step, persist after each one, and return exit code plus latest JSON."""

    root = root.resolve(strict=True)
    validation_root = (output_root or root / "tmp" / "validation").resolve()
    validation_root.mkdir(parents=True, exist_ok=True)
    run_id = f"{datetime.now(UTC):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}"
    run_dir = validation_root / run_id
    run_dir.mkdir()
    latest = validation_root / "latest.json"
    selected_steps = steps if steps is not None else validation_steps(root, mode, run_dir)
    report: dict[str, object] = {
        "schema_version": 1,
        "run_id": run_id,
        "mode": mode,
        "root": str(root),
        "started_at": _timestamp(),
        "finished_at": None,
        "status": "running",
        "passed": False,
        "steps": [],
        "run_directory": str(run_dir),
        "security": (
            "Logs redact common credential assignments and token forms; "
            "environment values are not listed."
        ),
    }
    _write_json(latest, report)
    results: list[dict[str, object]] = []
    for index, step in enumerate(selected_steps, start=1):
        safe_name = re.sub(r"[^a-z0-9-]+", "-", step.name.lower()).strip("-") or "step"
        log_path = run_dir / f"{index:02d}-{safe_name}.log"
        started = _timestamp()
        before = time.perf_counter()
        with log_path.open("x", encoding="utf-8") as log:
            returncode = _run_step(step, root, log, echo=echo)
        duration = round(time.perf_counter() - before, 3)
        result = {
            "name": step.name,
            "command": _display_command(step.command),
            "status": "passed" if returncode == 0 else "failed",
            "returncode": returncode,
            "started_at": started,
            "duration_seconds": duration,
            "log": str(log_path),
        }
        results.append(result)
        report["steps"] = results
        _write_json(latest, report)
        if echo:
            print(
                f"[{step.name}] {'PASS' if returncode == 0 else 'FAIL'} "
                f"({duration:.3f}s) log={log_path}",
                flush=True,
            )
    passed = all(item["returncode"] == 0 for item in results)
    report.update(
        {
            "finished_at": _timestamp(),
            "status": "passed" if passed else "failed",
            "passed": passed,
            "passed_steps": sum(item["returncode"] == 0 for item in results),
            "failed_steps": sum(item["returncode"] != 0 for item in results),
        }
    )
    _write_json(latest, report)
    if echo:
        print(f"Validation {'passed' if passed else 'failed'}; report={latest}", flush=True)
    return (0 if passed else 1), latest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--quick", action="store_true", help="Format, lint, mypy, and all tests")
    modes.add_argument(
        "--full",
        action="store_true",
        help="Basic checks, full coverage gate, MCP self-check, and workspace audit",
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    code, _ = execute_validation(root, "full" if args.full else "quick")
    raise SystemExit(code)


if __name__ == "__main__":
    main()
