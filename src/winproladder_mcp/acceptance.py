"""Executable Boolean and numeric requirements for the compiler, checked before file creation."""

from typing import Annotated, Any

from pydantic import Field

from .ir import Ladder, Model
from .runtime import MODEL_SCOPE, Scalar, check_value, simulate_runtime


class AcceptanceScan(Model):
    inputs: dict[str, Annotated[bool, Field(strict=True)]] = Field(
        default_factory=dict, max_length=256
    )
    expected: dict[str, Scalar] = Field(min_length=1, max_length=128)


class AcceptanceCase(Model):
    name: Annotated[str, Field(min_length=1, max_length=160)]
    initial: dict[str, Scalar] = Field(default_factory=dict, max_length=128)
    scans: list[AcceptanceScan] = Field(min_length=1, max_length=256)
    scan_ms: Annotated[int, Field(strict=True, ge=1, le=60000)] | None = None


def check_acceptance(ladder: Ladder, cases: list[AcceptanceCase]) -> dict[str, Any]:
    if not 1 <= len(cases) <= 32:
        raise ValueError("Provide 1..32 acceptance cases")
    results = []
    for case in cases:
        expected_values = [
            {name: check_value(name, value) for name, value in scan.expected.items()}
            for scan in case.scans
        ]
        trace = simulate_runtime(ladder, [s.inputs for s in case.scans], case.initial, case.scan_ms)
        failures = [
            {
                "scan": index,
                "device": name,
                "expected": expected,
                "actual": state.get(name, 0 if name.startswith(("R", "D")) else False),
            }
            for index, (expected_scan, state) in enumerate(zip(expected_values, trace, strict=True))
            for name, expected in expected_scan.items()
            if state.get(name, 0 if name.startswith(("R", "D")) else False) != expected
        ]
        results.append({"name": case.name, "passed": not failures, "failures": failures})
    return {
        "passed": all(r["passed"] for r in results),
        "cases": results,
        "scope": MODEL_SCOPE,
    }
