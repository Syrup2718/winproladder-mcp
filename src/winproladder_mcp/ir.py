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
from .registers import (
    comparison_word_references,
    decode_comparison_word,
    decode_register,
    decode_word,
    encode_comparison_word,
    encode_register,
    encode_word,
    register_span,
)


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
    mode: Literal["normal", "set", "reset"] = "normal"

    @model_validator(mode="after")
    def check_mode(self) -> "Coil":
        if self.mode != "normal" and self.inverted:
            raise ValueError("SET/RESET cannot also be an inverted coil")
        return self


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


class Arithmetic(Model):
    """test7: 16-bit register Sa, nonnegative immediate Sb, direct destination."""

    type: Literal["arithmetic"] = "arithmetic"
    operation: Literal["add", "sub", "mul", "div"]
    sa: str
    sb: Annotated[int, Field(strict=True, ge=0, le=32767)]
    destination: str
    enable: str = "always_on"
    unsigned_when: str = "FALSE"

    @property
    def destination_words(self) -> int:
        return 2 if self.operation in {"mul", "div"} else 1

    @model_validator(mode="after")
    def check_operands(self) -> "Arithmetic":
        register_span(self.sa, 1)
        register_span(self.destination, self.destination_words, writable=True)
        if self.operation == "div" and self.sb == 0:
            raise ValueError("Constant division by zero is not supported")
        return self


class EdgeContact(Model):
    kind: Literal["rising", "falling"]
    input: str = Field(pattern=r"^X(0|[1-9][0-9]{0,2})$")

    @model_validator(mode="after")
    def check_input(self) -> "EdgeContact":
        bit_address(self.input)
        return self


class RegisterStep(Model):
    type: Literal["increment", "decrement"]
    destination: str
    enable: str = "always_on"

    @model_validator(mode="after")
    def check_destination(self) -> "RegisterStep":
        register_span(self.destination, 1, writable=True)
        return self


class Bitwise(Model):
    type: Literal["bitwise"] = "bitwise"
    operation: Literal["and", "or"]
    sa: str
    sb: str
    destination: str
    enable: str = "always_on"

    @model_validator(mode="after")
    def check_registers(self) -> "Bitwise":
        register_span(self.sa, 1)
        register_span(self.sb, 1)
        register_span(self.destination, 1, writable=True)
        return self


class ExclusiveLogic(Model):
    """FUN35/36 word logic; sampled T1 is a numeric value, not a T contact."""

    type: Literal["exclusive_logic"] = "exclusive_logic"
    operation: Literal["xor", "xnr"]
    sa: str
    sb: str
    destination: str
    enable: str = "TRUE"

    @model_validator(mode="after")
    def check_words(self) -> "ExclusiveLogic":
        encode_word(self.sa)
        encode_word(self.sb)
        encode_word(self.destination, writable=True)
        return self


class WordConversion(Model):
    type: Literal["word_conversion"] = "word_conversion"
    operation: Literal["to_bcd", "to_bin"]
    source: str | Annotated[int, Field(strict=True, ge=0, le=9999)]
    destination: str
    enable: str = "TRUE"

    @model_validator(mode="after")
    def check_words(self) -> "WordConversion":
        if self.operation == "to_bcd":
            if not isinstance(self.source, int):
                raise ValueError("FUN20 currently supports constant source 0..9999 only")
        else:
            if not isinstance(self.source, str):
                raise ValueError("FUN21 requires a word source; constants are not supported")
            encode_word(self.source)
        encode_word(self.destination, writable=True)
        return self


class ZoneCompare(Model):
    type: Literal["zone_compare"] = "zone_compare"
    source: str
    upper: Annotated[int, Field(strict=True, ge=-32768, le=32767)]
    lower: Annotated[int, Field(strict=True, ge=-32768, le=32767)]
    enable: str = "TRUE"
    within: list[Coil] = Field(default_factory=list, max_length=32)
    above: list[Coil] = Field(default_factory=list, max_length=32)
    below: list[Coil] = Field(default_factory=list, max_length=32)

    @model_validator(mode="after")
    def check_operands(self) -> "ZoneCompare":
        register_span(self.source, 1)
        if self.lower > self.upper:
            raise ValueError("ZNCMP lower must not exceed upper")
        if any(c.mode != "normal" or c.inverted for c in self.within + self.above + self.below):
            raise ValueError("ZNCMP status outputs support normal coils only")
        return self


class Compare(Model):
    type: Literal["compare"] = "compare"
    sa: str
    sb: str
    enable: str = "always_on"
    unsigned_when: str = "FALSE"
    equal: list[Coil] = Field(default_factory=list, max_length=32)
    greater: list[Coil] = Field(default_factory=list, max_length=32)
    less: list[Coil] = Field(default_factory=list, max_length=32)

    @model_validator(mode="after")
    def check_operands(self) -> "Compare":
        register_span(self.sa, 1)
        register_span(self.sb, 1)
        if any(c.mode != "normal" or c.inverted for c in self.equal + self.greater + self.less):
            raise ValueError("CMP status outputs currently support normal coils only")
        return self


class ForLoop(Model):
    type: Literal["for"] = "for"
    count: Annotated[int, Field(strict=True, ge=1, le=16383)]


class MasterControl(Model):
    type: Literal["mc"] = "mc"
    number: Annotated[int, Field(strict=True, ge=0, le=127)]
    enable: str = "TRUE"


class MasterEnd(Model):
    type: Literal["mce"] = "mce"
    number: Annotated[int, Field(strict=True, ge=0, le=127)]


class Differential(Model):
    type: Literal["difu", "difd"]
    destination: str = Field(pattern=r"^[YM](0|[1-9][0-9]{0,2})$")
    trigger: str = "TRUE"

    @model_validator(mode="after")
    def check_destination(self) -> "Differential":
        bit_address(self.destination)
        return self


class UpDownCounter(Model):
    type: Literal["udctr"] = "udctr"
    cv: str
    preset: Annotated[int, Field(strict=True, ge=0, le=32767)]
    pulse: str
    up: str
    clear: str

    @model_validator(mode="after")
    def check_cv(self) -> "UpDownCounter":
        register_span(self.cv, 1, writable=True)
        return self


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


class ComparisonContact(Model):
    operation: Literal["eq", "gt", "lt", "ne", "ge", "le"]
    sa: str
    sb: str | Annotated[int, Field(strict=True, ge=0, le=32767)]

    @model_validator(mode="after")
    def check_operands(self) -> "ComparisonContact":
        encode_comparison_word(self.sa)
        if isinstance(self.sb, str):
            encode_comparison_word(self.sb)
        elif self.operation != "le":
            raise ValueError("Only chained FUN175 constant Sb is sampled")
        return self


class FloatOperation(Model):
    type: Literal["float_operation"] = "float_operation"
    operation: Literal["i_to_f", "f_to_i", "add", "sub", "mul"]
    sa: str
    sb: str | None = None
    destination: str
    enable: str = "TRUE"

    @property
    def source_words(self) -> int:
        return 1 if self.operation == "i_to_f" else 2

    @property
    def destination_words(self) -> int:
        return 1 if self.operation == "f_to_i" else 2

    @model_validator(mode="after")
    def check_operands(self) -> "FloatOperation":
        binary = self.operation in {"add", "sub", "mul"}
        if binary != (self.sb is not None):
            raise ValueError("Float arithmetic requires Sb; conversions forbid Sb")
        for name in [self.sa, self.sb, self.destination]:
            if name and name.startswith("R") and int(name[1:]) >= 3840:
                raise ValueError("Float operands currently support R0..3839 and D0..3999 only")
        register_span(self.sa, self.source_words)
        if self.sb is not None:
            register_span(self.sb, 2)
        register_span(self.destination, self.destination_words, writable=True)
        return self


class Network(Model):
    """Left-associative logic steps, then coils. No implicit operator precedence."""

    steps: list[Step] = Field(default_factory=list, max_length=256)
    coils: list[Coil] = Field(default_factory=list, max_length=32)
    empty: bool = False
    comment: str = Field(default="", max_length=1000)
    block: Annotated[Timer | Counter, Field(discriminator="type")] | None = None
    condition: str | None = None
    edge: EdgeContact | None = None
    direct_rail: bool = False
    branch_encoding: Literal["default", "test9_or"] = "default"
    comparison_chain: list[ComparisonContact] = Field(default_factory=list, max_length=32)
    action: (
        Annotated[
            RegisterOr
            | ForLoop
            | NextLoop
            | BreakLoop
            | LinearConversion
            | Arithmetic
            | RegisterStep
            | Bitwise
            | ExclusiveLogic
            | FloatOperation
            | WordConversion
            | ZoneCompare
            | Compare
            | MasterControl
            | MasterEnd
            | Differential
            | UpDownCounter,
            # test9 introduces native master control, pulse relays and register counting.
            Field(discriminator="type"),
        ]
        | None
    ) = None


HeaderProfile = Literal["FBs-20MC", "FBs-24MA", "FBs-24MA-test7", "FBs-32MA-test11"]


class Ladder(Model):
    profile: HeaderProfile = "FBs-20MC"
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

ARITHMETIC_OPCODES = {
    "add": b"\xf6\x62",
    "sub": b"\xf6\x64",
    "mul": b"\xf6\x66",
    "div": b"\xf6\x68",
}
ARITHMETIC_PAYLOADS = {
    1: "4fe87fe8f6620100000540c8",
    2: "4fe87fe8f66440c8000140ca",
    3: "4fe87fe8f66640cc000240ce",
    4: "4fe87fe8f6680102001440d2",
}
EDGE_PAYLOADS = {
    "e0004000c101": "test4.ldr N005 / test7.ldr N000",
    "e0005001c103": "test4.ldr N006",
}

TEST8_PAYLOADS = {
    0: "4fe8f4960ac8",
    1: "4fe8f4984190",
    2: "e00050000100",
    3: "4febd102",
    4: "4feb1103",
    5: "4fe87fe8f46a0100010200006ffcc8746ffdc8756ffec876",
    6: "4fe8f4c6010840f0412c",
}

TEST9_PAYLOADS = {
    0: "4810fc880000",
    1: "4201910061009201e422c100",
    2: "5201fd8000640392",
    3: "fc890000",
    4: "4811fc880002",
    5: "4fe8f8f60874",
    6: "4fe8fcf70875",
    7: "400160026003f10000640b90",
}


TEST10_PAYLOADS = {
    0: "4fe8f4ca13a442580adc",
    1: "4fe8f4cc0b9a03920bd2",
    2: "4fe8f7da0064fff601006ffcc1006ffdc1016ffec102",
    3: "4fe8f5a6014d0bbc",
    4: "4fe8f4a408000820",
}


TEST11_PAYLOADS = {
    0: "f47f00150a0428def47f002208850902f47f002341bc03940101",
    1: "f47f00180eb00f78f47f002503f40c58f67f0026059400641103",
    2: "4fe8f47f000000000aca0aca",
    3: "4fe8f47f00010acc40ce",
    4: "4fe8f47f000200000ad0000044560ac6",
    5: "4fe8f47f000300000a1200000a140acc",
    6: "4fe8f47f000400000a0000000a020a04",
}
COMPARISON_CHAIN_CODES = {"gt": 0x22, "lt": 0x23, "ge": 0x25, "le": 0x26}
COMPARISON_FIRST_CODES = {"eq": 0x15, "ne": 0x18}
FLOAT_CODES = {"i_to_f": 0, "f_to_i": 1, "add": 2, "sub": 3, "mul": 4}


def comparison_reads(network: Network) -> set[str]:
    reads: set[str] = set()
    for c in network.comparison_chain:
        reads |= comparison_word_references(c.sa)
        if isinstance(c.sb, str):
            reads |= comparison_word_references(c.sb)
    return reads


def network_coils(network: Network) -> list[Coil]:
    if isinstance(network.action, ZoneCompare):
        z = network.action
        return network.coils + z.within + z.above + z.below
    if isinstance(network.action, Differential):
        d = network.action.destination
        return [*network.coils, Coil.model_validate({"device": d[0], "address": int(d[1:])})]
    if isinstance(network.action, Compare):
        return network.coils + network.action.equal + network.action.greater + network.action.less
    return network.coils


def apply_coils(coils: list[Coil], power: bool, state: dict[str, bool]) -> None:
    """SET/RESET retain the previous bit when rung power is false."""
    for coil in coils:
        name = f"{coil.device}{coil.address}"
        if coil.mode == "normal":
            state[name] = not power if coil.inverted else power
        elif power:
            state[name] = coil.mode == "set"
        else:
            state.setdefault(name, False)


def decode_two_inputs(prefix: bytes) -> tuple[Expr, Expr]:
    candidates = []
    for split in range(2, len(prefix), 2):
        if prefix[split] & 0xE0 != 0x60:
            continue
        try:
            first = decode_expression(prefix[:split])
            second = decode_expression(bytes([prefix[split] - 0x20]) + prefix[split + 1 :])
            candidates.append((first, second))
        except ValueError:
            continue
    if len(candidates) != 1:
        raise ValueError("Ambiguous or unsupported function inputs")
    return candidates[0]


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
    if network.comparison_chain:
        raise UnsupportedInstruction(
            "Numeric comparison contacts require a register execution model"
        )
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
        base = {"set": 0x10, "reset": 0x00}.get(coil.mode, 0xD0 if coil.inverted else 0xC0)
        result.extend((base + (value >> 8), value & 255))
    return bytes(result)


def compile_network(network: Network) -> bytes:
    try:
        if network.comparison_chain:
            if (
                network.empty
                or network.steps
                or network.condition is not None
                or network.edge
                or network.action
                or network.block
                or network.direct_rail
                or network.branch_encoding != "default"
                or not network.coils
            ):
                raise UnsupportedInstruction("Comparison chain requires its own coil network")
            result = b""
            for index, c in enumerate(network.comparison_chain):
                codes = COMPARISON_FIRST_CODES if index == 0 else COMPARISON_CHAIN_CODES
                if c.operation not in codes or (index == 0 and isinstance(c.sb, int)):
                    raise UnsupportedInstruction(
                        "Sampled comparison placement: first eq/ne, subsequent gt/lt/ge/le only"
                    )
                result += bytes.fromhex("f67f" if isinstance(c.sb, int) else "f47f")
                result += codes[c.operation].to_bytes(2, "big") + encode_comparison_word(c.sa)
                result += (
                    c.sb.to_bytes(2, "big")
                    if isinstance(c.sb, int)
                    else encode_comparison_word(c.sb)
                )
            return result + compile_coils(network.coils)
        if network.branch_encoding == "test9_or":
            if (
                network.empty
                or network.action
                or network.block
                or network.edge
                or network.direct_rail
            ):
                raise UnsupportedInstruction("test9_or is only a two-branch Boolean coil network")
            expr = network_expression(network)
            if not (
                expr.op == "or"
                and len(expr.items) == 2
                and all(
                    item.op == "and"
                    and len(item.items) == 2
                    and all(t.op == "contact" for t in item.items)
                    for item in expr.items
                )
            ):
                raise UnsupportedInstruction("test9_or requires two branches of two contacts each")
        if network.direct_rail and (
            network.empty
            or network.action
            or network.block
            or network.edge
            or network.steps
            or network_expression(network).op != "true"
        ):
            raise UnsupportedInstruction("direct_rail requires a TRUE coil-only network")
        if network.edge is not None:
            if (
                network.empty
                or network.action
                or network.block
                or network.steps
                or network.condition is not None
                or not network.coils
            ):
                raise UnsupportedInstruction("Native edge requires its own network and coils")
            edge = network.edge
            load = Expr("contact", edge.input, edge.kind == "falling")
            return bytes.fromhex("e000") + compile_expression(load) + compile_coils(network.coils)
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
            if isinstance(action, MasterEnd):
                return bytes.fromhex("fc89") + action.number.to_bytes(2, "big")
            if isinstance(action, Differential):
                return (
                    compile_expression(parse_expression(action.trigger))
                    + bytes.fromhex("f8f6" if action.type == "difu" else "fcf7")
                    + bit_address(action.destination).to_bytes(2, "big")
                )
            if isinstance(action, UpDownCounter):
                return (
                    compile_expression(parse_expression(action.pulse))
                    + compile_expression(parse_expression(action.up), nested=True)
                    + compile_expression(parse_expression(action.clear), nested=True)
                    + bytes.fromhex("f100")
                    + action.preset.to_bytes(2, "big")
                    + encode_register(action.cv)
                )
            prefix = compile_expression(parse_expression(action.enable))
            if isinstance(action, ExclusiveLogic):
                return (
                    prefix
                    + bytes.fromhex("f4ca" if action.operation == "xor" else "f4cc")
                    + encode_word(action.sa)
                    + encode_word(action.sb)
                    + encode_word(action.destination, writable=True)
                )
            if isinstance(action, WordConversion):
                source = (
                    action.source.to_bytes(2, "big")
                    if isinstance(action.source, int)
                    else encode_word(action.source)
                )
                return (
                    prefix
                    + bytes.fromhex("f5a6" if action.operation == "to_bcd" else "f4a4")
                    + source
                    + encode_word(action.destination, writable=True)
                )
            if isinstance(action, ZoneCompare):
                result = (
                    prefix
                    + bytes.fromhex("f7da")
                    + action.upper.to_bytes(2, "big", signed=True)
                    + action.lower.to_bytes(2, "big", signed=True)
                    + encode_register(action.source)
                )
                for marker, coils in [
                    ("6ffc", action.within),
                    ("6ffd", action.above),
                    ("6ffe", action.below),
                ]:
                    if coils:
                        result += bytes.fromhex(marker) + compile_coils(coils)
                return result
            if isinstance(action, FloatOperation):
                result = (
                    prefix
                    + bytes.fromhex("f47f")
                    + FLOAT_CODES[action.operation].to_bytes(2, "big")
                )
                if action.operation == "f_to_i":
                    result += encode_register(action.sa)
                else:
                    result += b"\x00\x00" + encode_register(action.sa)
                    if action.sb is not None:
                        result += b"\x00\x00" + encode_register(action.sb)
                return result + encode_register(action.destination)
            if isinstance(action, MasterControl):
                return prefix + bytes.fromhex("fc88") + action.number.to_bytes(2, "big")
            if isinstance(action, BreakLoop):
                return prefix + bytes.fromhex("f476a7fe")
            if isinstance(action, RegisterStep):
                return (
                    prefix
                    + bytes.fromhex("f496" if action.type == "increment" else "f498")
                    + encode_register(action.destination)
                )
            if isinstance(action, Bitwise):
                return (
                    prefix
                    + bytes.fromhex("f4c6" if action.operation == "and" else "f4c8")
                    + encode_register(action.sa)
                    + encode_register(action.sb)
                    + encode_register(action.destination)
                )
            if isinstance(action, Compare):
                result = (
                    prefix
                    + compile_expression(parse_expression(action.unsigned_when), nested=True)
                    + bytes.fromhex("f46a")
                    + encode_register(action.sa)
                    + encode_register(action.sb)
                    + b"\x00\x00"
                )
                for marker, coils in [
                    ("6ffc", action.equal),
                    ("6ffd", action.greater),
                    ("6ffe", action.less),
                ]:
                    if coils:
                        result += bytes.fromhex(marker) + compile_coils(coils)
                return result
            if isinstance(action, Arithmetic):
                return (
                    prefix
                    + compile_expression(parse_expression(action.unsigned_when), nested=True)
                    + ARITHMETIC_OPCODES[action.operation]
                    + encode_register(action.sa)
                    + action.sb.to_bytes(2, "big")
                    + encode_register(action.destination)
                )
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
        prefix = (
            bytes.fromhex("4feb")
            if network.direct_rail
            else compile_expression(network_expression(network))
        )
        if network.branch_encoding == "test9_or":
            prefix = prefix.replace(bytes.fromhex("e443"), bytes.fromhex("e422"))
        return prefix + compile_coils(network.coils)
    except ValueError as error:
        raise UnsupportedInstruction(str(error)) from error


def decode_coils(data: bytes) -> list[Coil]:
    if len(data) % 2:
        raise ValueError("Truncated coil")
    coils = []
    for i in range(0, len(data), 2):
        code, low = data[i : i + 2]
        if code & 0xE0 not in {0xC0, 0x00}:
            raise ValueError("Unknown output instruction")
        name = device_name(((code & 15) << 8) + low)
        if name[0] not in {"Y", "M"}:
            raise ValueError("Unsupported coil family")
        coils.append(
            Coil.model_validate(
                {
                    "device": name[0],
                    "address": int(name[1:]),
                    "inverted": bool(code & 0x10) if code & 0xE0 == 0xC0 else False,
                    "mode": "normal" if code & 0xE0 == 0xC0 else "set" if code & 0x10 else "reset",
                }
            )
        )
    return coils


def decode_status_coils(tail: bytes) -> list[list[Coil]]:
    outputs: list[list[Coil]] = [[], [], []]
    markers = {bytes.fromhex("6ffc"): 0, bytes.fromhex("6ffd"): 1, bytes.fromhex("6ffe"): 2}
    while tail:
        index = markers.get(tail[:2])
        if index is None or outputs[index]:
            raise ValueError("Unknown or repeated function status output")
        end = next((j for j in range(2, len(tail), 2) if tail[j : j + 2] in markers), len(tail))
        coils = decode_coils(tail[2:end])
        if not coils:
            raise ValueError("Status output marker requires coils")
        outputs[index] = coils
        tail = tail[end:]
    return outputs


def decode_network(payload: bytes) -> Network | None:
    try:
        if payload[:2] == bytes.fromhex("f47f"):
            comparison_items = []
            offset11 = 0
            while payload[offset11 : offset11 + 2] in {b"\xf4\x7f", b"\xf6\x7f"}:
                chunk = payload[offset11 : offset11 + 8]
                if len(chunk) != 8:
                    return None
                code11 = int.from_bytes(chunk[2:4], "big")
                codes11 = COMPARISON_FIRST_CODES if offset11 == 0 else COMPARISON_CHAIN_CODES
                op11 = next((k for k, v in codes11.items() if v == code11), None)
                if op11 is None:
                    return None
                comparison_items.append(
                    ComparisonContact.model_validate(
                        {
                            "operation": op11,
                            "sa": decode_comparison_word(chunk[4:6]),
                            "sb": int.from_bytes(chunk[6:8], "big")
                            if chunk[0] == 0xF6
                            else decode_comparison_word(chunk[6:8]),
                        }
                    )
                )
                offset11 += 8
            n11 = Network(comparison_chain=comparison_items, coils=decode_coils(payload[offset11:]))
            return n11 if compile_network(n11) == payload else None
        for offset11 in range(2, len(payload) - 3, 2):
            if payload[offset11 : offset11 + 2] != b"\xf4\x7f":
                continue
            try:
                enable11 = expression_text(decode_expression(payload[:offset11]))
                code11 = int.from_bytes(payload[offset11 + 2 : offset11 + 4], "big")
                op_float = next((k for k, v in FLOAT_CODES.items() if v == code11), None)
                tail11 = payload[offset11 + 4 :]
                sb11 = None
                if op_float == "f_to_i" and len(tail11) == 4:
                    sa11 = decode_register(tail11[:2])
                elif op_float == "i_to_f" and len(tail11) == 6 and tail11[:2] == b"\x00\x00":
                    sa11 = decode_register(tail11[2:4])
                elif (
                    op_float in {"add", "sub", "mul"}
                    and len(tail11) == 10
                    and tail11[:2] == tail11[4:6] == b"\x00\x00"
                ):
                    sa11, sb11 = decode_register(tail11[2:4]), decode_register(tail11[6:8])
                else:
                    continue
                float_action = FloatOperation.model_validate(
                    {
                        "operation": op_float,
                        "sa": sa11,
                        "sb": sb11,
                        "destination": decode_register(tail11[-2:]),
                        "enable": enable11,
                    }
                )
                n11 = Network(action=float_action)
                if compile_network(n11) == payload:
                    return n11
            except ValueError:
                continue
        if len(payload) >= 6 and payload[:2] == bytes.fromhex("e000"):
            if payload[2] not in {0x40, 0x50}:
                return None
            edge_network = Network(
                edge=EdgeContact(
                    kind="rising" if payload[2] == 0x40 else "falling", input=f"X{payload[3]}"
                ),
                coils=decode_coils(payload[4:]),
            )
            return edge_network if compile_network(edge_network) == payload else None
        action: (
            RegisterOr
            | ForLoop
            | NextLoop
            | BreakLoop
            | LinearConversion
            | Arithmetic
            | RegisterStep
            | Bitwise
            | ExclusiveLogic
            | FloatOperation
            | WordConversion
            | ZoneCompare
            | Compare
            | MasterControl
            | MasterEnd
            | Differential
            | UpDownCounter
            | None
        ) = None
        candidates10 = []
        for i in range(2, len(payload), 2):
            opcode = payload[i : i + 2]
            if opcode not in {b"\xf4\xca", b"\xf4\xcc", b"\xf7\xda", b"\xf5\xa6", b"\xf4\xa4"}:
                continue
            try:
                enable10 = expression_text(decode_expression(payload[:i]))
                tail10 = payload[i + 2 :]
                candidate: ExclusiveLogic | WordConversion | ZoneCompare
                if opcode in {b"\xf4\xca", b"\xf4\xcc"}:
                    if len(tail10) != 6:
                        continue
                    candidate = ExclusiveLogic(
                        operation="xor" if opcode[-1] == 0xCA else "xnr",
                        sa=decode_word(tail10[:2]),
                        sb=decode_word(tail10[2:4]),
                        destination=decode_word(tail10[4:]),
                        enable=enable10,
                    )
                elif opcode in {b"\xf5\xa6", b"\xf4\xa4"}:
                    if len(tail10) != 4:
                        continue
                    candidate = WordConversion(
                        operation="to_bcd" if opcode[-1] == 0xA6 else "to_bin",
                        source=int.from_bytes(tail10[:2], "big")
                        if opcode[-1] == 0xA6
                        else decode_word(tail10[:2]),
                        destination=decode_word(tail10[2:]),
                        enable=enable10,
                    )
                else:
                    if len(tail10) < 6:
                        continue
                    flags = decode_status_coils(tail10[6:])
                    candidate = ZoneCompare(
                        source=decode_register(tail10[4:6]),
                        upper=int.from_bytes(tail10[:2], "big", signed=True),
                        lower=int.from_bytes(tail10[2:4], "big", signed=True),
                        enable=enable10,
                        within=flags[0],
                        above=flags[1],
                        below=flags[2],
                    )
                n10 = Network(action=candidate)
                if compile_network(n10) == payload:
                    candidates10.append(n10)
            except ValueError:
                continue
        if candidates10:
            return candidates10[0] if len(candidates10) == 1 else None
        if len(payload) == 4 and payload[:2] == bytes.fromhex("fc89"):
            action = MasterEnd(number=int.from_bytes(payload[2:], "big"))
        elif len(payload) >= 6 and payload[-4:-2] == bytes.fromhex("fc88"):
            action = MasterControl(
                number=int.from_bytes(payload[-2:], "big"),
                enable=expression_text(decode_expression(payload[:-4])),
            )
        elif len(payload) >= 6 and payload[-4:-2] in {b"\xf8\xf6", b"\xfc\xf7"}:
            action = Differential(
                type="difu" if payload[-4] == 0xF8 else "difd",
                destination=device_name(int.from_bytes(payload[-2:], "big")),
                trigger=expression_text(decode_expression(payload[:-4])),
            )
        elif len(payload) >= 12 and payload[-6:-4] == bytes.fromhex("f100"):
            prefix = payload[:-6]
            triples = []
            for split in range(4, len(prefix), 2):
                if prefix[split] & 0xE0 != 0x60:
                    continue
                try:
                    pulse, up = decode_two_inputs(prefix[:split])
                    clear = decode_expression(bytes([prefix[split] - 0x20]) + prefix[split + 1 :])
                    triples.append((pulse, up, clear))
                except ValueError:
                    continue
            if len(triples) != 1:
                return None
            pulse, up, clear = triples[0]
            action = UpDownCounter(
                cv=decode_register(payload[-2:]),
                preset=int.from_bytes(payload[-4:-2], "big"),
                pulse=expression_text(pulse),
                up=expression_text(up),
                clear=expression_text(clear),
            )
        if action is not None:
            network = Network(action=action)
            return network if compile_network(network) == payload else None
        cmp_candidates = []
        for position in range(4, len(payload) - 1, 2):
            if payload[position : position + 2] != bytes.fromhex("f46a"):
                continue
            try:
                first, second = decode_two_inputs(payload[:position])
                cmp_candidates.append((position, first, second))
            except ValueError:
                continue  # The word may be a timer/counter literal, not a CMP opcode.
        if cmp_candidates:
            if len(cmp_candidates) != 1:
                return None
            i, en, unsigned = cmp_candidates[0]
            if i + 8 > len(payload) or payload[i + 6 : i + 8] != b"\x00\x00":
                return None
            outputs: dict[str, list[Coil]] = {"equal": [], "greater": [], "less": []}
            tail = payload[i + 8 :]
            flag_markers = {
                bytes.fromhex("6ffc"): "equal",
                bytes.fromhex("6ffd"): "greater",
                bytes.fromhex("6ffe"): "less",
            }
            while tail:
                name = flag_markers.get(tail[:2])
                if name is None or outputs[name]:
                    return None
                end = next(
                    (j for j in range(2, len(tail), 2) if tail[j : j + 2] in flag_markers),
                    len(tail),
                )
                coils = decode_coils(tail[2:end])
                if not coils:
                    return None
                outputs[name] = coils
                tail = tail[end:]
            action = Compare(
                sa=decode_register(payload[i + 2 : i + 4]),
                sb=decode_register(payload[i + 4 : i + 6]),
                enable=expression_text(en),
                unsigned_when=expression_text(unsigned),
                equal=outputs["equal"],
                greater=outputs["greater"],
                less=outputs["less"],
            )
        elif len(payload) >= 6 and payload[-4:-2] in {b"\xf4\x96", b"\xf4\x98"}:
            action = RegisterStep(
                type="increment" if payload[-3] == 0x96 else "decrement",
                destination=decode_register(payload[-2:]),
                enable=expression_text(decode_expression(payload[:-4])),
            )
        elif payload == bytes.fromhex("f491"):
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
        elif len(payload) >= 12 and payload[-8:-6] in ARITHMETIC_OPCODES.values():
            en, unsigned = decode_two_inputs(payload[:-8])
            action = Arithmetic.model_validate(
                {
                    "operation": next(
                        k for k, v in ARITHMETIC_OPCODES.items() if v == payload[-8:-6]
                    ),
                    "sa": decode_register(payload[-6:-4]),
                    "sb": int.from_bytes(payload[-4:-2], "big"),
                    "destination": decode_register(payload[-2:]),
                    "enable": expression_text(en),
                    "unsigned_when": expression_text(unsigned),
                }
            )
        elif len(payload) >= 10 and payload[-8:-6] in {b"\xf4\xc6", b"\xf4\xc8"}:
            registers = [
                decode_register(payload[i : i + 2])
                for i in range(len(payload) - 6, len(payload), 2)
            ]
            enable = expression_text(decode_expression(payload[:-8]))
            if payload[-7] == 0xC8 and all(
                r.startswith("R") and int(r[1:]) <= 255 for r in registers
            ):
                action = RegisterOr(
                    sa=int(registers[0][1:]),
                    sb=int(registers[1][1:]),
                    destination=int(registers[2][1:]),
                    enable=enable,
                )
            else:
                action = Bitwise(
                    operation="and" if payload[-7] == 0xC6 else "or",
                    sa=registers[0],
                    sb=registers[1],
                    destination=registers[2],
                    enable=enable,
                )
        if action is not None:
            network = Network(action=action)
            return network if compile_network(network) == payload else None
    except ValueError:
        pass  # An opcode-looking word may be an operand in another known family.
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
                (i for i in range(0, len(payload) - 1, 2) if payload[i] & 0xE0 in {0xC0, 0x00}),
                len(payload),
            )
            network = Network(
                condition="TRUE"
                if payload[:split] == bytes.fromhex("4feb")
                else expression_text(
                    decode_expression(payload[:split].replace(b"\xe4\x22", b"\xe4\x43"))
                ),
                coils=decode_coils(payload[split:]),
                direct_rail=payload[:split] == bytes.fromhex("4feb"),
                branch_encoding="test9_or" if b"\xe4\x22" in payload[:split] else "default",
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
    masters: dict[int, int] = {}
    used_masters: set[int] = set()
    for index, network in enumerate(ladder.networks):
        if isinstance(network.action, MasterControl):
            number = network.action.number
            if number in used_masters:
                errors.append(f"N{index:03}: duplicate MC {number}")
            if masters:
                errors.append(
                    f"N{index:03}: nested/crossed MC regions are not supported for generation"
                )
            masters[number] = index
            used_masters.add(number)
        elif isinstance(network.action, MasterEnd):
            if network.action.number not in masters:
                errors.append(f"N{index:03}: MCE {network.action.number} without matching MC")
            masters.pop(network.action.number, None)
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
            if isinstance(network.action, (ExclusiveLogic, WordConversion, ZoneCompare)):
                observed10 = next(
                    (i for i, raw in TEST10_PAYLOADS.items() if payload.hex() == raw), None
                )
                instruction_evidence.append(
                    {
                        "network_index": index,
                        "instruction": network.action.type,
                        "status": "observed_export"
                        if observed10 is not None
                        else "inferred_variant",
                        "source": f"test10.ldr N{observed10:03}"
                        if observed10 is not None
                        else "test10",
                        "gui_import_verified": False,
                    }
                )
            if network.comparison_chain or isinstance(network.action, FloatOperation):
                observed11 = next(
                    (i for i, raw in TEST11_PAYLOADS.items() if payload.hex() == raw), None
                )
                instruction_evidence.append(
                    {
                        "network_index": index,
                        "instruction": "comparison_chain"
                        if network.comparison_chain
                        else "float_operation",
                        "status": "observed_export"
                        if observed11 is not None
                        else "inferred_variant",
                        "source": f"test11.ldr N{observed11:03}"
                        if observed11 is not None
                        else "test11",
                        "gui_import_verified": False,
                    }
                )
            observed9 = next((i for i, raw in TEST9_PAYLOADS.items() if payload.hex() == raw), None)
            if observed9 is not None or isinstance(
                network.action, (MasterControl, MasterEnd, Differential, UpDownCounter)
            ):
                instruction_evidence.append(
                    {
                        "network_index": index,
                        "instruction": network.action.type
                        if network.action
                        else "test9 Boolean/Timer",
                        "status": "observed_export"
                        if observed9 is not None
                        else "inferred_variant",
                        "source": f"test9.ldr N{observed9:03}"
                        if observed9 is not None
                        else "test9",
                        "gui_import_verified": False,
                    }
                )
            observed8 = next((i for i, raw in TEST8_PAYLOADS.items() if payload.hex() == raw), None)
            if (
                observed8 is not None
                or isinstance(network.action, (RegisterStep, Bitwise, Compare))
                or network.direct_rail
                or (not network.comparison_chain and any(c.mode != "normal" for c in network.coils))
            ):
                instruction_evidence.append(
                    {
                        "network_index": index,
                        "instruction": network.action.type
                        if network.action
                        else "native coil/rail",
                        "status": "observed_export"
                        if observed8 is not None
                        else "inferred_variant",
                        "source": f"test8.ldr N{observed8:03}"
                        if observed8 is not None
                        else "test8 + prior samples",
                        "gui_import_verified": False,
                    }
                )
            if observed8 is None and (
                isinstance(network.action, Arithmetic) or network.edge is not None
            ):
                if isinstance(network.action, Arithmetic):
                    instruction = f"16-bit {network.action.operation}"
                else:
                    assert network.edge is not None
                    instruction = f"native {network.edge.kind} edge"
                source = (
                    EDGE_PAYLOADS.get(payload.hex())
                    if network.edge
                    else next(
                        (
                            f"test7.ldr N{i:03}"
                            for i, raw in ARITHMETIC_PAYLOADS.items()
                            if payload.hex() == raw
                        ),
                        None,
                    )
                )
                instruction_evidence.append(
                    {
                        "network_index": index,
                        "instruction": instruction,
                        "status": "observed_export" if source else "inferred_variant",
                        "source": source or "test4/test7 + FBs manual",
                        "gui_import_verified": False,
                    }
                )
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
    errors.extend(f"N{i:03}: MC {number} missing MCE {number}" for number, i in masters.items())
    verified = payloads == ["41 00 a0 00 90 01 c1 00"] and not errors
    coils = [f"{c.device}{c.address}" for n in ladder.networks for c in network_coils(n)]
    warnings = [] if verified else ["Composition has not been verified by WinProLadder import."]
    if any(
        isinstance(n.action, (MasterControl, MasterEnd, Differential, UpDownCounter))
        for n in ladder.networks
    ):
        warnings.append(
            "test9: MC/MCE, DIFU/DIFD and 16-bit 07P.UDCTR encodings observed. "
            "Changed operands/conditions are inferred; no built-in runtime simulation. "
            "UDCTR clear uses direct polarity; never substitute ordinary Counter CLR encoding."
        )
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
    if any(isinstance(n.action, Arithmetic) for n in ladder.networks):
        warnings.append(
            "Arithmetic: test7 observes register Sa, positive constant Sb, EN=TRUE, U/S=FALSE. "
            "Changed operands/EN/U/S are inferred. MUL/DIV write two consecutive words. "
            "No arithmetic runtime simulation or connected status outputs; no GUI/PLC verification."
        )
    if any(
        isinstance(n.action, (ExclusiveLogic, WordConversion, ZoneCompare)) for n in ladder.networks
    ):
        warnings.append(
            "test10 functions: sampled 16-bit forms only; other operands/conditions "
            "are inferred. No D/P forms, additional flag wiring or runtime simulation. "
            "WX0/WY0 cover X0..15/Y0..15; T operands denote numeric timer words."
        )
    if any(n.comparison_chain or isinstance(n.action, FloatOperation) for n in ladder.networks):
        warnings.append(
            "test11: sampled comparison-chain positions and float subcodes only; "
            "parameter changes are inferred. No D/P, indirect, ERR wiring or runtime model. "
            "Unknown zero fields preserved; float values occupy two consecutive words."
        )
    if any(isinstance(n.action, (RegisterStep, Bitwise, Compare)) for n in ladder.networks):
        warnings.append(
            "test8 establishes INC F496, DEC F498, CMP F46A and AND F4C6. "
            "CMP reserved 0000 is preserved; its meaning is unknown. "
            "Other operands/conditions/status connections are inferred. "
            "No register-action runtime simulation or generated-file GUI/PLC verification."
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
    if any(network.action is not None or network.comparison_chain for network in ladder.networks):
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
        if not network.empty and network.edge is None
        for name in contacts(network_expression(network))
        if name.startswith("X")
    }
    x_devices.update(key for scan in inputs for key in scan)
    x_devices.update(key for key in initial if key.startswith("X"))
    x_devices.update(n.edge.input for n in ladder.networks if n.edge is not None)
    previous = {
        i: initial.get(n.edge.input, False)
        for i, n in enumerate(ladder.networks)
        if n.edge is not None
    }
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
        for index, network in enumerate(ladder.networks):
            if network.empty:
                continue
            if network.edge is not None:
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
