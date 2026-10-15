"""Small native register operations used by policy-compatible recipes."""

from .ir import Arithmetic, Coil, ExclusiveLogic, Network, ZoneCompare


def zero_word(destination: str) -> Network:
    """Clear a numeric word using the sampled native XOR form."""
    return Network(
        action=ExclusiveLogic(
            operation="xor",
            sa=destination,
            sb=destination,
            destination=destination,
        )
    )


def assign_word(destination: str, value: int, zero: str, enable: str = "TRUE") -> Network:
    """Load a numeric constant from the recipe's explicit zero word."""
    return Network(
        action=Arithmetic(
            operation="add",
            sa=zero,
            sb=value,
            destination=destination,
            enable=enable,
        )
    )


def status(source: str, low: int, high: int, memory: int) -> Network:
    return Network(
        action=ZoneCompare(
            source=source,
            lower=low,
            upper=high,
            within=[Coil(device="M", address=memory)],
        )
    )
