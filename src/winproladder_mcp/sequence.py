"""Compile register-based sequences with native timers or explicit pulse counters."""

from typing import Annotated, Any

from pydantic import Field

from .ir import AccumulativeTimer, Coil, Counter, Differential, Ladder, Model, Network, Timer
from .logic import contacts, parse_expression
from .native_state import assign_word, status, zero_word
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
    register_base: Annotated[int, Field(strict=True, ge=0, le=3774)] = 0
    tick_ms: Annotated[int, Field(strict=True, ge=1, le=60000)] = 100


def sequence_ladder(spec: SequenceSpec) -> tuple[Ladder, dict[str, Any]]:
    """Register state machine; native timers or an explicitly requested pulse input."""
    expressions = [spec.start, spec.pause, spec.reset, spec.abort]
    if spec.clock is not None:
        expressions.append(spec.clock)
    expressions += [step.complete_when for step in spec.steps]
    for expression in expressions:
        if any(not c.startswith("X") for c in contacts(parse_expression(expression))):
            raise ValueError("Sequence input conditions must use X contacts only")
    native = spec.clock is None
    accumulative = native and simplify(parse_expression(spec.pause)).op != "false"
    if native:
        for step in spec.steps:
            for ticks in (step.ticks, step.timeout_ticks):
                if ticks is not None and (
                    ticks * spec.tick_ms % 10 or ticks * spec.tick_ms > 327670
                ):
                    raise ValueError(
                        "Native duration must be a multiple of 10 ms, at most 327670 ms"
                    )
    state, zero = f"R{spec.register_base}", f"R{spec.register_base + 1}"
    count = len(spec.steps)
    ns = [zero_word(zero)]
    symbols = {
        state: f"Stage: 0 idle, 1..{count} active, {count + 1} done, {count + 2} aborted",
        zero: "Numeric zero",
        "M0": "Sequence running",
        "M4": "Start rising edge",
        "M5": "Sequence complete",
        "M6": "Abort or timeout latched",
    }

    def publish(*, snapshot: bool = False) -> None:
        if snapshot:
            ns.extend([status(state, 1, count, 64), status(state, count + 2, count + 2, 66)])
            symbols["M64"] = "Scan-entry running status"
            symbols["M66"] = "Scan-entry aborted status"
        else:
            ns.extend(
                [
                    status(state, 1, count, 0),
                    status(state, count + 1, count + 1, 5),
                    status(state, count + 2, count + 2, 6),
                ]
            )
        stage_base = 80 if snapshot else 16
        label = "Scan-entry stage" if snapshot else "Active stage"
        for i, step in enumerate(spec.steps):
            ns.append(status(state, i + 1, i + 1, stage_base + i))
            symbols[f"M{stage_base + i}"] = f"{label}: {step.name}"

    # Freeze entry state so even zero-time stages occupy one output scan.
    publish(snapshot=True)
    ns.append(Network(action=Differential(type="difu", trigger=spec.start, destination="M4")))
    if spec.clock is not None:
        ns.append(Network(action=Differential(type="difu", trigger=spec.clock, destination="M3")))
        symbols["M3"] = "External clock rising edge (sampled even during pause)"
    done: dict[int, str] = {}
    for i, step in enumerate(spec.steps):
        active = f"M{80 + i} AND NOT ({spec.reset}) AND NOT ({spec.abort})"
        for address, ticks in ((i, step.ticks), (16 + i, step.timeout_ticks)):
            if ticks is None:
                continue
            if accumulative:
                cv, pv = (
                    f"R{spec.register_base + 2 + address}",
                    f"R{spec.register_base + 34 + address}",
                )
                ns.append(assign_word(pv, ticks * spec.tick_ms // 10, zero))
                ns.append(
                    Network(
                        action=AccumulativeTimer(
                            type="accumulative_timer",
                            unit_ms=10,
                            cv=cv,
                            pv=pv,
                            timing=f"NOT ({spec.pause})",
                            enable=active,
                            done=[Coil(device="M", address=32 + address)],
                        )
                    )
                )
                done[address] = f"M{32 + address}"
                symbols.update(
                    {
                        cv: f"Elapsed ticks for timer {address}",
                        pv: f"Preset for timer {address}",
                        done[address]: f"Timer {address} reached preset",
                    }
                )
            elif native:
                ns.append(
                    Network(
                        block=Timer(
                            address=address, preset=ticks * spec.tick_ms // 10, enable=active
                        )
                    )
                )
                done[address] = f"T{address}"
            else:
                ns.append(
                    Network(
                        block=Counter(
                            address=address,
                            preset=ticks,
                            pulse=f"M3 AND {active} AND NOT ({spec.pause})",
                            clear=f"NOT M{80 + i} OR ({spec.reset}) OR ({spec.abort})",
                        )
                    )
                )
                done[address] = f"C{address}"
            symbols[done[address]] = f"{'Duration' if address == i else 'Timeout'}: {step.name}"
    for i, step in enumerate(spec.steps):
        ready = f"M{80 + i} AND NOT ({spec.pause}) AND NOT ({spec.reset}) AND NOT ({spec.abort})"
        ns.append(
            assign_word(state, i + 2, zero, f"{ready} AND {done[i]} AND ({step.complete_when})")
        )
        if step.timeout_ticks is not None:
            # Separate EN conditions avoid automatically lowered relay helpers.
            for incomplete in (f"NOT {done[i]}", f"NOT ({step.complete_when})"):
                ns.append(
                    assign_word(
                        state, count + 2, zero, f"{ready} AND {done[16 + i]} AND {incomplete}"
                    )
                )
    ns.append(
        assign_word(
            state,
            1,
            zero,
            f"M4 AND NOT M64 AND NOT M66 AND NOT ({spec.reset}) AND NOT ({spec.abort})",
        )
    )
    ns.append(assign_word(state, count + 2, zero, spec.abort))
    ns.append(assign_word(state, 0, zero, spec.reset))
    publish()
    for output in sorted({o for step in spec.steps for o in step.outputs}):
        active_steps = " OR ".join(
            f"M{16 + i}" for i, step in enumerate(spec.steps) if output in step.outputs
        )
        ns.append(
            Network(
                condition=f"({active_steps}) AND NOT ({spec.pause}) AND NOT ({spec.reset}) "
                f"AND NOT ({spec.abort})",
                coils=[Coil(address=output)],
            )
        )
    return Ladder(networks=ns, symbols=symbols), {
        "requirement": spec.requirement,
        "resolved_spec": spec.model_dump(),
        "timing_mode": "native_accumulative_10ms"
        if accumulative
        else "native_T_10ms"
        if native
        else "explicit_external_pulses",
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
            "State register must initially be zero, or assert the explicit reset before starting.",
            "Native T uses default T0..T49 .01s configuration; EN=false resets.",
            "Native pause uses FUN87: TIM=false retains elapsed ticks; EN=false clears.",
            "External pulse counting requires an explicitly specified clock input.",
            "All transitions use the initial stage comparisons; no same-scan cascade.",
            "Reset wins abort; completion wins simultaneous timeout. "
            "No power-loss retention guarantee.",
            "No GUI or PLC verification is implied.",
        ],
        "gui_import_verified": False,
    }
