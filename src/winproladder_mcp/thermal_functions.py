"""test19 accumulative timers, temperature control and opaque CALL anchor."""

from typing import TYPE_CHECKING

from .logic import bit_address, compile_expression, device_name, expression_text, parse_expression
from .registers import decode_register, decode_word, encode_register, encode_word

if TYPE_CHECKING:
    from .ir import AccumulativeTimer, Network, SampleCall, TemperatureControl

CALL_ANCHOR = bytes.fromhex("4fe8f78d672e188000000000")
TIMER_CODES = {10: 0xFC41, 100: 0xFC42, 1000: 0xFC43}
TP_FIELDS = ("setpoint", "offset", "proportional", "integral", "derivative", "destination", "work")


def compile_thermal(action: "AccumulativeTimer | TemperatureControl | SampleCall") -> bytes:
    from .ir import AccumulativeTimer, SampleCall, compile_coils

    if isinstance(action, SampleCall):
        return CALL_ANCHOR if action.target == "1" else bytes.fromhex("4fe8f78da7fe1c0000000000")
    if isinstance(action, AccumulativeTimer):
        raw = compile_expression(parse_expression(action.timing))
        raw += compile_expression(parse_expression(action.enable), nested=True)
        raw += TIMER_CODES[action.unit_ms].to_bytes(2, "big")
        raw += encode_register(action.pv) + encode_word(action.cv)
        groups = [action.done, action.not_done]
    else:
        raw = compile_expression(parse_expression(action.enable))
        raw += compile_expression(parse_expression(action.heat_cool), nested=True)
        raw += bytes.fromhex("f454") + bit_address(action.output).to_bytes(2, "big")
        raw += bytes([action.start, action.zones])
        raw += b"".join(encode_register(getattr(action, name)) for name in TP_FIELDS)
        groups = [action.error, action.alarm]
    for index, coils in enumerate(groups):
        if coils:
            raw += (0x6FFC + index).to_bytes(2, "big") + compile_coils(coils)
    return raw


def decode_thermal(payload: bytes) -> "Network | None":
    from .ir import (
        AccumulativeTimer,
        Network,
        SampleCall,
        TemperatureControl,
        decode_status_coils,
        decode_two_inputs,
    )

    if payload == bytes.fromhex("4fe8f78da7fe1c0000000000"):
        return Network(action=SampleCall(type="call", target="8"))
    if payload == CALL_ANCHOR:
        return Network(action=SampleCall(type="call"))
    for i in range(2, len(payload), 2):
        code = int.from_bytes(payload[i : i + 2], "big")
        if code not in {*TIMER_CODES.values(), 0xF454}:
            continue
        try:
            first, second = map(expression_text, decode_two_inputs(payload[:i]))
            tail = payload[i + 2 :]
            action: AccumulativeTimer | TemperatureControl
            if code in TIMER_CODES.values():
                groups = decode_status_coils(tail[4:])
                if groups[2]:
                    continue
                action = AccumulativeTimer.model_validate(
                    dict(
                        type="accumulative_timer",
                        timing=first,
                        enable=second,
                        unit_ms=next(k for k, v in TIMER_CODES.items() if v == code),
                        pv=decode_register(tail[:2]),
                        cv=decode_word(tail[2:4]),
                        done=groups[0],
                        not_done=groups[1],
                    )
                )
            else:
                if len(tail) < 18:
                    continue
                groups = decode_status_coils(tail[18:])
                if groups[2]:
                    continue
                action = TemperatureControl.model_validate(
                    dict(
                        type="tpctl",
                        enable=first,
                        heat_cool=second,
                        output=device_name(int.from_bytes(tail[:2], "big")),
                        start=tail[2],
                        zones=tail[3],
                        **{
                            name: decode_register(tail[4 + j * 2 : 6 + j * 2])
                            for j, name in enumerate(TP_FIELDS)
                        },
                        error=groups[0],
                        alarm=groups[1],
                    )
                )
            if compile_thermal(action) == payload:
                return Network(action=action)
        except ValueError:
            continue
    return None
