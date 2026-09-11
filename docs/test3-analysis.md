# test3.ldr 新證據

來源：使用者提供 `C:/VM_Share/test3.ldr`，已原樣複製至 samples。
畫面：[test3.png](../samples/screenshots/test3.png)。版本沿用使用者提供的 WinProLadder v3.28。
補充畫面：[test3-bottom.png](../samples/screenshots/test3-bottom.png)，涵蓋 N008–N011。

## Framing

468 bytes、12 records、footer offset 0x1CE。Header 與前三個樣本完全相同。
12/12 CRC 通過，既有長度公式、trailer、footer 均成立。
合計四個樣本 27/27 records 通過。測試：`test_all_observed_records`、
`test_headers_identical`；原始 SHA-256 已加入 `test_sample_integrity.py`。

## 畫面範圍與實體順序

兩張截圖合計涵蓋 N000–N011。全部非空 record 均與畫面反序對應；
N 編號仍來自人工畫面核對，而非 binary 內已解碼的編號欄位。

| offset (hex) | 對照 N | payload | 畫面 |
| --- | --- | --- | --- |
| 100 | 011 | `48 12 C1 05` | M2 NO 接點→Y5 coil |
| 10F | 010 | `43 01 C8 12` | C1 NO 接點→M2 coil |
| 11E | 009 | `4F E8 7F E8 F9 40 00 11 05 96` | C3、PV 17；PLS/CLR 接左母線 |
| 133 | 008 | `4F E8 7F E8 F9 40 00 10 05 94` | C2、PV 16；PLS/CLR 接左母線 |
| 148 | 007 | `4F E8 7F E8 F9 40 00 0A 05 92` | C1、PV 10；PLS/CLR 接左母線 |
| 15D | 006 | `4F E8 FD 80 00 65 03 96` | T3、.01S、101 |
| 170 | 005 | `4F E8 FD 80 03 E8 03 94` | T2、.01S、1000 |
| 183 | 004 | `4F E8 FD 80 01 00 03 92` | T1、.01S、256 |
| 196 | 003 | `5F EB` | 空 network |
| 1A3 | 002 | `40 01 C1 01` | X1→Y1 |
| 1B2 | 001 | `5F EB` | 空 network |
| 1BF | 000 | `40 00 C1 00` | X0→Y0 |

中間空 network 現已取得：兩筆 `5F EB` 的位置吻合 N001/N003，
支持空 network 有實際 record 並保留在反向序列中（HIGH CONFIDENCE）。
相同空 record 的身分無法獨立區別。測試固定上述實體 payload 次序；畫面對照為人工證據。

## Timer

HIGH CONFIDENCE：目前 .01S Timer 的 payload +4/+5 以 big endian 解讀，
可一致得到 100、101、256、1000。特別是 `01 00` 與 `03 E8`，
排除這兩個 bytes 在目前案例中採 little endian 的解釋。
尚未證明整個 operand 格式就是通用 uint16，也未確認最大範圍、其他 time base 或暫存器 preset。

T1/T2/T3 分別觀測 `03 92` / `03 94` / `03 96`。
`0x0390 + 2*n` 仍為 HYPOTHESIS，缺 T0/T10 等邊界或較大位址。

本圖 Timer 的 TUP 後沒有 Y coil，payload 長度為 8；
舊樣本則多出 `6F FC C1 nn`。尾端 `C1 nn` 對應 Y coil 有既有證據，
`6F FC` 可能與後續連接有關，但語意仍 UNKNOWN。
不能直接把它固定納入每個 Timer 指令。

## Counter 與 C/M 元件

N007–N009 現已核對：C1/PV10、C2/PV16、C3/PV17。
payload +6/+7 分別為 `00 0A`、`00 10`、`00 11`，支持 big endian 常數假設；
但 preset 都小於 256，尚不能確定完整 operand 寬度或編碼通則。
payload +8/+9 分別為 `05 92`、`05 94`、`05 96`，
`0x0590 + 2*n` 仍為 HYPOTHESIS：三例同時改 address/preset，且缺 C0/C10 等案例。
PLS/CLR 的個別編碼尚無差分證據，仍 UNKNOWN。

N010 的 `43 01` 對應 C1 NO 接點，`C8 12` 對應 M2 coil；
N011 的 `48 12` 對應 M2 NO 接點，`C1 05` 對應 Y5 coil。
結合 test2 的 M0 coil `C8 10`，M operand 使用 `0x10 + n` 是新 HYPOTHESIS，
不是已確認的任意位址公式；需要 M1/M10/M100 等跨範圍樣本。
上述具體畫面對照已完成，raw bytes 由 `test_all_observed_records` 固定；
測試不代表通用 Counter/M/C 語意 Encoder 已實作或驗證。

test3 的畫面已完整，足以繼續結構 Parser/Encoder 與無損往返實作。
