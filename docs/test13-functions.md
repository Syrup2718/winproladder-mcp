# test13：三角函數、取負值、絕對值、自然對數與指數

後續更新：[test14](test14-functions.md) 已補浮點 ERR 接線並取樣證實 F6 第二運算元常數；下文的未支援／推導記錄為當時驗證狀態。

2026-10-08 未發版原始碼更新，版本仍為 0.10.0。沒有製作安裝包。

依據原始 `samples/test13.ldr`、對照畫面及本機 `C:/Fatek/FBe進階篇/進階篇應用指令.pdf` 第 7-160～166 頁。
原檔 409 bytes、7 網路，SHA-256：`c221aafbe6708f529680b537420d6733cc838cd8e8b4edb8dbff5129f247cb88`。
新檔頭 `FBs-44MN-test13` 精確保留 CPU 名稱與 4040 metadata，不由名稱猜測硬體容量。

| FUNC | `float_operation.operation` | 來源與結果 |
| --- | --- | --- |
| 209 FSIN | `sin` | sa：16-bit 整數角度；destination：雙 word 浮點 |
| 210 FCOS | `cos` | 同上 |
| 211 FTAN | `tan` | 同上 |
| 212 FNEG | `neg` | 僅 destination，原地讀寫雙 word，改變正負號 |
| 213 FABS | `abs` | 僅 destination，原地讀寫雙 word，取絕對值 |
| 214 FLN | `ln` | sa：浮點來源或常數；destination：雙 word 浮點 |
| 215 FEXP | `exp` | 同上，求 e 的 sa 次方 |

## 三種格式，不混用來源寬度

FSIN／FCOS／FTAN 的 sa 範圍為 -18000～18000，單位 **0.01 度**。例如 sa=3000 代表 30 度，樣本 sa=123 代表 1.23 度；不使用弧度，也不是 binary32 常數。暫存器來源只讀一個 word，所以 R8071 可以作 FCOS 的來源。destination 仍需要兩個 word，D4094 對應 D4094／D4095。

```json
{"action":{"type":"float_operation","operation":"sin","sa":"R2222","destination":"R2223"}}
{"action":{"type":"float_operation","operation":"cos","sa":"R8071","destination":"D4094"}}
{"action":{"type":"float_operation","operation":"tan","sa":123,"destination":"R222"}}
{"action":{"type":"float_operation","operation":"neg","destination":"R222"}}
{"action":{"type":"float_operation","operation":"abs","destination":"R0"}}
{"action":{"type":"float_operation","operation":"ln","sa":"R22","destination":"R98"}}
{"action":{"type":"float_operation","operation":"exp","sa":"R8000","destination":"D123"}}
```

FNEG／FABS 不接受額外 sa／sb，讀寫分析會同時記錄目的雙字組。樣本 FNEG 讀寫 R222／R223，FABS 讀寫 R0／R1。保留樣本本身的重複寫入，不擅自換位址。

FLN／FEXP 第 7-165～166 頁的 DR 欄明列 **D0～D3999**，與前三角函數表的 D0～D4095 不同。編譯器依個別表格檢查完整雙字組，所以 FLN／FEXP 的 D 起點最多 D3998；R bank 維持 R0～3839、R5000～8071，雙字組起點最多 R3838／R8070。FLN 常數必須大於 0；暫存器內容的運行時錯誤仍由 PLC 處理。

手冊另列浮點指令不可用於中斷處理副程式；目前 MCP 不提供該結構。沒有將 Python 數學運算冒充 PLC 執行模擬。

## 原始 payload

| 網路 | bytes |
| --- | --- |
| N000 | `4fe8f47f00091b5c1b5e` |
| N001 | `4fe8f47f000a3ffe5ffc` |
| N002 | `4fe8f57f000b007b0bbc` |
| N003 | `4fe8f47f000c0bbc` |
| N004 | `4fe8f47f000d0a00` |
| N005 | `4fe8f47f000e00000a2c0ac4` |
| N006 | `4fe8f47f000f00003f7040f6` |

三角函數來源為 2 bytes，常數標記 F57F，暫存器 F47F；FNEG／FABS 僅一個 2-byte 目的位址。FLN／FEXP 的來源沿用 4-byte 浮點來源結構。

精確樣本標為 `observed_export`。其他 EN／位址組合、負角度常數的有號編碼、FLN／FEXP 浮點常數形式標為 `inferred_variant`，不自動取得 GUI 驗證。未知子碼、額外 operand、錯誤旗標組合保持 opaque。

## 交付與驗證

`test13_native_functions_roundtrip.ldr` 完整重建七網路，與原始 409 bytes 相同。`test13_trigonometry.ldr` 為 N000～N002，`test13_inplace_log_exp.ldr` 為 N003～N006；兩者是格式測試片段。

已經目前原始碼 MCP stdio 讀檔、生成、resource 下載與逐 byte 比對；離線檢查 CRC、單／雙字組範圍、讀寫集合、常數及未知格式拒絕。I/O contract 為空，不新增 X/Y，也不配置 M helper；產檔仍經來源、lowered 與 decoded 政策檢查。完整測試 531 項通過。

未建立獨立 PLC 數學執行模型；MCP 內建模擬對這些 action 明確拒絕。新檔尚未經 GUI 匯入或實體 PLC 驗證；P／間接尚未實作；有 ERR 的浮點運算已由 test14 補上普通 ERR 線圈。
