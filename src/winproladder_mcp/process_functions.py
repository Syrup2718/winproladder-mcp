"""Sampled ASCWR, RAMP, RAMP2 and register-to-table encodings (test20)."""

from typing import TYPE_CHECKING

from .logic import (
    compile_expression,
    decode_expression,
    expression_text,
    negate,
    parse_expression,
)
from .registers import decode_register, decode_word, encode_register, encode_word, register_span

if TYPE_CHECKING:
    from .ir import Network, ProcessFunction

FIELDS = {
    "ascwr": ("source", "work"),
    "ramp": ("preset", "timer", "lower", "upper", "destination"),
    "ramp2": ("maximum", "rise_ms", "fall_ms", "target", "destination", "work"),
    "reg_to_table": ("source", "destination", "pointer"),
}
CONTROLS = {
    "ascwr": ("enable", "pause", "abort"),
    "ramp": ("enable", "pause", "up"),
    "ramp2": ("enable",),
    "reg_to_table": ("enable", "increment", "clear"),
}
CODES = {"ascwr": "f103", "ramp": "f816", "ramp2": "f47e", "reg_to_table": "f406"}
STATUS = {
    "ascwr": ("active", "error", "done"),
    "ramp": ("error", "at_lower", "at_upper"),
    "ramp2": ("accelerating", "decelerating"),
    "reg_to_table": ("done", "error"),
}


def ramp2_span(name: str, count: int = 1) -> set[str]:
    # OR bank encoding inferred from the R3904 anchor, scoped to FUN98.
    if name.startswith("R") and name[1:].isdigit() and 3904 <= int(name[1:]) <= 3967:
        n = int(name[1:])
        if name != f"R{n}" or n + count > 3968 or count < 1:
            raise ValueError("RAMP2 OR span crosses R3967")
        return {f"R{i}" for i in range(n, n + count)}
    words = register_span(name, count, writable=True)
    if name.startswith("D") and int(name[1:]) + count > 4000:
        raise ValueError("RAMP2 manual D bank ends at D3999, including spans")
    return words


def encode_process_word(kind: str, name: str) -> bytes:
    if kind == "ramp2":
        ramp2_span(name)
        if name.startswith("R") and 3904 <= int(name[1:]) <= 3967:
            return (0x180 + 2 * (int(name[1:]) - 3904)).to_bytes(2, "big")
    return encode_word(name)


def decode_process_word(kind: str, raw: bytes) -> str:
    n = int.from_bytes(raw, "big")
    if kind == "ramp2" and len(raw) == 2 and 0x180 <= n <= 0x1FE and n % 2 == 0:
        return f"R{3904 + (n - 0x180) // 2}"
    return decode_word(raw)


def compile_process(action: "ProcessFunction") -> bytes:
    from .ir import compile_coils

    raw = b""
    for index, name in enumerate(CONTROLS[action.type]):
        expr = parse_expression(getattr(action, name))
        # CLR uses the sampled inverse-polarity pin representation.
        if action.type == "reg_to_table" and name == "clear":
            expr = negate(expr)
        raw += compile_expression(expr, nested=index > 0)
    raw += bytes.fromhex(CODES[action.type])
    if action.type in {"ramp", "ramp2"}:
        raw += b"\x00\x00"  # Reserved/sample form selector: never infer other modes.
    if action.type == "reg_to_table":
        assert action.length is not None
        raw += encode_register(action.operand("source"))
        raw += encode_register(action.operand("destination"))
        raw += (action.length - 1).to_bytes(2, "big")
        raw += encode_register(action.operand("pointer"))
    else:
        raw += b"".join(
            encode_process_word(action.type, action.operand(n)) for n in FIELDS[action.type]
        )
    for index, name in enumerate(STATUS[action.type]):
        coils = getattr(action, name)
        if coils:
            raw += (0x6FFC + index).to_bytes(2, "big") + compile_coils(coils)
    return raw


def decode_three(prefix: bytes) -> tuple[str, str, str]:
    from .ir import decode_two_inputs

    candidates = []
    for split in range(4, len(prefix), 2):
        if prefix[split] & 0xE0 != 0x60:
            continue
        try:
            first, second = decode_two_inputs(prefix[:split])
            third = decode_expression(bytes([prefix[split] - 0x20]) + prefix[split + 1 :])
            candidates.append(tuple(map(expression_text, (first, second, third))))
        except ValueError:
            continue
    if len(candidates) != 1:
        raise ValueError("Ambiguous three-input function prefix")
    first_text, second_text, third_text = candidates[0]
    return first_text, second_text, third_text


def decode_process(payload: bytes) -> "Network | None":
    from .ir import Network, ProcessFunction, decode_status_coils

    for i in range(2, len(payload), 2):
        kind = next((k for k, v in CODES.items() if payload[i : i + 2].hex() == v), None)
        if kind is None:
            continue
        try:
            controls = list(
                (expression_text(decode_expression(payload[:i])),)
                if kind == "ramp2"
                else decode_three(payload[:i])
            )
            fields: dict[str, object] = dict(zip(CONTROLS[kind], controls, strict=True))
            fields["type"] = kind
            tail = payload[i + 2 :]
            if kind in {"ramp", "ramp2"}:
                if tail[:2] != b"\x00\x00":
                    continue
                tail = tail[2:]
            if kind == "reg_to_table":
                fields.update(
                    source=decode_register(tail[:2]),
                    destination=decode_register(tail[2:4]),
                    length=int.from_bytes(tail[4:6], "big") + 1,
                    pointer=decode_register(tail[6:8]),
                    clear=expression_text(negate(parse_expression(controls[2]))),
                )
                size = 8
            else:
                size = len(FIELDS[kind]) * 2
                fields.update(
                    {
                        n: decode_process_word(kind, tail[j * 2 : j * 2 + 2])
                        for j, n in enumerate(FIELDS[kind])
                    }
                )
            if kind == "ascwr":
                fields.update(mode=1, pulse=True)
            outputs = decode_status_coils(tail[size:])
            if any(outputs[len(STATUS[kind]) :]):
                continue
            fields.update({name: outputs[j] for j, name in enumerate(STATUS[kind])})
            action = ProcessFunction.model_validate(fields)
            if compile_process(action) == payload:
                return Network(action=action)
        except ValueError:
            continue
    return None
