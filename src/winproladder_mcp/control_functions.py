"""test16 control instructions. Unknown counter selectors stay opaque."""

from typing import TYPE_CHECKING

from .logic import compile_expression, decode_expression, expression_text, parse_expression
from .registers import decode_register, encode_register

if TYPE_CHECKING:
    from .ir import PID, Divide48, HighSpeedCounter, Network, SumWords, Watchdog


def compile_control(action: "Watchdog | HighSpeedCounter | Divide48 | SumWords | PID") -> bytes:
    from .ir import PID, Divide48, HighSpeedCounter, SumWords, Watchdog, compile_coils

    raw = compile_expression(parse_expression(action.enable))
    groups = []
    if isinstance(action, Watchdog):
        raw += bytes.fromhex("f5d1" if action.type == "wdt" else "f4f2")
        if action.setting is not None:
            raw += action.setting.to_bytes(2, "big")
    elif isinstance(action, HighSpeedCounter):
        raw += bytes.fromhex("f4e50000" if action.type == "hsctr" else "f7e7010000000000")
    elif isinstance(action, SumWords):
        raw += bytes.fromhex("f5c0") + action.count.to_bytes(2, "big")
        raw += encode_register(action.source) + encode_register(action.destination)
    elif isinstance(action, Divide48):
        if action.encoding == "two_inputs":
            raw += compile_expression(parse_expression(action.unsigned_when), nested=True)
        raw += bytes.fromhex("f46c" if action.encoding == "two_inputs" else "f474")
        raw += b"".join(encode_register(v) for v in [action.sa, action.sb, action.destination])
        groups = [action.zero, action.error]
    elif isinstance(action, PID):
        raw += compile_expression(parse_expression(action.bumpless), nested=True)
        raw += compile_expression(parse_expression(action.direction), nested=True)
        raw += bytes.fromhex("f517") + action.interval.to_bytes(2, "big")
        raw += b"".join(
            encode_register(v)
            for v in [action.setting, action.destination, action.parameters, action.work]
        )
        groups = [action.error, action.high, action.low]
    for i, coils in enumerate(groups):
        if coils:
            raw += (0x6FFC + i).to_bytes(2, "big") + compile_coils(coils)
    return raw


def decode_control(payload: bytes) -> "Network | None":
    from .ir import (
        PID,
        Divide48,
        HighSpeedCounter,
        Network,
        SumWords,
        Watchdog,
        decode_status_coils,
        decode_two_inputs,
    )

    for i in range(2, len(payload), 2):
        code, tail = payload[i : i + 2].hex(), payload[i + 2 :]
        if code not in {"f5d1", "f4f2", "f4e5", "f7e7", "f517", "f46c", "f474", "f5c0"}:
            continue
        try:
            action: Watchdog | HighSpeedCounter | Divide48 | SumWords | PID
            prefix = payload[:i]
            if code in {"f46c", "f474"}:
                en, us = (
                    decode_two_inputs(prefix)
                    if code == "f46c"
                    else (decode_expression(prefix), parse_expression("FALSE"))
                )
                outputs = decode_status_coils(tail[6:])
                if outputs[2]:
                    continue
                action = Divide48(
                    encoding="two_inputs" if code == "f46c" else "single_input",
                    enable=expression_text(en),
                    unsigned_when=expression_text(us),
                    sa=decode_register(tail[:2]),
                    sb=decode_register(tail[2:4]),
                    destination=decode_register(tail[4:6]),
                    zero=outputs[0],
                    error=outputs[1],
                )
            elif code == "f517":
                candidates = []
                for split in range(4, len(prefix), 2):
                    if prefix[split] & 0xE0 != 0x60:
                        continue
                    try:
                        en, bum = decode_two_inputs(prefix[:split])
                        dr = decode_expression(bytes([prefix[split] - 0x20]) + prefix[split + 1 :])
                        candidates.append((en, bum, dr))
                    except ValueError:
                        continue
                if len(candidates) != 1:
                    continue
                en, bum, dr = candidates[0]
                outputs = decode_status_coils(tail[10:])
                action = PID(
                    enable=expression_text(en),
                    bumpless=expression_text(bum),
                    direction=expression_text(dr),
                    interval=int.from_bytes(tail[:2], "big"),
                    setting=decode_register(tail[2:4]),
                    destination=decode_register(tail[4:6]),
                    parameters=decode_register(tail[6:8]),
                    work=decode_register(tail[8:10]),
                    error=outputs[0],
                    high=outputs[1],
                    low=outputs[2],
                )
            else:
                enable = expression_text(decode_expression(prefix))
                if code == "f5d1" and len(tail) == 2:
                    action = Watchdog.model_validate(
                        dict(type="wdt", enable=enable, setting=int.from_bytes(tail, "big"))
                    )
                elif code == "f4f2" and not tail:
                    action = Watchdog(type="rswdt", enable=enable)
                elif code == "f4e5" and tail == b"\x00\x00":
                    action = HighSpeedCounter(type="hsctr", enable=enable)
                elif code == "f7e7" and tail == bytes.fromhex("010000000000"):
                    action = HighSpeedCounter(type="hsctw", enable=enable, source=0, target="PV")
                elif code == "f5c0" and len(tail) == 6:
                    action = SumWords(
                        enable=enable,
                        count=int.from_bytes(tail[:2], "big"),
                        source=decode_register(tail[2:4]),
                        destination=decode_register(tail[4:6]),
                    )
                else:
                    continue
            if compile_control(action) == payload:
                return Network(action=action)
        except ValueError:
            continue
    return None
