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
            "advanced": "進階篇應用指令.pdf: 7-151..171, 7-66, float operand tables",
            "basic": "基本應用指令.pdf: 7-2, 7-18..19, 7-26",
            "rtc": "CH16_萬年曆（RTC）.pdf: 16-1..2 (FB-PLC MA/MC with RTC)",  # noqa: RUF001
        },
        "rule": "Manual operand limits define PLC legality. Sample addresses are not maxima. "
        "LDR encoding support, CPU availability and manual editions are separate evidence.",
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
            "not_encoded": "Special M1912..2001, R3904..4167 (including RTC), S and arbitrary "
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
