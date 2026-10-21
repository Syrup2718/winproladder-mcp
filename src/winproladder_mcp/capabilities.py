"""Current client-facing capabilities, supported forms and evidence boundaries."""

from typing import Any

from . import __version__
from .design import design_guide
from .ir import Ladder, Network, block_catalog, start_stop
from .runtime import simulation_capabilities


def instruction_matrix() -> list[dict[str, Any]]:
    mapping = Network.model_json_schema()["properties"]["action"]["anyOf"][0]["discriminator"][
        "mapping"
    ]
    modeled = set(simulation_capabilities()["actions"])
    return [
        {
            "action": action,
            "schema_model": ref.rsplit("/", 1)[-1],
            "decode": "supported_forms_only",
            "generate": "decode_only"
            if action == "call"
            else "exact_test18_program_only"
            if action == "jmp"
            else "supported_forms_subject_to_schema_and_program_validation",
            "simulation": "bounded_subset" if action in modeled else "not_implemented",
            "gui_import": "requires_exact_artifact_evidence",
            "physical_plc": "not_verified",
            "form_limits": "See instruction details and schema; D/P/indirect forms are not implied",
        }
        for action, ref in sorted(mapping.items())
    ]


def capabilities() -> dict[str, Any]:
    return {
        "version": __version__,
        "profile": "Exact sampled headers: FBs-20MC, FBs-24MA (test6), FBs-24MA-test7, "
        "FBs-32MA-test11, FBs-40MA-test12, FBs-44MN-test13, FBs-60MC-test16, FBn-26MC-test17, "
        "FBe-20MA-test19, FBe-40MC-test21, FB-28MA-test22, HB1-32M-test23, "
        "FBs-40MC-test27, FBs-32MN-test29, FBs-32MC-test30; "
        "the two 24MA variants retain differing unknown metadata",
        "transport": "stdio",
        "simulation": "Boolean, direct R/D and native control scan model; not a PLC emulator",
        "simulation_model": simulation_capabilities(),
        "instruction_matrix": instruction_matrix(),
        "file_operations": [
            "inspect",
            "read",
            "create",
            "export",
            "replace",
            "insert",
            "delete",
            "component_comments",
        ],
        "ir": "Prefer condition Boolean expressions; legacy steps use left-fold semantics.",
        "address_subset": {
            "X": "0..255",
            "Y": "0..255",
            "M": "0..1911 (manual range, inferred encoding); helpers remain 0..255",
            "T": "0..255",
            "LCNV_registers": "R0..3839, input R3840..3903, R5000..8071, D0..4095 (CPU-dependent)",
            "C": "0..255",
        },
        "generation": "generate_control_ldr: 11 recipes; generate_sequence_ldr: up to 16 steps, "
        "register state, native T or FUN87 pause/resume, optional explicit pulse counting; "
        "generate_system_ldr: independent controls with "
        "internal allocation; generate_ldr: Boolean, native X edges, T/C, register, "
        "arithmetic, LCNV and loop IR.",
        "inference_notice": "Unseen combinations/ranges are inferred, not PLC-validated.",
        "component_comments": {
            "tool": "generate_component_comments",
            "trigger": "Use when the user explicitly requests 新增元件註解 or component comments",
            "artifact": "Separate .txt; not embedded into the .ldr",
            "columns": ["REF", "COMMENT", "DESCRIPTION"],
            "encoding": "CP950/Big5",
            "delimiter": "tab",
            "newline": "CRLF",
            "writes": "new files only; never overwrite",
        },
        "manual_reference_tool": "get_manual_reference",
        "rtc_snapshot_tool": "inspect_rtc_snapshot (no PLC connection)",
        "design_guide": design_guide(),
        "block_templates": [
            {
                "network": network.model_dump(),
                "payload_hex": payload.hex(" "),
                "source": source,
                "status": "observed_export; generated file needs import validation",
            }
            for network, payload, source in block_catalog()
        ],
        "analysis": [
            "analyze_ldr: descriptions and device cross-references",
            "compare_ldr: aligned record changes",
        ],
        "native_functions": {
            "test30_functions": {
                "actions": "file_register(160), memory_pack_write(161P), memory_pack_read(162), "
                "system_status(190)",
                "forms": "R/D direct operands; constant L 1..511 for RWFR, 1..128 for packs. "
                "Pack bank=1, offset=0; STAT group=0. "
                "Other documented forms need encoding evidence.",
                "labels": "LBL 1..6 ASCII alphanumeric characters; A/B1/JY1/1WX observed; "
                "longer names inferred. JMP/CALL generation restrictions remain.",
                "references": "Conservative file/STAT bank spans; "
                "external pack state not enumerated. "
                "No runtime simulation or PLC verification.",
                "profile": "FBs-32MC-test30",
            },
            "test29_functions": {
                "labels": "LBL single ASCII digit 0..9. Observed 0..6/8; 7/9 inferred. "
                "Extended to alphanumeric names by test30; does not unlock JMP/CALL generation.",
                "ascii": "test29 confirms 12-character digit and letter strings using the "
                "existing test27/28 literal packing, both R and D destinations.",
                "profile": "FBs-32MN-test29 exact sampled header",
            },
            "test28_functions": {
                "actions": "pulse_output(81), pwm(82), speed_detect(83); "
                "text_display(84) decode-only",
                "limits": "PLSO MD0 non-D, R/D Fr/PC/HO and explicit distinct UY/DY. "
                "PWM constants To/Tp milliseconds, To<=Tp, Y0..15. SPD X0..7, constant TI ms, "
                "three writable R/D words. PLSO and PWM each once. TDSP exact sample only, "
                "dynamic spans unresolved and generation rejected. LBL/JMP/CALL targets 1 and 8 "
                "recognized; JMP relocation and CALL generation remain unresolved.",
                "hardware": "Transistor main-unit outputs; actual CPU availability not verified. "
                "No pulse/speed/display execution simulation.",
            },
            "test27_functions": {
                "actions": "bit_shift(06), encode_bits(58), to_seven_segment(59), "
                "ascii_literal(60), hms_to_seconds(61), seconds_to_hms(62), "
                "ascii_to_hex(63), hex_to_ascii(64)",
                "operands": "source/destination; ENCOD source_index=Ns 0..15, count=NL 2..256; "
                "7SG count=N 0..3 (N+1 digits). HEX/ASCII count=1..511. "
                "ASC: 1..12 ASCII letters/digits/spaces; test27/28 packed literal encoding",
                "controls_status": "ENCOD enable/high_priority, zero/error; 7SG enable/error; "
                "SEC enable/zero; HMS enable/zero/overflow; HEX enable/error; "
                "ASCII and ASC enable only. BSHF enable/input_bit/left/clear and output=OTB",
                "footprints": "ENCOD ceil((Ns+NL)/16) source words, clipped at bank end, "
                "one result word. 7SG N+1 bytes, preserves unused high byte. SEC reads "
                "seconds/minutes/hours (3 words), writes signed seconds (2 words); HMS reverse. "
                "HEX N source words -> ceil(N/4) words preserving unused nibbles. "
                "ASCII ceil(N/4) source words -> N words preserving each high byte. "
                "BSHF CLR overrides other controls, including EN",
                "limits": "Sampled non-P direct forms; constant counts, ASC letters/digits/spaces. "
                "Other operand forms, strings, D/P/indirect encodings unresolved. "
                "Multiword conversions R/D only; BSHF D follows basic-manual max D3071. "
                "No runtime simulation; new FBs-40MC-test27 header",
            },
            "test26_functions": {
                "actions": "byte_distribute(50), shift_left(51), shift_right(52), rotate_left(53), "
                "rotate_right(54), binary_to_gray(55), gray_to_binary(56), decode_bits(57)",
                "operands": "source, destination; SHFL/ROTR use count=1..16, SHFR/ROTL use "
                "length_register=N. BDIST uses length_register=N (1..256 bytes at runtime). "
                "DECOD source_index=Ns 0..15, bit_length=NL 1..8",
                "controls_status": "All enable=EN; SHFL/SHFR input_bit=INB. "
                "51..54 output=OTB/error=ERR; DECOD error; no other status outputs",
                "footprints": "BDIST max 128 source and 256 destination words, high byte first, "
                "zero-extended outputs. Shift/rotate read-modify-write one word. "
                "DECOD reads across B15 into next source word, clips at operand bank end, "
                "writes max(1,2^NL/16) words; not NL words",
                "limits": "Observed 16-bit non-P forms only. Alternative N forms, dynamic "
                "DECOD Ns/NL, constants as sources, additional word banks and D/P/indirect "
                "encodings remain unresolved. Multiword destinations R/D only. "
                "No native runtime simulation. Dynamic BDIST spans conservatively use max N",
            },
            "test25_functions": {
                "actions": "bit_move(42), nibble_move(43), byte_move(44), word_exchange(45), "
                "byte_swap(46), nibble_unite(47), nibble_distribute(48), byte_unite(49)",
                "operands": "source=S/Da, destination=D/Db, enable=EN. "
                "42..44 source_index=Ns and destination_index=Nd (0..15/3/1 respectively); "
                "47/48 count=N constant 1..4; 49 length_register=N (runtime 1..256 bytes)",
                "status": "error on 42/43/44/47/48; no status on 45/46/49",
                "footprints": "42..44 preserve other destination bits; XCHG reads/writes both "
                "operands. UNIT reads N words, writes 1 and clears unused nibbles; DIST reads "
                "1 word, writes N zero-extended nibbles. BUNIT conservatively reads 256 source "
                "words, length register and 128 destination words; writes up to 128 words. "
                "Odd-N unused destination byte unspecified in supplied manual",
                "limits": "Sampled 16-bit non-P direct word forms. Multiword spans R/D only; "
                "single words use existing R/D/T/WX0/WY0 codec (destinations R/D/WY0). "
                "BUNIT HR/ROR/DR only. Dynamic Ns/Nd, constant BUNIT N, dynamic UNIT/DIST N, "
                "additional banks, D/P and indirect encodings unresolved; no runtime simulation",
            },
            "test24_functions": {
                "actions": "move_word(08), move_inverse(09), toggle_bit(10), table_sort(113), "
                "zone_write(114), matrix_bit_shift(128), matrix_bit_rotate(129), "
                "matrix_bit_count(130)",
                "length": "SORT 2..127 words; Z-WR N 1..511 words (literal encoded N); "
                "matrix 2..256 words (16*L bits). MBCNT writes only one result word",
                "controls": "TOGG trigger=TGU (rising edge); SORT enable/ascending=A/D; "
                "Z-WR and MBCNT enable/ones=1/0; MBSHF enable/input_bit/left=L/R; "
                "MBROT enable/left. MOV/MOV/ enable",
                "status": "SORT/Z-WR error; MBSHF/MBROT output=OTB; MBCNT zero=D=0",
                "limits": "Sampled 16-bit non-P direct operands, constant length; "
                "MOV word-source only (no constants), R/D and existing T/WX0/WY0 plus exact WY8. "
                "MOV uses basic manual D0..3071; MOV/ IR R3840..3847. Other word banks, "
                "dynamic lengths, D/P and indirect encoding remain unresolved. "
                "TOGG Y0..255/M0..999; other legal bit families not yet encoded. "
                "WY8 writes Y8..Y23, all must be in IO contract. Direct R/D MOV and TOGG "
                "are modeled; other forms are not",
            },
            "test23_functions": {
                "actions": "matrix_and(120), matrix_or(121), matrix_xor(122), matrix_xnr(123), "
                "matrix_invert(124), matrix_compare(125), matrix_bit_read(126), "
                "matrix_bit_write(127)",
                "operands": "source=Ma/Ms, source_b=Mb, destination=Md, pointer=Pr. "
                "MINV uses length_register (sample R1); other sampled forms use constant length",
                "length": "L=2..256 words, bit pointer=0..16*L-1. MINV dynamic L tracks "
                "all 256 possible words for static resource safety, not the runtime value",
                "controls": "MCMP enable/from_head/different; MBRD enable/increment/clear; "
                "MBWR enable/input_bit/increment/clear (four separate inputs)",
                "status": "MCMP found/done/error; MBRD output/done/error; MBWR done/error",
                "limits": "Non-P sampled forms and direct R/D banks. MINV constant L and "
                "other functions register L encodings unresolved; no native runtime simulation. "
                "Same source/destination permitted; dynamic spans may conservatively reject "
                "near-bank endpoints even if a particular runtime L would fit",
            },
            "test22_functions": {
                "actions": "register_table_search(105), table_compare(106), table_fill(107), "
                "table_shift(108), table_rotate(109), queue(110), stack(111), block_compare(112)",
                "form": "16-bit non-P, direct R/D operands, constant length. "
                "105/107 currently constant value Rs only (-32768..32767); signed variants "
                "inferred",
                "length": "105..111: 2..256; 112: 1..256; stored L-1",
                "inputs": "enable; 105/106 from_head=FHD, different=D/S; "
                "108/109 left=L/R; 110/111 push=I/O",
                "status": "105/106 found/done/error; 110/111 empty_flag/full/error; 112 error",
                "spans": "110/111 pointer range 0..L, QU/ST contains exactly L words. "
                "112 source is 2*L lower/upper words, bit_destination writes L Y/M bits "
                "(Y0..255/M0..999); reads M1975. Full I/O contract required",
                "limits": "No D/P, indirect, dynamic L, other word-bank encodings or native "
                "execution simulation. Manual 7-100..109 allows more than this sampled codec",
            },
            "test21_functions": {
                "actions": "table_to_reg(101), table_to_table(102), block_table_move(103), "
                "table_swap(104)",
                "operands": "source/destination direct R/D, constant length; pointer on "
                "101/102 only. "
                "101/102 L=2..2048; 103/104 L=2..256, stored as L-1",
                "pins": "101/102 enable/increment/clear, done/error; 103/104 enable only. "
                "CLR is ordinary Boolean polarity, acts independently of EN per manual",
                "spans": "Full source/destination tables tracked; 101 writes one word; "
                "104 reads and writes both tables, both must be writable",
                "limits": "16-bit non-P sampled forms; D/P, register length, indirect addressing "
                "and other word banks have no encoding here. No execution simulation or "
                "GUI/PLC validation",
                "manual": "7-96..99; 7-96 printed table places K=2..2048 on Pr instead of L, "
                "constant L supported by GUI sample and manual example",
            },
            "test20_functions": {
                "release_status": "included in 1.0.0 source; package not built",
                "actions": "ascwr(94P MD=1), ramp(95), ramp2(98), reg_to_table(100)",
                "ascwr": "enable/pause/abort; source S, work Pt8; active/error/done. "
                "MD=1 is reserved in manual 7-87: encoding only, ASCII source extent "
                "and runtime semantics unresolved; conservative Pt8 collision checks",
                "ramp": "enable/pause/up; Tn requires configured 10 ms time base and "
                "exclusive use; preset/lower/upper register operands; destination plus "
                "exclusive destination+1 work word. M1974 changes PV meaning. "
                "error/at_lower/at_upper status pins",
                "ramp2": "maximum/rise_ms/fall_ms/target/destination/work register operands; "
                "HR/OR/ROR/D0..3999, WR4 exclusive; accelerating/decelerating pins. "
                "Register contents Om/Rt=0..65535, Ta/Td=0..65000 ms; no runtime value check",
                "reg_to_table": "16-bit register source/destination/pointer, constant "
                "length=2..2048 encoded as length-1; enable/increment/clear, done/error. "
                "CLR can reset pointer independently of EN per manual; ordinary Boolean CLR "
                "polarity; test21 corrects the earlier inversion assumption",
                "limits": "No constant data operands, arbitrary word banks, ASCWR MD=0, "
                "unsampled D/P forms or execution simulation. Source test20 overlaps "
                "RAMP2 WR R15..R18 with table R10..R17: full generation rejected",
            },
            "test19_functions": {
                "release_status": "included in 1.0.0 source; package not built",
                "actions": "tpctl(86), accumulative_timer(87/88/89); call(67) decode-only",
                "timer": "timing=TIM, enable=EN; unit_ms=10/100/1000; PV direct R/D count; "
                "CV T0..255 or direct R/D including IR (instruction-specific manual 7-81). "
                "TIM=0 retains CV while EN=1; EN=0 clears. done=TUP, not_done=NUP",
                "tpctl": "EN, H/C, Yn, Sn=0..31, Zn=1..32, Sn+Zn<=32. "
                "Yn spans Zn outputs; SV/OS/PR/IR/DR/OR each Zn words; WR9 exclusive. "
                "error=ERR, alarm=ALM. Temperature source depends on PLC configuration",
                "limits": "No constant PV, other timer word banks, TPCTL Md encoding, "
                "D/P variants or CALL relocation. These are codec limits. Direct R/D timer scan "
                "model and native sequence pause are supported; TPCTL is not simulated. "
                "test19 N002/N005 are allowed "
                "when allow_function_m_to_m=true; CALL remains generation-blocked "
                "because its target metadata is unresolved and LBL/RTS are absent",
                "manual_editions": "Advanced 7-79 allows 32 zones/D4095; older CH20 20-44 "
                "shows 24 zones/D3071 and no Md, like sampled layout. H/C=1 heat, 0 cool "
                "per 20-45. CPU/edition compatibility remains unverified",
            },
            "test18_functions": {
                "release_status": "included in 1.0.0 source; package not built",
                "actions": "adcnv(32), mlc(34), bitrd(40), bitwr(41), lbl(65), jmp(66)",
                "analog": "ADCNV sampled Pl=0, constant N=1..64; selector is F/T "
                "(0=12-bit,1=14-bit). MLC constant Sl=1..64, register Tl=2..255 at runtime; "
                "selector is X/Y (0=Tx to Ty,1=Ty to Tx); D bank ends at D3999",
                "spans": "ADCNV and MLC S/D use count words; MLC Tx/Ty each track 255 "
                "possible words because Tl is runtime. Includes WR collision checks",
                "bits": "16-bit direct R/D word with constant bit=0..15. BITWR input_bit is INB; "
                "BITRD output is OTB, disabled OTB depends on M1919. Normal status coils only",
                "flow": "Only exact label 1 and JMP 1 record anchors. JMP target metadata "
                "unresolved: generation permits only byte-exact complete test18 program; "
                "no relocation, edits, different target, EN variants or profile changes",
                "unsupported": "ADCNV Pl=1, register counts, MLC constant Tl, D/P/indirect "
                "forms, general labels/jumps and runtime simulation are not encoded. "
                "These are codec limits, not blanket PLC restrictions",
            },
            "test17_functions": {
                "release_status": "included in 1.0.0 source; package not built",
                "actions": "mean(25), sqrt(26), neg(27), abs(28), ext(29), crc16(31); "
                "DIV48 single_input encoding and SUM additional export anchors",
                "forms": "16-bit direct R/D; MEAN register N (runtime 2..256), "
                "SQRT register source; NEG/ABS in-place; EXT 1-to-2 words",
                "dynamic_count": "MEAN checks all 256 possible source words, "
                "including WR conflicts",
                "crc16": "Only sampled MD=1, constant N=1..256. Supplied manual marks MD=1 "
                "reserved: encoding only, reference analysis marked incomplete; "
                "conservative N-source/2-destination spans use MD=0 rules",
                "div48": "single_input preserves F474 and has no U/S pin; "
                "signedness not inferred; old F46C two_inputs form preserved",
                "unsupported": "D/P/indirect variants, MEAN constant N, SQRT constants, "
                "CRC16 MD=0 or register N, runtime simulation; no GUI/PLC verification",
            },
            "test16_functions": {
                "release_status": "included in 1.0.0 source; package not built",
                "actions": "div48 (23), sum (24), pid (30), wdt (90), rswdt (91), "
                "hsctr (92), hsctw (93D)",
                "spans": "DIV48 Sa/Sb/D each 3 words; SUM N=1..511 words; "
                "PID SR8/OR1/PR7/WR5, exclusive WR",
                "time_units": "WDT setting=50,60,...120 in 10 ms units; "
                "PID interval=1..3000 in 10 ms units; existing Timer contract unchanged",
                "pid_inputs": "enable means A/M; bumpless means BUM; direction means D/R; "
                "each is an independent Boolean expression; ERR/HAL/LAL normal coils",
                "counter_scope": "HSCTR only HSC0; HSCTW only sampled 93D S=0/CN=HSC0/D=PV. "
                "Counter selector layout and other source forms are not inferred "
                "from zero operands",
                "unsupported": "P forms, SUM D form, indirect operands, PID register Ts, "
                "runtime simulation. No generated-file GUI or PLC verification",
            },
            "test15_functions": {
                "release_status": "included in 1.0.0 source; package not built",
                "actions": "tkey (76), hkey (77), dsw (78), 7sgdl (79), muxi (80)",
                "forms": "Sampled 16-bit forms; other parameters and status coils inferred. "
                "No D/P forms",
                "spans": "TKEY X10/KL10; HKEY X4/Y4/KL16; DSW X4/Y4/WR2; "
                "7SGDL Y8, mode0..3; MUXI X8/YN, N2..8, destination ceil(N/2) words",
                "work": "HKEY/7SGDL/MUXI WR1; DSW WR2; exclusive across networks",
                "special_words": "R3999=023E, V=0388 exact anchors scoped to peripheral operands",
                "policy": "Implicit KL and status coils participate in M-to-M guard "
                "and helper reservation; "
                "all physical spans require explicit io_contract",
                "unsupported": "D/P, indirect addressing, arbitrary special words, "
                "runtime simulation. "
                "No generated-file GUI or PLC verification; transistor output hardware must match.",
            },
            "test14_functions": {
                "release_status": "included in 1.0.0 source; package not built",
                "float_operations": "log (base 10), pow, asin, acos, atan (FUN216..220)",
                "power_order": "pow: sa=Sy exponent, sb=Sx base; result=sb**sa",
                "inverse_angles": "binary32 source and result in radians; asin/acos input -1..1",
                "D_bank": "FUN216..220 D0..3999; two-word start at most D3998",
                "error_coils": "float_operation.error: normal Y/M coils on ERR (6FFC); "
                "FLOG observed, other eligible float operations inferred; M-to-M policy applies",
                "constant_flags": "F6 second-operand constant observed in FPOW; F7 still inferred",
                "imdio": "action imdio: start X/Y, count 1..36, enable; all points in io_contract. "
                "X0,N10 observed; other X/Y spans inferred. Main-unit I/O only; table maxima "
                "X35/Y23 do not confirm capacity of the selected CPU",
                "unsupported": "No P/indirect, runtime simulation, GUI or PLC verification",
            },
            "test13_functions": {
                "release_status": "included in 1.0.0 source; package not built",
                "operations": "float_operation sin/cos/tan/neg/abs/ln/exp (FUN209..215)",
                "angles": "Sa is one signed 16-bit word or integral constant -18000..18000; "
                "unit=0.01 degrees, not radians or binary32. D is two words.",
                "in_place": "neg/abs require only destination; read and write its two words",
                "ln_exp": "Float source and result; manual D0..3999 bank, max pair start D3998; "
                "ln literal must be positive",
                "header": "Exact FBs-44MN-test13 header including 4040 metadata",
                "evidence": "Seven exact test13 payloads observed; other operands, negative "
                "angle constants and float constant ln/exp forms inferred",
                "unsupported": "P, indirect and runtime simulation; "
                "no generated-file GUI/PLC check. "
                "Normal ERR wiring for eligible operations is available via test14",
            },
            "test12_functions": {
                "release_status": "included in 1.0.0 source; package not built",
                "float_arithmetic": "FUN205 FDIV and FUN208 FSQR: float_operation div/sqrt. "
                "Arithmetic accepts register or finite binary32 immediate sources; "
                "I->F/F->I still require register source",
                "float_compare": "FUN206 FCMP: float_compare sa/sb, "
                "equal/greater/less normal coils",
                "float_zone_compare": "FUN207 FZCP: float_zone_compare register source, "
                "upper/lower register or immediate, within/above/below normal coils; no ERR wiring",
                "banks": "Float operands: R0..3839, R5000..8071, D0..4095; "
                "full two-word spans checked. "
                "R8000 and D4094 sampled; other newly available offsets inferred",
                "constants": "IEEE-754 binary32, big-endian; F5 first-source constant observed. "
                "F6 second-source marker observed in test14 FPOW; F7 both-source marker inferred. "
                "Neither implies GUI verification of generated variants",
                "outputs": "M0..1911 including sampled M999; M-to-M policy covers compare outputs",
                "header": "Exact FBs-40MA-test12 header",
                "verification": "Sample bytes observed; new outputs not GUI/PLC verified. "
                "No execution simulation; reject NaN/Inf, overflow, bank crossings, unknown forms",
            },
            "test11_functions": {
                "position_probe_gui_confirmation": {
                    "artifact": "FUN170_175_all_positions_probe.ldr",
                    "sha256": "252622c9cc544eeac82d525200a40c084b4aceb06f9978803ccfc7513db3781a",
                    "evidence": "User reported all positions correct on 2026-10-07",
                    "scope": "Exact six-rung R600/R700 probe; "
                    "first and series forms of six relations",
                    "reexport_received": False,
                    "plc_verified": False,
                },
                "comparison_contacts": "FUN170..175 via network.comparison_chain. "
                "All six relations at first and subsequent series positions; "
                "all 12 positions user GUI-confirmed in the exact R600/R700 probe; "
                "other operand combinations remain inferred; "
                "coil outputs including SET/RESET. No OR, mixed Boolean contacts, "
                "D form or runtime model",
                "comparison_operands": "Direct existing word banks plus exact WS0, WM0, C2, R5111. "
                "Only le permits constant Sb=0..32767. WM0 expands to M0..15 for policy. "
                "Other WS/WM/C addresses and constant forms remain unsupported; "
                "high-R bank is supported",
                "float": "FUN200 I->F, 201 F->I, 202 FADD, 203 FSUB, 204 FMUL; "
                "float_operation action with operation i_to_f/f_to_i/add/sub/mul, "
                "sa, sb, destination, EN. "
                "Conversions forbid sb; arithmetic requires it",
                "float_width": "I->F reads 1 word and writes 2; F->I reads 2 and writes 1; "
                "FADD/FSUB/FMUL read 2 per source and write 2. "
                "test12 extends float banks and immediate operands; no D/P modifiers, "
                "runtime model; ERR for eligible arithmetic operations is supported via test14",
                "evidence": "Exact test11 bytes observed; operand/enable changes inferred. "
                "F47F extension subcodes and unknown zero fields preserved. "
                "FBs-32MA-test11 exact header, not a generic conversion between CPUs",
            },
            "test10_functions": {
                "xor_xnr": "FUN35 XOR F4CA / FUN36 XNR F4CC; exclusive_logic action, "
                "sa/sb word sources and writable destination; no D=0 output wiring",
                "zncmp": "FUN37 F7DA; zone_compare source R/D, signed constant upper/lower; "
                "within/above/below normal coils. No register bounds or ERR wiring",
                "to_bcd": "FUN20 F5A6; word_conversion operation to_bcd; "
                "constant source 0..9999 only, writable word destination",
                "to_bin": "FUN21 F4A4; word_conversion operation to_bin; word source/destination",
                "words": "R/D banks; T0..255 read-only numeric values; exact WX0 and WY0 only. "
                "WX0/WY0 expand to X0..15/Y0..15 for I/O contract and overlap checks",
                "limitations": "Only sampled 16-bit opcode forms; parameter changes inferred. "
                "No D/P variants, indirect addressing or GUI verification; bounded direct "
                "R/D simulation available",
            },
            "test8_functions": {
                "increment": "FUN15 F496; action type increment, direct R/D destination, EN",
                "decrement": "FUN16 F498; action type decrement, direct R/D destination, EN",
                "compare": "FUN17 F46A; register Sa/Sb, EN/U/S, normal equal/greater/less coils; "
                "preserve unknown 0000 field; bounded direct R/D runtime model available",
                "bitwise": "FUN18 AND F4C6 / FUN19 OR F4C8; direct R/D Sa, Sb, destination",
                "coil_modes": "normal (optionally inverted), set, reset; test8 establishes Y forms",
            },
            "test9_functions": {
                "mc": "FC88 + number; MCE FC89 + number; unique 0..127 inferred from manual. "
                "Generation requires matched non-overlapping regions; no MC runtime simulation",
                "difu_difd": "DIFU F8F6 / DIFD FCF7; trigger expression, Y/M bit destination; "
                "Native function M results are allowed by allow_function_m_to_m; MC "
                "execution is not modeled",
                "udctr": "07P.UDCTR F100; pulse/up/clear Boolean inputs, constant preset 0..32767, "
                "writable R/D cv; no 32-bit, register preset, CUP wiring or runtime simulation",
                "branch_encoding": "test9_or preserves E422 two branches of two contacts; "
                "no helpers",
                "sample_status": "test9 decodes but MC2 lacks MCE2 and M1 implicitly drives "
                "M100/M101: full generation rejected under this workspace policy",
            },
            "arithmetic": {
                "fun": [11, 12, 13, 14],
                "action_type": "arithmetic",
                "operations": ["add", "sub", "mul", "div"],
                "source": "test7.ldr + screenshot",
                "observed": "16-bit, register Sa, positive immediate Sb, EN=TRUE, U/S=FALSE",
                "inferred": "Direct R/D operands; Sb=0..32767; Boolean EN/unsigned_when",
                "unsigned_when": "FALSE=signed (sampled); TRUE=unsigned (inferred wiring)",
                "destination_words": {"add": 1, "sub": 1, "mul": 2, "div": 2},
                "unsupported": [
                    "register Sb",
                    "constant Sa",
                    "negative Sb",
                    "32-bit D form",
                    "P form",
                    "indirect operands",
                    "connected status flags",
                ],
                "import_verified": False,
            },
            "LCNV": {
                "fun": 33,
                "action_type": "lcnv",
                "source": "test6.ldr",
                "observed": "Md=0, L=1, sources R3840..3844, tables R2001+5*n, D1000..1004",
                "inferred": "Md=0..3, L=1..64, direct R/D banks, Boolean EN",
                "unsupported": [
                    "33P",
                    "indirect addressing",
                    "register-valued L",
                    "table initialization",
                    "runtime simulation",
                ],
                "import_verified": False,
            },
            "other_FUN_numbers": "Cannot derive opcodes by incrementing FUN numbers",
        },
        "native_edge_contacts": {
            "schema": "edge: {kind: rising|falling, input: X0..X255}, plus coils",
            "observed": "test4 N005 rising X0 -> Y1; N006 falling X1 -> Y3; test7 N000 rising",
            "inferred": "Other X addresses and Y/M coils; isolated edge network only",
            "simulation": "One-scan pulse; previous input starts from initial or FALSE; "
            "software model only, PLC startup behavior not verified",
            "helper_memory": "None",
        },
        "further_inference": {
            "usable_compositions": "Increment/decrement via ADD/SUB with Sb=1; "
            "constant offset, integer scaling, quotient and remainder via FUN11..14. "
            "Arithmetic status/overflow semantics remain those of FUN11..14, not FUN15/16.",
            "candidates_not_enabled": [
                "Register Sb might change F6 to F4; needs same-operation exported comparison",
                "MOV and D/P modifiers still need independent exported evidence",
            ],
            "corrected_hypothesis": "test8 disproves FUN15=F46A/FUN16=F46C; actual F496/F498. "
            "F46A is CMP. Do not increment FUN numbers to guess opcode families.",
            "policy": "Unconfirmed native opcodes remain opaque; never emitted as supported",
        },
        "opaque_only": [
            "compound edge rungs and non-X edge operands",
            "unknown instructions",
        ],
        "verified_template": "start_stop: X1=1 stops; user reported import success",
        "layout_optimization": {
            "automatic": True,
            "rules": [
                "identities",
                "deduplication",
                "absorption",
                "common-factor extraction",
                "CH01 section 1.7 compound-first ordering",
            ],
            "scope": "Pure Boolean conditions only; network/output order unchanged",
            "preview_tool": "validate_ladder",
            "user_confirmed_import_sha256": (
                "a4694aa8db73737ada925742ebc6ba164aee52e56137bd5ae201017c203b3b94"
            ),
            "verification_scope": "Exact connected traffic-light baseline only; "
            "new optimized files still need GUI import verification",
        },
        "no_plc_connection": True,
        "writes": "new .ldr and requested component-comment .txt files only; never overwrite",
        "start_stop_example": start_stop().model_dump(),
        "schema": Ladder.model_json_schema(),
    }


def capability_summary() -> dict[str, Any]:
    """Return the stable top-level capability summary without large schemas/examples."""
    full = capabilities()
    keys = {
        "version",
        "profile",
        "transport",
        "simulation",
        "simulation_model",
        "address_subset",
        "generation",
        "component_comments",
        "inference_notice",
        "manual_reference_tool",
        "rtc_snapshot_tool",
        "no_plc_connection",
        "writes",
    }
    native = full["native_functions"]
    return {
        **{key: value for key, value in full.items() if key in keys},
        "instruction_family_count": len(native),
        "instruction_discovery": {
            "list_tool": "list_instruction_families",
            "detail_tool": "get_instruction_capabilities",
        },
    }


def instruction_families() -> list[dict[str, Any]]:
    """List small instruction-family summaries for tool discovery."""
    native = capabilities()["native_functions"]
    return [
        {
            "family": family,
            "actions": details.get("actions", "See family details")
            if isinstance(details, dict)
            else details,
            "profile": details.get("profile") if isinstance(details, dict) else None,
        }
        for family, details in native.items()
    ]


def instruction_capabilities(family: str) -> dict[str, Any]:
    """Return one instruction family instead of the complete capability document."""
    native = capabilities()["native_functions"]
    if family not in native:
        available = ", ".join(native)
        raise ValueError(f"Unknown instruction family {family!r}; available: {available}")
    return {"family": family, "details": native[family]}
