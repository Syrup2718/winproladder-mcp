# test17：整數運算與 CRC16

原始樣本 `samples/test17.ldr` 為8網路、420 bytes；新增精確 `FBn-26MC-test17` 檔頭，保留4030 metadata。原始截圖在 `samples/screenshots/test17.png`。此次為未發版更新，不調整0.10.0版本或製作安裝包。

| FUNC | action.type | 目前形式與讀寫範圍 |
| --- | --- | --- |
| 23 DIV48 | `div48` | 新增 `encoding=single_input`（F474），沒有 U/S 腳位；保留 test16 的 two_inputs（F46C）。Sa／Sb／D 仍依手冊各3 words |
| 24 SUM | `sum` | 新增 R100、N=12、R123 實際匯出錨點，既有16-bit常數 N 形式不變 |
| 25 MEAN | `mean` | source、count 暫存器、destination；執行時 N 有效範圍2～256；ERR |
| 26 SQRT | `sqrt` | source 暫存器及 destination，各1 word；ERR |
| 27 NEG | `neg` | destination 原地讀寫1 word |
| 28 ABS | `abs` | destination 原地讀寫1 word |
| 29 EXT | `ext` | 讀取 destination 的16-bit值，將符號擴展到 destination 與下一個 word |
| 31 CRC16 | `crc16` | 樣本 MD=1、常數 N=1～256、source／destination；zero／error 狀態輸出 |

以上新指令目前使用直接 R/D 暫存器，不支援 D/P、間接定址、MEAN 常數 N、SQRT 常數來源、CRC16 暫存器 N 或 MD=0。新增狀態接線與未取樣位址組合標為 `inferred_variant`；不宣稱已由 GUI 確認。

## 必須區分的語意

**MEAN 的 N=D600 是值，不是數量600。** 程式執行時才知道 N，因此分析追蹤 D400～D655 全部256個可能讀取位置，並另讀取 D600。這是保守的可能讀取集合，不表示每次都讀256個；來源必須能容納最大有效長度，也會檢查與 PID／周邊 WR 獨占範圍的衝突。N 超出2～256時 PLC 以 ERR 表示不執行，不由離線編譯器猜測 D600 的值。

**DIV48 的 F474 不與 F46C 混用。** 畫面與 bytes 都顯示新形式没有 U/S 輸入，因此單輸入形式不能配置 `unsigned_when` 條件；預設 FALSE 僅保留相容欄位，不代表已確認該新形式的有號／無號規則。原有兩輸入形式保持原樣。

**CRC16 的 MD=1 存在手冊差異。** 使用者提供的《進階篇應用指令》7-11頁把 MD=1 標成保留，但 test17 實際匯出該形式。MCP 支援保存及生成它的編碼，不推定其執行算法。分析暫以手冊 MD=0 的 N 個來源 word、2個目的 word 作保守記錄，並回傳 `complete=false` 與 `reference_uncertainties`，不能把這份引用表當作已確認的 MD=1 硬體行為。其他指令依據同一手冊7-3～9頁。

## 原始編碼

| 網路 | payload |
| --- | --- |
| N000 | `4fe8f47427fa0a0057f46ffcc819` |
| N001 | `4fe8f5c0000c0ac80af6` |
| N002 | `4fe8f4e244b0432040dc` |
| N003 | `4fe8f49c1a680a02` |
| N004 | `4fe8f49a0a18` |
| N005 | `4fe8f49e0ba2` |
| N006 | `4fe8f4b90a04` |
| N007 | `4fe8f77500080bb80bbc` |

完整 IR 在 [test17 JSON](../examples/test17_functions.json)，可交給 `generate_ldr`；原樣本没有 X/Y，`io_contract` 為 inputs=[]、outputs=[]。不額外配置實體輸入或輸出。

## 驗證

離線驗證涵蓋原始 bytes、CRC、暫存器範圍、動態 N 的可能讀取範圍、三層 M→M 政策與零額外 I/O。沒有建立獨立數學／PLC 執行模型；MCP 內建模擬會明確拒絕這批 action。新產檔尚未經 GUI 匯入或實體 PLC 驗證。

MCP stdio 已完成讀取、生成、resource 下載；重建420 bytes 與原檔完全相同，663項測試通過。交付檔為 `artifacts/test17_mcp_roundtrip.ldr`，共用目錄另存相同檔案；報告為 `artifacts/test17_verification.json`。
