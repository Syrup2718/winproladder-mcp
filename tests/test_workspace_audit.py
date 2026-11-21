"""The workspace audit separates source defects from disposable local output."""

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_workspace.py"


def run_audit(root, report, *, check=False):
    command = [
        sys.executable,
        str(SCRIPT),
        "--root",
        str(root),
        "--output",
        str(report),
    ]
    if check:
        command.append("--check")
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )


def test_audit_classifies_broken_links_by_owning_area(tmp_path):
    docs = tmp_path / "docs"
    archive = tmp_path / "artifacts" / "archive"
    docs.mkdir()
    archive.mkdir(parents=True)
    (docs / "guide.md").write_text("[missing](missing.md)", encoding="utf-8")
    (archive / "README.md").write_text("[old](old.ldr)", encoding="utf-8")
    report = tmp_path / "tmp" / "audit.json"
    completed = run_audit(tmp_path, report)

    assert completed.returncode == 0, completed.stdout + completed.stderr
    result = json.loads(report.read_text(encoding="utf-8"))
    assert result["source_broken_links"] == [{"document": "docs/guide.md", "target": "missing.md"}]
    assert result["local_output_broken_links"] == [
        {"document": "artifacts/archive/README.md", "target": "old.ldr"}
    ]
    summary = json.loads(completed.stdout)
    assert summary["source_broken_links"] == result["source_broken_links"]
    assert summary["local_output_broken_link_count"] == 1


def test_audit_check_fails_for_source_broken_link_after_writing_report(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "guide.md").write_text("[missing](missing.md)", encoding="utf-8")
    report = tmp_path / "tmp" / "source-check.json"

    completed = run_audit(tmp_path, report, check=True)

    assert completed.returncode == 1
    result = json.loads(report.read_text(encoding="utf-8"))
    assert result["source_broken_links"] == [{"document": "docs/guide.md", "target": "missing.md"}]
    assert not json.loads(completed.stdout)["passed"]


def test_audit_check_ignores_broken_link_in_local_artifact(tmp_path):
    archive = tmp_path / "artifacts" / "archive"
    archive.mkdir(parents=True)
    (archive / "README.md").write_text("[old](old.ldr)", encoding="utf-8")
    report = tmp_path / "tmp" / "artifact-check.json"

    completed = run_audit(tmp_path, report, check=True)

    assert completed.returncode == 0, completed.stdout + completed.stderr
    result = json.loads(report.read_text(encoding="utf-8"))
    assert result["source_broken_links"] == []
    assert result["local_output_broken_links"] == [
        {"document": "artifacts/archive/README.md", "target": "old.ldr"}
    ]
    assert json.loads(completed.stdout)["passed"]
