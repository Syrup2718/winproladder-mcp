# test11：比較接點與浮點 FUNC

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

**只支援目前取樣的位置**：首段 `eq/ne`，後续段 `gt/lt/ge/le`。尚未開放首段 gt/lt/ge/le、後續 eq/ne、OR 分支、與普通接點混接或 D 型。不能只用 FUN 編號推算未取樣的 selector。

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

除既有 R/D、T 數值、WX0/WY0 外，這個比較家族增加**精確取樣的** WS0、WM0、C2、R5111。沒有因此開放所有 WS/WM/C 或 R5000..8071。

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

轉換使用 `sa`，不可附 `sb`；加減乘必須有 `sb`。目前只接受 R0..3839、D0..3999 的直接暫存器，完整讀寫跨度不得跨界。P 形式、整數 D 型、常數、間接定址、ERR 接線、FDIV 及其他浮點指令皆未開放。

### 雙字組讀寫

- I→F R101 → R101：讀 R101，寫 R101、R102。
- F→I R102 → D103：讀 R102、R103，寫 D103。
- FADD R104、D555 → R99：讀 R104/R105、D555/D556，寫 R99/R100。
- FSUB R9、R10 → R102：讀 R9/R10、R10/R11，寫 R102/R103。
- FMUL R0、R1 → R2：讀 R0/R1、R1/R2，寫 R2/R3。

元件分析已記錄上述範圍，並列出樣本的 R102 重複寫入；不自行更改原樣本的重疊配置。

語意與資料寬度依本機 `C:/Fatek/FBe進階篇/進階篇應用指令.pdf` 第 7-143～148、7-151～155 頁核對；二進位編碼仍以 test11 為依據。

## 驗證範圍與交付

- 離線：7 筆 payload、CRC、完整檔案逐 byte 重建、精確檔頭、讀寫跨度、M→M 政策、I/O、邊界／未知子碼／額外欄位拒絕。
- MCP：以獨立安裝的 wheel，經 stdio 實際讀取、產檔與下載核對。
- 內建執行模擬：比較接點及浮點 action **尚未支援**，明確拒絕，並未以 Python 浮點計算冒充 PLC 模擬。
- GUI 匯入與實體 PLC：本次新生成檔案尚未驗證。

`test11_native_functions_roundtrip.ldr` 保留全部七個網路且與原檔相同；`test11_comparison_contacts.ldr`、`test11_float_blocks.ldr` 分別是抽出的格式測試片段，並非整份 test11 的等價控制程式。
