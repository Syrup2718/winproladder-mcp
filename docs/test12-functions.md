# test12：浮點除法、比較、區間比較與平方根

後續更新：[test14](test14-functions.md) 已補浮點 ERR 接線並取樣證實 F6 第二運算元常數；下文的未支援／推導記錄為當時驗證狀態。

2026-10-07 未發版原始碼更新；版本仍為 0.10.0，不產生新安裝包。

原始 `samples/test12.ldr` 共 388 bytes、4 個網路，SHA-256：
`ca61b33cf95e6af85cfe08dec0a6195fae475cad40330e3c00224389bd0caee5`。
原始檔保留不變；畫面存於 `samples/screenshots/test12.png`。使用新取樣檔頭 `FBs-40MA-test12`。

| FUNC | MCP action | 參數／結果 |
| --- | --- | --- |
| 205 FDIV | `float_operation`, operation=`div` | sa / sb → destination，拒絕常數除零 |
| 206 FCMP | `float_compare` | sa、sb；equal / greater / less 普通 Y/M 線圈 |
| 207 FZCP | `float_zone_compare` | source、upper、lower；within / above / below 普通 Y/M 線圈 |
| 208 FSQR | `float_operation`, operation=`sqrt` | sa → destination，拒絕負常數來源 |

所有 action 的 enable 預設 TRUE。狀態線圈仍受 I/O contract 與 M→M 政策檢查，不接受 SET／RESET／反相狀態線圈。不支援 P、間接定址或 ERR 接線。

## 可使用的結構

```json
{"action":{"type":"float_operation","operation":"div","sa":6.0120001,"sb":"D4094","destination":"R8000"}}
{"action":{"type":"float_compare","sa":102.2,"sb":"R2123","equal":[{"device":"Y","address":0}],"greater":[{"device":"M","address":123}],"less":[{"device":"M","address":55}]}}
{"action":{"type":"float_zone_compare","source":"R3838","upper":1.99,"lower":"R15","within":[{"device":"Y","address":1}],"above":[{"device":"M","address":3}],"below":[{"device":"M","address":999}]}}
{"action":{"type":"float_operation","operation":"sqrt","sa":"D123","destination":"R202"}}
```

這四個 network 可放入 `ladder.networks`，profile 選 `FBs-40MA-test12`，`io_contract` 使用 `{"inputs":[],"outputs":["Y0","Y1"]}`，透過 `generate_ldr` 產檔。

## 編碼證據與推導

| 網路 | 原始 payload |
| --- | --- |
| N000 | `4fe8f57f000540c0624e00005ffc3f70` |
| N001 | `4fe8f57f000642cc666600001a966ffcc1006ffdc88b6ffec847` |
| N002 | `4fe8f57f00073ffeb85200000a1e27fc6ffcc1016ffdc8136ffecbf7` |
| N003 | `4fe8f47f0008000040f60b94` |

子碼 0005..0008 分別對應這四個指令。FZCP 編碼順序是 **upper、lower、source**，不是畫面的 S、Su、Sl。FCMP/FZCP 的三個結果使用 6FFC、6FFD、6FFE。

- F47F：暫存器來源；F57F：第一個編碼運算元為浮點常數，已有原始樣本。
- F67F（第二個常數）與 F77F（兩個常數）是依旗標規律推導，已做內部編解碼測試，但未取得獨立原廠匯出或 GUI 確認。新增運算元／EN／狀態組合標為 `inferred_variant`。
- 常數以 big-endian IEEE-754 binary32 存放：6.0120001 → 40C0624E、102.2 → 42CC6666、1.99 → 3FFEB852。讀回可能顯示單精度的實際十進位值；bytes 保持相同。拒絕 NaN、Infinity、溢位與布林值。
- 常數也開放於既有 FADD／FSUB／FMUL；I→F、F→I 仍限暫存器來源。未知暫存器前綴及其他子碼保留 opaque，不假裝支援。

## 位址與架構檢查

浮點專用暫存器範圍為 R0..3839、R5000..8071、D0..4095。浮點值占連續兩個 word，不允許跨 bank；因此 D4094、R8070 可作雙字組起點，D4095、R8071 不可。轉換指令的整數端仍為一個 word。後續[手冊核對](manual-limits-rtc.md)另將這些 R/D bank 擴充至共用直接暫存器指令；指令型態限制仍適用。

樣本直接證明 D4094=5FFC、R8000=3F70；同 bank 其他位址按連續 word 規律推導。元件分析包括 D4095、R8001 等第二個 word。test12 取樣到 M999；後續手冊核對已開放一般 M0..1911；自動 helper 配置仍使用既有 M0..255 範圍。

無條件 FCMP/FZCP 可產生 M 狀態，供 Y 或計時／暫存器 EN 使用；若 M 接點驅動含 M 結果的比較，來源 IR、lowered IR、解碼出的 bytes 均拒絕。政策不變，不新增 X/Y。

## 交付與驗證

- `test12_native_functions_roundtrip.ldr`：四網路完整重建，與原始 388 bytes 完全相同。
- `test12_float_comparisons.ldr`：N001/N002 比較片段。
- `test12_float_blocks.ldr`：N000/N003 除法與平方根片段。
- `artifacts/test12_verification.json`：目前原始碼的 MCP stdio 讀取、產檔、resource 下載及政策拒絕測試。

離線驗證包含 CRC、完整 bytes、邊界、雙字組、常數與政策；不包含独立 PLC 浮點執行模型。MCP 內建執行模擬尚未支援這些 action，會明確拒絕。新生成檔尚未經 GUI 匯入或實體 PLC 驗證；既有比較接點位置的人工確認不適用於 test12。
