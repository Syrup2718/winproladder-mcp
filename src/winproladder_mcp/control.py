"""Common control recipes synthesized from supported instructions, not new opcodes."""

from typing import Annotated, Any, Literal

from pydantic import Field

from .ir import Coil, Counter, Ladder, Model, Network, Timer
from .logic import contacts, parse_expression

ControlKind = Literal[
    "start_stop",
    "set_reset",
    "toggle",
    "rising_edge",
    "falling_edge",
    "on_delay",
    "off_delay",
    "pulse",
    "counter",
    "forward_reverse",
    "star_delta",
]


class ControlSpec(Model):
    requirement: str = Field(min_length=1, max_length=16000)
    kind: ControlKind
    signal: str = "X0"
    stop: str = "X1"
    reset: str = "X2"
    reverse: str = "X3"
    output: Annotated[int, Field(strict=True, ge=0, le=253)] = 0
    memory: Annotated[int, Field(strict=True, ge=0, le=250)] = 0
    timer: Annotated[int, Field(strict=True, ge=0, le=48)] = 0
    counter: Annotated[int, Field(strict=True, ge=0, le=255)] = 0
    delay_ms: Annotated[int, Field(strict=True, ge=10, le=327670)] = 1000
    gap_ms: Annotated[int, Field(strict=True, ge=10, le=327670)] = 100
    count: Annotated[int, Field(strict=True, ge=1, le=32767)] = 10


def control_ladder(spec: ControlSpec) -> tuple[Ladder, dict[str, Any]]:
    for expression in (spec.signal, spec.stop, spec.reset, spec.reverse):
        if any(not c.startswith("X") for c in contacts(parse_expression(expression))):
            raise ValueError("Recipe inputs must use X contacts; internal devices are allocated")
    if spec.delay_ms % 10 or spec.gap_ms % 10:
        raise ValueError("Timer durations must be multiples of 10 ms; no silent rounding")
    ns: list[Network] = []
    s, stop, reset, rev = (f"({v})" for v in (spec.signal, spec.stop, spec.reset, spec.reverse))
    y, m, t = f"Y{spec.output}", f"M{spec.memory}", f"T{spec.timer}"
    prev, edge = f"M{spec.memory + 1}", f"M{spec.memory + 2}"

    def coil(expr: str, name: str) -> None:
        ns.append(
            Network(
                condition=expr,
                coils=[Coil.model_validate({"device": name[0], "address": int(name[1:])})],
            )
        )

    def timer(enable: str, offset: int = 0, duration: int | None = None) -> None:
        ns.append(
            Network(
                block=Timer(
                    address=spec.timer + offset,
                    preset=(duration if duration is not None else spec.delay_ms) // 10,
                    enable=enable,
                )
            )
        )

    if spec.kind in {"start_stop", "set_reset"}:
        clear = stop if spec.kind == "start_stop" else reset
        coil(f"({y} OR {s}) AND NOT {clear}", y)
    elif spec.kind in {"rising_edge", "falling_edge", "toggle", "pulse"}:
        coil(f"{s} AND NOT {prev}" if spec.kind != "falling_edge" else f"NOT {s} AND {prev}", edge)
        coil(s, prev)
        if spec.kind in {"rising_edge", "falling_edge"}:
            coil(f"{edge} AND NOT {reset}", y)
        elif spec.kind == "toggle":
            coil(f"(({y} AND NOT {edge}) OR (NOT {y} AND {edge})) AND NOT {reset}", y)
        else:
            # Ignore triggers while active. A reset must cancel the timer as well.
            coil(f"({m} OR ({edge} AND NOT {m})) AND NOT {t} AND NOT {reset}", m)
            timer(m)
            coil(f"{m} AND NOT {t} AND NOT {reset}", y)
    elif spec.kind == "on_delay":
        timer(f"{s} AND NOT {reset}")
        coil(t, y)
    elif spec.kind == "off_delay":
        timer(f"{m} AND NOT {s} AND NOT {reset}")
        coil(f"({s} OR ({m} AND NOT {t})) AND NOT {reset}", m)
        coil(m, y)
    elif spec.kind == "counter":
        ns.append(
            Network(block=Counter(address=spec.counter, preset=spec.count, pulse=s, clear=reset))
        )
        coil(f"C{spec.counter}", y)
    elif spec.kind == "forward_reverse":
        reverse_output = f"Y{spec.output + 1}"
        coil(f"({y} OR {s}) AND NOT {stop} AND NOT {reverse_output}", y)
        coil(f"({reverse_output} OR {rev}) AND NOT {stop} AND NOT {y}", reverse_output)
    elif spec.kind == "star_delta":
        coil(f"({m} OR {s}) AND NOT {stop} AND NOT {reset}", m)
        timer(m)
        timer(f"{m} AND {t}", 1, spec.gap_ms)
        coil(m, y)
        coil(f"{m} AND NOT {t}", f"Y{spec.output + 1}")
        coil(f"{m} AND {t} AND T{spec.timer + 1}", f"Y{spec.output + 2}")
    return Ladder(networks=ns), {
        "requirement": spec.requirement,
        "kind": spec.kind,
        "resolved_spec": spec.model_dump(),
        "defaults_used": sorted(set(ControlSpec.model_fields) - spec.model_fields_set),
        "assumptions": [
            "Offline candidate, not certified or commissioned equipment control.",
            "Absent I/O and timing values use the disclosed resolved_spec defaults.",
            "Input expressions describe PLC bit polarity; physical NC wiring is not inferred.",
            "Timers assume default T0..T49 .01s configuration; M/Y startup states must be reset.",
            "Edges/toggle/SET-RST are synthesized Boolean networks, not native function opcodes.",
            "Forward/reverse favors forward on simultaneous starts when stopped.",
            "Star/delta: Y(base)=main, Y(base+1)=star, Y(base+2)=delta; "
            "hardware interlocks required.",
        ],
        "gui_import_verified": False,
    }
