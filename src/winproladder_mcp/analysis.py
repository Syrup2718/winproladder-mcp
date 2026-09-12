"""Explain supported networks and expose incomplete analysis explicitly."""

from typing import Any

from .ir import BreakLoop, ForLoop, Network, NextLoop, RegisterOr, Timer, network_expression
from .logic import contacts, expression_text, parse_expression


def describe(network: Network) -> str:
    if isinstance(network.action, RegisterOr):
        a = network.action
        return f"16-bit OR R{a.sa}, R{a.sb} -> R{a.destination}; EN={a.enable}"
    if isinstance(network.action, ForLoop):
        return f"FOR {network.action.count} iterations"
    if isinstance(network.action, NextLoop):
        return "NEXT"
    if isinstance(network.action, BreakLoop):
        return f"BREAK; EN={network.action.enable}"
    if network.empty:
        return "Empty network"
    outputs = ", ".join(
        ("inverted " if c.inverted else "") + f"{c.device}{c.address}" for c in network.coils
    )
    if isinstance(network.block, Timer):
        block = network.block
        return (
            f"Timer T{block.address}: base={block.time_base}, "
            f"preset={block.preset}, EN={block.enable}"
            + (f"; TUP -> {outputs}" if outputs else "; TUP unconnected")
        )
    if network.block is not None:
        counter = network.block
        return (
            f"Counter C{counter.address}: preset={counter.preset}, "
            f"PLS={counter.pulse}, CLR={counter.clear}; "
            + (f"CUP -> {outputs}" if outputs else "CUP unconnected")
        )
    return f"{expression_text(network_expression(network))} -> {outputs}"


def device_references(networks: list[tuple[int, Network | None]]) -> dict[str, Any]:
    references: dict[str, dict[str, list[int]]] = {}
    unknown = []
    for index, network in networks:
        if network is None:
            unknown.append(index)
            continue
        if isinstance(network.action, (RegisterOr, BreakLoop)):
            reads = contacts(parse_expression(network.action.enable))
            if isinstance(network.action, RegisterOr):
                reads |= {f"R{network.action.sa}", f"R{network.action.sb}"}
        elif network.action is not None:
            reads = set()
        elif isinstance(network.block, Timer):
            reads = contacts(parse_expression(network.block.enable))
        elif network.block is not None:
            reads = contacts(parse_expression(network.block.pulse)) | contacts(
                parse_expression(network.block.clear)
            )
        else:
            reads = contacts(network_expression(network)) if not network.empty else set()
        writes = {f"{c.device}{c.address}" for c in network.coils}
        if isinstance(network.action, RegisterOr):
            writes.add(f"R{network.action.destination}")
        if network.block is not None:
            family = "T" if isinstance(network.block, Timer) else "C"
            writes.add(f"{family}{network.block.address}")
        for kind, devices in [("reads", reads), ("writes", writes)]:
            for device in sorted(devices):
                references.setdefault(device, {"reads": [], "writes": []})[kind].append(index)
    return {
        "devices": dict(sorted(references.items())),
        "complete": not unknown,
        "opaque_networks": unknown,
        "multiple_writers": {d: v["writes"] for d, v in references.items() if len(v["writes"]) > 1},
        "note": "Decoded networks only. T/C block writes denote device state, not raw registers.",
    }
