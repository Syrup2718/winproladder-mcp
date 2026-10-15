# test14：FLOG、FPOW、反三角函數、ERR 與 IMDIO

> 指令研究紀錄：參數與編碼依據保留於下文。測試數及產物狀態屬當次紀錄；目前能力請以功能清單為準。本機產物不隨 Git 發布。

[首頁](../README.md) · [文件索引](README.md) · [功能清單](../FEATURES.md)

2026-10-08 未發版原始碼更新；版本保持 0.10.0，未製作安裝包。

來源為 `samples/test14.ldr`、`samples/screenshots/test14.png`，及本機 《進階篇應用指令.pdf》 第 7-66、7-167～171 頁。原檔 404 bytes、6 網路，SHA-256：`5155c779d0a8bf2bf3fc6511ccd8287de95e266a75ba2dee07cb8caba92489b9`。檔頭與已取樣 `FBs-44MN-test13` 相同。

| FUNC | IR | 行為 |
| --- | --- | --- |
| 216 FLOG | `float_operation`, `log` | log10(sa)，常數 sa 必須大於 0 |
| 217 FPOW | `float_operation`, `pow` | **sa=Sy 指數、sb=Sx 底數**；結果為 sb 的 sa 次方 |
| 218 FASIN | `float_operation`, `asin` | 浮點來源 -1～1，浮點結果為弧度 |
| 219 FACOS | `float_operation`, `acos` | 浮點來源 -1～1，浮點結果為弧度 |
| 220 FATAN | `float_operation`, `atan` | 浮點來源，浮點結果為弧度 |
| 74 IMDIO | `imdio` | 由 start 開始，立即更新連續 count 點主機 X 或 Y |

## 浮點運算與 ERR

FUN216～220 的 R bank 為 R0～3839、R5000～8071；這幾個指令的手冊 D bank 為 D0～3999。來源／目的地均保留雙 word，最高起點分別是 R3838、R8070、D3998。反三角函數結果不是 FUN209～211 的 0.01 度整數角度，不能直接互換。

```json
{"action":{"type":"float_operation","operation":"log","sa":"R2222","destination":"D2221","error":[{"device":"M","address":23}]}}
{"action":{"type":"float_operation","operation":"pow","sa":"R700","sb":2,"destination":"R710"}}
{"action":{"type":"float_operation","operation":"asin","sa":"R101","destination":"R102"}}
{"action":{"type":"float_operation","operation":"acos","sa":"R103","destination":"R105"}}
{"action":{"type":"float_operation","operation":"atan","sa":"R5000","destination":"R8070"}}
{"action":{"type":"imdio","start":"X0","count":10}}
```

樣本 FPOW 是 **2 的 R700/R701 浮點值次方**，不是 R700 的平方。F6 第二運算元常數標記由本次原始匯出證實；F7 雙常數組合仍為推導。

`float_operation.error` 使用普通 Y/M 線圈，ERR 標記為 6FFC。FLOG→M23 已取樣；其他有 ERR 的浮點算術／三角函數沿用相同結構，標為推導形式。I→F、F→I、FNEG、FABS 的 ERR 形式未開放；FCMP／FZCP 未因此新增 ERR。

ERR 線圈參與元件讀寫分析、M 資源保留、I/O 契約與架構政策。無條件 FLOG 可以輸出 M23；目前政策允許 M0 啟用原生 FLOG 並輸出 M23，來源 IR、lowered IR 與 decoded bytes 均區分 function 結果與無意義的繼電器複製。SET／RESET／反相 ERR 線圈未實作。

## IMDIO 的 I/O 範圍

count 為整數 1～36。X0、count=10 表示 X0～X9，必須全部列入 `io_contract.inputs`；不是新增九個外部時脈或控制輸入，而是原始指令既有的刷新範圍。Y 更新同樣要求整段列入 outputs。讀寫分析將 X 列為讀取，Y 列為讀取輸出影像並更新實體輸出。

手冊只允許**主機本身** I/O，不含擴充模組。10／14／20／24／32／40／60 點主機的 X 點數依序為 6／8／12／14／20／24／36，Y 點數為 4／6／8／10／12／16／24。程式檢查表格總上限 X35／Y23；這不是特定 CPU 的容量保證。44MN 沒有列在這張表中，不能從名稱猜出其 X/Y 點數，生成報告會保留主機容量尚未核對的提示。

樣本 X0、N10 已取樣；其他 X/Y 位址／長度是依格式外推。尚無 P 形式、即時 I/O 執行模擬或真實硬體更新測試。產檔本身不連線或操作 PLC。

## 原始 payload 與驗證

| 網路 | bytes |
| --- | --- |
| N000 | `4fe8f47f001000001b5c515a6ffcc827` |
| N001 | `4fe8f67f001100000f78400000000f8c` |
| N002 | `4fe8f47f001200000aca0acc` |
| N003 | `4fe8f47f001300000ace0ad2` |
| N004 | `4fe8f47f0014000028003ffc` |
| N005 | `4fe8f4e80000000a` |

`test14_native_functions_roundtrip.ldr` 經目前原始碼 MCP stdio 讀取、生成與 resource 下載後，與原檔 404 bytes 完全相同。另提供 `test14_float_functions.ldr`（前五網路）及 `test14_imdio.ldr`（最後一網路）作格式測試片段。

559 項測試通過，包含邊界、常數定義域、ERR 政策、IMDIO 整段 I/O 契約、未知格式拒絕及原始樣本 CRC／逐 byte 重建。沒有新增 helper 或擅改樣本位址。詳細紀錄為 `artifacts/test14_verification.json`。

驗證限離線格式與靜態分析；沒有獨立 PLC 數學／即時 I/O 執行模型。MCP 內建模擬明確拒絕這些 action；新檔未經 WinProLadder GUI 匯入或實體 PLC 驗證。
