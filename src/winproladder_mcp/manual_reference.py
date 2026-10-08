"""Manual-defined operand limits and RTC reference; no PLC connection or execution."""

from typing import Any

RTC_FIELDS = {
    "R4128": ("second", 0, 59),
    "R4129": ("minute", 0, 59),
    "R4130": ("hour", 0, 23),
    "R4131": ("day", 1, 31),
    "R4132": ("month", 1, 12),
    "R4133": ("year_code", 0, 99),
    "R4134": ("weekday_code", 0, 6),
}


def manual_reference() -> dict[str, Any]:
    return {
        "sources": {
            "advanced": "進階篇應用指令.pdf: 7-3..11, 7-83..86, 7-151..171, 7-66..73",
            "basic": "基本應用指令.pdf: 7-2, 7-18..19, 7-26",
            "rtc": "CH16_萬年曆（RTC）.pdf: 16-1..2 (FB-PLC MA/MC with RTC)",  # noqa: RUF001
        },
        "rule": "Manual operand limits define PLC legality. Sample addresses are not maxima. "
        "LDR encoding support, CPU availability and manual editions are separate evidence.",
        "instruction_modes": {
            "DIV48": {
                "page": "7-3",
                "unsigned_when": {"0": "signed", "1": "unsigned"},
                "operand_words": {"Sa": 3, "Sb": 3, "D": 3},
                "outputs": {"FO0": "quotient zero", "FO1": "divisor zero; no execution"},
                "encoding_boundary": "Manual explains U/S semantics, not LDR opcodes. "
                "test16 F46C has U/S; test17 F474 omits it. The supplied page "
                "does not identify fixed signedness for F474 or FBn-specific behavior.",
            },
            "MEAN": {
                "page": "7-5",
                "runtime_N": [2, 256],
                "forms_in_manual": "16-bit, D=32-bit, P=rising-edge execution; N constant/register",
                "invalid_N": "ERR=1; instruction does not execute",
                "encoding_boundary": "Current encoder supports register N, 16-bit non-P form; "
                "constant N and D/P are manual-legal but not encoded yet",
            },
            "CRC16": {
                "page": "7-11",
                "N_bytes": [1, 256],
                "MD0": "Uses low byte of each of N consecutive source registers; "
                "D receives CRC upper byte, D+1 receives lower byte",
                "MD1": "Reserved in the supplied manual; export test17 proves GUI accepts "
                "and encodes MD=1, but does not define its runtime algorithm",
                "encoding_boundary": "MD=1 constant-N export form supported; MD=0 and "
                "register N are described in the manual but their encodings are not implemented",
            },
            "PID": {
                "page": "7-10",
                "inputs": ["A/M", "BUM", "D/R"],
                "Ts": {"range": [1, 3000], "unit_ms": 10},
                "words": {"SR": 8, "OR": 1, "PR": 7, "WR": 5},
                "WR": "Exclusive workspace; other locations must not reuse it",
            },
            "WDT": {
                "page": "7-83",
                "settings": list(range(50, 121, 10)),
                "unit_ms": 10,
            },
            "HSCT": {
                "pages": ["7-85", "7-86"],
                "CN": {"0..3": "HSC0..3 or corresponding HST", "4": "HSTA"},
                "D": {"0": "CV", "1": "PV"},
                "encoding_boundary": "Manual selector values do not determine serialized "
                "byte positions. Current anchors: HSC0 read and 93D source=0,HSC0,PV write",
            },
        },
        "limits": {
            "trig_angle": {"range": [-18000, 18000], "unit": "0.01 degrees", "source_words": 1},
            "FUN214_220_D_bank": [0, 3999],
            "inverse_trig_result_unit": "radians",
            "imdio": {
                "count": [1, 36],
                "main_unit_points": {
                    "10": {"X": 6, "Y": 4},
                    "14": {"X": 8, "Y": 6},
                    "20": {"X": 12, "Y": 8},
                    "24": {"X": 14, "Y": 10},
                    "32": {"X": 20, "Y": 12},
                    "40": {"X": 24, "Y": 16},
                    "60": {"X": 36, "Y": 24},
                },
            },
            "ordinary_M": [0, 1911],
            "special_M": [1912, 2001],
            "S": [0, 999],
            "X_Y_T_C": [0, 255],
            "word_groups": {"WX_WY": [0, 240], "WM": [0, 1896], "WS": [0, 984]},
            "R_banks": {
                "HR": [0, 3839],
                "IR": [3840, 3903],
                "OR": [3904, 3967],
                "SR": [3968, 4167],
                "ROR": [5000, 8071],
            },
            "D_manual_editions": {"basic": [0, 3071], "advanced": [0, 4095]},
            "signed_16": [-32768, 32767],
            "signed_32": [-2147483648, 2147483647],
            "float": {
                "format": "IEEE-754 binary32",
                "manual_approx_max": 3.4e38,
                "encoding_max_finite": 3.4028234663852886e38,
            },
            "timer_preset": [0, 32767],
            "timer_factory_bases_seconds": {"T0..49": 0.01, "T50..199": 0.1, "T200..255": 1},
        },
        "compiler_boundary": {
            "direct_words": "R0..3839, read-only R3840..3903, R5000..8071, D0..4095; "
            "full spans checked. High-bank encoding inferred from test11/test12 anchors. "
            "D capacity depends on CPU/manual edition; header alone does not validate hardware.",
            "M": "M0..1911: ordinary relay range, address extension inferred. "
            "Automatic helper allocation remains M0..255. M-to-M remains forbidden.",
            "not_encoded": "Special M1912..2001, R3904..4167 (except peripheral R3999), "
            "S and arbitrary "
            "word groups are manual-defined but not yet implemented in the binary codec.",
            "forms": "Per-instruction K/register permissions apply. Integer Sb constants are "
            "still 0..32767 in the implemented opcode form; negative/32-bit/P/indirect forms "
            "require their own encoding. Do not label them illegal PLC operands.",
            "timing": "Manual factory time bases do not override the user's current project "
            "timing contract or GUI millisecond entry. No automatic scaling change.",
        },
        "rtc": {
            "registers": {
                r: {"field": f, "min": lo, "max": hi} for r, (f, lo, hi) in RTC_FIELDS.items()
            },
            "R4135": "hour in high byte; minute in low byte. hour*256+minute, not HHMM.",
            "M1952": "0: RTC runs, CPU refreshes R4128..R4135 every scan. "
            "1: stop counting/readback; 1->0 writes R4128..R4134 to RTC and resumes.",
            "M1953": "0->1 rounds RTC to a minute: seconds 0..29 clear; "
            "30..59 clear and increment minute.",
            "M1954": "Read-only installation flag: 1 means RTC installed.",
            "M1955": "Read-only invalid-setting flag: 1 means setting rejected.",
            "set_sequence": [
                "Verify RTC installed and intended CPU mapping.",
                "Set M1952=1 before writing to prevent refresh overwrites.",
                "Load valid R4128..R4134; do not write packed R4135 as a setting.",
                "Make M1952 transition 1->0, then check M1955 and readback.",
            ],
            "schedule": "For daily control use hour/minute, with an explicit inclusive start "
            "and exclusive end. Overnight windows use after-start OR before-end. "
            "Do not assume weekday 0=Sunday or a century: these pages do not specify them.",
            "policy": "Do not build M1954 -> M1952 or M self-holds. Special RTC relays are "
            "not exempt from forbid_m_to_m. Read-only scheduling need not write the clock.",
            "support": "Reference and supplied snapshot validation only. RTC LDR read/write "
            "generation, hardware access and execution simulation are not implemented.",
        },
    }


def analyze_rtc_snapshot(registers: dict[str, int]) -> dict[str, Any]:
    """Inspect caller-supplied numeric register values, never read a PLC."""
    required = set(RTC_FIELDS)
    if not required <= registers.keys() or registers.keys() - (required | {"R4135"}):
        raise ValueError("Supply R4128..R4134 exactly, optionally R4135")
    result: dict[str, Any] = {}
    for register, (field, low, high) in RTC_FIELDS.items():
        value = registers[register]
        if type(value) is not int or not low <= value <= high:
            raise ValueError(f"{register} {field} must be {low}..{high}")
        result[field] = value
    # February 29 remains possible: the manual gives no century interpretation.
    max_day = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][result["month"] - 1]
    if result["day"] > max_day:
        raise ValueError("Impossible month/day combination")
    packed = (result["hour"] << 8) | result["minute"]
    if "R4135" in registers:
        value = registers["R4135"]
        if type(value) is not int or not 0 <= value <= 65535:
            raise ValueError("R4135 must be a 16-bit word")
        result["packed_consistent"] = value == packed
    result.update(
        expected_R4135=packed,
        minute_of_day=result["hour"] * 60 + result["minute"],
        source="caller-supplied snapshot; no PLC connection",
        calendar_validation="field ranges and month/day only; century and weekday "
        "mapping unspecified; not a hardware setting approval",
    )
    return result
