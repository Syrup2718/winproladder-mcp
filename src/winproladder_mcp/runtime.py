"""Bounded scan model for direct words and native control instructions.

Words are unsigned 16-bit storage; signed arithmetic interprets bit 15. This is
an offline model, not a PLC emulator. Hardware functions and control flow fail
closed. Disabled comparison flags assume M1919=0 (retain previous result).
"""

from typing import Annotated, Any

from pydantic import Field

from .ir import (
    AccumulativeTimer,
    Arithmetic,
    Bitwise,
    Coil,
    Compare,
    Counter,
    Differential,
    ExclusiveLogic,
    Ladder,
    ProcessFunction,
    RegisterStep,
    Timer,
    WordConversion,
    ZoneCompare,
    apply_coils,
    network_expression,
    validation,
)
from .logic import bit_address, evaluate, parse_expression
from .registers import register_span

Scalar = Annotated[bool, Field(strict=True)] | Annotated[int, Field(strict=True)]
State = dict[str, bool | int]
SUPPORTED_ACTIONS = (
    Arithmetic,
    RegisterStep,
    Bitwise,
    ExclusiveLogic,
    Compare,
    ZoneCompare,
    Differential,
    AccumulativeTimer,
    WordConversion,
)
SUPPORTED_PROCESS = {"toggle_bit", "move_word", "move_inverse"}
MODEL_SCOPE = (
    "Offline scan model, not PLC emulation or GUI verification. Direct R/D words are "
    "unsigned 16-bit storage (signed interpretation for signed operations); missing words "
    "start at zero. Missing X inputs are false per scan. Timer scans use a deterministic "
    "scan-boundary clock, default T0..T49 .01s; accumulative timers retain sub-tick "
    "remainder on pause. Disabled comparison flags assume M1919=0. No hardware timing, "
    "power-loss retention, loops, jumps or peripheral execution is modeled."
)


def check_value(name: str, value: bool | int) -> bool | int:
    if name.startswith(("R", "D")):
        register_span(name, 1)
        if type(value) is not int or not -32768 <= value <= 65535:
            raise ValueError("Register values require integers -32768..65535")
        return value & 0xFFFF
    bit_address(name)
    if type(value) is not bool or name != f"{name[0]}{int(name[1:])}":
        raise ValueError("Bit devices require canonical names and boolean values")
    return value


def signed(value: int) -> int:
    return value - 65536 if value & 0x8000 else value


def simulate_runtime(
    ladder: Ladder,
    inputs: list[dict[str, bool]],
    initial: State,
    scan_ms: int | None = None,
) -> list[State]:
    if scan_ms is not None and (type(scan_ms) is not int or not 1 <= scan_ms <= 60000):
        raise ValueError("scan_ms must be an integer in 1..60000")
    report = validation(ladder)
    if not report["valid"]:
        raise ValueError(str(report["errors"]))
    if len(inputs) > 256 or len(initial) > 128:
        raise ValueError("Simulation limited to 256 scans and 128 initial devices")
    state = {name: check_value(name, value) for name, value in initial.items()}
    for scan in inputs:
        if len(scan) > 256:
            raise ValueError("At most X0..X255 per scan")
        for name, input_value in scan.items():
            check_value(name, input_value)
            if not name.startswith("X") or type(input_value) is not bool:
                raise ValueError("Scan inputs must be canonical boolean X devices")
    timer_keys: set[str] = set()
    for n in ladder.networks:
        a = n.action
        if n.comparison_chain:
            raise ValueError("Runtime model cannot execute comparison chains")
        if a is not None:
            if not isinstance(a, SUPPORTED_ACTIONS) and not (
                isinstance(a, ProcessFunction) and a.type in SUPPORTED_PROCESS
            ):
                raise ValueError(f"Runtime model cannot execute {a.type}; no partial trace")
            if isinstance(a, AccumulativeTimer):
                if scan_ms is None:
                    raise ValueError("Accumulative timer execution requires scan_ms")
                if a.cv in timer_keys:
                    raise ValueError("Runtime model requires a single writer per timer/counter")
                timer_keys.add(a.cv)
            # Keep the numeric model separate from packed I/O and timer-word semantics.
            for field in ("sa", "sb", "source", "destination", "cv", "pv"):
                operand = getattr(a, field, None)
                if (
                    isinstance(operand, str)
                    and not isinstance(a, Differential)
                    and not operand.startswith(("R", "D"))
                ):
                    raise ValueError(
                        f"Runtime model cannot execute non-R/D numeric operands: {operand}"
                    )
        b = n.block
        if b is not None:
            if scan_ms is None:
                raise ValueError("Timer/Counter execution requires scan_ms")
            name = f"{'T' if isinstance(b, Timer) else 'C'}{b.address}"
            if name in timer_keys:
                raise ValueError("Timed model requires a single writer per timer/counter")
            timer_keys.add(name)
            if b.preset > 32767:
                raise ValueError("Timed model supports presets 0..32767 only")
            if isinstance(b, Timer) and b.address > 49:
                raise ValueError("Timed model assumes default .01s T0..T49 configuration")
            if name in initial:
                raise ValueError(
                    "Generated T/C blocks start reset; no initial block state supported"
                )

    def bits() -> dict[str, bool]:
        return {k: v for k, v in state.items() if type(v) is bool}

    def test(expression: str) -> bool:
        return evaluate(parse_expression(expression), bits())

    def word(name: str) -> int:
        return int(state.get(name, 0)) & 0xFFFF

    def put(name: str, value: int) -> None:
        state[name] = value & 0xFFFF

    def coils(items: list[Coil], power: bool) -> None:
        b = bits()
        apply_coils(items, power, b)
        state.update(b)

    previous: dict[int, bool] = {}
    elapsed: dict[int, int] = {}
    counts: dict[int, int] = {}
    flags: dict[int, tuple[bool, ...]] = {}
    for i, n in enumerate(ladder.networks):
        if n.edge is not None:
            previous[i] = bool(state.get(n.edge.input, False))
        elif isinstance(n.action, Differential) or (
            isinstance(n.action, ProcessFunction) and n.action.type == "toggle_bit"
        ):
            previous[i] = test(n.action.trigger)
    trace = []
    for scan in inputs:
        for name in list(state):
            if name.startswith("X"):
                state[name] = False
        state.update(scan)
        for i, n in enumerate(ladder.networks):
            if n.empty:
                continue
            a, b = n.action, n.block
            if isinstance(b, Timer):
                assert scan_ms is not None
                enabled = test(b.enable)
                elapsed[i] = elapsed.get(i, 0) + scan_ms if enabled else 0
                power = enabled and elapsed[i] >= b.preset * 10
                state[f"T{b.address}"] = power
            elif isinstance(b, Counter):
                pulse, clear = test(b.pulse), test(b.clear)
                counts[i] = (
                    0
                    if clear
                    else min(32767, counts.get(i, 0) + int(pulse and not previous.get(i, False)))
                )
                previous[i] = pulse
                power = not clear and counts[i] >= b.preset
                state[f"C{b.address}"] = power
            elif isinstance(a, Differential):
                current = test(a.trigger)
                state[a.destination] = (
                    (current and not previous[i])
                    if a.type == "difu"
                    else (previous[i] and not current)
                )
                previous[i] = current
                continue
            elif isinstance(a, AccumulativeTimer):
                assert scan_ms is not None
                preset, current_word = word(a.pv), word(a.cv)
                if preset > 32767 or current_word > 32767:
                    raise ValueError("Accumulative timer model requires CV/PV 0..32767")
                enabled = test(a.enable)
                if not enabled:
                    current_word, elapsed[i] = 0, 0
                elif test(a.timing):
                    ticks, elapsed[i] = divmod(elapsed.get(i, 0) + scan_ms, a.unit_ms)
                    current_word = min(32767, current_word + ticks)
                put(a.cv, current_word)
                coils(a.done, enabled and current_word >= preset)
                coils(a.not_done, enabled and current_word < preset)
                continue
            elif isinstance(a, (Compare, ZoneCompare)):
                groups = (
                    [a.equal, a.greater, a.less]
                    if isinstance(a, Compare)
                    else [a.within, a.above, a.below]
                )
                if test(a.enable):
                    if isinstance(a, Compare):
                        left, right = word(a.sa), word(a.sb)
                        if not test(a.unsigned_when):
                            left, right = signed(left), signed(right)
                        flags[i] = (left == right, left > right, left < right)
                    else:
                        value = signed(word(a.source))
                        flags[i] = (a.lower <= value <= a.upper, value > a.upper, value < a.lower)
                for group, flag in zip(groups, flags.get(i, (False, False, False)), strict=True):
                    coils(group, flag)
                continue
            elif isinstance(a, ProcessFunction) and a.type == "toggle_bit":
                current = test(a.trigger)
                destination = a.operand("bit_destination")
                if current and not previous[i]:
                    state[destination] = not bool(state.get(destination, False))
                state.setdefault(destination, False)
                previous[i] = current
                continue
            elif a is not None:
                if not test(getattr(a, "enable", "TRUE")):
                    continue
                if isinstance(a, Arithmetic):
                    left, right = word(a.sa), a.sb
                    if not test(a.unsigned_when):
                        left = signed(left)
                    if a.operation == "add":
                        value = left + right
                    elif a.operation == "sub":
                        value = left - right
                    elif a.operation == "mul":
                        value = left * right
                        put(f"{a.destination[0]}{int(a.destination[1:]) + 1}", value >> 16)
                    else:
                        value = (abs(left) // right) * (-1 if left < 0 else 1)
                        put(f"{a.destination[0]}{int(a.destination[1:]) + 1}", left - value * right)
                    put(a.destination, value)
                elif isinstance(a, RegisterStep):
                    put(a.destination, word(a.destination) + (1 if a.type == "increment" else -1))
                elif isinstance(a, (Bitwise, ExclusiveLogic)):
                    left, right = word(a.sa), word(a.sb)
                    value = {
                        "and": left & right,
                        "or": left | right,
                        "xor": left ^ right,
                        "xnr": ~(left ^ right),
                    }[a.operation]
                    put(a.destination, value)
                elif isinstance(a, WordConversion):
                    if a.operation == "to_bcd":
                        assert isinstance(a.source, int)
                        value = int(str(a.source), 16)
                    else:
                        assert isinstance(a.source, str)
                        digits = f"{word(a.source):04x}"
                        if any(c not in "0123456789" for c in digits):
                            raise ValueError("Invalid BCD source; error flags are not modeled")
                        value = int(digits)
                    put(a.destination, value)
                elif isinstance(a, ProcessFunction):
                    value = word(a.operand("source"))
                    put(a.operand("destination"), ~value if a.type == "move_inverse" else value)
                continue
            elif n.edge is not None:
                current = bool(state.get(n.edge.input, False))
                power = (
                    (current and not previous[i])
                    if n.edge.kind == "rising"
                    else (previous[i] and not current)
                )
                previous[i] = current
            else:
                power = evaluate(network_expression(n), bits())
            coils(n.coils, power)
        trace.append(dict(state))
    return trace


def simulation_capabilities() -> dict[str, Any]:
    return {
        "scope": MODEL_SCOPE,
        "actions": [
            "arithmetic",
            "increment",
            "decrement",
            "bitwise",
            "exclusive_logic",
            "compare",
            "zone_compare",
            "difu",
            "difd",
            "accumulative_timer",
            "word_conversion",
            *sorted(SUPPORTED_PROCESS),
        ],
        "word_operands": "direct R/D only",
        "max_scans": 256,
        "unsupported_behavior": "Explicit error before execution; no success or partial trace",
    }
