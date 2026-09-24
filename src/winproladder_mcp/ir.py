"""Inferred semantic IR/compiler; unknown instruction families remain opaque."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .logic import (
    Expr,
    bit_address,
    compile_expression,
    contacts,
    decode_expression,
    device_name,
    evaluate,
    expression_text,
    negate,
    parse_expression,
)
from .registers import decode_register, encode_register, register_span


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Contact(Model):
    device: Literal["X", "Y", "M", "T", "C"]
    address: Annotated[int, Field(strict=True, ge=0, le=65535)]
    normally_closed: bool = False


class Step(Model):
    op: Literal["load", "and", "or"]
    contact: Contact


class Coil(Model):
    device: Literal["Y", "M"] = "Y"
    address: Annotated[int, Field(strict=True, ge=0, le=65535)]
    inverted: bool = False


class Timer(Model):
    type: Literal["timer"] = "timer"
    address: Annotated[int, Field(strict=True, ge=0, le=65535)]
    preset: Annotated[int, Field(strict=True, ge=0, le=65535)]
    time_base: Literal["0.01s"] = "0.01s"
    enable: str = "always_on"


class Counter(Model):
    type: Literal["counter"] = "counter"
    address: Annotated[int, Field(strict=True, ge=0, le=65535)]
    preset: Annotated[int, Field(strict=True, ge=0, le=65535)]
    pulse: str = "always_on"
    clear: str = "always_on"


class RegisterOr(Model):
    type: Literal["register_or"] = "register_or"
    sa: Annotated[int, Field(strict=True, ge=0, le=255)]
    sb: Annotated[int, Field(strict=True, ge=0, le=255)]
    destination: Annotated[int, Field(strict=True, ge=0, le=255)]
    enable: str = "always_on"


class ForLoop(Model):
    type: Literal["for"] = "for"
    count: Annotated[int, Field(strict=True, ge=1, le=16383)]


class LinearConversion(Model):
    """FUN33 LCNV. Md/L variations are inferred; pulse/indirect forms unsupported."""

    type: Literal["lcnv"] = "lcnv"
    mode: Annotated[int, Field(strict=True, ge=0, le=3)] = 0
    source: str
    table: str
    destination: str
    length: Annotated[int, Field(strict=True, ge=1, le=64)] = 1
    enable: str = "always_on"

    @property
    def table_words(self) -> int:
        return (4 if self.mode < 2 else 3) * (self.length if self.mode % 2 else 1)

    @model_validator(mode="after")
    def check_registers(self) -> "LinearConversion":
        register_span(self.source, self.length)
        register_span(self.table, self.table_words, writable=True)
        register_span(self.destination, self.length, writable=True)
        return self


class NextLoop(Model):
    type: Literal["next"] = "next"


class BreakLoop(Model):
    type: Literal["break"] = "break"
    enable: str = "always_on"


class Network(Model):
    """Left-associative logic steps, then coils. No implicit operator precedence."""

    steps: list[Step] = Field(default_factory=list, max_length=256)
    coils: list[Coil] = Field(default_factory=list, max_length=32)
    empty: bool = False
    comment: str = Field(default="", max_length=1000)
    block: Annotated[Timer | Counter, Field(discriminator="type")] | None = None
    condition: str | None = None
    action: (
        Annotated[
            RegisterOr | ForLoop | NextLoop | BreakLoop | LinearConversion,
            Field(discriminator="type"),
        ]
        | None
    ) = None


class Ladder(Model):
    profile: Literal["FBs-20MC", "FBs-24MA"] = "FBs-20MC"
    networks: list[Network] = Field(min_length=1, max_length=1000)
    symbols: dict[str, str] = Field(default_factory=dict, max_length=512)


class UnsupportedInstruction(ValueError):
    pass


# Exact exported networks, not extrapolated address/preset formulae.
# kind, address, preset, optional Y coil, raw payload, source network
BLOCK_CASES = (
    ("timer", 1, 100, 4, "4fe8fd80006403926ffcc104", "test.ldr N003"),
    ("timer", 2, 101, 0, "4fe8fd80006503946ffcc100", "test2.ldr N004"),
    ("timer", 1, 256, None, "4fe8fd8001000392", "test3.ldr N004"),
    ("timer", 2, 1000, None, "4fe8fd8003e80394", "test3.ldr N005"),
    ("timer", 3, 101, None, "4fe8fd8000650396", "test3.ldr N006"),
    ("counter", 1, 10, None, "4fe87fe8f940000a0592", "test3.ldr N007"),
    ("counter", 2, 16, None, "4fe87fe8f94000100594", "test3.ldr N008"),
    ("counter", 3, 17, None, "4fe87fe8f94000110596", "test3.ldr N009"),
)

# Independent payloads from test6, in display order. N008 is outside the screenshot;
# its operand labels are inferred from the four photographed rows' address pattern.
LCNV_PAYLOADS = {
    0: "4fe8f57c0000010019a247d00001",
    2: "4fe8f57c0000010219ac47d20001",
    4: "4fe8f57c0000010419b647d40001",
    6: "4fe8f57c0000010619c047d60001",
    8: "4fe8f57c0000010819ca47d80001",
}


def block_catalog() -> list[tuple[Network, bytes, str]]:
    result = []
    for kind, address, preset, output, raw, source in BLOCK_CASES:
        block = (
            Timer(address=address, preset=preset)
            if kind == "timer"
            else Counter(address=address, preset=preset)
        )
        network = Network(block=block, coils=[] if output is None else [Coil(address=output)])
        result.append((network, bytes.fromhex(raw), source))
    return result


# Compatibility decoder for the original flat IR. General decoding follows it.
OPCODES: dict[tuple[Literal["load", "and", "or"], Literal["X", "Y", "M", "T", "C"], bool], int] = {
    ("load", "X", False): 0x40,
    ("load", "X", True): 0x50,
    ("and", "X", False): 0x80,
    ("and", "X", True): 0x90,
    ("or", "X", False): 0xA0,
    ("load", "Y", False): 0x41,
    ("load", "Y", True): 0x51,
    ("and", "Y", False): 0x81,
    ("and", "Y", True): 0x91,
    ("load", "M", False): 0x48,
    ("load", "M", True): 0x58,
    ("and", "M", False): 0x88,
    ("load", "T", False): 0x42,
    ("load", "C", False): 0x43,
}


def operand(device: str, address: int) -> int:
    try:
        return bit_address(f"{device}{address}") & 255
    except ValueError as error:
        raise UnsupportedInstruction(str(error)) from error


def _decode_legacy(payload: bytes) -> Network | None:
    for network, raw, _ in block_catalog():
        if payload == raw:
            return network
    if payload == bytes.fromhex("5feb"):
        return Network(empty=True)
    if len(payload) % 2:
        return None
    inverse = {value: key for key, value in OPCODES.items()}
    steps = []
    coils = []
    try:
        for i in range(0, len(payload), 2):
            code, value = payload[i : i + 2]
            if code in {0xC1, 0xC8}:
                device: Literal["Y", "M"] = "Y" if code == 0xC1 else "M"
                coils.append(Coil(device=device, address=value if device == "Y" else value - 0x10))
            elif code in inverse and not coils:
                op, family, nc = inverse[code]
                steps.append(
                    Step(
                        op=op,
                        contact=Contact(
                            device=family,
                            address=value - 0x10 if family == "M" else value,
                            normally_closed=nc,
                        ),
                    )
                )
            else:
                return None
        network = Network(steps=steps, coils=coils)
        return network if compile_network(network) == payload else None
    except ValueError:
        return None


def network_expression(network: Network) -> Expr:
    if network.condition is not None:
        if network.steps:
            raise UnsupportedInstruction("Use condition or steps, not both")
        return parse_expression(network.condition)
    if not network.steps:
        raise UnsupportedInstruction("Network requires a condition or steps")
    expr: Expr | None = None
    for index, step in enumerate(network.steps):
        if (index == 0) != (step.op == "load"):
            raise UnsupportedInstruction("First step must be load; later steps must be and/or")
        term = Expr(
            "contact", f"{step.contact.device}{step.contact.address}", step.contact.normally_closed
        )
        bit_address(term.name)
        expr = term if expr is None else Expr(step.op, items=(expr, term))
    assert expr is not None
    return expr


def compile_coils(coils: list[Coil]) -> bytes:
    result = bytearray()
    for coil in coils:
        value = bit_address(f"{coil.device}{coil.address}")
        result.extend(((0xD0 if coil.inverted else 0xC0) + (value >> 8), value & 255))
    return bytes(result)


def compile_network(network: Network) -> bytes:
    try:
        if network.action is not None:
            if (
                network.empty
                or network.steps
                or network.coils
                or network.block
                or network.condition is not None
            ):
                raise UnsupportedInstruction(
                    "Action must occupy its own network; use action.enable"
                )
            action = network.action
            if isinstance(action, ForLoop):
                return bytes.fromhex("f590") + action.count.to_bytes(2, "big")
            if isinstance(action, NextLoop):
                return bytes.fromhex("f491")
            prefix = compile_expression(parse_expression(action.enable))
            if isinstance(action, BreakLoop):
                return prefix + bytes.fromhex("f476a7fe")
            if isinstance(action, LinearConversion):
                return (
                    prefix
                    + bytes.fromhex("f57c")
                    + action.mode.to_bytes(2, "big")
                    + encode_register(action.source)
                    + encode_register(action.table)
                    + encode_register(action.destination)
                    + action.length.to_bytes(2, "big")
                )
            return (
                prefix
                + bytes.fromhex("f4c8")
                + b"".join(
                    (0xA00 + 2 * n).to_bytes(2, "big")
                    for n in (action.sa, action.sb, action.destination)
                )
            )
        if network.empty:
            if network.steps or network.coils or network.block or network.condition is not None:
                raise UnsupportedInstruction("Empty network cannot have logic or outputs")
            return bytes.fromhex("5feb")
        if network.block is not None:
            if network.steps or network.condition is not None:
                raise UnsupportedInstruction("Block input logic belongs in enable/pulse/clear")
            block = network.block
            if block.address > 255:
                raise UnsupportedInstruction("Inferred block addresses are limited to 0..255")
            if isinstance(block, Timer):
                result = compile_expression(parse_expression(block.enable)) + bytes.fromhex("fd80")
                base = 0x390
            else:
                result = compile_expression(parse_expression(block.pulse))
                result += compile_expression(negate(parse_expression(block.clear)), nested=True)
                result += bytes.fromhex("f940")
                base = 0x590
            result += block.preset.to_bytes(2, "big") + (base + 2 * block.address).to_bytes(
                2, "big"
            )
            return result + (
                bytes.fromhex("6ffc") + compile_coils(network.coils) if network.coils else b""
            )
        if not network.coils:
            raise UnsupportedInstruction("Logic network requires at least one coil")
        return compile_expression(network_expression(network)) + compile_coils(network.coils)
    except ValueError as error:
        raise UnsupportedInstruction(str(error)) from error


def decode_coils(data: bytes) -> list[Coil]:
    if len(data) % 2:
        raise ValueError("Truncated coil")
    coils = []
    for i in range(0, len(data), 2):
        code, low = data[i : i + 2]
        if code & 0xE0 != 0xC0:
            raise ValueError("Unknown output instruction")
        name = device_name(((code & 15) << 8) + low)
        if name[0] not in {"Y", "M"}:
            raise ValueError("Unsupported coil family")
        coils.append(
            Coil.model_validate(
                {"device": name[0], "address": int(name[1:]), "inverted": bool(code & 0x10)}
            )
        )
    return coils


def decode_network(payload: bytes) -> Network | None:
    try:
        action: RegisterOr | ForLoop | NextLoop | BreakLoop | LinearConversion | None = None
        if payload == bytes.fromhex("f491"):
            action = NextLoop()
        elif len(payload) == 4 and payload[:2] == bytes.fromhex("f590"):
            action = ForLoop(count=int.from_bytes(payload[2:], "big"))
        elif payload.endswith(bytes.fromhex("f476a7fe")):
            action = BreakLoop(enable=expression_text(decode_expression(payload[:-4])))
        elif len(payload) >= 14 and payload[-12:-10] == bytes.fromhex("f57c"):
            action = LinearConversion(
                mode=int.from_bytes(payload[-10:-8], "big"),
                source=decode_register(payload[-8:-6]),
                table=decode_register(payload[-6:-4]),
                destination=decode_register(payload[-4:-2]),
                length=int.from_bytes(payload[-2:], "big"),
                enable=expression_text(decode_expression(payload[:-12])),
            )
        elif len(payload) >= 10 and payload[-8:-6] == bytes.fromhex("f4c8"):
            values = [
                int.from_bytes(payload[i : i + 2], "big") - 0xA00
                for i in range(len(payload) - 6, len(payload), 2)
            ]
            if any(v < 0 or v % 2 or v > 510 for v in values):
                return None
            action = RegisterOr(
                sa=values[0] // 2,
                sb=values[1] // 2,
                destination=values[2] // 2,
                enable=expression_text(decode_expression(payload[:-8])),
            )
        if action is not None:
            network = Network(action=action)
            return network if compile_network(network) == payload else None
    except ValueError:
        return None
    legacy = _decode_legacy(payload)
    if legacy is not None:
        return legacy
    try:
        markers = [
            i
            for i in range(0, len(payload) - 1, 2)
            if payload[i : i + 2] in {b"\xfd\x80", b"\xf9\x40"}
        ]
        if markers:
            if len(markers) != 1:
                return None
            i = markers[0]
            if i + 6 > len(payload):
                return None
            timer = payload[i : i + 2] == b"\xfd\x80"
            preset = int.from_bytes(payload[i + 2 : i + 4], "big")
            offset = int.from_bytes(payload[i + 4 : i + 6], "big") - (0x390 if timer else 0x590)
            if offset < 0 or offset % 2 or offset > 510:
                return None
            tail = payload[i + 6 :]
            if tail and (not tail.startswith(bytes.fromhex("6ffc")) or len(tail) < 4):
                return None
            coils = decode_coils(tail[2:]) if tail else []
            if timer:
                block: Timer | Counter = Timer(
                    address=offset // 2,
                    preset=preset,
                    enable=expression_text(decode_expression(payload[:i])),
                )
            else:
                candidates = []
                for split in range(2, i, 2):
                    if payload[split] & 0xE0 != 0x60:
                        continue
                    try:
                        pulse = decode_expression(payload[:split])
                        clear = negate(
                            decode_expression(
                                bytes([payload[split] - 0x20]) + payload[split + 1 : i]
                            )
                        )
                        candidates.append((pulse, clear))
                    except ValueError:
                        continue
                if len(candidates) != 1:
                    return None
                pulse, clear = candidates[0]
                block = Counter(
                    address=offset // 2,
                    preset=preset,
                    pulse=expression_text(pulse),
                    clear=expression_text(clear),
                )
            network = Network(block=block, coils=coils)
        else:
            split = next(
                (i for i in range(0, len(payload) - 1, 2) if payload[i] & 0xE0 == 0xC0),
                len(payload),
            )
            network = Network(
                condition=expression_text(decode_expression(payload[:split])),
                coils=decode_coils(payload[split:]),
            )
        return network if compile_network(network) == payload else None
    except (ValueError, RecursionError):
        return None


def start_stop(stop_normally_closed: bool = True) -> Ladder:
    return Ladder(
        networks=[
            Network(
                steps=[
                    Step(op="load", contact=Contact(device="Y", address=0)),
                    Step(op="or", contact=Contact(device="X", address=0)),
                    Step(
                        op="and",
                        contact=Contact(
                            device="X", address=1, normally_closed=stop_normally_closed
                        ),
                    ),
                ],
                coils=[Coil(device="Y", address=0)],
            )
        ]
    )


def validation(ladder: Ladder) -> dict[str, object]:
    errors = []
    payloads = []
    loops: list[int] = []
    instruction_evidence = []
    for index, network in enumerate(ladder.networks):
        if isinstance(network.action, ForLoop):
            loops.append(index)
            if len(loops) > 1:
                errors.append(f"N{index:03}: nested loop encoding is not established by test5")
        elif isinstance(network.action, NextLoop):
            if not loops:
                errors.append(f"N{index:03}: NEXT without FOR")
            else:
                loops.pop()
        elif isinstance(network.action, BreakLoop) and not loops:
            errors.append(f"N{index:03}: BREAK requires a FOR/NEXT loop")
        try:
            payload = compile_network(network)
            payloads.append(payload.hex(" "))
            if isinstance(network.action, LinearConversion):
                observed = next(
                    (i for i, raw in LCNV_PAYLOADS.items() if payload == bytes.fromhex(raw)), None
                )
                instruction_evidence.append(
                    {
                        "network_index": index,
                        "instruction": "FUN33 LCNV",
                        "status": "observed_export" if observed is not None else "inferred_variant",
                        "source": f"test6.ldr N{observed:03}"
                        if observed is not None
                        else "test6 + manual",
                        "operand_labels": "screenshot" if observed in {0, 2, 4, 6} else "inferred",
                        "gui_import_verified": False,
                    }
                )
        except ValueError as error:
            errors.append(f"N{index:03}: {error}")
    errors.extend(f"N{i:03}: FOR missing NEXT" for i in loops)
    verified = payloads == ["41 00 a0 00 90 01 c1 00"] and not errors
    coils = [f"{c.device}{c.address}" for n in ladder.networks for c in n.coils]
    warnings = [] if verified else ["Composition has not been verified by WinProLadder import."]
    if any(
        isinstance(n.action, (RegisterOr, ForLoop, NextLoop, BreakLoop)) for n in ladder.networks
    ):
        warnings.append(
            "test5-based inference: register OR supports 16-bit direct R0..R255 only; "
            "BREAK A7FE meaning is not independently established. "
            "No loop runtime verification; loops may trigger watchdog."
        )
    if any(isinstance(n.action, LinearConversion) for n in ladder.networks):
        warnings.append(
            "LCNV: test6 observes Md=0, L=1, R3840..3844 to D1000..1004. "
            "Other modes/lengths/registers/EN conditions are inferred, not GUI/PLC verified. "
            "Conversion table contents must already exist in the destination project; "
            "this LDR does not initialize those register values. No LCNV runtime simulation."
        )
    if len(coils) != len(set(coils)):
        warnings.append("Repeated coils: later networks may overwrite earlier network results.")
    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "payloads": payloads,
        "instruction_evidence": instruction_evidence,
        "block_evidence": [
            {"network_index": index, "source": source, "status": "observed_export"}
            for index, network in enumerate(ladder.networks)
            for observed, _, source in block_catalog()
            if network == observed
        ],
        "import_verified": verified,
        "verification_scope": (
            "User reported successful import of exact X1-NC start/stop payload; "
            "no PLC runtime verification."
        ),
    }


def simulate(
    ladder: Ladder, inputs: list[dict[str, bool]], initial: dict[str, bool]
) -> list[dict[str, bool]]:
    """Boolean-only scan model for this IR, not a PLC emulator."""
    result = validation(ladder)
    if not result["valid"]:
        raise UnsupportedInstruction(str(result["errors"]))
    if any(network.action is not None for network in ladder.networks):
        raise UnsupportedInstruction("Boolean simulation cannot execute register or loop actions")
    if any(network.block is not None for network in ladder.networks):
        raise UnsupportedInstruction("Boolean simulation cannot execute Timer/Counter blocks")
    if len(inputs) > 256 or len(initial) > 128:
        raise ValueError("Simulation limited to 256 scans and 128 initial devices")
    for key, value in initial.items():
        if not key or not key[1:].isdigit() or type(value) is not bool:
            raise ValueError("Initial state requires device names and boolean values")
        operand(key[0], int(key[1:]))
        if key != f"{key[0]}{int(key[1:])}":
            raise ValueError("Device names must be canonical, e.g. X0, not X00")
    state = dict(initial)
    x_devices = {
        name
        for network in ladder.networks
        if not network.empty
        for name in contacts(network_expression(network))
        if name.startswith("X")
    }
    x_devices.update(key for scan in inputs for key in scan)
    x_devices.update(key for key in initial if key.startswith("X"))
    trace = []
    for scan in inputs:
        if len(scan) > 256:
            raise ValueError("At most X0..X255 per scan")
        for key, value in scan.items():
            if not key.startswith("X") or not key[1:].isdigit() or type(value) is not bool:
                raise ValueError("Scan inputs must be boolean X devices")
            operand("X", int(key[1:]))
            if key != f"X{int(key[1:])}":
                raise ValueError("Device names must be canonical, e.g. X0, not X00")
        # Each scan is a fresh input snapshot; unspecified X inputs are false.
        for name in x_devices:
            state[name] = scan.get(name, False)
        for network in ladder.networks:
            if network.empty:
                continue
            power = evaluate(network_expression(network), state)
            for coil in network.coils:
                state[f"{coil.device}{coil.address}"] = not power if coil.inverted else power
        trace.append(dict(state))
    return trace
