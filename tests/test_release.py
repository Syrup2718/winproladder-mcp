"""Run the release verifier as shipped, through the actual MCP subprocess transport."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import get_args

from winproladder_mcp.control import ControlKind


def test_release_verifier_delivers_all_recipes_and_replays_decoded_files(tmp_path):
    script = Path(__file__).resolve().parents[1] / "scripts" / "verify_release.py"
    completed = subprocess.run(
        [sys.executable, str(script), "--root", str(tmp_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=180,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    manifests = list((tmp_path / "artifacts").glob("release-*/manifest.json"))
    assert len(manifests) == 1
    manifest = json.loads(manifests[0].read_text(encoding="utf-8"))
    assert manifest["status"] == "passed"
    cases = manifest["cases"]
    assert len(cases) == 16
    kinds = {
        case["request"]["arguments"]["spec"]["kind"]
        for case in cases
        if case["request"]["tool"] == "generate_control_ldr"
    }
    assert kinds == set(get_args(ControlKind))
    assert {
        "nested_boolean",
        "custom_timer_counter",
        "independent_motors",
        "pause_resume_sequence",
    } <= {case["id"] for case in cases}
    for case in cases:
        assert Path(case["path"]).parent == manifests[0].parent
        assert hashlib.sha256(Path(case["path"]).read_bytes()).hexdigest() == case["sha256"]
        assert case["crc_valid"]
        assert all(scenario["passed"] for scenario in case["decoded_behavior"])
        assert case["delivery"]["resource_read"] and case["delivery"]["embedded_download"]
        assert case["gui_import"] == {"status": "pending", "sha256": case["sha256"]}
    boolean_case = next(case for case in cases if case["id"] == "nested_boolean")
    assert boolean_case["decoded_behavior"][0]["scans"] == 128
    assert all(manifest["rejections"].values())
