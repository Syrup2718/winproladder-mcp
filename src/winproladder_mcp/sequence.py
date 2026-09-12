"""Compile bounded, pause/resume sequences using sampled Boolean/counter families."""

from typing import Annotated, Any

from pydantic import Field

from .ir import Coil, Counter, Ladder, Model, Network
from .logic import contacts, parse_expression


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
    start: str = "X0"
    pause: str = "X1"
    reset: str = "X2"
    abort: str = "X3"
    clock: str = "X4"
    tick_ms: Annotated[int, Field(strict=True, ge=1, le=60000)] = 100


def sequence_ladder(spec: SequenceSpec) -> tuple[Ladder, dict[str, Any]]:
    """A clock is an external PLC input, not an invented firmware timer opcode.

    Count only observed rising edges while active. Paused edges are ignored and
    resuming with clock already high cannot create a false elapsed-time tick.
    """
    expressions = [spec.start, spec.pause, spec.reset, spec.abort, spec.clock]
    expressions += [step.complete_when for step in spec.steps]
    for expression in expressions:
        if any(not c.startswith("X") for c in contacts(parse_expression(expression))):
            raise ValueError(
                "Sequence inputs/conditions must use X contacts only; M/C are allocated"
            )
    if len({spec.start, spec.pause, spec.reset, spec.abort, spec.clock}) != 5:
        raise ValueError("Start/pause/reset/abort/clock expressions must be distinct")
    ns: list[Network] = []

    def bit(condition: str, address: int) -> None:
        ns.append(Network(condition=condition, coils=[Coil(device="M", address=address)]))

    # All prior-state snapshots precede all transitions: no within-scan cascade.
    for i in range(len(spec.steps)):
        bit(f"M{16 + i}", 64 + i)
    bit(f"({spec.clock}) AND NOT M2", 3)
    bit(f"({spec.start}) AND NOT M1 AND (NOT M0 OR M5)", 4)
    bit(spec.clock, 2)
    bit(spec.start, 1)
    bit(f"(M6 OR ({spec.abort})) AND NOT ({spec.reset})", 6)
    bit(f"M5 AND NOT M4 AND NOT ({spec.reset})", 5)
    bit(f"(M0 OR M4) AND NOT M5 AND NOT M6 AND NOT ({spec.reset})", 0)
    for i, step in enumerate(spec.steps):
        active = f"M{64 + i} AND M0 AND NOT ({spec.pause})"
        ns.append(
            Network(
                block=Counter(
                    address=i,
                    preset=step.ticks,
                    pulse=f"M3 AND ({active})",
                    clear=f"({spec.reset}) OR NOT M{64 + i} OR M4",
                )
            )
        )
        ns.append(
            Network(
                block=Counter(
                    address=16 + i,
                    preset=step.timeout_ticks or min(32767, max(100, step.ticks * 3)),
                    pulse=f"M3 AND ({active})",
                    clear=f"({spec.reset}) OR NOT M{64 + i} OR M4",
                )
            )
        )
    timeouts = " OR ".join(
        f"(M{64 + i} AND C{16 + i} AND NOT (C{i} AND ({step.complete_when})))"
        for i, step in enumerate(spec.steps)
    )
    bit(f"(M6 OR ({timeouts})) AND NOT ({spec.reset})", 6)
    for i, step in enumerate(spec.steps):
        bit(
            f"M{64 + i} AND M0 AND NOT M6 AND NOT ({spec.pause}) "
            f"AND C{i} AND ({step.complete_when})",
            96 + i,
        )
    for i in range(len(spec.steps)):
        enter = "M4" if i == 0 else f"M{95 + i}"
        bit(f"((M{64 + i} AND NOT M{96 + i}) OR {enter}) AND M0", 16 + i)
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
    return Ladder(networks=ns), {
        "requirement": spec.requirement,
        "resolved_spec": spec.model_dump(),
        "effective_timeout_ticks": [
            s.timeout_ticks or min(32767, max(100, s.ticks * 3)) for s in spec.steps
        ],
        "io": {
            "start": spec.start,
            "pause": spec.pause,
            "reset": spec.reset,
            "abort": spec.abort,
            "external_clock": spec.clock,
        },
        "allocated": {
            "running": "M0",
            "done": "M5",
            "fault": "M6",
            "internal": "M0..M6, M16..M31, M64..M79, M96..M111, C0..C31",
        },
        "assumptions": [
            "Candidate design, not commissioned machine or safety logic.",
            "Default I/O X0 start, X1 pause, X2 reset, X3 abort are active-high.",
            f"External clock {spec.clock}: one observable rising edge every {spec.tick_ms} ms.",
            "Both clock high and low must be sampled; missing pulses undercount elapsed time.",
            "Pause forces outputs off, preserving whole ticks only, not sub-tick time.",
            "Abort latches until reset. Reset clears sequence. No power-loss retention.",
            "Default timeout is max(100, 3*step ticks), capped at 32767 active ticks.",
            "Timeout pauses with the process; completion wins a simultaneous timeout.",
            "Feedback and safety interlocks must be explicit conditions, not inferred hardware.",
            "No automatic repeat; a new start rising edge is required after completion.",
        ],
        "gui_import_verified": False,
    }
