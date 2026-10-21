"""Human-readable evidence warnings kept separate from IR encoding and decoding."""

from collections.abc import Callable

from .conversion_functions import CODES as CONVERSION_CODES
from .instruction_catalog import (
    ARITHMETIC_PAYLOADS,
    EDGE_PAYLOADS,
    LCNV_PAYLOADS,
    TEST8_PAYLOADS,
    TEST9_PAYLOADS,
    TEST10_PAYLOADS,
    TEST11_PAYLOADS,
    TEST12_PAYLOADS,
    TEST13_PAYLOADS,
    TEST14_PAYLOADS,
    TEST15_PAYLOADS,
    TEST28_PAYLOADS,
    TEST29_PAYLOADS,
    TEST30_PAYLOADS,
)
from .ir import (
    PID,
    AccumulativeTimer,
    AnalogConversion,
    Arithmetic,
    BitAccess,
    Bitwise,
    BreakLoop,
    Compare,
    Differential,
    Divide48,
    ExclusiveLogic,
    FloatCompare,
    FloatOperation,
    FloatZoneCompare,
    ForLoop,
    HighSpeedCounter,
    ImmediateIO,
    IntegerFunction,
    Ladder,
    LinearConversion,
    MasterControl,
    MasterEnd,
    Network,
    NextLoop,
    PeripheralIO,
    ProcessFunction,
    RegisterOr,
    RegisterStep,
    SampleCall,
    SampleFlow,
    SumWords,
    TemperatureControl,
    UpDownCounter,
    Watchdog,
    WordConversion,
    ZoneCompare,
    compile_network,
)
from .matrix_functions import CODES as MATRIX_CODES
from .memory_functions import CODES as MEMORY_CODES
from .packing_functions import CODES as PACKING_CODES
from .shift_functions import CODES as SHIFT_CODES
from .table_functions import CODES as TABLE22_CODES
from .transfer_functions import CODES as TRANSFER_CODES

Predicate = Callable[[Ladder], bool]

def collect_instruction_evidence(
    index: int, network: Network, payload: bytes
) -> list[dict[str, object]]:
    """Classify one compiled network against observed export anchors."""
    instruction_evidence: list[dict[str, object]] = []
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
            TEST28_PAYLOADS,
        )
        from .matrix_functions import CODES as MATRIX_CODES
        from .packing_functions import CODES as PACKING_CODES
        from .pulse_functions import CODES as PULSE_CODES
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
        if network.action.type in PULSE_CODES or payload.hex() == TEST28_PAYLOADS[7]:
            anchors = TEST28_PAYLOADS
            evidence_name = "test28"
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
    return instruction_evidence



def normalize_instruction_evidence(
    ladder: Ladder, evidence_rows: list[dict[str, object]]
) -> None:
    """Upgrade evidence rows when newer exact sample payloads supersede older families."""
    anchors = (
        (TEST28_PAYLOADS, "test28"),
        (TEST29_PAYLOADS, "test29"),
        (TEST30_PAYLOADS, "test30"),
    )
    for evidence in evidence_rows:
        index = evidence["network_index"]
        if not isinstance(index, int):
            continue
        network = ladder.networks[index]
        encoded = compile_network(network).hex()
        matched = False
        for payloads, source_name in anchors:
            observed = next((i for i, raw in payloads.items() if raw == encoded), None)
            if observed is not None:
                evidence.update(
                    status="observed_export", source=f"{source_name}.ldr N{observed:03}"
                )
                matched = True
        if (
            not matched
            and isinstance(network.action, ProcessFunction)
            and network.action.type in MEMORY_CODES
        ):
            evidence.update(status="inferred_variant", source="test30 + manual 7-137..150")


def _action(ladder: Ladder, classes: type | tuple[type, ...]) -> bool:
    return any(isinstance(network.action, classes) for network in ladder.networks)


def _process(ladder: Ladder, actions: set[str]) -> bool:
    return any(
        isinstance(network.action, ProcessFunction) and network.action.type in actions
        for network in ladder.networks
    )


WARNING_RULES: tuple[tuple[Predicate, str], ...] = (
    (
        lambda ladder: _action(ladder, (AnalogConversion, BitAccess, SampleFlow)),
        "test18: MLC register Tl tracks 255 possible table words; BITRD disabled OTB behavior "
        "depends on M1919. No runtime simulation. JMP only preserves the exact sample; "
        "unconditional backward jump can prevent scan completion and trigger watchdog. "
        "No GUI/PLC verification.",
    ),
    (
        lambda ladder: _action(ladder, (AccumulativeTimer, TemperatureControl)),
        "test19: timer unit_ms is the native time base (10/100/1000 ms); PV is a register "
        "count, TIM pauses, EN=0 clears. TPCTL temperature source depends on PLC planning/"
        "R4003/R4004; Md encoding unresolved. Accumulative timers have a bounded offline "
        "model; TPCTL does not. No GUI/PLC verification.",
    ),
    (
        lambda ladder: _process(ladder, {"ascwr", "ramp", "ramp2", "reg_to_table"}),
        "test20: ASCWR 94P MD=1 is reserved in manual 7-87; runtime and ASCII file spans "
        "unresolved. RAMP requires a 10 ms configured Tn and depends on M1974. RAMP2 times "
        "are ms, D bank ends D3999. No new function runtime simulation, GUI or PLC verification.",
    ),
    (
        lambda ladder: _process(
            ladder, {"table_to_reg", "table_to_table", "block_table_move", "table_swap"}
        ),
        "test21: sampled 16-bit non-P table functions, constant L, direct R/D operands. "
        "No built-in execution simulation, GUI import or PLC verification.",
    ),
    (
        lambda ladder: _process(
            ladder, {"system_status", "file_register", "memory_pack_write", "memory_pack_read"}
        ),
        "test30: STAT may overlap other registers/work areas; actual module count required. "
        "File/pack pointer bounds are runtime-dependent. Conservative references, no execution "
        "simulation, GUI import or PLC verification.",
    ),
    (
        lambda ladder: _process(ladder, set(TABLE22_CODES)),
        "test22: direct-register 16-bit non-P encodings, constant Rs only for 105/107. BKCMP "
        "reads 2*L limit words and M1975; writes L result bits. No native runtime simulation "
        "or GUI/PLC verification.",
    ),
    (
        lambda ladder: _process(ladder, set(CONVERSION_CODES)),
        "test27: ENCOD NL counts points; 7SG N means N+1 digits. ASC supports 1..12 ASCII "
        "letters/digits/spaces (packing inferred from test27/28). SEC/HMS use seconds, minutes, "
        "hours word order. HEX/ASCII and odd-digit 7SG preserve unused destination portions. "
        "BSHF CLR overrides EN; no independent or built-in execution model, GUI or PLC "
        "verification.",
    ),
    (
        lambda ladder: _process(ladder, set(SHIFT_CODES)),
        "test26: sampled 16-bit non-P shift/Gray/DECOD forms. BDIST N counts bytes; conservative "
        "max 128 source / 256 destination words. DECOD NL counts source bits, output 2^NL bits; "
        "source crosses B15 and clips at operand bank end. Unused output bits for NL<4 are not "
        "runtime-modeled. No native runtime simulation, GUI import or PLC verification.",
    ),
    (
        lambda ladder: _process(ladder, set(PACKING_CODES)),
        "test25: 16-bit non-P packing forms. BUNIT N is runtime bytes (1..256); static footprint "
        "covers 256 source and 128 destination words, including conservative destination reads "
        "for unspecified odd-N trailing byte behavior. UNIT/DIST clear unused nibbles; partial "
        "moves preserve other bits. No native runtime simulation, GUI import or PLC verification.",
    ),
    (
        lambda ladder: _process(ladder, set(TRANSFER_CODES)),
        "test24: sampled 16-bit non-P forms and constant lengths. TOGG uses rising edges. Matrix "
        "L counts words; MBCNT writes one word. Z-WR N is literal, 1..511. WY8 writes Y8..Y23. "
        "Direct R/D MOV and TOGG have a bounded model; other forms do not. No GUI or PLC "
        "verification.",
    ),
    (
        lambda ladder: _process(ladder, set(MATRIX_CODES)),
        "test23: matrix L counts words; bit pointer ranges 0..16*L-1. MINV register L uses "
        "conservative 256-word possible spans; actual length is a runtime value and is not "
        "evaluated. Sampled non-P forms only; no native execution, GUI or PLC verification.",
    ),
    (
        lambda ladder: _action(ladder, IntegerFunction),
        "test17: MEAN register N tracks all 256 potentially read words; CRC16 MD=1 is reserved "
        "in the supplied manual, so only encoding is supported and its runtime/reference "
        "semantics remain unverified. No native runtime simulation.",
    ),
    (
        lambda ladder: _action(
            ladder, (Watchdog, HighSpeedCounter, Divide48, SumWords, PID)
        ),
        "test16: WDT and PID times use 10 ms units. PID A/M is not EN. Only sampled HSC0 read "
        "and 93D zero-to-PV write supported. No runtime simulation or hardware verification.",
    ),
    (
        lambda ladder: _action(ladder, PeripheralIO),
        "FUN76..80: sampled 16-bit forms; other operands/status wiring inferred. Full I/O, KL "
        "and WR spans tracked; scan outputs require appropriate transistor hardware. No D/P or "
        "runtime simulation. R3999/V are exact special-word anchors, not whole-bank support.",
    ),
    (
        lambda ladder: _action(ladder, ImmediateIO),
        "IMDIO refreshes main-unit I/O only. N=1..36; X35/Y23 are table-wide maxima, not this "
        "CPU capacity. Exact CPU I/O capacity is not verified by this codec or header. No refresh "
        "runtime simulation.",
    ),
    (
        lambda ladder: _action(
            ladder, (MasterControl, MasterEnd, Differential, UpDownCounter)
        ),
        "test9: MC/MCE, DIFU/DIFD and 16-bit 07P.UDCTR encodings observed. Changed operands/"
        "conditions are inferred. DIFU/DIFD have an offline model; MC/MCE and UDCTR do not. "
        "UDCTR clear uses direct polarity; never substitute ordinary Counter CLR encoding.",
    ),
    (
        lambda ladder: _action(ladder, (RegisterOr, ForLoop, NextLoop, BreakLoop)),
        "test5-based inference: register OR supports 16-bit direct R0..R255 only; BREAK A7FE "
        "meaning is not independently established. No loop runtime verification; loops may "
        "trigger watchdog.",
    ),
    (
        lambda ladder: _action(ladder, LinearConversion),
        "LCNV: test6 observes Md=0, L=1, R3840..3844 to D1000..1004. Other modes/lengths/"
        "registers/EN conditions are inferred, not GUI/PLC verified. Conversion table contents "
        "must already exist in the destination project; this LDR does not initialize those "
        "register values. No LCNV runtime simulation.",
    ),
    (
        lambda ladder: _action(ladder, Arithmetic),
        "Arithmetic: test7 observes register Sa, positive constant Sb, EN=TRUE, U/S=FALSE. "
        "Changed operands/EN/U/S are inferred. MUL/DIV write two consecutive words. Bounded "
        "direct R/D arithmetic model; no connected status outputs or GUI/PLC verification.",
    ),
    (
        lambda ladder: _action(ladder, (ExclusiveLogic, WordConversion, ZoneCompare)),
        "test10 functions: sampled 16-bit forms only; other operands/conditions are inferred. "
        "No D/P forms or additional flag wiring; bounded direct R/D model available. WX0/WY0 "
        "cover X0..15/Y0..15; T operands denote numeric timer words.",
    ),
    (
        lambda ladder: _action(ladder, (FloatOperation, FloatCompare, FloatZoneCompare)),
        "Floating functions: binary32 constants and double-word register spans; sin/cos/tan "
        "sources are single-word integer angles in 0.01 degrees; neg/abs modify the destination "
        "pair in place. test12 observes F5; test14 observes F6 second-operand constants; F7 is "
        "inferred. Normal ERR coils supported (FLOG sampled, other ERR forms inferred). No P or "
        "indirect forms; no runtime simulation or generated-file GUI/PLC check.",
    ),
    (
        lambda ladder: any(network.comparison_chain for network in ladder.networks),
        "test11: all six comparisons support first/series positions; all 12 positions user "
        "GUI-confirmed in the exact position probe. parameter changes are inferred. No D/P, "
        "indirect, ERR wiring or runtime model. Unknown zero fields preserved; float values "
        "occupy two consecutive words.",
    ),
    (
        lambda ladder: _action(ladder, (RegisterStep, Bitwise, Compare)),
        "test8 establishes INC F496, DEC F498, CMP F46A and AND F4C6. CMP reserved 0000 is "
        "preserved; its meaning is unknown. Other operands/conditions/status connections are "
        "inferred. Bounded direct R/D register-action model available; no generated-file "
        "GUI/PLC verification.",
    ),
)


def validation_warnings(
    ladder: Ladder, *, import_verified: bool, repeated_coils: bool
) -> list[str]:
    """Build evidence warnings from declarative rules."""
    warnings = (
        []
        if import_verified
        else ["Composition has not been verified by WinProLadder import."]
    )
    warnings.extend(message for predicate, message in WARNING_RULES if predicate(ladder))
    if repeated_coils:
        warnings.append("Repeated coils: later networks may overwrite earlier network results.")
    return warnings
