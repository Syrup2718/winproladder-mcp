"""Deterministic scan-boundary T/C model, explicitly not a hardware emulator."""

from .ir import Counter, Ladder, Timer, apply_coils, network_expression, validation
from .logic import bit_address, evaluate, parse_expression


def timed_simulate(
    ladder: Ladder, inputs: list[dict[str, bool]], initial: dict[str, bool], scan_ms: int
) -> list[dict[str, bool]]:
    """Inputs apply for scan_ms, then networks execute once in display order.

    Timers start at zero, accumulate while EN is true, and reset on EN=false.
    Counters count rising PLS edges; CLR wins. Only bit states are returned.
    """
    if type(scan_ms) is not int or not 1 <= scan_ms <= 60000:
        raise ValueError("scan_ms must be an integer in 1..60000")
    check = validation(ladder)
    if not check["valid"]:
        raise ValueError(str(check["errors"]))
    if len(inputs) > 256 or len(initial) > 128:
        raise ValueError("Simulation limited to 256 scans and 128 initial devices")
    if any(n.action is not None for n in ladder.networks):
        raise ValueError("Timed model cannot execute register/loop actions")
    for name, value in initial.items():
        bit_address(name)
        if type(value) is not bool or name != f"{name[0]}{int(name[1:])}":
            raise ValueError("Initial devices must be canonical boolean values")
    blocks = [n.block for n in ladder.networks if n.block is not None]
    keys = [(type(b), b.address) for b in blocks]
    if len(keys) != len(set(keys)):
        raise ValueError("Timed model requires a single writer per timer/counter")
    for configured in blocks:
        if configured.preset > 32767:
            raise ValueError("Timed model supports presets 0..32767 only")
        if isinstance(configured, Timer) and configured.address > 49:
            raise ValueError("Timed model assumes default .01s T0..T49 configuration")
        family = "T" if isinstance(configured, Timer) else "C"
        if f"{family}{configured.address}" in initial:
            raise ValueError("Generated T/C blocks start reset; no initial block state supported")
    state = dict(initial)
    elapsed: dict[int, int] = {}
    counts: dict[int, int] = {}
    pulses: dict[int, bool] = {}
    previous = {
        i: initial.get(n.edge.input, False)
        for i, n in enumerate(ladder.networks)
        if n.edge is not None
    }
    trace = []
    for scan in inputs:
        for name, value in scan.items():
            bit_address(name)
            if name[0] != "X" or type(value) is not bool or name != f"X{int(name[1:])}":
                raise ValueError("Scan inputs must be canonical boolean X devices")
        for name in list(state):
            if name.startswith("X"):
                state[name] = False
        state.update(scan)
        for index, network in enumerate(ladder.networks):
            if network.empty:
                continue
            block = network.block
            if isinstance(block, Timer):
                enabled = evaluate(parse_expression(block.enable), state)
                elapsed[index] = elapsed.get(index, 0) + scan_ms if enabled else 0
                power = enabled and elapsed[index] >= block.preset * 10
                state[f"T{block.address}"] = power
            elif isinstance(block, Counter):
                pulse = evaluate(parse_expression(block.pulse), state)
                clear = evaluate(parse_expression(block.clear), state)
                count = counts.get(index, 0)
                counts[index] = (
                    0 if clear else min(32767, count + int(pulse and not pulses.get(index, False)))
                )
                pulses[index] = pulse
                power = not clear and counts[index] >= block.preset
                state[f"C{block.address}"] = power
            elif network.edge is not None:
                current = state.get(network.edge.input, False)
                power = (
                    (current and not previous[index])
                    if network.edge.kind == "rising"
                    else (previous[index] and not current)
                )
                previous[index] = current
            else:
                power = evaluate(network_expression(network), state)
            apply_coils(network.coils, power, state)
        trace.append(dict(state))
    return trace
