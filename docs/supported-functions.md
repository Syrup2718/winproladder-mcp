# Supported native instructions / 原生指令支援表

[繁體中文首頁](../README.md) · [English home](../README.en.md) · [中文功能總覽](../FEATURES.md) · [English features](../FEATURES.en.md)

本表是 GitHub 訪客可直接閱讀的精簡清單。`✅` 只表示目前 schema 與驗證允許的形式，不代表該 FUNC 的所有 D/P、間接定址、CPU 或 operand 變體。

This is a compact public list. `✅` means only the forms accepted by the current schema and validation; it does not imply every D/P, indirect, CPU-specific, or operand variant.

| FUNC | Instruction / 指令 | Decode / 解析 | Generate / 產生 | Offline model / 離線模型 | Main boundary / 主要邊界 |
| --- | --- | :---: | :---: | :---: | --- |
| — | MC / MCE | ✅ | ✅ | — | Matched, non-overlapping regions / 區域必須配對且不可重疊 |
| — | DIFU / DIFD | ✅ | ✅ | ✅ | Y/M destinations / Y、M 目的元件 |
| — | FOR / BREAK / NEXT | ✅ | ✅ | — | Matched loop structure / 迴圈結構必須配對 |
| 07P | UDCTR | ✅ | ✅ | — | 16-bit sampled form / 已取樣的 16 位元形式 |
| 06 | Bit shift / 位元移位 | ✅ | ✅ | — | Direct sampled form / 直接定址取樣形式 |
| 08–10 | MOV, MOV/, TOGG | ✅ | ✅ | ✅ | Direct supported operands; TOGG Y/M / 直接定址；TOGG 使用 Y/M |
| 11–14 | ADD, SUB, MUL, DIV | ✅ | ✅ | ✅ | 16-bit direct R/D subset / 16 位元直接 R/D 子集 |
| 15–16 | INC, DEC | ✅ | ✅ | ✅ | Direct R/D destination / 直接 R/D 目的元件 |
| 17 | CMP | ✅ | ✅ | ✅ | Direct register comparison / 直接暫存器比較 |
| 18–19 | AND, OR | ✅ | ✅ | ✅ | Direct R/D operands / 直接 R/D 運算元 |
| 20–21 | BCD, BIN | ✅ | ✅ | ✅ | Sampled 16-bit forms / 已取樣的 16 位元形式 |
| 23–24 | DIV48, SUM | ✅ | ✅ | — | Fixed multiword and length rules / 固定多字組與長度規則 |
| 25–29 | MEAN, SQRT, NEG, ABS, EXT | ✅ | ✅ | — | Direct R/D forms / 直接 R/D 形式 |
| 30 | PID | ✅ | ✅ | — | Sampled register layout and 10 ms units / 已取樣暫存器配置與 10 ms 單位 |
| 31 | CRC16 | ✅ | ⚠️ | — | Sampled MD=1 encoding; manual marks it reserved / 僅 MD=1 取樣編碼，手冊標為保留 |
| 32–34 | ADCNV, LCNV, MLC | ✅ | ✅ | — | Sampled direct forms; dynamic spans are conservative / 已取樣直接形式，動態範圍採保守檢查 |
| 35–37 | XOR, XNR, ZNCMP | ✅ | ✅ | ✅ | Sampled 16-bit forms / 已取樣的 16 位元形式 |
| 40–49 | BITRD, BITWR, bit/nibble/byte move and pack / 位元、半位元組與 byte 搬移組合 | ✅ | ✅ | — | Direct supported word banks / 支援的直接 word bank |
| 50–59 | BDIST, shifts, rotates, Gray/BIN, DECOD, ENCOD, 7SG | ✅ | ✅ | — | Sampled non-P forms and bounded lengths / 已取樣非 P 形式與有限長度 |
| 60–65 | ASC, SEC, HMS, HEX, ASCII, LBL | ✅ | ✅ | — | ASCII is limited; labels are 1–6 alphanumeric characters / ASCII 有限；標籤為 1–6 位英數字 |
| 66 | JMP | ✅ | ⚠️ | — | Exact complete sampled program only / 僅限完整且逐 byte 相同的取樣程式 |
| 67 | CALL | ✅ | — | — | Decode-only; target relocation unresolved / 僅解析，目標重定位未解決 |
| 74 | IMDIO | ✅ | ✅ | — | Main-unit I/O with explicit contract / 主機 I/O 且必須明確宣告契約 |
| 76–80 | TKEY, HKEY, DSW, 7SGDL, MUXI | ✅ | ✅ | — | Explicit physical I/O and exclusive work areas / 明確實體 I/O 與獨占工作區 |
| 81–83 | PLSO, PWM, SPD | ✅ | ✅ | — | Sampled modes and hardware-dependent outputs / 已取樣模式，輸出受硬體限制 |
| 84 | TDSP | ✅ | — | — | Exact sample is decode-only / 僅解析精確樣本 |
| 86 | TPCTL | ✅ | ✅ | — | Temperature source depends on PLC configuration / 溫度來源取決於 PLC 設定 |
| 87–89 | Accumulative timers / 積算型計時器 | ✅ | ✅ | ✅ | 10, 100, or 1000 ms time base / 10、100 或 1000 ms 時基 |
| 90–93 | WDT, RSWDT, HSCTR, HSCTW | ✅ | ✅ | — | Sampled watchdog and HSC0 forms / 已取樣 watchdog 與 HSC0 形式 |
| 94P | ASCWR | ✅ | ⚠️ | — | MD=1 encoding only; runtime semantics unresolved / 僅 MD=1 編碼，執行語意未解決 |
| 95, 98 | RAMP, RAMP2 | ✅ | ✅ | — | Exclusive timer/work-register resources / 計時器與工作暫存器須獨占 |
| 100–104 | Register/table transfers and swap / 暫存器與表格搬移交換 | ✅ | ✅ | — | Direct R/D and supported constant lengths / 直接 R/D 與支援的固定長度 |
| 105–114 | Search, compare, fill, shift, rotate, queue, stack, SORT, Z-WR | ✅ | ✅ | — | Sampled 16-bit non-P forms / 已取樣的 16 位元非 P 形式 |
| 120–130 | Matrix logic, compare, bit read/write/shift/rotate/count / 矩陣邏輯、比較與位元操作 | ✅ | ✅ | — | Direct R/D matrices and bounded lengths / 直接 R/D 矩陣與有限長度 |
| 160, 161P, 162 | File register and memory pack read/write / 檔案暫存器與記憶體封包讀寫 | ✅ | ✅ | — | Sampled banks, offsets, and lengths / 已取樣 bank、offset 與長度 |
| 170–175 | Comparison contacts / 比較接點 | ✅ | ✅ | — | Confirmed first and series positions; no OR form / 已確認首段與串聯位置，不支援 OR 形式 |
| 190 | System status / 系統狀態 | ✅ | ✅ | — | Hardware-dependent extent / 範圍取決於硬體 |
| 200–208 | I→F, F→I, FADD, FSUB, FMUL, FDIV, FCMP, FZCP, FSQR | ✅ | ✅ | — | Supported float banks and finite binary32 constants / 支援的浮點 bank 與有限 binary32 常數 |
| 209–220 | FSIN, FCOS, FTAN, FNEG, FABS, FLN, FEXP, FLOG, FPOW, FASIN, FACOS, FATAN | ✅ | ✅ | — | Sampled direct forms; angle and error rules vary / 已取樣直接形式；角度與錯誤規則依指令而異 |

## Status notes / 狀態說明

- `✅`: supported within the documented subset / 在文件所述子集內支援。
- `⚠️`: generation is deliberately restricted or encoding-only / 產生受到刻意限制或僅保證編碼。
- `—`: not implemented for that stage / 該階段尚未實作。
- Offline model means a bounded deterministic scan model, not PLC emulation / 離線模型是有限且確定性的掃描模型，不是 PLC 模擬器。
- GUI import and physical PLC execution remain user verification steps / GUI 匯入與實體 PLC 執行仍由使用者驗證。

For exact operands, device ranges, status pins, work areas, and evidence, call `list_instruction_families` and then `get_instruction_capabilities` for the selected family.

若要查詢精確運算元、元件範圍、狀態腳位、工作區與證據，請先呼叫 `list_instruction_families`，再對指定家族呼叫 `get_instruction_capabilities`。
