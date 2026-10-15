"""Inferred semantic IR/compiler; unknown instruction families remain opaque."""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .floating import (
    decode_float_register,
    decode_float_source,
    encode_float_register,
    encode_float_source,
    float_span,
    normalize_float_source,
)
from .instruction_catalog import (
    ARITHMETIC_OPCODES as ARITHMETIC_OPCODES,
)
from .instruction_catalog import (
    ARITHMETIC_PAYLOADS as ARITHMETIC_PAYLOADS,
)
from .instruction_catalog import (
    BLOCK_CASES as BLOCK_CASES,
)
from .instruction_catalog import (
    COMPARISON_CHAIN_CODES as COMPARISON_CHAIN_CODES,
)
from .instruction_catalog import (
    COMPARISON_FIRST_CODES as COMPARISON_FIRST_CODES,
)
from .instruction_catalog import (
    EDGE_PAYLOADS as EDGE_PAYLOADS,
)
from .instruction_catalog import (
    FLOAT_CODES as FLOAT_CODES,
)
from .instruction_catalog import (
    LCNV_PAYLOADS as LCNV_PAYLOADS,
)
from .instruction_catalog import (
    PERIPHERAL_CODES as PERIPHERAL_CODES,
)
from .instruction_catalog import (
    PERIPHERAL_FIELDS as PERIPHERAL_FIELDS,
)
from .instruction_catalog import (
    TEST8_PAYLOADS as TEST8_PAYLOADS,
)
from .instruction_catalog import (
    TEST9_PAYLOADS as TEST9_PAYLOADS,
)
from .instruction_catalog import (
    TEST10_PAYLOADS as TEST10_PAYLOADS,
)
from .instruction_catalog import (
    TEST11_PAYLOADS as TEST11_PAYLOADS,
)
from .instruction_catalog import (
    TEST12_PAYLOADS as TEST12_PAYLOADS,
)
from .instruction_catalog import (
    TEST13_PAYLOADS as TEST13_PAYLOADS,
)
from .instruction_catalog import (
    TEST14_PAYLOADS as TEST14_PAYLOADS,
)
from .instruction_catalog import (
    TEST15_PAYLOADS as TEST15_PAYLOADS,
)
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
from .peripheral import bit_span, decode_peripheral_word, peripheral_word, peripheral_words
from .profiles import HeaderProfile as HeaderProfile
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

FloatSource = str | Annotated[float, Field(strict=True)]


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
    operation: Literal[
        "i_to_f",
        "f_to_i",
        "add",
        "sub",
        "mul",
        "div",
        "sqrt",
        "sin",
        "cos",
        "tan",
        "neg",
        "abs",
        "ln",
        "exp",
        "log",
        "pow",
        "asin",
        "acos",
        "atan",
    ]
    sa: FloatSource | None = None
    sb: FloatSource | None = None
    destination: str
    enable: str = "TRUE"
    error: list[Coil] = Field(default_factory=list, max_length=32)

    @property
    def source_words(self) -> int:
        return 1 if self.operation in {"i_to_f", "sin", "cos", "tan"} else 2

    @property
    def destination_words(self) -> int:
        return 1 if self.operation == "f_to_i" else 2

    @model_validator(mode="after")
    def check_operands(self) -> "FloatOperation":
        if self.error:
            if self.operation in {"neg", "abs", "i_to_f", "f_to_i"}:
                raise ValueError("ERR wiring is not supported on this operation")
            if any(c.mode != "normal" or c.inverted for c in self.error):
                raise ValueError("ERR supports normal coils only")
        float_span(self.destination, self.destination_words)
        if self.operation in {"neg", "abs"}:
            if self.sa is not None or self.sb is not None:
                raise ValueError("FNEG/FABS operate in place; specify destination only")
            return self
        if self.sa is None:
            raise ValueError("This float operation requires Sa")
        if self.operation in {"sin", "cos", "tan"}:
            if self.sb is not None:
                raise ValueError("Trigonometric operations forbid Sb")
            if isinstance(self.sa, str):
                float_span(self.sa, 1)
            elif not self.sa.is_integer() or not -18000 <= self.sa <= 18000:
                raise ValueError("Angle must be an integer -18000..18000 in 0.01 degree units")
            return self
        self.sa = normalize_float_source(self.sa)
        if self.sb is not None:
            self.sb = normalize_float_source(self.sb)
        binary = self.operation in {"add", "sub", "mul", "div", "pow"}
        if binary != (self.sb is not None):
            raise ValueError("Binary float operations require Sb; unary operations forbid it")
        if self.operation in {"i_to_f", "f_to_i"}:
            if not isinstance(self.sa, str):
                raise ValueError("Integer/float conversions currently require register sources")
            float_span(self.sa, self.source_words)
        else:
            encode_float_source(self.sa)
        if self.sb is not None:
            encode_float_source(self.sb)
        if self.operation == "div" and isinstance(self.sb, float) and self.sb == 0:
            raise ValueError("Constant division by zero")
        if self.operation in {"ln", "exp", "log", "pow", "asin", "acos", "atan"}:
            for operand in [self.sa, self.sb, self.destination]:
                if isinstance(operand, str) and operand.startswith("D") and int(operand[1:]) > 3998:
                    raise ValueError(
                        "This instruction manual D bank ends at D3999; reserve two words"
                    )
            if self.operation in {"ln", "log"} and isinstance(self.sa, float) and self.sa <= 0:
                raise ValueError("Constant logarithm requires a positive source")
        if (
            self.operation in {"asin", "acos"}
            and isinstance(self.sa, float)
            and not -1 <= self.sa <= 1
        ):
            raise ValueError("Inverse sine/cosine constant must be -1..1")
        if self.operation == "sqrt" and isinstance(self.sa, float) and self.sa < 0:
            raise ValueError("Constant square root of negative value")
        float_span(self.destination, self.destination_words)
        return self


class FloatCompare(Model):
    type: Literal["float_compare"] = "float_compare"
    sa: FloatSource
    sb: FloatSource
    enable: str = "TRUE"
    equal: list[Coil] = Field(default_factory=list, max_length=32)
    greater: list[Coil] = Field(default_factory=list, max_length=32)
    less: list[Coil] = Field(default_factory=list, max_length=32)

    @model_validator(mode="after")
    def check_operands(self) -> "FloatCompare":
        self.sa = normalize_float_source(self.sa)
        self.sb = normalize_float_source(self.sb)
        encode_float_source(self.sa)
        encode_float_source(self.sb)
        if any(c.mode != "normal" or c.inverted for c in self.equal + self.greater + self.less):
            raise ValueError("FCMP supports normal output coils only")
        return self


class FloatZoneCompare(Model):
    type: Literal["float_zone_compare"] = "float_zone_compare"
    source: str
    upper: FloatSource
    lower: FloatSource
    enable: str = "TRUE"
    within: list[Coil] = Field(default_factory=list, max_length=32)
    above: list[Coil] = Field(default_factory=list, max_length=32)
    below: list[Coil] = Field(default_factory=list, max_length=32)

    @model_validator(mode="after")
    def check_operands(self) -> "FloatZoneCompare":
        self.upper = normalize_float_source(self.upper)
        self.lower = normalize_float_source(self.lower)
        float_span(self.source, 2)
        encode_float_source(self.upper)
        encode_float_source(self.lower)
        if (
            isinstance(self.upper, float)
            and isinstance(self.lower, float)
            and self.lower > self.upper
        ):
            raise ValueError("FZCP lower exceeds upper")
        if any(c.mode != "normal" or c.inverted for c in self.within + self.above + self.below):
            raise ValueError("FZCP supports normal output coils only")
        return self


class ImmediateIO(Model):
    type: Literal["imdio"] = "imdio"
    start: str
    count: Annotated[int, Field(strict=True, ge=1, le=36)]
    enable: str = "TRUE"

    @model_validator(mode="after")
    def check_span(self) -> "ImmediateIO":
        bit_address(self.start)
        if self.start[0] not in "XY":
            raise ValueError("IMDIO requires X or Y start")
        maximum = 35 if self.start[0] == "X" else 23
        if int(self.start[1:]) + self.count - 1 > maximum:
            raise ValueError("IMDIO exceeds maximum main-unit I/O range in manual")
        return self

    def devices(self) -> set[str]:
        start = int(self.start[1:])
        return {f"{self.start[0]}{i}" for i in range(start, start + self.count)}


class PeripheralIO(Model):
    type: Literal["tkey", "hkey", "dsw", "7sgdl", "muxi"]
    input: str | None = None
    output: str | None = None
    destination: str | None = None
    key_start: str | None = None
    work: str | None = None
    source: str | None = None
    mode: Annotated[int, Field(strict=True, ge=0, le=3)] | None = None
    rows: Annotated[int, Field(strict=True, ge=2, le=8)] | None = None
    enable: str = "TRUE"
    pressed: list[Coil] = Field(default_factory=list, max_length=32)
    function_pressed: list[Coil] = Field(default_factory=list, max_length=32)
    done: list[Coil] = Field(default_factory=list, max_length=32)
    error: list[Coil] = Field(default_factory=list, max_length=32)

    def statuses(self) -> list[list[Coil]]:
        if self.type == "tkey":
            return [self.pressed]
        if self.type == "hkey":
            return [self.pressed, self.function_pressed]
        if self.type == "dsw":
            return [self.done, self.error]
        return [self.done]

    def input_devices(self) -> set[str]:
        if self.input is None:
            return set()
        return bit_span(
            self.input, 10 if self.type == "tkey" else 8 if self.type == "muxi" else 4, "X"
        )

    def output_devices(self) -> set[str]:
        if self.output is None:
            return set()
        return bit_span(
            self.output,
            8
            if self.type == "7sgdl"
            else self.rows
            if self.type == "muxi" and self.rows is not None
            else 4,
            "Y",
        )

    def key_devices(self) -> set[str]:
        return (
            bit_span(self.key_start, 10 if self.type == "tkey" else 16, "YM")
            if self.key_start
            else set()
        )

    def work_devices(self) -> set[str]:
        return (
            register_span(self.work, 2 if self.type == "dsw" else 1, writable=True)
            if self.work
            else set()
        )

    def destination_devices(self) -> set[str]:
        count = (self.rows + 1) // 2 if self.type == "muxi" and self.rows is not None else 1
        return (
            peripheral_words(self.destination, count, writable=True) if self.destination else set()
        )

    @model_validator(mode="after")
    def check_operands(self) -> "PeripheralIO":
        expected = {
            "tkey": {"input", "destination", "key_start"},
            "hkey": {"input", "output", "destination", "key_start", "work"},
            "dsw": {"input", "output", "destination", "work"},
            "7sgdl": {"source", "output", "mode", "work"},
            "muxi": {"input", "output", "rows", "destination", "work"},
        }[self.type]
        for name in [
            "input",
            "output",
            "destination",
            "key_start",
            "work",
            "source",
            "mode",
            "rows",
        ]:
            if (getattr(self, name) is not None) != (name in expected):
                raise ValueError(f"{self.type}: incorrect or missing operand {name}")
        allowed = {
            "tkey": {"pressed"},
            "hkey": {"pressed", "function_pressed"},
            "dsw": {"done", "error"},
            "7sgdl": {"done"},
            "muxi": {"done"},
        }[self.type]
        for name in ["pressed", "function_pressed", "done", "error"]:
            if getattr(self, name) and name not in allowed:
                raise ValueError(f"{self.type}: invalid status {name}")
        if any(c.mode != "normal" or c.inverted for group in self.statuses() for c in group):
            raise ValueError("Peripheral status outputs require normal coils")
        self.input_devices()
        self.output_devices()
        self.key_devices()
        self.work_devices()
        self.destination_devices()
        if self.source:
            peripheral_words(self.source)
        other = self.destination_devices() | (
            peripheral_words(self.source) if self.source else set()
        )
        if self.work_devices() & other:
            raise ValueError("Peripheral WR cannot overlap source/destination")
        return self


class Watchdog(Model):
    type: Literal["wdt", "rswdt"]
    enable: str = "TRUE"
    setting: Literal[50, 60, 70, 80, 90, 100, 110, 120] | None = None

    @model_validator(mode="after")
    def check(self) -> "Watchdog":
        if (self.type == "wdt") != (self.setting is not None):
            raise ValueError("WDT requires setting; RSWDT has no operand")
        parse_expression(self.enable)
        return self


class HighSpeedCounter(Model):
    """Exact HSC0 read / double-word constant-zero PV write anchors only."""

    type: Literal["hsctr", "hsctw"]
    enable: str = "TRUE"
    counter: Literal["HSC0"] = "HSC0"
    source: Literal[0] | None = None
    target: Literal["PV"] | None = None

    @model_validator(mode="after")
    def check(self) -> "HighSpeedCounter":
        if self.type == "hsctw":
            if self.source != 0 or self.target != "PV":
                raise ValueError("HSCTW currently requires sampled S=0, CN=HSC0, D=PV")
        elif self.source is not None or self.target is not None:
            raise ValueError("HSCTR has no source/target operands")
        parse_expression(self.enable)
        return self


class Divide48(Model):
    encoding: Literal["two_inputs", "single_input"] = "two_inputs"
    type: Literal["div48"] = "div48"
    enable: str = "TRUE"
    unsigned_when: str = "FALSE"
    sa: str
    sb: str
    destination: str
    zero: list[Coil] = Field(default_factory=list, max_length=32)
    error: list[Coil] = Field(default_factory=list, max_length=32)

    @model_validator(mode="after")
    def check(self) -> "Divide48":
        if self.encoding == "single_input" and self.unsigned_when != "FALSE":
            raise ValueError("Single-input DIV48 has no U/S pin; signedness is not inferred")
        for name in [self.sa, self.sb, self.destination]:
            register_span(name, 3, writable=True)
        for coil in self.zero + self.error:
            if coil.mode != "normal" or coil.inverted:
                raise ValueError("DIV48 status outputs require normal coils")
        parse_expression(self.enable)
        parse_expression(self.unsigned_when)
        return self


class SumWords(Model):
    type: Literal["sum"] = "sum"
    enable: str = "TRUE"
    source: str
    count: Annotated[int, Field(strict=True, ge=1, le=511)]
    destination: str

    @model_validator(mode="after")
    def check(self) -> "SumWords":
        register_span(self.source, self.count)
        register_span(self.destination, 1, writable=True)
        parse_expression(self.enable)
        return self


class PID(Model):
    """FUN30: enable denotes A/M, not an execution enable pin. Ts is in 10 ms units."""

    type: Literal["pid"] = "pid"
    enable: str = "TRUE"
    bumpless: str = "FALSE"
    direction: str = "TRUE"
    interval: Annotated[int, Field(strict=True, ge=1, le=3000)]
    setting: str
    destination: str
    parameters: str
    work: str
    error: list[Coil] = Field(default_factory=list, max_length=32)
    high: list[Coil] = Field(default_factory=list, max_length=32)
    low: list[Coil] = Field(default_factory=list, max_length=32)

    def work_devices(self) -> set[str]:
        return register_span(self.work, 5, writable=True)

    @model_validator(mode="after")
    def check(self) -> "PID":
        blocks = [
            register_span(n, size, writable=True)
            for n, size in [
                (self.setting, 8),
                (self.destination, 1),
                (self.parameters, 7),
                (self.work, 5),
            ]
        ]
        if blocks[-1] & set().union(*blocks[:-1]):
            raise ValueError("PID WR cannot overlap SR/OR/PR")
        for coil in self.error + self.high + self.low:
            if coil.mode != "normal" or coil.inverted:
                raise ValueError("PID status outputs require normal coils")
        for expr in [self.enable, self.bumpless, self.direction]:
            parse_expression(expr)
        return self


class IntegerFunction(Model):
    type: Literal["mean", "sqrt", "neg", "abs", "ext", "crc16"]
    enable: str = "TRUE"
    source: str | None = None
    count: str | Annotated[int, Field(strict=True, ge=1, le=256)] | None = None
    destination: str
    mode: Literal[1] | None = None
    zero: list[Coil] = Field(default_factory=list, max_length=32)
    error: list[Coil] = Field(default_factory=list, max_length=32)

    def source_devices(self) -> set[str]:
        if self.type in {"neg", "abs", "ext"}:
            return {self.destination}
        assert self.source is not None
        if self.type == "mean":
            assert isinstance(self.count, str)
            # Runtime N may select any valid length 2..256. Never treat the
            # count register address as its value or silently assume N=2.
            return register_span(self.source, 256) | {self.count}
        return register_span(self.source, self.count if isinstance(self.count, int) else 1)

    def destination_devices(self) -> set[str]:
        return register_span(
            self.destination, 2 if self.type in {"ext", "crc16"} else 1, writable=True
        )

    @model_validator(mode="after")
    def check(self) -> "IntegerFunction":
        required_source = self.type in {"mean", "sqrt", "crc16"}
        if required_source != (self.source is not None):
            raise ValueError("Source required only for MEAN, SQRT and CRC16")
        if self.type == "mean":
            if not isinstance(self.count, str):
                raise ValueError("MEAN currently requires register N; runtime valid range 2..256")
            register_span(self.count, 1)
        elif self.type == "crc16":
            if not isinstance(self.count, int) or self.mode != 1:
                raise ValueError("CRC16 currently requires constant N=1..256 and sampled MD=1")
        elif self.count is not None:
            raise ValueError("Count is only supported for MEAN/CRC16")
        if self.type != "crc16" and (self.mode is not None or self.zero):
            raise ValueError("Only CRC16 supports mode and zero status")
        if self.type in {"neg", "abs", "ext"} and self.error:
            raise ValueError("In-place integer operations have no ERR output")
        for coil in self.zero + self.error:
            if coil.mode != "normal" or coil.inverted:
                raise ValueError("Integer status outputs require normal coils")
        self.source_devices()
        self.destination_devices()
        parse_expression(self.enable)
        return self


class AnalogConversion(Model):
    type: Literal["adcnv", "mlc"]
    enable: str = "TRUE"
    selector: str = "FALSE"
    source: str
    count: Annotated[int, Field(strict=True, ge=1, le=64)]
    destination: str
    polarity: Literal[0] | None = None
    x_table: str | None = None
    y_table: str | None = None
    table_length: str | None = None
    overflow: list[Coil] = Field(default_factory=list, max_length=32)

    def span(self, name: str, count: int, writable: bool = False) -> set[str]:
        result = register_span(name, count, writable=writable)
        if self.type == "mlc" and name.startswith("D") and int(name[1:]) + count > 4000:
            raise ValueError("MLC manual D bank ends at D3999, including full spans")
        return result

    def source_devices(self) -> set[str]:
        result = self.span(self.source, self.count)
        if self.type == "mlc":
            assert self.x_table and self.y_table and self.table_length
            result |= self.span(self.x_table, 255, True) | self.span(self.y_table, 255, True)
            result |= self.span(self.table_length, 1, True)
        return result

    def destination_devices(self) -> set[str]:
        return self.span(self.destination, self.count, True)

    @model_validator(mode="after")
    def check(self) -> "AnalogConversion":
        if self.type == "adcnv":
            if self.polarity != 0 or any(
                [self.x_table, self.y_table, self.table_length, self.overflow]
            ):
                raise ValueError("ADCNV currently uses sampled Pl=0, no tables or status outputs")
        elif self.polarity is not None or not all([self.x_table, self.y_table, self.table_length]):
            raise ValueError("MLC requires Tx, Ty and register Tl, without ADCNV polarity")
        self.source_devices()
        self.destination_devices()
        for c in self.overflow:
            if c.mode != "normal" or c.inverted:
                raise ValueError("MLC OVR requires normal coils")
        parse_expression(self.enable)
        parse_expression(self.selector)
        return self


class BitAccess(Model):
    type: Literal["bitrd", "bitwr"]
    enable: str = "TRUE"
    word: str
    bit: Annotated[int, Field(strict=True, ge=0, le=15)]
    input_bit: str | None = None
    output: list[Coil] = Field(default_factory=list, max_length=32)
    error: list[Coil] = Field(default_factory=list, max_length=32)

    @model_validator(mode="after")
    def check(self) -> "BitAccess":
        register_span(self.word, 1, writable=self.type == "bitwr")
        if self.type == "bitwr":
            if self.input_bit is None or self.output:
                raise ValueError("BITWR requires INB, has no OTB")
            parse_expression(self.input_bit)
        elif self.input_bit is not None:
            raise ValueError("BITRD has no INB")
        for c in self.output + self.error:
            if c.mode != "normal" or c.inverted:
                raise ValueError("Bit access status outputs require normal coils")
        parse_expression(self.enable)
        return self


class AccumulativeTimer(Model):
    type: Literal["accumulative_timer"]
    timing: str = "TRUE"
    enable: str = "TRUE"
    unit_ms: Literal[10, 100, 1000]
    cv: str
    pv: str
    done: list[Coil] = Field(default_factory=list, max_length=32)
    not_done: list[Coil] = Field(default_factory=list, max_length=32)

    @model_validator(mode="after")
    def check(self) -> "AccumulativeTimer":
        # CV T words are instruction-specific; do not relax ordinary destinations.
        if self.cv.startswith("T"):
            encode_word(self.cv)
        else:
            # Manual 7-81 explicitly permits the IR bank for this instruction's CV.
            register_span(self.cv, 1)
        register_span(self.pv, 1)
        parse_expression(self.timing)
        parse_expression(self.enable)
        for coil in self.done + self.not_done:
            if coil.mode != "normal" or coil.inverted:
                raise ValueError("Accumulative timer status outputs require normal coils")
        return self


class TemperatureControl(Model):
    type: Literal["tpctl"]
    enable: str = "TRUE"
    heat_cool: str = "TRUE"
    output: str
    start: Annotated[int, Field(strict=True, ge=0, le=31)]
    zones: Annotated[int, Field(strict=True, ge=1, le=32)]
    setpoint: str
    offset: str
    proportional: str
    integral: str
    derivative: str
    destination: str
    work: str
    error: list[Coil] = Field(default_factory=list, max_length=32)
    alarm: list[Coil] = Field(default_factory=list, max_length=32)

    def work_devices(self) -> set[str]:
        return register_span(self.work, 9, writable=True)

    def source_devices(self) -> set[str]:
        return set().union(
            *(
                register_span(name, self.zones, writable=True)
                for name in [
                    self.setpoint,
                    self.offset,
                    self.proportional,
                    self.integral,
                    self.derivative,
                ]
            )
        )

    def output_devices(self) -> set[str]:
        from .peripheral import bit_span

        return bit_span(self.output, self.zones, "Y", maximum_start=255)

    def destination_devices(self) -> set[str]:
        return register_span(self.destination, self.zones, writable=True) | self.work_devices()

    @model_validator(mode="after")
    def check(self) -> "TemperatureControl":
        if self.start + self.zones > 32:
            raise ValueError("TPCTL Sn + Zn must not exceed 32 (manual 7-79)")
        sources = self.source_devices()
        dest = register_span(self.destination, self.zones, writable=True)
        if self.work_devices() & (sources | dest):
            raise ValueError("TPCTL exclusive WR overlaps its operands")
        self.output_devices()
        parse_expression(self.enable)
        parse_expression(self.heat_cool)
        for coil in self.error + self.alarm:
            if coil.mode != "normal" or coil.inverted:
                raise ValueError("TPCTL status outputs require normal coils")
        return self


class ProcessFunction(Model):
    """Direct-register forms sampled in test20/21; not arbitrary instruction modes."""

    type: Literal[
        "encode_bits",
        "to_seven_segment",
        "ascii_literal",
        "hms_to_seconds",
        "seconds_to_hms",
        "ascii_to_hex",
        "hex_to_ascii",
        "bit_shift",
        "byte_distribute",
        "shift_left",
        "shift_right",
        "rotate_left",
        "rotate_right",
        "binary_to_gray",
        "gray_to_binary",
        "decode_bits",
        "bit_move",
        "nibble_move",
        "byte_move",
        "word_exchange",
        "byte_swap",
        "nibble_unite",
        "nibble_distribute",
        "byte_unite",
        "move_word",
        "move_inverse",
        "toggle_bit",
        "table_sort",
        "zone_write",
        "matrix_bit_shift",
        "matrix_bit_rotate",
        "matrix_bit_count",
        "matrix_and",
        "matrix_or",
        "matrix_xor",
        "matrix_xnr",
        "matrix_invert",
        "matrix_compare",
        "matrix_bit_read",
        "matrix_bit_write",
        "ascwr",
        "ramp",
        "ramp2",
        "reg_to_table",
        "table_to_reg",
        "table_to_table",
        "block_table_move",
        "table_swap",
        "register_table_search",
        "table_compare",
        "table_fill",
        "table_shift",
        "table_rotate",
        "queue",
        "stack",
        "block_compare",
    ]
    source_index: Annotated[int, Field(strict=True, ge=0, le=15)] | None = None
    destination_index: Annotated[int, Field(strict=True, ge=0, le=15)] | None = None
    count: Annotated[int, Field(strict=True, ge=0, le=511)] | None = None
    text: str | None = None
    high_priority: str = "FALSE"
    overflow: list[Coil] = Field(default_factory=list, max_length=32)
    bit_length: Annotated[int, Field(strict=True, ge=1, le=8)] | None = None
    trigger: str = "FALSE"
    ascending: str = "FALSE"
    ones: str = "FALSE"
    zero: list[Coil] = Field(default_factory=list, max_length=32)
    input_bit: str = "FALSE"
    source_b: str | None = None
    length_register: str | None = None
    output: list[Coil] = Field(default_factory=list, max_length=32)
    enable: str = "TRUE"
    pause: str = "FALSE"
    abort: str = "FALSE"
    up: str = "FALSE"
    increment: str = "FALSE"
    clear: str = "FALSE"
    from_head: str = "FALSE"
    different: str = "FALSE"
    left: str = "FALSE"
    push: str = "FALSE"
    value: Annotated[int, Field(strict=True, ge=-32768, le=32767)] | None = None
    input_word: str | None = None
    output_word: str | None = None
    bit_destination: str | None = None
    found: list[Coil] = Field(default_factory=list, max_length=32)
    empty_flag: list[Coil] = Field(default_factory=list, max_length=32)
    full: list[Coil] = Field(default_factory=list, max_length=32)
    mode: Literal[1] | None = None
    pulse: Literal[True] | None = None
    source: str | None = None
    work: str | None = None
    preset: str | None = None
    timer: str | None = None
    lower: str | None = None
    upper: str | None = None
    destination: str | None = None
    maximum: str | None = None
    rise_ms: str | None = None
    fall_ms: str | None = None
    target: str | None = None
    pointer: str | None = None
    length: Annotated[int, Field(strict=True, ge=1, le=2048)] | None = None
    active: list[Coil] = Field(default_factory=list, max_length=32)
    error: list[Coil] = Field(default_factory=list, max_length=32)
    done: list[Coil] = Field(default_factory=list, max_length=32)
    at_lower: list[Coil] = Field(default_factory=list, max_length=32)
    at_upper: list[Coil] = Field(default_factory=list, max_length=32)
    accelerating: list[Coil] = Field(default_factory=list, max_length=32)
    decelerating: list[Coil] = Field(default_factory=list, max_length=32)

    def operand(self, name: str) -> str:
        value = getattr(self, name)
        if not isinstance(value, str):
            raise ValueError(f"{self.type} requires register operand {name}")
        return value

    def work_devices(self) -> set[str]:
        from .process_functions import ramp2_span

        if self.type == "ascwr":
            return register_span(self.operand("work"), 8)
        if self.type == "ramp":
            destination = self.operand("destination")
            return register_span(destination, 2, writable=True) - {destination}
        if self.type == "ramp2":
            return ramp2_span(self.operand("work"), 4)
        return set()

    def source_devices(self) -> set[str]:
        from . import (
            conversion_functions,
            matrix_functions,
            packing_functions,
            shift_functions,
            transfer_functions,
        )
        from .process_functions import FIELDS
        from .table_functions import CODES, references

        if self.type in conversion_functions.CODES:
            return conversion_functions.references(self)[0]
        if self.type in shift_functions.CODES:
            return shift_functions.references(self)[0]
        if self.type in packing_functions.CODES:
            return packing_functions.references(self)[0]
        if self.type in transfer_functions.CODES:
            return transfer_functions.references(self)[0]
        if self.type in matrix_functions.CODES:
            return matrix_functions.references(self)[0]
        if self.type in CODES:
            return references(self)[0]
        if self.type == "ascwr":
            return {self.operand("source")}  # File terminator/MD1 semantics not resolved.
        if self.type == "ramp":
            return {self.operand(n) for n in ["preset", "lower", "upper"]} | {"M1974"}
        if self.type == "ramp2":
            return {self.operand(n) for n in FIELDS[self.type] if n != "work"}
        if self.type in {"table_to_reg", "table_to_table", "block_table_move", "table_swap"}:
            assert self.length is not None
            words = register_span(self.operand("source"), self.length)
            if self.type == "table_swap":
                words |= register_span(self.operand("destination"), self.length)
            elif self.type in {"table_to_reg", "table_to_table"}:
                words.add(self.operand("pointer"))
            return words
        return {self.operand("source"), self.operand("pointer")}

    def destination_devices(self) -> set[str]:
        from . import (
            conversion_functions,
            matrix_functions,
            packing_functions,
            shift_functions,
            transfer_functions,
        )
        from .table_functions import CODES, references

        if self.type in conversion_functions.CODES:
            return conversion_functions.references(self)[1]
        if self.type in shift_functions.CODES:
            return shift_functions.references(self)[1]
        if self.type in packing_functions.CODES:
            return packing_functions.references(self)[1]
        if self.type in transfer_functions.CODES:
            return transfer_functions.references(self)[1]
        if self.type in matrix_functions.CODES:
            return matrix_functions.references(self)[1]
        if self.type in CODES:
            return references(self)[1]
        if self.type == "ascwr":
            return self.work_devices()
        if self.type == "ramp":
            return self.work_devices() | {self.operand("timer"), self.operand("destination")}
        if self.type == "ramp2":
            return self.work_devices() | {self.operand("destination")}
        assert self.length is not None
        count = 1 if self.type == "table_to_reg" else self.length
        words = register_span(self.operand("destination"), count, writable=True)
        if self.type == "table_swap":
            words |= register_span(self.operand("source"), self.length, writable=True)
        elif self.type not in {"block_table_move"}:
            words |= register_span(self.operand("pointer"), 1, writable=True)
        return words

    @model_validator(mode="after")
    def check(self) -> "ProcessFunction":
        from . import conversion_functions, packing_functions, shift_functions, transfer_functions
        from .matrix_functions import CODES as MATRIX_CODES
        from .process_functions import CONTROLS, FIELDS, STATUS, ramp2_span
        from .table_functions import CODES, output_bits

        if self.type not in conversion_functions.CODES and self.text is not None:
            raise ValueError(f"{self.type} has no literal text")
        if self.type in conversion_functions.CODES:
            conversion_functions.check_parameters(self)
        elif self.type in shift_functions.CODES:
            shift_functions.check_parameters(self)
        else:
            packing_functions.check_parameters(self)
            if self.bit_length is not None:
                raise ValueError(f"{self.type} has no bit_length")
        required = FIELDS[self.type]
        for name in set().union(*map(set, FIELDS.values())):
            if name in required:
                value = self.operand(name)
                if self.type in conversion_functions.CODES:
                    conversion_functions.operand_check(self.type, name, value)
                elif self.type in shift_functions.CODES:
                    shift_functions.operand_check(self.type, name, value)
                elif self.type in packing_functions.CODES:
                    packing_functions.operand_check(self.type, name, value)
                elif self.type in transfer_functions.CODES:
                    transfer_functions.operand_check(self.type, name, value)
                elif name == "bit_destination":
                    output_bits(value, self.length or 1)
                elif name == "timer":
                    if not value.startswith("T"):
                        raise ValueError("RAMP Tn requires T0..255 with configured 10 ms time base")
                    encode_word(value)
                elif self.type == "ramp2":
                    ramp2_span(value)
                else:
                    register_span(value, 1)
            elif getattr(self, name) is not None:
                raise ValueError(f"{self.type} has no {name} operand")
        if self.type == "ascwr":
            if self.mode != 1 or self.pulse is not True:
                raise ValueError("ASCWR codec currently supports sampled 94P MD=1 only")
        elif self.mode is not None or self.pulse is not None:
            raise ValueError("Unencoded mode/pulse form for this function")
        if (
            self.type
            in (
                {"reg_to_table", "table_to_reg", "table_to_table", "block_table_move", "table_swap"}
                | set(CODES)
                | (set(MATRIX_CODES) - {"matrix_invert"})
                | set(transfer_functions.LENGTHS)
            )
        ) != (self.length is not None):
            raise ValueError("Table functions require constant length; other functions have none")
        if (
            self.type in {"block_table_move", "table_swap"}
            and self.length is not None
            and self.length > 256
        ):
            raise ValueError("BT_M/T_SWP length must be 2..256 (manual 7-98..99)")
        if self.length is not None:
            if self.type in transfer_functions.LENGTHS:
                low, high = transfer_functions.LENGTHS[self.type]
                if not low <= self.length <= high:
                    raise ValueError(f"{self.type} length must be {low}..{high}")
            if self.type not in {"block_compare", "zone_write"} and self.length < 2:
                raise ValueError("Table length must be at least 2")
            if self.type in (set(CODES) | set(MATRIX_CODES)) and self.length > 256:
                raise ValueError(
                    "FUN105..112/120..127 length maximum is 256 (manual 7-100..109, 7-114..121)"
                )
        if (self.type in {"register_table_search", "table_fill"}) != (self.value is not None):
            raise ValueError(
                "Only sampled FUN105/107 require constant value; register Rs not encoded"
            )
        for name in set().union(*map(set, CONTROLS.values())):
            if name in CONTROLS[self.type]:
                parse_expression(getattr(self, name))
            elif getattr(self, name) != ("TRUE" if name == "enable" else "FALSE"):
                raise ValueError(f"{self.type} has no {name} control")
        for name in set().union(*map(set, STATUS.values())):
            group = getattr(self, name)
            if name not in STATUS[self.type] and group:
                raise ValueError(f"{self.type} has no {name} status")
            for coil in group:
                if coil.mode != "normal" or coil.inverted:
                    raise ValueError("Process function status outputs require normal coils")
        self.destination_devices()
        self.source_devices()
        if self.type == "reg_to_table":
            register_span(self.operand("pointer"), 1, writable=True)
        if self.work_devices() & self.source_devices():
            raise ValueError("Exclusive function work area overlaps source operands")
        return self


class SampleCall(Model):
    """Forensic anchor only: unresolved relocation bytes, generation rejected."""

    type: Literal["call"]
    target: Literal["1"] = "1"


class SampleFlow(Model):
    """Exact test18 label/jump pair, not a general relocated jump compiler."""

    type: Literal["lbl", "jmp"]
    target: Literal["1"] = "1"


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
            | AnalogConversion
            | BitAccess
            | SampleFlow
            | AccumulativeTimer
            | TemperatureControl
            | SampleCall
            | ProcessFunction
            | IntegerFunction
            | Watchdog
            | HighSpeedCounter
            | Divide48
            | SumWords
            | PID
            | PeripheralIO
            | ImmediateIO
            | FloatOperation
            | FloatCompare
            | FloatZoneCompare
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


class Ladder(Model):
    profile: HeaderProfile = "FBs-20MC"
    networks: list[Network] = Field(min_length=1, max_length=1000)
    symbols: dict[str, str] = Field(default_factory=dict, max_length=512)


class UnsupportedInstruction(ValueError):
    pass


def comparison_reads(network: Network) -> set[str]:
    reads: set[str] = set()
    for c in network.comparison_chain:
        reads |= comparison_word_references(c.sa)
        if isinstance(c.sb, str):
            reads |= comparison_word_references(c.sb)
    return reads


def network_coils(network: Network) -> list[Coil]:
    if isinstance(network.action, ProcessFunction):
        from .process_functions import STATUS

        implicit = [
            Coil(device="Y" if name.startswith("Y") else "M", address=int(name[1:]))
            for name in sorted(network.action.destination_devices())
            if name.startswith(("Y", "M")) and name[1:].isdigit()
        ]
        return (
            network.coils
            + implicit
            + [c for name in STATUS[network.action.type] for c in getattr(network.action, name)]
        )
    if isinstance(network.action, AccumulativeTimer):
        return network.coils + network.action.done + network.action.not_done
    if isinstance(network.action, TemperatureControl):
        return network.coils + network.action.error + network.action.alarm
    if isinstance(network.action, AnalogConversion):
        return network.coils + network.action.overflow
    if isinstance(network.action, BitAccess):
        return network.coils + network.action.output + network.action.error
    if isinstance(network.action, IntegerFunction):
        return network.coils + network.action.zero + network.action.error
    if isinstance(network.action, PID):
        pid = network.action
        return network.coils + pid.error + pid.high + pid.low
    if isinstance(network.action, Divide48):
        return network.coils + network.action.zero + network.action.error
    if isinstance(network.action, PeripheralIO):
        a = network.action
        implicit = [
            Coil.model_validate({"device": d[0], "address": int(d[1:])})
            for d in sorted(a.key_devices())
        ]
        return network.coils + implicit + [c for group in a.statuses() for c in group]
    if isinstance(network.action, FloatOperation):
        return network.coils + network.action.error
    if isinstance(network.action, (ZoneCompare, FloatZoneCompare)):
        z = network.action
        return network.coils + z.within + z.above + z.below
    if isinstance(network.action, Differential):
        d = network.action.destination
        return [*network.coils, Coil.model_validate({"device": d[0], "address": int(d[1:])})]
    if isinstance(network.action, (Compare, FloatCompare)):
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
                if index == 0 and isinstance(c.sb, int):
                    raise UnsupportedInstruction(
                        "First comparison with constant Sb is not yet supported"
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
            if isinstance(action, ProcessFunction):
                from .process_functions import compile_process

                return compile_process(action)
            if isinstance(action, (AccumulativeTimer, TemperatureControl, SampleCall)):
                from .thermal_functions import compile_thermal

                return compile_thermal(action)
            if isinstance(action, (AnalogConversion, BitAccess, SampleFlow)):
                from .analog_functions import compile_analog

                return compile_analog(action)
            if isinstance(action, IntegerFunction):
                from .integer_functions import compile_integer

                return compile_integer(action)
            if isinstance(action, (Watchdog, HighSpeedCounter, Divide48, SumWords, PID)):
                from .control_functions import compile_control

                return compile_control(action)
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
            if isinstance(action, PeripheralIO):
                result = prefix + bytes.fromhex(PERIPHERAL_CODES[action.type])
                for field in PERIPHERAL_FIELDS[action.type]:
                    value = getattr(action, field)
                    if field in {"input", "output", "key_start"}:
                        result += bit_address(value).to_bytes(2, "big")
                    elif field in {"rows", "mode"}:
                        result += value.to_bytes(2, "big")
                    else:
                        result += peripheral_word(value, writable=field != "source")
                for i, coils in enumerate(action.statuses()):
                    if coils:
                        result += (0x6FFC + i).to_bytes(2, "big") + compile_coils(coils)
                return result
            if isinstance(action, ImmediateIO):
                return (
                    prefix
                    + bytes.fromhex("f4e8")
                    + bit_address(action.start).to_bytes(2, "big")
                    + action.count.to_bytes(2, "big")
                )
            if isinstance(action, (FloatOperation, FloatCompare, FloatZoneCompare)):
                if isinstance(action, FloatOperation):
                    code = FLOAT_CODES[action.operation]
                    operands = ([] if action.sa is None else [action.sa]) + (
                        [] if action.sb is None else [action.sb]
                    )
                    suffix = encode_float_register(action.destination)
                elif isinstance(action, FloatCompare):
                    code, operands, suffix = 6, [action.sa, action.sb], b""
                else:
                    code, operands = 7, [action.upper, action.lower]
                    suffix = encode_float_register(action.source)
                flags = sum(1 << i for i, v in enumerate(operands) if isinstance(v, float))
                result = prefix + bytes([0xF4 + flags, 0x7F]) + code.to_bytes(2, "big")
                if isinstance(action, FloatOperation) and action.operation in {"sin", "cos", "tan"}:
                    assert action.sa is not None
                    result += (
                        encode_float_register(action.sa)
                        if isinstance(action.sa, str)
                        else int(action.sa).to_bytes(2, "big", signed=True)
                    )
                elif isinstance(action, FloatOperation) and action.operation == "f_to_i":
                    assert isinstance(action.sa, str)
                    result += encode_float_register(action.sa)
                elif isinstance(action, FloatOperation) and action.operation == "i_to_f":
                    assert isinstance(action.sa, str)
                    result += b"\x00\x00" + encode_float_register(action.sa)
                else:
                    result += b"".join(encode_float_source(v) for v in operands)
                result += suffix
                if isinstance(action, FloatCompare):
                    outputs = [action.equal, action.greater, action.less]
                elif isinstance(action, FloatZoneCompare):
                    outputs = [action.within, action.above, action.below]
                else:
                    outputs = [action.error]
                for i, coils in enumerate(outputs):
                    if coils:
                        result += (0x6FFC + i).to_bytes(2, "big") + compile_coils(coils)
                return result
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
    from .process_functions import decode_process

    process = decode_process(payload)
    if process is not None:
        return process
    from .thermal_functions import decode_thermal

    thermal = decode_thermal(payload)
    if thermal is not None:
        return thermal
    from .analog_functions import decode_analog

    analog = decode_analog(payload)
    if analog is not None:
        return analog
    from .control_functions import decode_control
    from .integer_functions import decode_integer

    integer = decode_integer(payload)
    if integer is not None:
        return integer
    control = decode_control(payload)
    if control is not None:
        return control
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
        for offset15 in range(2, len(payload) - 1, 2):
            kind15 = next(
                (
                    k
                    for k, v in PERIPHERAL_CODES.items()
                    if payload[offset15 : offset15 + 2].hex() == v
                ),
                None,
            )
            if kind15 is None:
                continue
            try:
                fields15 = PERIPHERAL_FIELDS[kind15]
                end15 = offset15 + 2 + 2 * len(fields15)
                if len(payload) < end15:
                    continue
                values15: dict[str, Any] = {
                    "type": kind15,
                    "enable": expression_text(decode_expression(payload[:offset15])),
                }
                for j, field in enumerate(fields15):
                    raw15 = payload[offset15 + 2 + 2 * j : offset15 + 4 + 2 * j]
                    values15[field] = (
                        device_name(int.from_bytes(raw15, "big"))
                        if field in {"input", "output", "key_start"}
                        else int.from_bytes(raw15, "big")
                        if field in {"mode", "rows"}
                        else decode_peripheral_word(raw15)
                    )
                outs15 = decode_status_coils(payload[end15:])
                names15 = {
                    "tkey": ["pressed"],
                    "hkey": ["pressed", "function_pressed"],
                    "dsw": ["done", "error"],
                    "7sgdl": ["done"],
                    "muxi": ["done"],
                }[kind15]
                if any(outs15[len(names15) :]):
                    continue
                values15.update({name: outs15[i] for i, name in enumerate(names15)})
                n15 = Network(action=PeripheralIO.model_validate(values15))
                if compile_network(n15) == payload:
                    return n15
            except ValueError:
                continue
        for offset11 in range(2, len(payload) - 3, 2):
            if payload[offset11 : offset11 + 2] not in {
                b"\xf4\x7f",
                b"\xf5\x7f",
                b"\xf6\x7f",
                b"\xf7\x7f",
            }:
                continue
            try:
                enable11 = expression_text(decode_expression(payload[:offset11]))
                code11 = int.from_bytes(payload[offset11 + 2 : offset11 + 4], "big")
                flags12 = payload[offset11] - 0xF4
                tail11 = payload[offset11 + 4 :]
                op_float = next((k for k, v in FLOAT_CODES.items() if v == code11), None)
                f_action: FloatOperation | FloatCompare | FloatZoneCompare
                if code11 == 6 and len(tail11) >= 8:
                    outs = decode_status_coils(tail11[8:])
                    f_action = FloatCompare(
                        sa=decode_float_source(tail11[:4], bool(flags12 & 1)),
                        sb=decode_float_source(tail11[4:8], bool(flags12 & 2)),
                        enable=enable11,
                        equal=outs[0],
                        greater=outs[1],
                        less=outs[2],
                    )
                elif code11 == 7 and len(tail11) >= 10:
                    outs = decode_status_coils(tail11[10:])
                    f_action = FloatZoneCompare(
                        upper=decode_float_source(tail11[:4], bool(flags12 & 1)),
                        lower=decode_float_source(tail11[4:8], bool(flags12 & 2)),
                        source=decode_float_register(tail11[8:10]),
                        enable=enable11,
                        within=outs[0],
                        above=outs[1],
                        below=outs[2],
                    )
                elif op_float is not None:
                    width14 = (
                        2
                        if op_float in {"neg", "abs"}
                        else 4
                        if op_float in {"sin", "cos", "tan", "f_to_i"}
                        else 10
                        if op_float in {"add", "sub", "mul", "div", "pow"}
                        else 6
                    )
                    status14 = decode_status_coils(tail11[width14:])
                    if status14[1] or status14[2]:
                        continue
                    tail11 = tail11[:width14]
                    sb12 = None
                    sa12: str | float | None
                    if op_float in {"neg", "abs"} and len(tail11) == 2 and flags12 == 0:
                        sa12 = None
                    elif op_float in {"sin", "cos", "tan"} and len(tail11) == 4 and flags12 <= 1:
                        sa12 = (
                            float(int.from_bytes(tail11[:2], "big", signed=True))
                            if flags12
                            else decode_float_register(tail11[:2])
                        )
                    elif op_float == "f_to_i" and len(tail11) == 4 and flags12 == 0:
                        sa12 = decode_float_register(tail11[:2])
                    elif (
                        op_float == "i_to_f"
                        and len(tail11) == 6
                        and flags12 == 0
                        and tail11[:2] == b"\x00\x00"
                    ):
                        sa12 = decode_float_register(tail11[2:4])
                    elif (
                        op_float in {"sqrt", "ln", "exp", "log", "asin", "acos", "atan"}
                        and len(tail11) == 6
                        and flags12 <= 1
                    ):
                        sa12 = decode_float_source(tail11[:4], bool(flags12 & 1))
                    elif op_float in {"add", "sub", "mul", "div", "pow"} and len(tail11) == 10:
                        sa12 = decode_float_source(tail11[:4], bool(flags12 & 1))
                        sb12 = decode_float_source(tail11[4:8], bool(flags12 & 2))
                    else:
                        continue
                    f_action = FloatOperation.model_validate(
                        {
                            "operation": op_float,
                            "sa": sa12,
                            "sb": sb12,
                            "destination": decode_float_register(tail11[-2:]),
                            "error": status14[0],
                            "enable": enable11,
                        }
                    )
                else:
                    continue
                n11 = Network(action=f_action)
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
            | AnalogConversion
            | BitAccess
            | SampleFlow
            | AccumulativeTimer
            | TemperatureControl
            | SampleCall
            | ProcessFunction
            | IntegerFunction
            | Watchdog
            | HighSpeedCounter
            | Divide48
            | SumWords
            | PID
            | PeripheralIO
            | ImmediateIO
            | FloatOperation
            | FloatCompare
            | FloatZoneCompare
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
        if len(payload) >= 8 and payload[-6:-4] == bytes.fromhex("f4e8"):
            action = ImmediateIO(
                start=device_name(int.from_bytes(payload[-4:-2], "big")),
                count=int.from_bytes(payload[-2:], "big"),
                enable=expression_text(decode_expression(payload[:-6])),
            )
        elif len(payload) == 4 and payload[:2] == bytes.fromhex("fc89"):
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
            observed12 = next(
                (i for i, raw in TEST12_PAYLOADS.items() if payload.hex() == raw), None
            )
            observed13 = next(
                (i for i, raw in TEST13_PAYLOADS.items() if payload.hex() == raw), None
            )
            if isinstance(network.action, PeripheralIO):
                observed15 = next(
                    (i for i, raw in TEST15_PAYLOADS.items() if payload.hex() == raw), None
                )
                instruction_evidence.append(
                    {
                        "network_index": index,
                        "instruction": network.action.type,
                        "status": "observed_export"
                        if observed15 is not None
                        else "inferred_variant",
                        "source": f"test15.ldr N{observed15:03}"
                        if observed15 is not None
                        else "test15",
                        "gui_import_verified": False,
                    }
                )
            if isinstance(network.action, (Watchdog, HighSpeedCounter, Divide48, SumWords, PID)):
                from .instruction_catalog import TEST16_PAYLOADS

                observed16 = next(
                    (i for i, raw in TEST16_PAYLOADS.items() if payload.hex() == raw), None
                )
                instruction_evidence.append(
                    {
                        "network_index": index,
                        "instruction": network.action.type,
                        "status": "observed_export"
                        if observed16 is not None
                        else "inferred_variant",
                        "source": f"test16.ldr N{observed16:03}"
                        if observed16 is not None
                        else "test16",
                        "gui_import_verified": False,
                    }
                )
            if isinstance(network.action, (IntegerFunction, Divide48, SumWords)):
                from .instruction_catalog import TEST17_PAYLOADS

                observed17 = next(
                    (i for i, raw in TEST17_PAYLOADS.items() if payload.hex() == raw), None
                )
                if (
                    observed17 is not None
                    or isinstance(network.action, IntegerFunction)
                    or (
                        isinstance(network.action, Divide48)
                        and network.action.encoding == "single_input"
                    )
                ):
                    instruction_evidence[:] = [
                        e for e in instruction_evidence if e["network_index"] != index
                    ]
                    instruction_evidence.append(
                        {
                            "network_index": index,
                            "instruction": network.action.type,
                            "status": "observed_export"
                            if observed17 is not None
                            else "inferred_variant",
                            "source": f"test17.ldr N{observed17:03}"
                            if observed17 is not None
                            else "test17",
                            "gui_import_verified": False,
                        }
                    )
            if isinstance(network.action, (AnalogConversion, BitAccess, SampleFlow)):
                from .instruction_catalog import TEST18_PAYLOADS

                observed18 = next(
                    (i for i, raw in TEST18_PAYLOADS.items() if payload.hex() == raw), None
                )
                instruction_evidence.append(
                    {
                        "network_index": index,
                        "instruction": network.action.type,
                        "status": "observed_export"
                        if observed18 is not None
                        else "inferred_variant",
                        "source": f"test18.ldr N{observed18:03}"
                        if observed18 is not None
                        else "test18",
                        "gui_import_verified": False,
                    }
                )
            if isinstance(network.action, (AccumulativeTimer, TemperatureControl, SampleCall)):
                from .instruction_catalog import TEST19_PAYLOADS

                observed19 = next(
                    (i for i, raw in TEST19_PAYLOADS.items() if payload.hex() == raw), None
                )
                instruction_evidence.append(
                    {
                        "network_index": index,
                        "instruction": network.action.type,
                        "status": "observed_export"
                        if observed19 is not None
                        else "inferred_variant",
                        "source": f"test19.ldr N{observed19:03}"
                        if observed19 is not None
                        else "test19",
                        "gui_import_verified": False,
                    }
                )
            if isinstance(network.action, ProcessFunction):
                from .conversion_functions import CODES as CONVERSION_CODES
                from .instruction_catalog import (
                    TEST20_PAYLOADS,
                    TEST21_PAYLOADS,
                    TEST22_PAYLOADS,
                    TEST23_PAYLOADS,
                    TEST24_PAYLOADS,
                    TEST25_PAYLOADS,
                    TEST26_PAYLOADS,
                    TEST27_PAYLOADS,
                )
                from .matrix_functions import CODES as MATRIX_CODES
                from .packing_functions import CODES as PACKING_CODES
                from .shift_functions import CODES as SHIFT_CODES
                from .table_functions import CODES as TABLE22_CODES
                from .transfer_functions import CODES as TRANSFER_CODES

                table21 = network.action.type in {
                    "table_to_reg",
                    "table_to_table",
                    "block_table_move",
                    "table_swap",
                }
                anchors = TEST21_PAYLOADS if table21 else TEST20_PAYLOADS
                evidence_name = "test21" if table21 else "test20"
                if network.action.type in TABLE22_CODES:
                    anchors = TEST22_PAYLOADS
                    evidence_name = "test22"
                if network.action.type in MATRIX_CODES:
                    anchors = TEST23_PAYLOADS
                    evidence_name = "test23"
                if network.action.type in TRANSFER_CODES:
                    anchors = TEST24_PAYLOADS
                    evidence_name = "test24"
                if network.action.type in PACKING_CODES:
                    anchors = TEST25_PAYLOADS
                    evidence_name = "test25"
                if network.action.type in SHIFT_CODES:
                    anchors = TEST26_PAYLOADS
                    evidence_name = "test26"
                if network.action.type in CONVERSION_CODES:
                    anchors = TEST27_PAYLOADS
                    evidence_name = "test27"
                observed20 = next((i for i, raw in anchors.items() if payload.hex() == raw), None)
                instruction_evidence.append(
                    {
                        "network_index": index,
                        "instruction": network.action.type,
                        "status": "observed_export"
                        if observed20 is not None
                        else "inferred_variant",
                        "source": f"{evidence_name}.ldr N{observed20:03}"
                        if observed20 is not None
                        else evidence_name,
                        "gui_import_verified": False,
                    }
                )
            observed14 = next(
                (i for i, raw in TEST14_PAYLOADS.items() if payload.hex() == raw), None
            )
            if isinstance(network.action, ImmediateIO) or (
                isinstance(network.action, FloatOperation)
                and (
                    network.action.operation in {"log", "pow", "asin", "acos", "atan"}
                    or network.action.error
                )
            ):
                instruction_evidence.append(
                    {
                        "network_index": index,
                        "instruction": network.action.type,
                        "status": "observed_export"
                        if observed14 is not None
                        else "inferred_variant",
                        "source": f"test14.ldr N{observed14:03}"
                        if observed14 is not None
                        else "test14",
                        "gui_import_verified": False,
                    }
                )
            elif isinstance(network.action, FloatOperation) and network.action.operation in {
                "sin",
                "cos",
                "tan",
                "neg",
                "abs",
                "ln",
                "exp",
            }:
                instruction_evidence.append(
                    {
                        "network_index": index,
                        "instruction": network.action.operation,
                        "status": "observed_export"
                        if observed13 is not None
                        else "inferred_variant",
                        "source": f"test13.ldr N{observed13:03}"
                        if observed13 is not None
                        else "test13",
                        "gui_import_verified": False,
                    }
                )
            elif (
                observed12 is not None
                or isinstance(network.action, (FloatCompare, FloatZoneCompare))
                or (
                    isinstance(network.action, FloatOperation)
                    and network.action.operation in {"div", "sqrt"}
                )
            ):
                assert network.action is not None
                instruction_evidence.append(
                    {
                        "network_index": index,
                        "instruction": network.action.type,
                        "status": "observed_export"
                        if observed12 is not None
                        else "inferred_variant",
                        "source": f"test12.ldr N{observed12:03}"
                        if observed12 is not None
                        else "test12",
                        "gui_import_verified": False,
                    }
                )
            elif network.comparison_chain or isinstance(network.action, FloatOperation):
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
    if any(isinstance(n.action, SampleCall) for n in ladder.networks):
        errors.append(
            "CALL 1 target metadata unresolved (manual 7-61); test19 has no "
            "LBL 1 / RTS. Anchor is decode-only; generation is not supported"
        )
    flow = [n.action for n in ladder.networks if isinstance(n.action, SampleFlow)]
    if flow:
        from .instruction_catalog import TEST18_PAYLOADS

        labels = [a.target for a in flow if a.type == "lbl"]
        if len(labels) != len(set(labels)):
            errors.append("Duplicate LBL target")
        if any(a.type == "jmp" and a.target not in labels for a in flow):
            errors.append("JMP target has no matching LBL")
        if any(a.type == "jmp" for a in flow) and (
            ladder.profile != "FBs-20MC"
            or [p.replace(" ", "") for p in payloads] != list(TEST18_PAYLOADS.values())
        ):
            errors.append(
                "JMP target metadata is unresolved: generation is limited to "
                "the exact complete test18 export; no relocation or modified program"
            )
    errors.extend(f"N{i:03}: FOR missing NEXT" for i in loops)
    errors.extend(f"N{i:03}: MC {number} missing MCE {number}" for number, i in masters.items())
    verified = payloads == ["41 00 a0 00 90 01 c1 00"] and not errors
    coils = [f"{c.device}{c.address}" for n in ladder.networks for c in network_coils(n)]
    if any(
        isinstance(n.action, (PeripheralIO, PID, TemperatureControl, ProcessFunction))
        for n in ladder.networks
    ):
        from .analysis import device_references

        refs15 = device_references(list(enumerate(ladder.networks)))["devices"]
        for i15, n15 in enumerate(ladder.networks):
            if isinstance(n15.action, (PeripheralIO, PID, TemperatureControl, ProcessFunction)):
                for word15 in sorted(n15.action.work_devices()):
                    other15 = (set(refs15[word15]["reads"]) | set(refs15[word15]["writes"])) - {i15}
                    if other15:
                        errors.append(
                            f"N{i15:03}: exclusive WR {word15} also used by "
                            f"networks {sorted(other15)}"
                        )
    if any(
        isinstance(n.action, ProcessFunction) and n.action.type == "ramp" for n in ladder.networks
    ):
        from .analysis import device_references

        ramp_refs = device_references(list(enumerate(ladder.networks)))["devices"]
        for i20, n20 in enumerate(ladder.networks):
            if isinstance(n20.action, ProcessFunction) and n20.action.type == "ramp":
                timer20 = n20.action.operand("timer")
                other20 = (set(ramp_refs[timer20]["reads"]) | set(ramp_refs[timer20]["writes"])) - {
                    i20
                }
                if other20:
                    errors.append(
                        f"N{i20:03}: exclusive RAMP Tn {timer20} also used by {sorted(other20)}"
                    )
    warnings = [] if verified else ["Composition has not been verified by WinProLadder import."]
    if any(
        isinstance(n.action, (AnalogConversion, BitAccess, SampleFlow)) for n in ladder.networks
    ):
        warnings.append(
            "test18: MLC register Tl tracks 255 possible table words; "
            "BITRD disabled OTB behavior depends on M1919. No runtime simulation. "
            "JMP only preserves the exact sample; unconditional backward jump "
            "can prevent scan completion and trigger watchdog. No GUI/PLC verification."
        )
    if any(isinstance(n.action, (AccumulativeTimer, TemperatureControl)) for n in ladder.networks):
        warnings.append(
            "test19: timer unit_ms is the native time base (10/100/1000 ms); "
            "PV is a register count, TIM pauses, EN=0 clears. TPCTL temperature "
            "source depends on PLC planning/R4003/R4004; Md encoding unresolved. "
            "No built-in runtime simulation or GUI/PLC verification."
        )
    if any(
        isinstance(n.action, ProcessFunction)
        and n.action.type in {"ascwr", "ramp", "ramp2", "reg_to_table"}
        for n in ladder.networks
    ):
        warnings.append(
            "test20: ASCWR 94P MD=1 is reserved in manual 7-87; runtime and "
            "ASCII file spans unresolved. RAMP requires a 10 ms configured Tn "
            "and depends on M1974. RAMP2 times are ms, D bank ends D3999. "
            "No new function runtime simulation, GUI or PLC verification."
        )
    if any(
        isinstance(n.action, ProcessFunction)
        and n.action.type in {"table_to_reg", "table_to_table", "block_table_move", "table_swap"}
        for n in ladder.networks
    ):
        warnings.append(
            "test21: sampled 16-bit non-P table functions, constant L, direct R/D operands. "
            "No built-in execution simulation, GUI import or PLC verification."
        )
    from .table_functions import CODES as TABLE22_CODES

    if any(
        isinstance(n.action, ProcessFunction) and n.action.type in TABLE22_CODES
        for n in ladder.networks
    ):
        warnings.append(
            "test22: direct-register 16-bit non-P encodings, constant Rs only for 105/107. "
            "BKCMP reads 2*L limit words and M1975; writes L result bits. "
            "No native runtime simulation or GUI/PLC verification."
        )
    from .conversion_functions import CODES as CONVERSION_CODES

    if any(
        isinstance(n.action, ProcessFunction) and n.action.type in CONVERSION_CODES
        for n in ladder.networks
    ):
        warnings.append(
            "test27: ENCOD NL counts points; 7SG N means N+1 digits. "
            "ASC supports exact ABCDEF literal only. SEC/HMS use seconds, minutes, hours "
            "word order. HEX/ASCII and odd-digit 7SG preserve unused destination portions. "
            "BSHF CLR overrides EN; no independent or built-in execution model, "
            "GUI or PLC verification."
        )
    from .shift_functions import CODES as SHIFT_CODES

    if any(
        isinstance(n.action, ProcessFunction) and n.action.type in SHIFT_CODES
        for n in ladder.networks
    ):
        warnings.append(
            "test26: sampled 16-bit non-P shift/Gray/DECOD forms. "
            "BDIST N counts bytes; conservative max 128 source / 256 destination words. "
            "DECOD NL counts source bits, output 2^NL bits; source crosses B15 and clips "
            "at operand bank end. Unused output bits for NL<4 are not runtime-modeled. "
            "No native runtime simulation, GUI import or PLC verification."
        )
    from .packing_functions import CODES as PACKING_CODES

    if any(
        isinstance(n.action, ProcessFunction) and n.action.type in PACKING_CODES
        for n in ladder.networks
    ):
        warnings.append(
            "test25: 16-bit non-P packing forms. BUNIT N is runtime bytes (1..256); "
            "static footprint covers 256 source and 128 destination words, including "
            "conservative destination reads for unspecified odd-N trailing byte behavior. "
            "UNIT/DIST clear unused nibbles; partial moves preserve other bits. "
            "No native runtime simulation, GUI import or PLC verification."
        )
    from .transfer_functions import CODES as TRANSFER_CODES

    if any(
        isinstance(n.action, ProcessFunction) and n.action.type in TRANSFER_CODES
        for n in ladder.networks
    ):
        warnings.append(
            "test24: sampled 16-bit non-P forms and constant lengths. TOGG uses rising edges. "
            "Matrix L counts words; MBCNT writes one word. Z-WR N is literal, 1..511. "
            "WY8 writes Y8..Y23. No built-in execution model, GUI or PLC verification."
        )
    from .matrix_functions import CODES as MATRIX_CODES

    if any(
        isinstance(n.action, ProcessFunction) and n.action.type in MATRIX_CODES
        for n in ladder.networks
    ):
        warnings.append(
            "test23: matrix L counts words; bit pointer ranges 0..16*L-1. "
            "MINV register L uses conservative 256-word possible spans; "
            "actual length is a runtime value and is not evaluated. "
            "Sampled non-P forms only; no native execution, GUI or PLC verification."
        )
    if any(isinstance(n.action, IntegerFunction) for n in ladder.networks):
        warnings.append(
            "test17: MEAN register N tracks all 256 potentially read words; "
            "CRC16 MD=1 is reserved in the supplied manual, so only encoding "
            "is supported and its runtime/reference semantics remain unverified. "
            "No native runtime simulation."
        )
    if any(
        isinstance(n.action, (Watchdog, HighSpeedCounter, Divide48, SumWords, PID))
        for n in ladder.networks
    ):
        warnings.append(
            "test16: WDT and PID times use 10 ms units. PID A/M is not EN. "
            "Only sampled HSC0 read and 93D zero-to-PV write supported. "
            "No runtime simulation or hardware verification."
        )
    if any(isinstance(n.action, PeripheralIO) for n in ladder.networks):
        warnings.append(
            "FUN76..80: sampled 16-bit forms; other operands/status wiring inferred. "
            "Full I/O, KL and WR spans tracked; scan outputs require appropriate "
            "transistor hardware. No D/P or runtime simulation. R3999/V are exact "
            "special-word anchors, not whole-bank support."
        )
    if any(isinstance(n.action, ImmediateIO) for n in ladder.networks):
        warnings.append(
            "IMDIO refreshes main-unit I/O only. N=1..36; X35/Y23 are table-wide "
            "maxima, not this CPU capacity. Exact CPU I/O capacity is not verified "
            "by this codec or header. No refresh runtime simulation."
        )
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
    if any(
        isinstance(n.action, (FloatOperation, FloatCompare, FloatZoneCompare))
        for n in ladder.networks
    ):
        warnings.append(
            "Floating functions: binary32 constants and double-word register spans; "
            "sin/cos/tan sources are single-word integer angles in 0.01 degrees; "
            "neg/abs modify the destination pair in place. "
            "test12 observes F5; test14 observes F6 second-operand constants; F7 is inferred. "
            "Normal ERR coils supported (FLOG sampled, other ERR forms inferred). "
            "No P or indirect forms; no runtime simulation or generated-file GUI/PLC check."
        )
    if any(n.comparison_chain for n in ladder.networks):
        warnings.append(
            "test11: all six comparisons support first/series positions; "
            "all 12 positions user GUI-confirmed in the exact position probe. "
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
