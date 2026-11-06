"""The workspace audit separates source defects from disposable local output."""

import json
import subprocess
import sys
from pathlib import Path


def test_audit_classifies_broken_links_by_owning_area(tmp_path):
    docs = tmp_path / "docs"
    archive = tmp_path / "artifacts" / "archive"
    docs.mkdir()
    archive.mkdir(parents=True)
    (docs / "guide.md").write_text("[missing](missing.md)", encoding="utf-8")
    (archive / "README.md").write_text("[old](old.ldr)", encoding="utf-8")
    report = tmp_path / "tmp" / "audit.json"
    script = Path(__file__).resolve().parents[1] / "scripts" / "audit_workspace.py"

    completed = subprocess.run(
        [
            sys.executable,
            str(script),
            "--root",
            str(tmp_path),
            "--output",
            str(report),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    result = json.loads(report.read_text(encoding="utf-8"))
    assert result["source_broken_links"] == [
        {"document": "docs/guide.md", "target": "missing.md"}
    ]
    assert result["local_output_broken_links"] == [
        {"document": "artifacts/archive/README.md", "target": "old.ldr"}
    ]
    summary = json.loads(completed.stdout)
    assert summary["source_broken_links"] == result["source_broken_links"]
    assert summary["local_output_broken_link_count"] == 1

