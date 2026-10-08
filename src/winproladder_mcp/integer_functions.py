"""test17 integer operations; MD=1 CRC is encoding-only, not a runtime model."""

from typing import TYPE_CHECKING, Any

from .logic import compile_expression, decode_expression, expression_text, parse_expression
from .registers import decode_register, encode_register

if TYPE_CHECKING:
    from .ir import IntegerFunction, Network

CODES = {
    "mean": "f4e2",
    "sqrt": "f49c",
    "neg": "f49a",
    "abs": "f49e",
    "ext": "f4b9",
    "crc16": "f775",
}


def compile_integer(action: "IntegerFunction") -> bytes:
    from .ir import compile_coils

    raw = compile_expression(parse_expression(action.enable)) + bytes.fromhex(CODES[action.type])
    if action.type == "mean":
        assert isinstance(action.count, str) and action.source is not None
        raw += encode_register(action.count) + encode_register(action.source)
    elif action.type == "crc16":
        assert isinstance(action.count, int) and action.source is not None
        raw += action.count.to_bytes(2, "big") + encode_register(action.source)
    elif action.type == "sqrt":
        assert action.source is not None
        raw += encode_register(action.source)
    raw += encode_register(action.destination)
    groups = [action.zero, action.error] if action.type == "crc16" else [action.error]
    for i, coils in enumerate(groups):
        if coils:
            raw += (0x6FFC + i).to_bytes(2, "big") + compile_coils(coils)
    return raw


def decode_integer(payload: bytes) -> "Network | None":
    from .ir import IntegerFunction, Network, decode_status_coils

    for i in range(2, len(payload), 2):
        kind = next((k for k, v in CODES.items() if payload[i : i + 2].hex() == v), None)
        if kind is None:
            continue
        try:
            tail = payload[i + 2 :]
            values: dict[str, Any] = {
                "type": kind,
                "enable": expression_text(decode_expression(payload[:i])),
            }
            size = 6 if kind in {"mean", "crc16"} else 4 if kind == "sqrt" else 2
            values["destination"] = decode_register(tail[size - 2 : size])
            if kind in {"mean", "crc16"}:
                values["source"] = decode_register(tail[2:4])
                values["count"] = (
                    decode_register(tail[:2]) if kind == "mean" else int.from_bytes(tail[:2], "big")
                )
                if kind == "crc16":
                    values["mode"] = 1
            elif kind == "sqrt":
                values["source"] = decode_register(tail[:2])
            outputs = decode_status_coils(tail[size:])
            if outputs[2] or (kind != "crc16" and outputs[1]):
                continue
            if kind == "crc16":
                values["zero"], values["error"] = outputs[:2]
            else:
                values["error"] = outputs[0]
            action = IntegerFunction.model_validate(values)
            if compile_integer(action) == payload:
                return Network(action=action)
        except ValueError:
            continue
    return None
