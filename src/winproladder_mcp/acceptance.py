"""Executable requirements for the Boolean compiler, checked before file creation."""

from typing import Annotated, Any

from pydantic import Field

from .ir import Ladder, Model, simulate
from .logic import bit_address
from .timing import timed_simulate


class AcceptanceScan(Model):
    inputs: dict[str, bool] = Field(default_factory=dict, max_length=256)
    expected: dict[str, bool] = Field(min_length=1, max_length=128)


class AcceptanceCase(Model):
    name: Annotated[str, Field(min_length=1, max_length=160)]
    initial: dict[str, bool] = Field(default_factory=dict, max_length=128)
    scans: list[AcceptanceScan] = Field(min_length=1, max_length=256)
    scan_ms: Annotated[int, Field(strict=True, ge=1, le=60000)] | None = None


def check_acceptance(ladder: Ladder, cases: list[AcceptanceCase]) -> dict[str, Any]:
    if not 1 <= len(cases) <= 32:
        raise ValueError("Provide 1..32 acceptance cases")
    results = []
    for case in cases:
        for scan in case.scans:
            for name in scan.expected:
                bit_address(name)
                if name != f"{name[0]}{int(name[1:])}":
                    raise ValueError("Expected devices must use canonical names")
        snapshots = [s.inputs for s in case.scans]
        trace = (
            simulate(ladder, snapshots, case.initial)
            if case.scan_ms is None
            else timed_simulate(ladder, snapshots, case.initial, case.scan_ms)
        )
        failures = [
            {"scan": index, "device": name, "expected": expected, "actual": state.get(name, False)}
            for index, (scan, state) in enumerate(zip(case.scans, trace, strict=True))
            for name, expected in scan.expected.items()
            if state.get(name, False) != expected
        ]
        results.append({"name": case.name, "passed": not failures, "failures": failures})
    return {
        "passed": all(r["passed"] for r in results),
        "cases": results,
        "scope": "Offline scan model; timed cases assume default T0..T49 .01s configuration. "
        "Not WinProLadder import or PLC runtime validation",
    }
