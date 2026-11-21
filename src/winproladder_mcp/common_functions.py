"""High-level builder for parameterized, commonly used native functions."""

from typing import Annotated, Literal

from pydantic import Field, model_validator

from .ir import (
    PID,
    AccumulativeTimer,
    AnalogConversion,
    Arithmetic,
    BitAccess,
    Bitwise,
    Coil,
    Compare,
    ComparisonContact,
    Counter,
    Divide48,
    ExclusiveLogic,
    FloatCompare,
    FloatOperation,
    FloatZoneCompare,
    HighSpeedCounter,
    ImmediateIO,
    IntegerFunction,
    Ladder,
    LinearConversion,
    Model,
    Network,
    PeripheralIO,
    ProcessFunction,
    RegisterStep,
    SumWords,
    TemperatureControl,
    Timer,
    UpDownCounter,
    Watchdog,
    WordConversion,
    ZoneCompare,
)
from .logic import parse_expression
from .profiles import HeaderProfile
from .registers import register_span


class CommonMove(Model):
    """FUN8 MOV with a direct word or signed 16-bit constant source."""

    type: Literal["move_word"] = "move_word"
    source: str | Annotated[int, Field(strict=True, ge=-32768, le=32767)]
    destination: str
    enable: str = "TRUE"

    @model_validator(mode="after")
    def check(self) -> "CommonMove":
        if isinstance(self.source, str):
            register_span(self.source, 1)
        register_span(self.destination, 1, writable=True)
        parse_expression(self.enable)
        return self


class CommonMean(Model):
    """FUN25 MEAN with register-valued or constant count operand."""

    type: Literal["mean"] = "mean"
    source: str
    count: str | Annotated[int, Field(strict=True, ge=2, le=256)]
    destination: str
    enable: str = "TRUE"
    error: list[Coil] = Field(default_factory=list, max_length=32)

    def integer_action(self) -> IntegerFunction:
        return IntegerFunction.model_validate(self.model_dump())

    @model_validator(mode="after")
    def check(self) -> "CommonMean":
        self.integer_action()
        return self


class CommonSqrt(Model):
    """FUN26 SQRT with direct register source and destination."""

    type: Literal["sqrt"] = "sqrt"
    source: str
    destination: str
    enable: str = "TRUE"
    error: list[Coil] = Field(default_factory=list, max_length=32)

    def integer_action(self) -> IntegerFunction:
        return IntegerFunction.model_validate(self.model_dump())

    @model_validator(mode="after")
    def check(self) -> "CommonSqrt":
        self.integer_action()
        return self


class CommonInPlaceInteger(Model):
    """Sampled in-place FUN27 NEG, FUN28 ABS, and FUN29 EXT forms."""

    type: Literal["neg", "abs", "ext"]
    destination: str
    enable: str = "TRUE"

    def integer_action(self) -> IntegerFunction:
        return IntegerFunction.model_validate(self.model_dump())

    @model_validator(mode="after")
    def check(self) -> "CommonInPlaceInteger":
        self.integer_action()
        return self


class CommonComparisonContact(Model):
    """One FUN170..175 comparison contact driving explicit result coils."""

    type: Literal["comparison_contact"] = "comparison_contact"
    operation: Literal["eq", "gt", "lt", "ne", "ge", "le"]
    sa: str
    sb: str | Annotated[int, Field(strict=True, ge=0, le=32767)]
    result: Annotated[list[Coil], Field(min_length=1, max_length=32)]

    def contact(self) -> ComparisonContact:
        return ComparisonContact(operation=self.operation, sa=self.sa, sb=self.sb)

    @model_validator(mode="after")
    def check(self) -> "CommonComparisonContact":
        self.contact()
        return self


class CommonProcessFunction(ProcessFunction):
    """Sample-backed register/table/matrix forms exposed by the Common builder."""

    type: Literal[
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
        "matrix_and",
        "matrix_or",
        "matrix_xor",
        "matrix_xnr",
        "matrix_invert",
        "matrix_compare",
        "matrix_bit_read",
        "matrix_bit_write",
        "matrix_bit_shift",
        "matrix_bit_rotate",
        "matrix_bit_count",
        "table_sort",
        "zone_write",
        "move_inverse",
        "toggle_bit",
        "bit_move",
        "nibble_move",
        "byte_move",
        "word_exchange",
        "byte_swap",
        "nibble_unite",
        "nibble_distribute",
        "byte_unite",
        "byte_distribute",
        "shift_left",
        "shift_right",
        "rotate_left",
        "rotate_right",
        "binary_to_gray",
        "gray_to_binary",
        "decode_bits",
        "hms_to_seconds",
        "seconds_to_hms",
        "encode_bits",
        "to_seven_segment",
        "ascii_literal",
        "ascii_to_hex",
        "hex_to_ascii",
        "bit_shift",
        "file_register",
        "memory_pack_write",
        "memory_pack_read",
        "system_status",
        "pulse_output",
        "pwm",
        "speed_detect",
    ]


CommonFunction = Annotated[
    CommonMove
    | CommonMean
    | CommonSqrt
    | CommonInPlaceInteger
    | CommonComparisonContact
    | CommonProcessFunction
    | Arithmetic
    | AnalogConversion
    | BitAccess
    | FloatOperation
    | FloatCompare
    | FloatZoneCompare
    | RegisterStep
    | Bitwise
    | ExclusiveLogic
    | ZoneCompare
    | Compare
    | WordConversion
    | Divide48
    | SumWords
    | LinearConversion
    | Timer
    | Counter
    | AccumulativeTimer
    | Watchdog
    | HighSpeedCounter
    | UpDownCounter
    | ImmediateIO
    | PeripheralIO
    | TemperatureControl
    | PID,
    Field(discriminator="type"),
]


COMMON_FUN_EVIDENCE: dict[str, dict[str, object]] = {
    "move_word": {
        "fun": 8,
        "samples": ["private native export", "private native export"],
        "forms": "signed 16-bit constant or direct word source; direct writable destination",
    },
    "arithmetic:add": {
        "fun": 11,
        "samples": ["private native export", "private native export"],
        "forms": "direct Sa/D; nonnegative constant or sampled register Sb",
    },
    "arithmetic:sub": {
        "fun": 12,
        "samples": ["private native export"],
        "forms": (
            "direct Sa/D; nonnegative constant Sb is sample-backed; register Sb is inferred "
            "from shared operand metadata and the FUN11..14 opcode family"
        ),
    },
    "arithmetic:mul": {
        "fun": 13,
        "samples": ["private native export"],
        "forms": (
            "direct Sa; nonnegative constant Sb is sample-backed; register Sb is inferred; "
            "two-word destination"
        ),
    },
    "arithmetic:div": {
        "fun": 14,
        "samples": ["private native export"],
        "forms": (
            "direct Sa; nonzero nonnegative constant Sb is sample-backed; register Sb is "
            "inferred; quotient/remainder destination"
        ),
    },
    "increment": {
        "fun": 15,
        "samples": ["private native export"],
        "forms": "16-bit direct writable R/D destination",
    },
    "decrement": {
        "fun": 16,
        "samples": ["private native export"],
        "forms": "16-bit direct writable R/D destination",
    },
    "compare": {
        "fun": 17,
        "samples": ["private native export"],
        "forms": "direct register Sa/Sb; equal/greater/less normal status coils",
    },
    "bitwise:and": {
        "fun": 18,
        "samples": ["private native export"],
        "forms": "16-bit direct R/D Sa/Sb and writable destination",
    },
    "bitwise:or": {
        "fun": 19,
        "samples": ["private native export"],
        "forms": (
            "16-bit direct R/D Sa/Sb and writable destination; F4C8 OR is an inferred "
            "opcode-family variant without its own native export"
        ),
    },
    "word_conversion:to_bcd": {
        "fun": 20,
        "samples": ["private native export"],
        "forms": "constant 0..9999 source; direct writable word destination",
    },
    "word_conversion:to_bin": {
        "fun": 21,
        "samples": ["private native export"],
        "forms": "direct word source and writable destination",
    },
    "div48": {
        "fun": 23,
        "samples": ["private native export", "private native export"],
        "forms": (
            "direct three-word Sa/Sb/D; sampled two-input form has U/S and sampled "
            "single-input form omits U/S; optional normal zero/error coils"
        ),
    },
    "sum": {
        "fun": 24,
        "samples": ["private native export", "private native export"],
        "forms": "direct source span; constant N=1..511; direct writable destination",
    },
    "mean": {
        "fun": 25,
        "samples": ["private native export"],
        "forms": (
            "direct R/D source/destination; register N is sample-backed; constant N=2..256 "
            "is inferred from static operand metadata and mode encoding"
        ),
    },
    "sqrt": {
        "fun": 26,
        "samples": ["private native export"],
        "forms": "16-bit direct R/D source and destination",
    },
    "neg": {
        "fun": 27,
        "samples": ["private native export"],
        "forms": "16-bit in-place direct R/D destination",
    },
    "abs": {
        "fun": 28,
        "samples": ["private native export"],
        "forms": "16-bit in-place direct R/D destination",
    },
    "ext": {
        "fun": 29,
        "samples": ["private native export"],
        "forms": "16-bit direct R/D source in place; two-word destination span",
    },
    "pid": {
        "fun": 30,
        "samples": ["private native export"],
        "forms": "sampled SR8/OR1/PR7/WR5 register layout; constant 10 ms interval units",
    },
    "lcnv": {
        "fun": 33,
        "samples": ["private native export"],
        "forms": "sample-backed Md=0/L=1; other accepted Md/L combinations are inferred",
    },
    "exclusive_logic:xor": {
        "fun": 35,
        "samples": ["private native export"],
        "forms": "16-bit direct supported word operands and writable destination",
    },
    "exclusive_logic:xnr": {
        "fun": 36,
        "samples": ["private native export"],
        "forms": "16-bit direct supported word operands and writable destination",
    },
    "zone_compare": {
        "fun": 37,
        "samples": ["private native export"],
        "forms": "direct R/D source; signed constant upper/lower; normal result coils",
    },
    "timer": {
        "fun": "T",
        "samples": ["private native export", "private native export"],
        "forms": "constant preset and direct T address; configured time base remains external",
    },
    "counter": {
        "fun": "C",
        "samples": ["private native export", "private native export"],
        "forms": "constant preset and direct C address; pulse and clear Boolean expressions",
    },
    "accumulative_timer": {
        "fun": "87/88/89",
        "samples": ["private native export"],
        "forms": "10/100/1000 ms units with direct register PV/CV",
    },
}

_FLOAT_SAMPLE_NETWORKS = {
    "i_to_f": "private native export",
    "f_to_i": "private native export",
    "add": "private native export",
    "sub": "private native export",
    "mul": "private native export",
    "div": "private native export",
    "sqrt": "private native export",
    "sin": "private native export",
    "cos": "private native export",
    "tan": "private native export",
    "neg": "private native export",
    "abs": "private native export",
    "ln": "private native export",
    "exp": "private native export",
    "log": "private native export",
    "pow": "private native export",
    "asin": "private native export",
    "acos": "private native export",
    "atan": "private native export",
}
_FLOAT_FUN_NUMBERS = {
    "i_to_f": 200,
    "f_to_i": 201,
    "add": 202,
    "sub": 203,
    "mul": 204,
    "div": 205,
    "sqrt": 208,
    "sin": 209,
    "cos": 210,
    "tan": 211,
    "neg": 212,
    "abs": 213,
    "ln": 214,
    "exp": 215,
    "log": 216,
    "pow": 217,
    "asin": 218,
    "acos": 219,
    "atan": 220,
}

COMMON_FUN_EVIDENCE.update(
    {
        f"float_operation:{operation}": {
            "fun": _FLOAT_FUN_NUMBERS[operation],
            "samples": [sample],
            "forms": (
                "sample-backed 32-bit floating operation; direct R/D and sampled constant mode"
            ),
        }
        for operation, sample in _FLOAT_SAMPLE_NETWORKS.items()
    }
)

COMMON_FUN_EVIDENCE.update(
    {
        "udctr": {
            "fun": 7,
            "samples": ["private native export"],
            "forms": (
                "sample-backed 16-bit UDCTR with direct CV, constant preset and "
                "pulse/up/clear controls"
            ),
        },
        "imdio": {
            "fun": 74,
            "samples": ["private native export"],
            "forms": (
                "sample-backed main-unit X/Y span with explicit IO contract and target profile"
            ),
        },
        "tkey": {
            "fun": 76,
            "samples": ["private native export"],
            "forms": "sample-backed X10 keypad span, destination and explicit Y/M key range",
        },
        "hkey": {
            "fun": 77,
            "samples": ["private native export"],
            "forms": "sample-backed X4/Y4 keypad, destination, Y/M key range and exclusive WR1",
        },
        "dsw": {
            "fun": 78,
            "samples": ["private native export"],
            "forms": "sample-backed X4/Y4 switch, destination and exclusive WR2",
        },
        "7sgdl": {
            "fun": 79,
            "samples": ["private native export"],
            "forms": "sample-backed Y8 display span, mode 0..3, source and exclusive WR1",
        },
        "muxi": {
            "fun": 80,
            "samples": ["private native export"],
            "forms": (
                "sample-backed X8/YN multiplex input, rows 2..8, destination and exclusive WR1"
            ),
        },
        "pulse_output": {
            "fun": 81,
            "samples": ["private native export"],
            "forms": (
                "sample-backed PLSO MD0 non-P with explicit distinct UY/DY and register operands"
            ),
        },
        "pwm": {
            "fun": 82,
            "samples": ["private native export"],
            "forms": "sample-backed PWM with constant To/Tp milliseconds and explicit Y0..15",
        },
        "speed_detect": {
            "fun": 83,
            "samples": ["private native export"],
            "forms": (
                "sample-backed SPD with explicit X0..7, constant sample time and "
                "three-word destination"
            ),
        },
        "tpctl": {
            "fun": 86,
            "samples": ["private native export"],
            "forms": (
                "sample-backed TPCTL register layout with explicit Y span, target profile and "
                "exclusive WR9"
            ),
        },
        "comparison_contact:eq": {
            "fun": 170,
            "samples": ["private native export"],
            "forms": (
                "sample-backed first-position register equality contact with explicit result coils"
            ),
        },
        "comparison_contact:gt": {
            "fun": 171,
            "samples": ["private native export"],
            "forms": (
                "inferred first-position register greater-than contact; native sample is "
                "series position"
            ),
        },
        "comparison_contact:lt": {
            "fun": 172,
            "samples": ["private native export"],
            "forms": (
                "inferred first-position register less-than contact; native sample is "
                "series position"
            ),
        },
        "comparison_contact:ne": {
            "fun": 173,
            "samples": ["private native export"],
            "forms": (
                "sample-backed first-position register not-equal contact with explicit result coils"
            ),
        },
        "comparison_contact:ge": {
            "fun": 174,
            "samples": ["private native export"],
            "forms": (
                "inferred first-position register greater-or-equal contact; native sample is "
                "series position"
            ),
        },
        "comparison_contact:le": {
            "fun": 175,
            "samples": ["private native export"],
            "forms": (
                "inferred first-position register less-or-equal contact; native sample is "
                "series position"
            ),
        },
    }
)

_COMMON_PROCESS_EVIDENCE: dict[str, tuple[int, str]] = {
    "ramp": (95, "private native export"),
    "ramp2": (98, "private native export"),
    "reg_to_table": (100, "private native export"),
    "table_to_reg": (101, "private native export"),
    "table_to_table": (102, "private native export"),
    "block_table_move": (103, "private native export"),
    "table_swap": (104, "private native export"),
    "register_table_search": (105, "private native export"),
    "table_compare": (106, "private native export"),
    "table_fill": (107, "private native export"),
    "table_shift": (108, "private native export"),
    "table_rotate": (109, "private native export"),
    "queue": (110, "private native export"),
    "stack": (111, "private native export"),
    "block_compare": (112, "private native export"),
    "table_sort": (113, "private native export"),
    "zone_write": (114, "private native export"),
    "matrix_and": (120, "private native export"),
    "matrix_or": (121, "private native export"),
    "matrix_xor": (122, "private native export"),
    "matrix_xnr": (123, "private native export"),
    "matrix_invert": (124, "private native export"),
    "matrix_compare": (125, "private native export"),
    "matrix_bit_read": (126, "private native export"),
    "matrix_bit_write": (127, "private native export"),
    "matrix_bit_shift": (128, "private native export"),
    "matrix_bit_rotate": (129, "private native export"),
    "matrix_bit_count": (130, "private native export"),
    "move_inverse": (9, "private native export"),
    "toggle_bit": (10, "private native export"),
    "bit_move": (42, "private native export"),
    "nibble_move": (43, "private native export"),
    "byte_move": (44, "private native export"),
    "word_exchange": (45, "private native export"),
    "byte_swap": (46, "private native export"),
    "nibble_unite": (47, "private native export"),
    "nibble_distribute": (48, "private native export"),
    "byte_unite": (49, "private native export"),
    "byte_distribute": (50, "private native export"),
    "shift_left": (51, "private native export"),
    "shift_right": (52, "private native export"),
    "rotate_left": (53, "private native export"),
    "rotate_right": (54, "private native export"),
    "binary_to_gray": (55, "private native export"),
    "gray_to_binary": (56, "private native export"),
    "decode_bits": (57, "private native export"),
    "hms_to_seconds": (61, "private native export"),
    "seconds_to_hms": (62, "private native export"),
    "encode_bits": (58, "private native export"),
    "to_seven_segment": (59, "private native export"),
    "ascii_literal": (60, "private native export"),
    "ascii_to_hex": (63, "private native export"),
    "hex_to_ascii": (64, "private native export"),
    "bit_shift": (6, "private native export"),
    "system_status": (190, "private native export"),
    "file_register": (160, "private native export"),
    "memory_pack_write": (161, "private native export"),
    "memory_pack_read": (162, "private native export"),
}

COMMON_FUN_EVIDENCE.update(
    {
        function: {
            "fun": fun,
            "samples": [sample],
            "forms": "sample-backed direct register form with Production-validated controls",
        }
        for function, (fun, sample) in _COMMON_PROCESS_EVIDENCE.items()
    }
)

COMMON_FUN_EVIDENCE.update(
    {
        "wdt": {
            "fun": 90,
            "samples": ["private native export"],
            "forms": "sample-backed WDT with discrete 50..120 ms setting and Boolean EN",
        },
        "rswdt": {
            "fun": 91,
            "samples": ["private native export"],
            "forms": "sample-backed reset-watchdog form with Boolean EN",
        },
        "hsctr": {
            "fun": 92,
            "samples": ["private native export"],
            "forms": "sample-backed HSC0 current-value read anchor",
        },
        "hsctw": {
            "fun": 93,
            "samples": ["private native export"],
            "forms": "sample-backed double-word constant-zero write to HSC0.PV",
        },
    }
)


def _float_form_is_sample_backed(function: FloatOperation) -> bool:
    """Match operand modes present in native test11..14 exports."""

    operation = function.operation
    if operation in {"i_to_f", "f_to_i", "sqrt", "sin", "cos", "ln", "exp", "log"}:
        return isinstance(function.sa, str) and function.sb is None
    if operation in {"add", "sub", "mul"}:
        return isinstance(function.sa, str) and isinstance(function.sb, str)
    if operation == "div":
        return isinstance(function.sa, float) and isinstance(function.sb, str)
    if operation == "tan":
        return isinstance(function.sa, float) and function.sb is None
    if operation in {"neg", "abs"}:
        return function.sa is None and function.sb is None
    if operation == "pow":
        return isinstance(function.sa, str) and isinstance(function.sb, float)
    if operation in {"asin", "acos", "atan"}:
        return isinstance(function.sa, str) and function.sb is None
    return False


COMMON_FUN_EVIDENCE.update(
    {
        "float_compare": {
            "fun": 206,
            "samples": ["private native export"],
            "forms": "32-bit float compare with sampled constant/register sources and status coils",
        },
        "float_zone_compare": {
            "fun": 207,
            "samples": ["private native export"],
            "forms": "32-bit float zone compare with direct source, bounds and status coils",
        },
        "adcnv": {
            "fun": 32,
            "samples": ["private native export"],
            "forms": "sampled Pl=0, constant N=1..64, direct source/destination and selector EN",
        },
        "mlc": {
            "fun": 34,
            "samples": ["private native export"],
            "forms": "constant Sl=1..64, direct S/D, Tx/Ty tables and register Tl",
        },
        "bitrd": {
            "fun": 40,
            "samples": ["private native export"],
            "forms": "16-bit direct word, constant bit 0..15 and optional OTB/ERR coils",
        },
        "bitwr": {
            "fun": 41,
            "samples": ["private native export"],
            "forms": "16-bit writable direct word, constant bit 0..15 and Boolean INB",
        },
    }
)


def common_fun_evidence(function: CommonFunction) -> dict[str, object]:
    """Return the traceable sample/form record for one supported common function."""

    operation = getattr(function, "operation", None)
    key = f"{function.type}:{operation}" if operation is not None else function.type
    inferred = (
        isinstance(function, Arithmetic)
        and function.operation in {"sub", "mul", "div"}
        and isinstance(function.sb, str)
    ) or (isinstance(function, CommonMean) and isinstance(function.count, int))
    if isinstance(function, Bitwise) and function.operation == "or":
        inferred = True
    if isinstance(function, LinearConversion) and (function.mode != 0 or function.length != 1):
        inferred = True
    if isinstance(function, FloatOperation) and not _float_form_is_sample_backed(function):
        inferred = True
    if isinstance(function, FloatCompare) and not (
        isinstance(function.sa, float) and isinstance(function.sb, str)
    ):
        inferred = True
    if isinstance(function, FloatZoneCompare) and not (
        isinstance(function.upper, float) and isinstance(function.lower, str)
    ):
        inferred = True
    if isinstance(function, CommonComparisonContact) and function.operation not in {"eq", "ne"}:
        inferred = True
    return {
        "key": key,
        **COMMON_FUN_EVIDENCE[key],
        "evidence_level": "inferred" if inferred else "sample-backed",
        "gui_verification": "not verified for generated artifact",
    }


class CommonFunSpec(Model):
    """Ordered common-function program; every entry becomes one Ladder network."""

    requirement: Annotated[str, Field(min_length=1, max_length=1000)]
    functions: Annotated[list[CommonFunction], Field(min_length=1, max_length=1000)]
    symbols: dict[str, str] = Field(default_factory=dict, max_length=512)


PHYSICAL_COMMON_TYPES = frozenset(
    {
        "imdio",
        "tkey",
        "hkey",
        "dsw",
        "7sgdl",
        "muxi",
        "pulse_output",
        "pwm",
        "speed_detect",
        "tpctl",
    }
)


def common_fun_physical_types(spec: CommonFunSpec) -> list[str]:
    """List hardware-facing Common entries that require an explicit CPU profile."""

    return sorted({function.type for function in spec.functions} & PHYSICAL_COMMON_TYPES)


def common_fun_ladder(
    spec: CommonFunSpec, *, profile: HeaderProfile = "FBs-20MC"
) -> tuple[Ladder, dict[str, object]]:
    """Lower a focused common-FUN specification to the canonical Ladder IR."""

    networks: list[Network] = []
    for function in spec.functions:
        comment = f"{function.type}: {spec.requirement}"
        if isinstance(function, (Timer, Counter)):
            networks.append(Network(block=function, comment=comment))
        elif isinstance(function, CommonMove):
            networks.append(
                Network(
                    action=ProcessFunction(
                        type="move_word",
                        source=function.source,
                        destination=function.destination,
                        enable=function.enable,
                    ),
                    comment=comment,
                )
            )
        elif isinstance(function, (CommonMean, CommonSqrt, CommonInPlaceInteger)):
            networks.append(Network(action=function.integer_action(), comment=comment))
        elif isinstance(function, CommonComparisonContact):
            networks.append(
                Network(
                    comparison_chain=[function.contact()],
                    coils=function.result,
                    comment=comment,
                )
            )
        else:
            networks.append(Network(action=function, comment=comment))
    ladder = Ladder(profile=profile, networks=networks, symbols=spec.symbols)
    return ladder, {
        "kind": "common_fun",
        "requirement": spec.requirement,
        "functions": [function.model_dump(mode="json") for function in spec.functions],
        "evidence": [common_fun_evidence(function) for function in spec.functions],
        "network_count": len(networks),
        "scope": (
            "Parameterized common FUN generation through the canonical Production LDR pipeline"
        ),
    }
