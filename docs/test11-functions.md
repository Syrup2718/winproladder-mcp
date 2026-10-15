# test11：比較接點與浮點 FUNC

> 指令研究紀錄：參數與編碼依據保留於下文。測試數及產物狀態屬當次紀錄；目前能力請以功能清單為準。本機產物不隨 Git 發布。

[首頁](../README.md) · [文件索引](README.md) · [功能清單](../FEATURES.md)

MCP v0.10.0 以使用者提供的 `test11.ldr` 與截圖為編碼依據。來源共 461 bytes、7 網路；SHA-256 為 `43f823427d4dfa69a0b6c09a833ea9c996ef7b8ae16e7b8d97531b171ffd4e4a`。此檔是格式樣本，不修改其控制需求或補入元件。

## 新檔頭

檔頭 CPU 文字是 **FBs-32MA**，176..177 metadata 為 `10 40`。新增精確 profile `FBs-32MA-test11`；僅辨識整個已取樣檔頭，不將任意未知欄位忽略，也不宣稱能自動轉換 CPU 型號。

## 170～175 比較接點

| 網路／位置 | 畫面 | 編碼 |
| --- | --- | --- |
| N000 首段 | 170 `R2 = R5111` | `F47F 0015 0A04 28DE` |
| N000 第二段 | 171 `WS0 > WM0` | `F47F 0022 0885 0902` |
| N000 第三段 | 172 `D222 < T2` | `F47F 0023 41BC 0394` |
| N001 首段 | 173 `R600 <> R700` | `F47F 0018 0EB0 0F78` |
| N001 第二段 | 174 `T50 >= R300` | `F47F 0025 03F4 0C58` |
| N001 第三段 | 175 `C2 <= 100` | `F67F 0026 0594 0064` |

N000 尾端 `0101` 是 RESET Y1；N001 的 `1103` 是 SET Y3。比較輸出直接串聯後驅動原線圈，不另外建立 M 結果中繼。

**2026-10-07 未發版更新：六種比較均可作為首段或後續串聯段。** 以首段子碼 0015..001A 與串聯子碼 0021..0026 推導完整位置表；原 test11 直接證實首段 eq/ne 和串聯 gt/lt/ge/le，其餘六個位置已透過位置試檔取得使用者 GUI 正確回報。這是編碼證據差異，不是比較邏輯的用途限制。尚未開放 OR 分支、普通接點混接及 D 型。版本號與既有安裝包不變。

`comparison_chain` 是 Network 欄位，不能與 action、condition、steps、block、edge 混用；必須有目的線圈。例如：

```json
{
  "profile":"FBs-32MA-test11",
  "networks":[{
    "comparison_chain":[
      {"operation":"eq","sa":"R2","sb":"R5111"},
      {"operation":"gt","sa":"WS0","sb":"WM0"},
      {"operation":"lt","sa":"D222","sb":"T2"}
    ],
    "coils":[{"device":"Y","address":1,"mode":"reset"}]
  }]
}
```

Sa 目前為直接 word 位址。Sb 可為直接 word；只有後續 `le` 支援 0..32767 常數，負數與其他常數位置未取樣。不同已支援 operand 的組合仍標示外推，並非都已 GUI 驗證。

### 新 operand 的限定範圍

除既有 R/D、T 數值、WX0/WY0 外，這個比較家族增加**精確取樣的** WS0、WM0、C2、R5111。WS/WM/C 仍未整區開放；後續[手冊核對](manual-limits-rtc.md)已將 R5000..8071 擴充至共用直接暫存器。

WM0 視為 M0..M15 的整字讀取，WS0 視為 S0..S15；T2/T50/C2 是數值，不是完成接點。WM0 的讀取會納入元件分析、M 資源保留及架構政策，故 WM0 比較後直接寫入 M 線圈／SET／RESET 也會被拒絕。不允許以 word 或比較接點隱藏 M→M。

## 200～204 浮點指令

| FUNC | action.operation | 來源／結果寬度 | 原始 payload |
| --- | --- | --- | --- |
| 200 I→F | `i_to_f` | 整數來源 1 word → 浮點結果 2 words | `4FE8 F47F 0000 0000 0ACA 0ACA` |
| 201 F→I | `f_to_i` | 浮點來源 2 words → 整數結果 1 word | `4FE8 F47F 0001 0ACC 40CE` |
| 202 FADD | `add` | 各來源 2 words → 結果 2 words | `4FE8 F47F 0002 0000 0AD0 0000 4456 0AC6` |
| 203 FSUB | `sub` | 各來源 2 words → 結果 2 words | `4FE8 F47F 0003 0000 0A12 0000 0A14 0ACC` |
| 204 FMUL | `mul` | 各來源 2 words → 結果 2 words | `4FE8 F47F 0004 0000 0A00 0000 0A02 0A04` |

浮點家族使用 `F47F` 延伸標記及子碼 0000..0004。部分來源前有額外 `0000` 欄位，其二進位用途尚未確定，原樣保留；非零變體不猜測。不是直接把 FUN200 的數字寫進檔案。

```json
{"action":{"type":"float_operation","operation":"i_to_f","sa":"R101","destination":"R101","enable":"TRUE"}}
{"action":{"type":"float_operation","operation":"add","sa":"R104","sb":"D555","destination":"R99","enable":"TRUE"}}
```

轉換使用 `sa`，不可附 `sb`；加減乘必須有 `sb`。test11 初版只有直接暫存器；目前未發版原始碼已由 [test12](test12-functions.md) 擴充浮點常數、R5000..8071／D0..4095、FDIV／FCMP／FZCP／FSQR。完整跨度不得跨界；P／間接仍未支援；浮點算術的普通 ERR 接線已由 [test14](test14-functions.md) 補上。

### 雙字組讀寫

- I→F R101 → R101：讀 R101，寫 R101、R102。
- F→I R102 → D103：讀 R102、R103，寫 D103。
- FADD R104、D555 → R99：讀 R104/R105、D555/D556，寫 R99/R100。
- FSUB R9、R10 → R102：讀 R9/R10、R10/R11，寫 R102/R103。
- FMUL R0、R1 → R2：讀 R0/R1、R1/R2，寫 R2/R3。

元件分析已記錄上述範圍，並列出樣本的 R102 重複寫入；不自行更改原樣本的重疊配置。

語意與資料寬度依本機 《進階篇應用指令.pdf》 第 7-143～148、7-151～155 頁核對；二進位編碼仍以 test11 為依據。

## 驗證範圍與交付

- 離線：7 筆 payload、CRC、完整檔案逐 byte 重建、精確檔頭、讀寫跨度、M→M 政策、I/O、邊界／未知子碼／額外欄位拒絕。
- MCP：以獨立安裝的 wheel，經 stdio 實際讀取、產檔與下載核對。
- 內建執行模擬：比較接點及浮點 action **尚未支援**，明確拒絕，並未以 Python 浮點計算冒充 PLC 模擬。
- GUI 匯入與實體 PLC：本次新生成檔案尚未驗證。

`test11_native_functions_roundtrip.ldr` 保留全部七個網路且與原檔相同；`test11_comparison_contacts.ldr`、`test11_float_blocks.ldr` 分別是抽出的格式測試片段，並非整份 test11 的等價控制程式。

## 首段／串聯位置試檔

`FUN170_175_all_positions_probe.ldr` 共6網路，每個網路包含兩個相同關係比較，依序為 =、>、<、<>、>=、<=；第一個比較使用0015..001A，第二個使用0021..0026。全部使用 R600/R700，依序輸出 Y1、Y3、Y1、Y3、Y1、Y3。這些重複輸出只用於匯入格式檢查，不是完整控制程式。新版編譯器可解碼及檢查此推導格式；使用者後續已確認 GUI 正確，詳見下節；尚未取得重新匯出 bytes。未建立新安裝包、未變更版本。


## 使用者 GUI 確認（2026-10-07）

使用者針對 `FUN170_175_all_positions_probe.ldr` 回覆「都正確」。記錄為該檔六種比較、首段與串聯段共12種位置的 GUI 匯入／畫面確認。

- SHA-256：`252622c9cc544eeac82d525200a40c084b4aceb06f9978803ccfc7513db3781a`。
- 範圍：FBs-32MA-test11，R600/R700，比較順序 =、>、<、<>、>=、<=，Y1/Y3。
- 這項人工回報獨立於離線CRC及編碼測試；沒有收到 WinProLadder 重新匯出檔，尚無原廠重新匯出 bytes 比對。
- 內建執行模擬與實體 PLC 未驗證；OR、混合接點、D/P 或其他運算元變體不繼承這次確認。
- 原產檔報告保留當時狀態，另存 `artifacts/FUN170_175_all_positions_probe.gui-confirmation.json` 作為後續確認紀錄。
