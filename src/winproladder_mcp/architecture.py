"""Workspace architecture rules, enforced on source and exact emitted networks."""

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, StrictBool

from .ir import Ladder, MasterControl, MasterEnd, comparison_reads, network_coils
from .layout import expressions
from .logic import contacts

POLICY_FILE = ".winproladder-policy.json"


class ArchitecturePolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    forbid_m_to_m: StrictBool = False


def load_policy(root: Path) -> ArchitecturePolicy:
    """Reload each operation; invalid policy must never silently disable the guard."""
    path = root / POLICY_FILE
    if not path.exists():
        return ArchitecturePolicy()
    if path.stat().st_size > 65536:
        raise ValueError("Architecture policy exceeds 64 KiB")
    return ArchitecturePolicy.model_validate(json.loads(path.read_text(encoding="utf-8")))


def architecture_report(ladder: Ladder, policy: ArchitecturePolicy) -> dict[str, Any]:
    violations = []
    master_reads: dict[int, set[str]] = {}
    for index, network in enumerate(ladder.networks):
        if isinstance(network.action, MasterEnd):
            master_reads.pop(network.action.number, None)
        reads = {
            name for expr in expressions(network) for name in contacts(expr) if name.startswith("M")
        }
        reads |= {name for name in comparison_reads(network) if name.startswith("M")}
        writes = {f"M{c.address}" for c in network_coils(network) if c.device == "M"}
        if isinstance(network.action, MasterControl):
            master_reads[network.action.number] = reads.copy()
        reads |= set().union(*master_reads.values()) if master_reads else set()
        if reads and writes:
            violations.append({"network": index, "reads": sorted(reads), "writes": sorted(writes)})
    return {
        "policy": policy.model_dump(),
        "valid": not policy.forbid_m_to_m or not violations,
        "m_to_m_networks": violations,
        "scope": "M contacts feeding M coils, including block/status outputs, "
        "implicit MC control dependencies and compiler helpers",
    }


def enforce_architecture(ladder: Ladder, policy: ArchitecturePolicy) -> dict[str, Any]:
    report = architecture_report(ladder, policy)
    if not report["valid"]:
        details = "; ".join(
            f"N{v['network']:03d}: {','.join(v['reads'])} -> {','.join(v['writes'])}"
            for v in report["m_to_m_networks"][:12]
        )
        raise ValueError(
            "Workspace architecture forbids M-to-M networks; no file written. "
            + details
            + ". Redesign state with native registers/timers/counters; "
            "do not rename relays or introduce helper chains."
        )
    return report
