"""Explain supported networks and expose incomplete analysis explicitly."""

from typing import Any

from .floating import float_source_reads, float_span
from .ir import (
    Arithmetic,
    Bitwise,
    BreakLoop,
    Compare,
    Differential,
    ExclusiveLogic,
    FloatCompare,
    FloatOperation,
    FloatZoneCompare,
    ForLoop,
    ImmediateIO,
    LinearConversion,
    MasterControl,
    MasterEnd,
    Network,
    NextLoop,
    RegisterOr,
    RegisterStep,
    Timer,
    UpDownCounter,
    WordConversion,
    ZoneCompare,
    comparison_reads,
    network_coils,
    network_expression,
)
from .logic import contacts, expression_text, parse_expression
from .registers import register_span, word_references


def describe(network: Network) -> str:
    if isinstance(network.action, ImmediateIO):
        immediate = network.action
        return (
            f"FUN74 IMDIO: refresh {immediate.start} + {immediate.count} points; "
            f"EN={immediate.enable}"
        )
    if isinstance(network.action, FloatCompare):
        fc = network.action
        return f"FUN206 FCMP: Sa={fc.sa}, Sb={fc.sb}; EN={fc.enable}"
    if isinstance(network.action, FloatZoneCompare):
        fz = network.action
        return f"FUN207 FZCP: S={fz.source}, Su={fz.upper}, Sl={fz.lower}; EN={fz.enable}"
    if network.comparison_chain:
        conditions = " AND ".join(f"{c.sa} {c.operation} {c.sb}" for c in network.comparison_chain)
        outputs = ", ".join(f"{c.mode} {c.device}{c.address}" for c in network.coils)
        return f"Signed 16-bit comparison contacts: {conditions} -> {outputs}"
    if isinstance(network.action, FloatOperation):
        fp = network.action
        if fp.operation == "pow":
            return (
                f"FUN217 FPOW: Sx(base)={fp.sb} ** Sy(exponent)={fp.sa} -> {fp.destination}; "
                f"EN={fp.enable}; ERR={fp.error}"
            )
        if fp.operation in {"neg", "abs"}:
            return (
                f"Float {fp.operation}: in-place read/write {fp.destination} (2 words); "
                f"EN={fp.enable}"
            )
        return (
            f"Float {fp.operation}: Sa={fp.sa}, Sb={fp.sb}, D={fp.destination}; "
            f"source_words={fp.source_words}, destination_words={fp.destination_words}; "
            f"EN={fp.enable}"
        )
    if isinstance(network.action, ExclusiveLogic):
        word_action = network.action
        return (
            f"FUN{35 if word_action.operation == 'xor' else 36} {word_action.operation.upper()}: "
            + (
                f"Sa={word_action.sa}, Sb={word_action.sb}, D={word_action.destination}; "
                f"EN={word_action.enable}"
            )
        )
    if isinstance(network.action, WordConversion):
        conversion_action = network.action
        return (
            f"{conversion_action.operation}: S={conversion_action.source}, "
            f"D={conversion_action.destination}; EN={conversion_action.enable}"
        )
    if isinstance(network.action, ZoneCompare):
        z = network.action
        return f"FUN37 ZNCMP: S={z.source}, Su={z.upper}, Sl={z.lower}; EN={z.enable}; " + (
            f"INZ={[f'{c.device}{c.address}' for c in z.within]}, "
            f"S>U={[f'{c.device}{c.address}' for c in z.above]}, "
            f"S<L={[f'{c.device}{c.address}' for c in z.below]}"
        )
    if isinstance(network.action, MasterControl):
        return f"FUN00 MC {network.action.number}; EN/={network.action.enable}; 1 permits execution"
    if isinstance(network.action, MasterEnd):
        return f"FUN01 MCE {network.action.number}"
    if isinstance(network.action, Differential):
        pulse = network.action
        return f"{pulse.type.upper()}: TG={pulse.trigger} -> {pulse.destination}"
    if isinstance(network.action, UpDownCounter):
        u = network.action
        return f"07P.UDCTR: CV={u.cv}, PV={u.preset}; PLS={u.pulse}, U/D={u.up}, CLR={u.clear}"
    if isinstance(network.action, RegisterStep):
        step = network.action
        return (
            f"FUN{15 if step.type == 'increment' else 16} {step.type}: "
            f"D={step.destination}; EN={step.enable}"
        )
    if isinstance(network.action, Bitwise):
        bitwise = network.action
        return (
            f"16-bit {bitwise.operation.upper()}: Sa={bitwise.sa}, Sb={bitwise.sb}, "
            f"D={bitwise.destination}; EN={bitwise.enable}"
        )
    if isinstance(network.action, Compare):
        compare = network.action
        outputs = "; ".join(
            f"{label} -> {','.join(f'{c.device}{c.address}' for c in coils) or 'unconnected'}"
            for label, coils in [
                ("a=b", compare.equal),
                ("a>b", compare.greater),
                ("a<b", compare.less),
            ]
        )
        return (
            f"FUN17 CMP: Sa={compare.sa}, Sb={compare.sb}; EN={compare.enable}; "
            f"U/S={compare.unsigned_when}; {outputs}"
        )
    if isinstance(network.action, Arithmetic):
        arithmetic = network.action
        writes = sorted(register_span(arithmetic.destination, arithmetic.destination_words))
        return (
            f"16-bit {arithmetic.operation.upper()}: Sa={arithmetic.sa}, Sb={arithmetic.sb}, "
            f"D={arithmetic.destination}; writes={','.join(writes)}; "
            f"EN={arithmetic.enable}, U/S={arithmetic.unsigned_when} (FALSE=signed, TRUE=unsigned)"
        )
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
        (c.mode + " " if c.mode != "normal" else "inverted " if c.inverted else "")
        + f"{c.device}{c.address}"
        for c in network.coils
    )
    if network.edge is not None:
        return f"Native {network.edge.kind} edge {network.edge.input} -> {outputs}"
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
        if isinstance(
            network.action,
            (
                RegisterOr,
                BreakLoop,
                LinearConversion,
                Arithmetic,
                RegisterStep,
                Bitwise,
                Compare,
                MasterControl,
                FloatOperation,
                ImmediateIO,
                FloatCompare,
                FloatZoneCompare,
                ExclusiveLogic,
                WordConversion,
                ZoneCompare,
            ),
        ):
            reads = contacts(parse_expression(network.action.enable))
            if isinstance(network.action, ImmediateIO):
                reads |= network.action.devices()
            if isinstance(network.action, FloatOperation):
                if network.action.operation in {"neg", "abs"}:
                    reads |= float_span(network.action.destination, 2)
                if isinstance(network.action.sa, str):
                    reads |= float_span(network.action.sa, network.action.source_words)
                if network.action.sb is not None:
                    reads |= float_source_reads(network.action.sb)
            elif isinstance(network.action, FloatCompare):
                reads |= float_source_reads(network.action.sa) | float_source_reads(
                    network.action.sb
                )
            elif isinstance(network.action, FloatZoneCompare):
                reads |= float_span(network.action.source, 2)
                reads |= float_source_reads(network.action.upper)
                reads |= float_source_reads(network.action.lower)
            elif isinstance(network.action, ExclusiveLogic):
                reads |= word_references(network.action.sa) | word_references(network.action.sb)
            elif isinstance(network.action, WordConversion):
                if isinstance(network.action.source, str):
                    reads |= word_references(network.action.source)
            elif isinstance(network.action, ZoneCompare):
                reads.add(network.action.source)
            elif isinstance(network.action, RegisterOr):
                reads |= {f"R{network.action.sa}", f"R{network.action.sb}"}
            elif isinstance(network.action, LinearConversion):
                reads |= register_span(network.action.source, network.action.length)
                reads |= register_span(network.action.table, network.action.table_words)
            elif isinstance(network.action, Arithmetic):
                reads |= {network.action.sa}
                reads |= contacts(parse_expression(network.action.unsigned_when))
            elif isinstance(network.action, RegisterStep):
                reads.add(network.action.destination)
            elif isinstance(network.action, (Bitwise, Compare)):
                reads |= {network.action.sa, network.action.sb}
                if isinstance(network.action, Compare):
                    reads |= contacts(parse_expression(network.action.unsigned_when))
        elif network.comparison_chain:
            reads = comparison_reads(network)
        elif network.action is not None:
            if isinstance(network.action, Differential):
                reads = contacts(parse_expression(network.action.trigger))
            elif isinstance(network.action, UpDownCounter):
                u = network.action
                reads = {u.cv} | set().union(
                    *(contacts(parse_expression(e)) for e in (u.pulse, u.up, u.clear))
                )
            else:
                reads = set()
        elif isinstance(network.block, Timer):
            reads = contacts(parse_expression(network.block.enable))
        elif network.block is not None:
            reads = contacts(parse_expression(network.block.pulse)) | contacts(
                parse_expression(network.block.clear)
            )
        elif network.edge is not None:
            reads = {network.edge.input}
        else:
            reads = contacts(network_expression(network)) if not network.empty else set()
        writes = {f"{c.device}{c.address}" for c in network_coils(network)}
        if isinstance(network.action, FloatOperation):
            writes |= float_span(network.action.destination, network.action.destination_words)
        elif isinstance(network.action, (ExclusiveLogic, WordConversion)):
            writes |= word_references(network.action.destination)
        elif isinstance(network.action, RegisterOr):
            writes.add(f"R{network.action.destination}")
        elif isinstance(network.action, LinearConversion):
            writes |= register_span(
                network.action.destination, network.action.length, writable=True
            )
        elif isinstance(network.action, Arithmetic):
            writes |= register_span(
                network.action.destination, network.action.destination_words, writable=True
            )
        elif isinstance(network.action, (RegisterStep, Bitwise)):
            writes.add(network.action.destination)
        elif isinstance(network.action, UpDownCounter):
            writes.add(network.action.cv)
        if isinstance(network.action, ImmediateIO) and network.action.start.startswith("Y"):
            writes |= network.action.devices()
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
