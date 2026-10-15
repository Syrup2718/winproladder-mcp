# test8／test9 原生 function 編碼

[文件索引](README.md) · [功能清單](../FEATURES.md)

這兩份資料是**指令格式樣本**。讀取和研究不要求使用者先把範例改成完整控制程式。MCP v0.8.0 已將以下已觀察到的指令接入 `read_ldr`、`generate_ldr`、`modify_network`、`analyze_ldr`；範例參數以外的組合仍標示為外推。

## DIFU／DIFD 的具體寫法

test9 N005、N006：

```text
4F E8  F8 F6  08 74   → FUN04 DIFU，TG=TRUE，D=M100
4F E8  FC F7  08 75   → FUN05 DIFD，TG=TRUE，D=M101
  TG   opcode   D
```

M100 位址是 `0x810+100=0x874`；M101 是 `0x875`。目的位址在 function 參數裡，所以不是普通 OUT M100 線圈的 `C874`。DIFU 和 DIFD 的兩個 opcode bytes 都有差異，不能只把尾碼 F6 改成 F7。其寫法也不同於原生 TU／TD 接點的 `E000` 前綴。

```json
{
  "profile": "FBs-24MA-test7",
  "networks": [
    {"action": {"type": "difu", "trigger": "TRUE", "destination": "M100"}},
    {"action": {"type": "difd", "trigger": "TRUE", "destination": "M101"}}
  ]
}
```

`get_design_guide` 的 `native_difu_difd_sample` 已提供此範例。M100／M101 是使用者樣本中的結果位址，不會另外分配 M 當上一掃描記憶。支援的外推範圍是布林 trigger 與 Y/M0～255 目的位址；仍受 I/O 契約和專案禁止 M→M 政策限制。

交付的 `test9_DIFU_DIFD_blocks.ldr` 是抽出的兩個 function 編碼測試網路；payload 分別與原 N005、N006 相同，沒有包含原檔的 MC 區域，也不是整份 test9 的等價控制程式。

## test8 修正了哪個猜測

| 指令 | 先前猜測 | 實際匯出 |
| --- | --- | --- |
| FUN15 加一 | F46A | **F496**，後接 D 暫存器 |
| FUN16 減一 | F46C | **F498**，後接 D 暫存器 |
| FUN17 CMP | 尚未確認 | **F46A** |
| FUN18 AND | 尚未確認 | **F4C6** |

先前「只延續 FUN11～14 的 opcode 步距」推理不成立。單一 EN 和 D 暫存器的參數布局則吻合。舊猜測 A 的說明已標示推翻，產檔腳本也拒絕再輸出；既有歷史檔案保留，不會被改成貌似成功的新檔。

新增 action：`increment`／`decrement` 使用 `destination`、`enable`；`bitwise` 使用 `operation=and|or`、直接 R/D 的 `sa`／`sb`／`destination`、`enable`。舊 `register_or` 介面仍可使用。`compare` 使用直接 R/D 的 `sa`／`sb`、`enable`、`unsigned_when` 及 `equal`／`greater`／`less` 正常線圈清單。

CMP 的三個結果選擇碼分別是 `6FFC`、`6FFD`、`6FFE`，在 test8 接到 M100、M101、M102。參數尾端另有 `0000` 欄位，意義尚未知，必須原樣保留；非零值不猜測。這不是新增 D0 目的暫存器。CMP 輸出位址會納入資源保留，避免編譯器 helpers 使用同一個 M。

test8 也建立 RESET Y0=`0100`、SET Y3=`1103`，以及直接電源軌 `4FEB` 的證據。`coils[].mode` 可指定 `normal|set|reset`，SET／RESET 在條件不成立時保留原值。`direct_rail=true` 僅允許 TRUE 的線圈網路，以保留這個匯出形式。

## test9 其他格式

| 樣本 | 觀察到的格式 | MCP 參數 |
| --- | --- | --- |
| MC0、MC2 | enable + `FC88` + 編號 BE16 | `type=mc, number, enable` |
| MCE0 | `FC89` + 編號 BE16 | `type=mce, number` |
| 07P.UDCTR | PLS + nested U/D + nested CLR + `F100` + PV BE16 + CV word | `type=udctr, pulse, up, clear, preset, cv` |
| N001 並聯 | `4201 9100 6100 9201 E422 C100` | `branch_encoding=test9_or`，僅兩個二接點分支 |

UDCTR 的原樣本是 `4001 6002 6003 F100 0064 0B90`，對應 X1、X2、X3、PV=100、CV=R200。CLR 是直接極性，不能套用既有一般 Counter 的反相 CLR 編碼。保留畫面中的 07P 形式；沒有外推 D 型、register PV 或 CUP 接線。

`E422` 目前只在這個二分支形式使用，避免把它當成所有並聯情境的通用取代碼。這個形式會保留原接線，不拆出多餘的 M helpers。

MC／MCE 的參數範圍、DIFU／DIFD 介面與 UDCTR 語意可對照使用者提供的 《基本應用指令.pdf》 第 7-12～14、7-18～19、7-21～22 頁。手冊提供語意，二進位編碼以 test9 和截图為依據。完整程式生成目前只支援配對且不交錯／巢狀的 MC 區域；片段仍可解碼研究。

## 政策與驗證層次

讀取 test9 不會拒絕或改寫原樣本；把它作為完整程式重新生成則另有結構與政策檢查：原 N004 的 MC2 沒有 MCE2，M1 主控區間的 DIFU／DIFD 寫入 M100／M101 則屬於目前政策允許的原生 function 結果。MC 區間內的普通 M 複製仍禁止。

- **獨立離線驗證**：樣本 payload／容器逐 byte 核對、CRC、位址引用、MC 配對和架構限制；另有布林分支真值表及 S/R 保持行為測試。這些不是 PLC 執行證據。
- **MCP 內建模擬**：一般布林、原生邊沿和 S/R 可用既有掃描模型；新增 DIFU／DIFD、MC／MCE、UDCTR 以及暫存器 function 目前明確拒絕執行模擬，不假裝已驗證狀態切換。
- **GUI 匯入**：使用者提供的截圖用於辨識原樣本；本次新生成的檔案尚未經 GUI 匯入。
- **實體 PLC**：未驗證。

## 下一步推理

現在能確認 function 編碼分組不按 FUN 編號排列：加減乘除和 CMP 使用 62～6A，INC／DEC 在 96／98，AND／OR 在 C6／C8；MC／MCE 是另一组 FC88／FC89，DIFU／DIFD 又有 F8／FC 的差異。先區分指令族、參數數量及接線，再做局部外推。

仍待獨立匯出驗證的候選：同一 ADD 把 Sb 常數改成暫存器，可能由 F662 變成 F462；MC/MCE 相鄰碼是否能推到 SKP/SKPE 亦待證明。不能把這些假說列為正式支援，也不能套用單一 F4／F5／F6 規則到 DIFU 或 UDCTR。現有嚴格政策要求輸出可解碼檢查，因此本次不交付未辨識 opcode 的猜測檔。

後續更新：test10 已確認 FUN35 XOR、FUN36 XNR、FUN37 ZNCMP、FUN20 →BCD、FUN21 →BIN，見 [test10 編碼](test10-functions.md)。
