# test10：XOR、XNR、ZNCMP、→BCD、→BIN

[文件索引](README.md) · [功能清單](../FEATURES.md)

MCP v0.9.0 將使用者提供的 test10 當作 function 格式樣本，支援讀取、分析、產檔及網路編輯；原樣本不修改。來源為 `samples/test10.ldr` 與 `samples/screenshots/test10.png`。375 bytes、5 networks，SHA-256：`0b00e0d1da4d7f466928f76921bd281d0c55158c32a5aa9ee41b373aa4cf3600`。

## 五筆實際編碼

| 網路 | 畫面 | payload |
| --- | --- | --- |
| N000 | 35.XOR R1234, D300 → R110 | `4FE8 F4CA 13A4 4258 0ADC` |
| N001 | 36.XNR R205, T1 → R233 | `4FE8 F4CC 0B9A 0392 0BD2` |
| N002 | 37.ZNCMP S=R3840, Su=100, Sl=-10 | `4FE8 F7DA 0064 FFF6 0100 6FFC C100 6FFD C101 6FFE C102` |
| N003 | 20.→BCD S=333 → R222 | `4FE8 F5A6 014D 0BBC` |
| N004 | 21.→BIN WX0 → WY0 | `4FE8 F4A4 0800 0820` |

ZNCMP 的實際 operand 順序為 **Su、Sl、S**，不是畫面顯示的 S、Su、Sl。`FFF6` 是有號 16-bit 的 -10，不能解讀成正數 65526。`6FFC/6FFD/6FFE` 分別連接 INZ、S>U、S<L，在樣本中寫入 Y0、Y1、Y2。ERR 未接線。

XNR 的 `0392` 是 T1 的**數值字組**；不會編成讀取 T1 完成狀態的布林接點。FUN35/FUN36 只確認 F4CA/F4CC 直接 word 形式，不由 FUN 編號推算 opcode。

## MCP action

```json
{"type":"exclusive_logic","operation":"xor","sa":"R1234","sb":"D300","destination":"R110","enable":"TRUE"}
```

operation 可為 `xor` 或 `xnr`。

```json
{"type":"zone_compare","source":"R3840","upper":100,"lower":-10,"enable":"TRUE","within":[{"device":"Y","address":0}],"above":[{"device":"Y","address":1}],"below":[{"device":"Y","address":2}]}
```

上下限目前僅支援 -32768..32767 常數，lower 不得大於 upper。source 使用直接 R/D，三組結果可接普通 Y/M 線圈；M 輸出仍受專案架構政策限制。暫不支援 ERR 接線或暫存器上下限。

```json
{"type":"word_conversion","operation":"to_bcd","source":333,"destination":"R222","enable":"TRUE"}
{"type":"word_conversion","operation":"to_bin","source":"WX0","destination":"WY0","enable":"TRUE"}
```

→BCD 目前只產生樣本確認的 **常數來源 F5A6**，有效值 0..9999；尚未宣稱支援暫存器來源。→BIN 使用 **word 來源 F4A4**，不接受常數。兩者尚不支援 ERR 接線、D/P 形式或間接定址。

## Word 位址與 I/O 契約

這批新增 action 支援既有 R/D bank、T0..255 數值來源，以及已取樣的 WX0/WY0。T1 為實際樣本，其他 T 位址沿已知每字兩 byte 規則外推。T 不開放寫入；WX0 和 R3840..3903 為唯讀。其他 WX/WY 編號、WM/WS/C word 等尚不外推。

WX0 對應 X0..X15，WY0 對應 Y0..Y15。生成工具會將全部位元納入 io_contract、讀寫引用和重複寫入檢查；不能只申報 X0/Y0 就通過。這是原樣本的整字 I/O 範圍，不是新增硬體。可對照本機 《基本應用指令.pdf》 第 7-38 頁 WX0 圖，以及 [FATEK 原廠手冊鏡像第 9-28 頁](https://www.esea.cz/support/fatek/doc/FBe-Manual-PDF/advance/CH09.pdf) 的 WY0 圖。

整份 test10 的 N002 與 N004 都寫入 Y0/Y1/Y2；分析會列出重複寫入。這份檔案用於辨識 function 格式，沒有替使用者重設其控制邏輯。原樣重建檔 `test10_native_functions_roundtrip.ldr` 保留全部五個網路；`test10_XOR_XNR_blocks.ldr` 僅抽出前兩個 function，方便單獨檢查。

## 驗證界線

- 獨立離線核對：原始 bytes/CRC、逐 byte 重建、負數編码、位址分類、完整 I/O、狀態輸出政策、未知變體拒絕與 opcode/常數碰撞。
- MCP：實際安裝 wheel，透過 stdio 讀取、生成、下載二進位檔，再核對來源。
- 內建模擬：新增 function 尚無執行模型，遇到執行模擬請求會明確拒絕。
- GUI／實體 PLC：本次新檔未驗證；原截圖只證明提供樣本中的指令與參數。其他參數組合會標示 inferred_variant。

不宣稱已完成全部 function 或硬體支援；專案政策、既有時間設定和 I/O 契約保持不變。
