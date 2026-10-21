"""Generation quality gates that are independent from binary instruction codecs."""

from typing import Any

from .acceptance import AcceptanceCase
from .ir import Ladder, network_coils


def writer_report(ladder: Ladder, *, strict: bool = False) -> dict[str, Any]:
    """Classify repeated coil destinations and optionally reject normal-coil writers.

    SET/RESET programs often intentionally share a destination, so strict mode only
    rejects a destination written by a normal coil in more than one network. Function
    status pins are included because they are real writes in the emitted program.
    """
    writers: dict[str, list[dict[str, Any]]] = {}
    for index, network in enumerate(ladder.networks):
        ordinary_ids = {id(coil) for coil in network.coils}
        for coil in network_coils(network):
            name = f"{coil.device}{coil.address}"
            writers.setdefault(name, []).append(
                {
                    "network": index,
                    "mode": coil.mode,
                    "kind": "ordinary_coil" if id(coil) in ordinary_ids else "function_output",
                }
            )

    repeated = {name: rows for name, rows in writers.items() if len(rows) > 1}
    violations = {
        name: rows
        for name, rows in repeated.items()
        if len({row["network"] for row in rows if row["mode"] == "normal"}) > 1
    }
    report = {
        "strict": strict,
        "valid": not strict or not violations,
        "multiple_writers": repeated,
        "strict_violations": violations,
        "rule": (
            "Strict mode rejects normal coils writing the same destination from multiple "
            "networks; SET/RESET-only sharing remains reported but allowed."
        ),
    }
    if strict and violations:
        details = "; ".join(
            f"{name}: {','.join('N{:03d}'.format(row['network']) for row in rows)}"
            for name, rows in list(violations.items())[:12]
        )
        raise ValueError(f"Strict single-writer policy failed; no file written. {details}")
    return report


def behavior_verification(
    acceptance: list[AcceptanceCase] | None,
    source_report: dict[str, Any] | None,
    emitted_report: dict[str, Any] | None,
    *,
    required: bool,
) -> dict[str, Any]:
    """Return an explicit behavior-verification level for every generation result."""
    if acceptance is None:
        return {
            "level": "not_run",
            "required": required,
            "passed": False,
            "source_checked": False,
            "emitted_checked": False,
            "warning": "No executable acceptance cases were supplied.",
        }
    passed = bool(
        source_report
        and emitted_report
        and source_report["passed"]
        and emitted_report["passed"]
    )
    return {
        "level": "source_and_emitted_acceptance",
        "required": required,
        "passed": passed,
        "source_checked": source_report is not None,
        "emitted_checked": emitted_report is not None,
        "case_count": len(acceptance),
        "scope": "Bounded MCP offline model; not WinProLadder GUI or physical PLC verification.",
    }
