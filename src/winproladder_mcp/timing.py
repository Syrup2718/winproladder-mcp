"""Compatibility entry point for the bounded scan model."""

from .ir import Ladder
from .runtime import State, simulate_runtime


def timed_simulate(
    ladder: Ladder, inputs: list[dict[str, bool]], initial: State, scan_ms: int
) -> list[State]:
    return simulate_runtime(ladder, inputs, initial, scan_ms)
