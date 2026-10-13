"""Compile bounded, pause/resume sequences using sampled Boolean/counter families."""

from typing import Annotated, Any

from pydantic import Field

from .ir import Coil, Counter, Ladder, Model, Network, Timer
from .logic import contacts, parse_expression
from .optimize import simplify


class SequenceStep(Model):
    name: str = Field(min_length=1, max_length=120)
    outputs: list[Annotated[int, Field(strict=True, ge=0, le=255)]] = Field(
        default_factory=list, max_length=32
    )
    ticks: Annotated[int, Field(strict=True, ge=0, le=32767)] = 10
    complete_when: str = "TRUE"
    timeout_ticks: Annotated[int, Field(strict=True, ge=1, le=32767)] | None = None


class SequenceSpec(Model):
    requirement: str = Field(min_length=1, max_length=16000)
    steps: list[SequenceStep] = Field(min_length=1, max_length=16)
    start: str
    pause: str = "FALSE"
    reset: str = "FALSE"
    abort: str = "FALSE"
    clock: str | None = None
    tick_ms: Annotated[int, Field(strict=True, ge=1, le=60000)] = 100


def sequence_ladder(spec: SequenceSpec) -> tuple[Ladder, dict[str, Any]]:
    """Use native T timers unless the caller explicitly supplies a pulse input."""
    expressions = [spec.start, spec.pause, spec.reset, spec.abort]
    if spec.clock is not None:
        expressions.append(spec.clock)
    expressions += [step.complete_when for step in spec.steps]
    for expression in expressions:
        if any(not c.startswith("X") for c in contacts(parse_expression(expression))):
            raise ValueError("Sequence input conditions must use X contacts only")
    native = spec.clock is None
    if native and simplify(parse_expression(spec.pause)).op != "false":
        raise ValueError(
            "Native pause/resume requires accumulative timer FUN87/88/89. "
            "Low-level generate_ldr now supports sampled register-PV forms, but the "
            "high-level sequence generator does not integrate them. Ordinary T resets "
            "when EN is false. "
            "No external X input will be added; no file written."
        )
    if native:
        for step in spec.steps:
            for ticks in (step.ticks, step.timeout_ticks):
                if ticks is not None and (
                    ticks * spec.tick_ms % 10 or ticks * spec.tick_ms > 327670
                ):
                    raise ValueError(
                        "Native T duration must be a multiple of 10 ms, at most 327670 ms"
                    )
    ns: list[Network] = []

    def bit(condition: str, address: int) -> None:
        ns.append(Network(condition=condition, coils=[Coil(device="M", address=address)]))

    # Compute every transition before changing any stage; snapshots are unnecessary.
    if not native:
        bit(f"({spec.clock}) AND NOT M2", 3)
    bit(f"({spec.start}) AND NOT M1 AND (NOT M0 OR M5)", 4)
    if spec.clock is not None:
        bit(spec.clock, 2)
    bit(spec.start, 1)
    bit(f"(M6 OR ({spec.abort})) AND NOT ({spec.reset})", 6)
    bit(f"M5 AND NOT M4 AND NOT ({spec.reset})", 5)
    bit(f"(M0 OR M4) AND NOT M5 AND NOT M6 AND NOT ({spec.reset})", 0)
    family = "T" if native else "C"
    for i, step in enumerate(spec.steps):
        active = f"M{16 + i} AND M0 AND NOT ({spec.pause}) AND NOT M4"
        for address, ticks in ((i, step.ticks), (16 + i, step.timeout_ticks)):
            if ticks is None:
                continue
            if native:
                ns.append(
                    Network(
                        block=Timer(
                            address=address, preset=ticks * spec.tick_ms // 10, enable=active
                        )
                    )
                )
            else:
                ns.append(
                    Network(
                        block=Counter(
                            address=address,
                            preset=ticks,
                            pulse=f"M3 AND ({active})",
                            clear=f"({spec.reset}) OR NOT M{16 + i} OR M4",
                        )
                    )
                )
    timeouts = " OR ".join(
        f"(M{16 + i} AND {family}{16 + i} AND NOT ({family}{i} AND ({step.complete_when})))"
        for i, step in enumerate(spec.steps)
        if step.timeout_ticks is not None
    )
    if timeouts:
        bit(f"(M6 OR ({timeouts})) AND NOT ({spec.reset})", 6)
    for i, step in enumerate(spec.steps):
        bit(
            f"M{16 + i} AND M0 AND NOT M6 AND NOT ({spec.pause}) "
            f"AND {family}{i} AND ({step.complete_when})",
            96 + i,
        )
    for i in range(len(spec.steps)):
        enter = "M4" if i == 0 else f"M{95 + i}"
        bit(f"((M{16 + i} AND NOT M{96 + i}) OR {enter}) AND M0", 16 + i)
    # Completion cuts outputs in the same scan, not one scan later.
    bit(f"(M5 OR M{95 + len(spec.steps)}) AND NOT ({spec.reset})", 5)
    for output in sorted({o for s in spec.steps for o in s.outputs}):
        active_steps = " OR ".join(
            f"M{16 + i}" for i, s in enumerate(spec.steps) if output in s.outputs
        )
        ns.append(
            Network(
                condition=f"({active_steps}) AND M0 AND NOT M5 AND NOT M6 "
                f"AND NOT ({spec.pause}) AND NOT ({spec.reset}) AND NOT ({spec.abort})",
                coils=[Coil(address=output)],
            )
        )
    symbols = {
        "M0": "Sequence running",
        "M1": "Previous scan start condition",
        "M4": "Accepted one-scan start command",
        "M5": "Sequence complete",
        "M6": "Abort or explicit timeout latch",
    }
    if not native:
        symbols.update({"M2": "Previous scan pulse input", "M3": "One-scan pulse edge"})
    for i, step in enumerate(spec.steps):
        symbols[f"M{16 + i}"] = f"Active stage: {step.name}"
        symbols[f"M{96 + i}"] = f"Advance from stage: {step.name}"
        symbols[f"{family}{i}"] = f"Duration for stage: {step.name}"
        if step.timeout_ticks is not None:
            symbols[f"{family}{16 + i}"] = f"Explicit timeout for stage: {step.name}"
    for n in ns:
        n.comment = "; ".join(symbols.get(f"{c.device}{c.address}", "") for c in n.coils)
    return Ladder(networks=ns, symbols=symbols), {
        "requirement": spec.requirement,
        "resolved_spec": spec.model_dump(),
        "timing_mode": "native_T_10ms" if native else "explicit_external_pulses",
        "effective_timeout_ticks": [s.timeout_ticks for s in spec.steps],
        "io": {
            "start": spec.start,
            "pause": spec.pause,
            "reset": spec.reset,
            "abort": spec.abort,
            "external_clock": spec.clock,
        },
        "allocated": symbols,
        "assumptions": [
            "Native T uses the sampled default T0..T49 .01s configuration; EN=false resets.",
            "External pulse counting requires an explicitly specified clock input.",
            "Pulse counting retains whole ticks only. No implicit external inputs or timeouts.",
            "All transitions are calculated before stage writes to prevent same-scan cascade.",
            "Abort latches until reset. No power-loss retention or automatic repeat.",
            "No GUI or PLC verification is implied.",
        ],
        "gui_import_verified": False,
    }
