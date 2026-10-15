"""test18 sampled analog, bit access and exact flow-record encodings."""

from typing import TYPE_CHECKING

from .logic import compile_expression, decode_expression, expression_text, parse_expression
from .registers import decode_register, encode_register

if TYPE_CHECKING:
    from .ir import AnalogConversion, BitAccess, Network, SampleFlow

FLOW = {"lbl": "ef31000000000000", "jmp": "4fe8f78ca7fe188000000000"}


def compile_analog(action: "AnalogConversion | BitAccess | SampleFlow") -> bytes:
    from .ir import AnalogConversion, SampleFlow, compile_coils

    if isinstance(action, SampleFlow):
        if action.type == "lbl":
            return encode_label(action.target)
        return bytes.fromhex("4fe8f78ca7fe1c0000000000" if action.target == "8" else FLOW["jmp"])
    raw = compile_expression(parse_expression(action.enable))
    if isinstance(action, AnalogConversion):
        raw += compile_expression(parse_expression(action.selector), nested=True)
        if action.type == "adcnv":
            raw += bytes.fromhex("f55a") + action.count.to_bytes(2, "big")
            raw += encode_register(action.source) + encode_register(action.destination)
        else:
            assert action.x_table and action.y_table and action.table_length
            raw += bytes.fromhex("f55e") + encode_register(action.source)
            raw += action.count.to_bytes(2, "big")
            raw += b"".join(
                encode_register(v)
                for v in [action.x_table, action.y_table, action.table_length, action.destination]
            )
        groups = [action.overflow]
    elif action.type == "bitrd":
        raw += bytes.fromhex("f4ba") + encode_register(action.word) + action.bit.to_bytes(2, "big")
        groups = [action.output, action.error]
    else:
        assert action.input_bit is not None
        raw += compile_expression(parse_expression(action.input_bit), nested=True)
        raw += bytes.fromhex("f544") + action.bit.to_bytes(2, "big") + encode_register(action.word)
        groups = [action.error]
    for i, coils in enumerate(groups):
        if coils:
            raw += (0x6FFC + i).to_bytes(2, "big") + compile_coils(coils)
    return raw


def decode_analog(payload: bytes) -> "Network | None":
    from .ir import (
        AnalogConversion,
        BitAccess,
        Network,
        SampleFlow,
        decode_status_coils,
        decode_two_inputs,
    )

    if len(payload) == 8 and payload[0] == 0xEF:
        try:
            chars = [payload[1]]
            for i in (2, 4, 6):
                word = int.from_bytes(payload[i : i + 2], "big")
                chars.extend((word >> 7, word & 127))
            target = bytes(chars).rstrip(b"\x00").decode("ascii")
            label = SampleFlow(type="lbl", target=target)
            if encode_label(target) == payload:
                return Network(action=label)
        except (ValueError, UnicodeError):
            return None
    for kind in FLOW:
        candidate = SampleFlow.model_validate({"type": kind, "target": "8"})
        if compile_analog(candidate) == payload:
            return Network(action=candidate)
    for kind, raw in FLOW.items():
        if payload.hex() == raw:
            return Network(action=SampleFlow.model_validate({"type": kind}))
    for i in range(2, len(payload), 2):
        code = payload[i : i + 2].hex()
        if code not in {"f55a", "f55e", "f4ba", "f544"}:
            continue
        try:
            tail = payload[i + 2 :]
            action: AnalogConversion | BitAccess
            if code == "f4ba":
                en = decode_expression(payload[:i])
                outputs = decode_status_coils(tail[4:])
                if outputs[2]:
                    continue
                action = BitAccess(
                    type="bitrd",
                    enable=expression_text(en),
                    word=decode_register(tail[:2]),
                    bit=int.from_bytes(tail[2:4], "big"),
                    output=outputs[0],
                    error=outputs[1],
                )
            else:
                en, secondary = decode_two_inputs(payload[:i])
                size = 6 if code == "f55a" else 12 if code == "f55e" else 4
                outputs = decode_status_coils(tail[size:])
                if outputs[1] or outputs[2]:
                    continue
                if code == "f544":
                    action = BitAccess(
                        type="bitwr",
                        enable=expression_text(en),
                        input_bit=expression_text(secondary),
                        word=decode_register(tail[2:4]),
                        bit=int.from_bytes(tail[:2], "big"),
                        error=outputs[0],
                    )
                elif code == "f55a":
                    if outputs[0]:
                        continue
                    action = AnalogConversion(
                        type="adcnv",
                        polarity=0,
                        enable=expression_text(en),
                        selector=expression_text(secondary),
                        count=int.from_bytes(tail[:2], "big"),
                        source=decode_register(tail[2:4]),
                        destination=decode_register(tail[4:6]),
                    )
                else:
                    action = AnalogConversion(
                        type="mlc",
                        enable=expression_text(en),
                        selector=expression_text(secondary),
                        source=decode_register(tail[:2]),
                        count=int.from_bytes(tail[2:4], "big"),
                        x_table=decode_register(tail[4:6]),
                        y_table=decode_register(tail[6:8]),
                        table_length=decode_register(tail[8:10]),
                        destination=decode_register(tail[10:12]),
                        overflow=outputs[0],
                    )
            if compile_analog(action) == payload:
                return Network(action=action)
        except ValueError:
            continue
    return None


def encode_label(target: str) -> bytes:
    """First ASCII byte, then pairs of seven-bit characters in big-endian words."""
    data = target.encode("ascii").ljust(7, b"\x00")
    return (
        b"\xef"
        + data[:1]
        + b"".join(((data[i] << 7) | data[i + 1]).to_bytes(2, "big") for i in (1, 3, 5))
    )
