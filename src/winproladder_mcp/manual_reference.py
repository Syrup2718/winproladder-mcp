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
            "advanced": "進階篇應用指令.pdf: 7-3..13, 7-19..24, 7-28..29, "
            "7-59..61, 7-79..99, 7-151..171, 7-66..73",
            "temperature": "CH20_FB-PLC溫度量測及溫度PID控制.pdf: 20-44..47 (older edition)",
            "basic": "基本應用指令.pdf: 7-2, 7-18..19, 7-26",
            "rtc": "CH16_萬年曆（RTC）.pdf: 16-1..2 (FB-PLC MA/MC with RTC)",  # noqa: RUF001
        },
        "rule": "Manual operand limits define PLC legality. Sample addresses are not maxima. "
        "LDR encoding support, CPU availability and manual editions are separate evidence.",
        "instruction_modes": {
            "TABLE_TRANSFERS": {
                "pages": ["7-96", "7-97", "7-98", "7-99"],
                "length": "101/102: 2..2048; 103/104: 2..256",
                "101_102": "CLR clears Pr before transfer, independent of EN. "
                "Then Ts[Pr] -> Rd (101) or Td[Pr] (102). END when Pr=L-1; "
                "otherwise INC increments Pr. Invalid Pr sets ERR",
                "103": "Whole source table copied to destination in one execution",
                "104": "Both tables exchanged in one execution; both must be writable",
                "codec": "16-bit non-P, constant L, direct R/D banks only. Manual allows "
                "additional D/P, register-length and indirect forms; those encodings remain "
                "unresolved",
                "evidence": "test21 N002 CLR X5 uses normal contact 6005; "
                "7FE8 denotes FALSE, not inverted physical CLR. Corrects test20 interpretation",
            },
            "ASCWR": {
                "pages": ["7-87"],
                "MD": "0 ASCII/Printer via Port1; 1 reserved for specific purposes",
                "work": "Pt uses 8 exclusive registers; file S ends at END, may embed operands",
                "inputs": "EN rising-edge starts, PAU=1 pauses, ABT=1 aborts",
                "codec": "Only sampled 94P MD=1. Do not apply MD=0 runtime semantics "
                "to reserved MD=1; variable source span is unresolved",
            },
            "RAMP": {
                "pages": ["7-88", "7-89"],
                "Tn": "T0..255, must be configured for 10 ms time base and not reused",
                "PV": "M1974=0 timer count in 10 ms units; M1974=1 increment per 10 ms",
                "direction": "U/D=1 ramp up, 0 ramp down; sampled when EN rises; PAU pauses",
                "limits": "SU must exceed SL at runtime; D+1 is an exclusive work register",
                "codec": "Sampled non-P form and register PV/SL/SU; constants/P not encoded",
            },
            "RAMP2": {
                "pages": ["7-90", "7-91", "7-92", "7-93"],
                "values": "Om/Rt 0..65535; Ta/Td 0..65000 ms; Rt stable at least 2 scans",
                "banks": "HR R0..3839, OR R3904..3967, ROR R5000..8071, D0..3999",
                "work": "4 exclusive registers",
                "EN": "0 immediately clears Rc and ACC/DEC; 1 tracks/clamps Rt toward Om",
                "OS": "V4.60 or later; not verified on attached hardware",
                "codec": "Register operands only. R3904 is sampled, other OR offsets inferred",
            },
            "REGISTER_TO_TABLE": {
                "pages": ["7-94", "7-95"],
                "length": "2..2048; pointer range 0..L-1, 16-bit pointer even in D form",
                "order": "CLR resets Pr before transfer and also works independently of EN; "
                "copy Rs to Td[Pr]; END if Pr=L-1, otherwise INC increments Pr",
                "codec": "16-bit non-P, register Rs/Td/Pr, constant L. Constant data, "
                "register length, D/P and indirect modes not yet serialized",
            },
            "ACCUMULATIVE_TIMER": {
                "pages": ["7-81", "7-82"],
                "units_ms": {"87": 10, "88": 100, "89": 1000},
                "inputs": "EN=0 clears CV; EN=1/TIM=0 retains; EN=1/TIM=1 counts",
                "PV": "constant 0..32767 or word; current codec implements direct R/D only",
                "CV": "Manual permits T/C, word groups and register banks including IR; "
                "codec currently implements T0..255 and direct R/D, including IR",
                "outputs": "TUP done; NUP not done",
            },
            "TPCTL": {
                "pages": ["7-79", "7-80", "20-44", "20-45", "20-46", "20-47"],
                "zones": "Sn0..31, Zn1..32, Sn+Zn<=32; Yn and SV/OS/PR/IR/DR/OR span Zn",
                "work": "9 exclusive words",
                "Md": "0 modified minimum overshoot, 1 generic PID; absent from test19, "
                "encoding unresolved, do not guess default",
                "H/C": "Older CH20 20-45: 1 heating, 0 cooling",
                "temperature_source": "7-80: planning table unless R4003=A55AH and "
                "R4004=10000..13839 (R0..3839) or 20000..23999 (D0..3999)",
                "edition_difference": "Older CH20 20-44: Sn0..23, Zn1..24, D0..3071, "
                "FUN85 prerequisite; newer 7-79: 32 zones/D4095 and planning. "
                "Do not transfer hardware prerequisites or defaults between editions",
            },
            "CALL": {
                "pages": ["7-61"],
                "semantics": "Calls labeled subroutine, returns via RTS; max 5 nested levels "
                "including interrupts",
                "encoding_boundary": "Exact test19 CALL1 anchor decoded; target metadata "
                "unresolved, sample lacks LBL1/RTS; generation rejected",
            },
            "ADCNV": {
                "pages": ["7-12", "7-13"],
                "Pl": {"0": "unipolar", "1": "bipolar"},
                "F/T": {"0": "12-bit", "1": "14-bit"},
                "N_words": [1, 64],
                "evidence": "Source IR column blank in page 7-12 operand table, but "
                "page 7-13 example and test18 both use R3840; supported on that evidence",
                "encoding_boundary": "Only Pl=0 and constant N sampled; Pl=1/register N "
                "are manual-defined but not encoded yet",
            },
            "MLC": {
                "pages": ["7-19", "7-20"],
                "Sl": [1, 64],
                "Tl": [2, 255],
                "D_bank": [0, 3999],
                "X/Y": {"0": "Tx to Ty", "1": "Ty to Tx"},
                "OVR": "source below/above conversion table range",
                "encoding_boundary": "Only constant Sl and register Tl sampled; "
                "dynamic Tl conservatively tracks 255 possible words in each table",
            },
            "BITRD_BITWR": {
                "pages": ["7-28", "7-29"],
                "N_16bit": [0, 15],
                "N_D_form": [0, 31],
                "BITRD_EN0": "M1919=0 retains previous OTB; M1919=1 clears OTB",
                "BITWR": "Replaces only selected bit with INB, other bits unchanged",
                "encoding_boundary": "16-bit direct R/D and constant N currently encoded",
            },
            "LBL_JMP": {
                "pages": ["7-59", "7-60"],
                "names": "1..6 alphanumeric, unique; reserved "
                "interrupt names are not ordinary labels",
                "JMP": "Forward/backward within same main/subprogram region; backward "
                "loops can exceed watchdog time",
                "encoding_boundary": "Only exact test18 label/jump 1 pair. Target metadata "
                "not decoded, so only complete unchanged sample generation allowed",
            },
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
