"""test28 FUN81..84, advanced manual 7-74..78. No hardware simulation."""

from typing import TYPE_CHECKING

from .logic import bit_address, device_name
from .registers import decode_register, encode_register, register_span

if TYPE_CHECKING:
    from .ir import ProcessFunction

FIELDS = {
    "pulse_output": ("frequency", "pulse_count", "forward_output", "reverse_output", "destination"),
    "pwm": ("physical_output",),
    "speed_detect": ("physical_input", "destination"),
    "text_display": ("source", "start_register", "length_register", "destination"),
}
CONTROLS = {
    "pulse_output": ("enable", "pause", "up"),
    "pwm": ("enable",),
    "speed_detect": ("enable",),
    "text_display": ("enable", "display_off", "display_on"),
}
STATUS = {
    "pulse_output": ("active", "done", "error"),
    "pwm": ("error",),
    "speed_detect": ("overflow",),
    "text_display": (),
}
CODES = {"pulse_output": "f414", "pwm": "f7f3", "speed_detect": "f6fb", "text_display": "fc0f"}
SCALARS = ("on_ms", "period_ms", "sample_ms", "display_number")


def check_parameters(action: "ProcessFunction") -> None:
    required = {
        "pwm": {"on_ms", "period_ms"},
        "speed_detect": {"sample_ms"},
        "text_display": {"display_number"},
    }.get(action.type, set())
    for name in SCALARS:
        if (getattr(action, name) is not None) != (name in required):
            raise ValueError(f"{action.type}: invalid {name} presence")
    expected_mode = {"pulse_output": 0, "text_display": 1}.get(action.type)
    if action.mode != expected_mode or action.pulse is not None:
        raise ValueError("Only sampled PLSO MD0 / TDSP MD1 non-D/P forms are encoded")
    if action.type == "pulse_output" and action.forward_output == action.reverse_output:
        raise ValueError("PLSO UY and DY must be distinct")
    if action.type == "text_display" and (
        action.source,
        action.start_register,
        action.length_register,
        action.destination,
        action.display_number,
    ) != ("R3904", "R3906", "R3908", "R1000", 1):
        raise ValueError("TDSP operand layout is an exact test28 decode-only anchor")


def operand_check(kind: str, field: str, name: str) -> None:
    if field in {"forward_output", "reverse_output", "physical_output", "physical_input"}:
        prefix = "X" if field == "physical_input" else "Y"
        bit_address(name)
        limit = 7 if prefix == "X" else 15 if kind == "pwm" else 255
        if not name.startswith(prefix) or int(name[1:]) > limit:
            raise ValueError(f"{field} requires {prefix}0..{limit}")
    elif kind == "text_display" and name in {"R3904", "R3906", "R3908"}:
        return
    else:
        register_span(name, 1, writable=True)


def references(action: "ProcessFunction") -> tuple[set[str], set[str]]:
    if action.type == "pulse_output":
        return {
            action.operand("frequency"),
            action.operand("pulse_count"),
            action.operand("destination"),
        }, {
            action.operand("forward_output"),
            action.operand("reverse_output"),
            action.operand("destination"),
        }
    if action.type == "pwm":
        return set(), {action.operand("physical_output")}
    if action.type == "speed_detect":
        words = register_span(action.operand("destination"), 3, writable=True)
        return {action.operand("physical_input")} | words, words
    # TDSP variable Ns/Nl spans unknown: diagnostic anchors only, generation rejected.
    return {action.operand(k) for k in ("source", "start_register", "length_register")}, {
        action.operand("destination")
    }


def compile_operands(action: "ProcessFunction") -> bytes:
    if action.type == "pulse_output":
        return (
            encode_register(action.operand("frequency"))
            + encode_register(action.operand("pulse_count"))
            + bit_address(action.operand("forward_output")).to_bytes(2, "big")
            + bit_address(action.operand("reverse_output")).to_bytes(2, "big")
            + encode_register(action.operand("destination"))
        )
    if action.type == "pwm":
        assert action.on_ms is not None and action.period_ms is not None
        return (
            action.on_ms.to_bytes(2, "big")
            + action.period_ms.to_bytes(2, "big")
            + bit_address(action.operand("physical_output")).to_bytes(2, "big")
        )
    if action.type == "speed_detect":
        assert action.sample_ms is not None
        return (
            bit_address(action.operand("physical_input")).to_bytes(2, "big")
            + action.sample_ms.to_bytes(2, "big")
            + encode_register(action.operand("destination"))
        )
    return bytes.fromhex("0000018000010184018811d00001")


def decode_operands(kind: str, tail: bytes) -> tuple[dict[str, object], int]:
    size = {"pulse_output": 10, "pwm": 6, "speed_detect": 6, "text_display": 14}[kind]
    if len(tail) < size:
        raise ValueError("Truncated pulse function")
    words = [tail[i : i + 2] for i in range(0, size, 2)]
    nums = [int.from_bytes(w, "big") for w in words]
    if kind == "pulse_output":
        return dict(
            mode=0,
            frequency=decode_register(words[0]),
            pulse_count=decode_register(words[1]),
            forward_output=device_name(nums[2]),
            reverse_output=device_name(nums[3]),
            destination=decode_register(words[4]),
        ), size
    if kind == "pwm":
        return dict(on_ms=nums[0], period_ms=nums[1], physical_output=device_name(nums[2])), size
    if kind == "speed_detect":
        return dict(
            physical_input=device_name(nums[0]),
            sample_ms=nums[1],
            destination=decode_register(words[2]),
        ), size
    if tail[:size] != bytes.fromhex("0000018000010184018811d00001"):
        raise ValueError("Unresolved TDSP form")
    return dict(
        mode=1,
        source="R3904",
        start_register="R3906",
        length_register="R3908",
        destination="R1000",
        display_number=1,
    ), size
