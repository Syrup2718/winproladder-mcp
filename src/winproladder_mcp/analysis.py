"""Explain supported networks and expose incomplete analysis explicitly."""

from typing import Any

from .ir import (
    BreakLoop,
    ForLoop,
    LinearConversion,
    Network,
    NextLoop,
    RegisterOr,
    Timer,
    network_expression,
)
from .logic import contacts, expression_text, parse_expression
from .registers import register_span


def describe(network: Network) -> str:
    if isinstance(network.action, LinearConversion):
        conversion = network.action
        return (
            f"FUN33 LCNV: Md={conversion.mode}, S={conversion.source}, Ts={conversion.table}, "
            f"D={conversion.destination}, L={conversion.length}; "
            f"table_words={conversion.table_words}; EN={conversion.enable}"
        )
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
            f"Timer T{block.address}: assumed base={block.time_base}, "
            f"preset={block.preset} ticks, "
            + (f"nominal_duration={block.preset * 10} ms, " if block.address < 50 else "")
            + f"EN={block.enable}"
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


def timer_settings(networks: list[tuple[int, Network | None]]) -> dict[str, Any]:
    """Keep preset counts separate from milliseconds and disclose the profile assumption.

    The supported LDR timer payload contains a preset, not a verified destination
    project's timer allocation. Do not present inferred timing as measured runtime.
    """
    return {
        "configuration_verified": False,
        "scope": "Assumes destination T0..T49 use .01S (10 ms) time base; "
        "destination project configuration is not verified from this LDR.",
        "formula": "nominal_duration_ms = preset_ticks * time_base_ms",
        "timers": [
            {
                "network_index": index,
                "device": f"T{network.block.address}",
                "preset_ticks": network.block.preset,
                "assumed_time_base_ms": 10 if network.block.address < 50 else None,
                "nominal_duration_ms": network.block.preset * 10
                if network.block.address < 50
                else None,
            }
            for index, network in networks
            if network is not None and isinstance(network.block, Timer)
        ],
    }


def device_references(networks: list[tuple[int, Network | None]]) -> dict[str, Any]:
    references: dict[str, dict[str, list[int]]] = {}
    unknown = []
    for index, network in networks:
        if network is None:
            unknown.append(index)
            continue
        if isinstance(network.action, (RegisterOr, BreakLoop, LinearConversion)):
            reads = contacts(parse_expression(network.action.enable))
            if isinstance(network.action, RegisterOr):
                reads |= {f"R{network.action.sa}", f"R{network.action.sb}"}
            elif isinstance(network.action, LinearConversion):
                reads |= register_span(network.action.source, network.action.length)
                reads |= register_span(network.action.table, network.action.table_words)
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
        elif isinstance(network.action, LinearConversion):
            writes |= register_span(
                network.action.destination, network.action.length, writable=True
            )
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
