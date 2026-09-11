# WinProLadder LDR：第一輪樣本分析

分析日期：2026-09-11。這是樣本導出的規格草稿，並非官方規格。
`CONFIRMED` 僅表示在目前樣本內逐筆驗證成功，不代表所有 PLC 型號或匯出版本通用。
原始樣本 SHA-256 由 `tests/test_sample_integrity.py` 固定。
使用者確認 WinProLadder 版本為 **v3.28**（2026-09-11）；跨版本相容性尚未驗證。

## 證據範圍

第五份樣本見 [test4 分析](test4-analysis.md)：五份共 35/35 CRC 通過，
新增 Y/M 接點、反相 coil、邊沿接點及混合分支的畫面對照。

新增第四份樣本的結果見 [test3 分析](test3-analysis.md)：共 27/27 CRC 通過，
包含中間 empty 與 Timer preset 256/1000。以下前三份分析保留初始證據範圍；
Timer endian 與中間 empty 的新進展以 test3 分析為準。

| 樣本 | bytes | records | CRC 通過 | footer offset |
| --- | ---: | ---: | ---: | --- |
| w1.ldr | 277 | 1 | 1/1 | 0x10F |
| test.ldr | 404 | 8 | 8/8 | 0x18E |
| test2.ldr | 362 | 6 | 6/6 | 0x164 |

2026-09-11 使用者提供兩張截圖，內容分別吻合 test 與 test2：
[test 畫面](../samples/screenshots/test.png)、[test2 畫面](../samples/screenshots/test2.png)。
以下對照納入人工畫面核對；w1 仍依 brief 與相同 record 對照。
工具採檔案實際順序，從 0 開始編 `file_index`，N 編號不是從 binary 獨立解碼出的欄位。

### 畫面核對與更正

- test N000：X0→Y1；N001：X1→Y2；N002：X2 同時驅動 Y2、Y3。
- test N003：直接接左母線的 Timer T1，.01S、100，TUP 接 Y4。
- test N004：T1 AND X3 AND X4 AND /X5→Y5。
- test N005：**(/X6 OR X8) AND X7 AND (X9 OR X10)→Y6**。
  brief 將 X7/X8 描述為並聯不精確；畫面中 X8 跨接 /X6，X7 位於第一組並聯之後。
- test N006/N007：空白。
- test2 N000：X0→Y0；N001：/X0→Y0；N002：/X0→M0；N003：X0→M0。
- test2 N004：直接接左母線的 Timer T2，.01S、101，TUP 接 Y0。
- test2 N005：(X0 OR X1)→Y0。

test N005 的 bytes 可提出候選分組：`50 06 A0 08`、`80 07`、
`60 09 A0 0A E2 00`、`C1 06`，但這只是 HYPOTHESIS。
尚無單變數 branch 樣本可證明 `60` / `E2` 的通用運算或堆疊語意。

## Header

**CONFIRMED（3/3）**：前 256 bytes 完全相同，第一筆 record 均在 `0x100`。
自動測試：`test_headers_identical`。目前沒有反例，但無法由相同 header 推出欄位寬度、版本相容性或所有檔案都固定 256 bytes。

| offset | 觀測內容 | 意義可信度 |
| --- | --- | --- |
| 0x000 | ASCII `Fatek Resource File Format 1` | 字串已確認；版本編碼規則 UNKNOWN |
| 0x01C | `16` | UNKNOWN |
| 0x080 | ASCII `FB-RES` | 字串已確認；欄位結構 UNKNOWN |
| 0x090 | ASCII `WinProladder` | 字串已確認 |
| 0x0A0 | ASCII `FBs-20MC` | 字串已確認；跨型號規則 UNKNOWN |
| 0x0B0 | `40 40` | UNKNOWN |
| 0x0C0 | `48 01` | UNKNOWN |

三個不同檔案長度卻具有完全相同 header，因此 `48 01` 不能直接解釋為這些檔案的總長度。
其餘 bytes 仍需原樣保留，不將零值假設為可任意丟棄的 padding。

## Record framing 與 CRC

**CONFIRMED（15/15）**：所有 records 依下列結構連續排列，無間隙。
自動測試：`test_all_observed_records`。目前無反例。

| 相對 offset | 大小 | 內容 |
| --- | ---: | --- |
| +0 | 2 | `12 10` |
| +2 | 2 | record_length，little endian |
| +4 | 2 | payload_length，little endian |
| +6 | payload_length | raw payload |
| +6+payload_length | 3 | `01 00 00`，實際語意 UNKNOWN |
| +9+payload_length | 2 | CRC，little endian |

`record_length = payload_length + 5`。
整筆實際佔 `payload_length + 11 = record_length + 6` bytes。
長度欄位的名稱是本專案工作用名稱，非官方定義。

**CONFIRMED（15/15）**：CRC 使用 reflected polynomial `0xA001`、initial `0xFFFF`、無 final XOR，
覆蓋範圍為 `[record+4, CRC起點)`：payload length 的兩個 bytes、payload、三個 trailer bytes。
marker 與 record_length 不在計算範圍。演算法符合 CRC-16/MODBUS；
另以 `123456789 → 0x4B37` 及 brief 的 `04 00 40 00 C1 00 01 00 00 → 0xE515` 驗證。
測試：`test_crc_known_vectors`、`test_all_observed_records`、`test_corruption_is_reported`。
CRC 相符只證明資料一致性，不代表梯形圖語法或控制邏輯正確。

**CONFIRMED（3/3）**：最後 record 後恰為六 bytes `FF FF 00 00 00 00`，沒有其他資料。
作為通用 resource 結束標記的語意仍為 HIGH CONFIDENCE。

## 全部 payload（實體順序）

下列 bytes 由 `test_all_observed_records` 精確比對；test/test2 N 編號已與畫面核對。
兩筆相同 empty 的個別身分仍不可區別，依反序排列標示。

| 檔案 | offset | 推測 N | payload |
| --- | --- | --- | --- |
| w1 | 100 | 000 | `40 00 C1 01` |
| test | 100 | 007 | `5F EB` |
| test | 10D | 006 | `5F EB` |
| test | 11A | 005 | `50 06 A0 08 80 07 60 09 A0 0A E2 00 C1 06` |
| test | 133 | 004 | `42 01 80 03 80 04 90 05 C1 05` |
| test | 148 | 003 | `4F E8 FD 80 00 64 03 92 6F FC C1 04` |
| test | 15F | 002 | `40 02 C1 02 C1 03` |
| test | 170 | 001 | `40 01 C1 02` |
| test | 17F | 000 | `40 00 C1 01` |
| test2 | 100 | 005 | `40 00 A0 01 C1 00` |
| test2 | 111 | 004 | `4F E8 FD 80 00 65 03 94 6F FC C1 00` |
| test2 | 128 | 003 | `40 00 C8 10` |
| test2 | 137 | 002 | `50 00 C8 10` |
| test2 | 146 | 001 | `50 00 C1 00` |
| test2 | 155 | 000 | `40 00 C1 00` |

所有 offset 為十六進位。`w1` 與 `test` 最後一筆 record 完全相同。

## 順序與 opcode 假設

| 假設 | 結論與證據 | 信心 |
| --- | --- | --- |
| Network 反向儲存 | test/test2 的非空內容與畫面反序吻合；兩個相同 empty 無法互相區別；仍缺中間 empty 案例 | HIGH CONFIDENCE |
| `40 nn` 為開頭 X NO | X0/X1/X2 對照吻合；test2 的 NO/NC 有兩組只改首 byte 的配對 | HIGH CONFIDENCE |
| `50 nn` 為開頭 X NC | test2 的 `40→50`，Y0/M0 輸出不變；test 有 `50 06` | HIGH CONFIDENCE |
| `C1 nn` 為 Y coil | brief 中 Y0–Y6 皆可對上；w1/test2 的 X0→Y1/Y0 僅 coil operand 不同 | HIGH CONFIDENCE |
| `80 nn` / `90 nn` 串聯 NO/NC | 主要來自 test N004，缺單變數對照 | HYPOTHESIS |
| `C8 10` 為 M0 coil | test2 兩筆吻合，無其他 M 位址 | HYPOTHESIS |
| `42 01` 為 T1 contact | test N004 單一案例 | HYPOTHESIS |
| `A0 nn` 為 parallel X NO | test2 N005 吻合；複雜 branch 不足以驗證通則 | HYPOTHESIS |
| `60` / `E2` branch topology | test N005 有出現，但無法可靠分段與還原拓樸 | UNKNOWN |
| `5F EB` 為 empty | test 最前面兩筆對應畫面 N006/N007 空白；非零長度 payload，缺獨立 empty 匯出 | HIGH CONFIDENCE |

上述語意已與 test/test2 畫面核對，目前無已知反例，但證據集中於三個同型號樣本。
`test_all_observed_records` 固定原始 bytes，**不能自動證明畫面語意**；因此尚未提供語意 Encoder。

## Timer

**HYPOTHESIS**：test/test2 的 Timer payload 相同長度，差異為 payload 相對 offset：
`+5: 64→65`、`+7: 92→94`、`+11: 04→00`。
畫面確認兩例同時改了 timer address、preset 與輸出 coil，故不是單變數差分。
`64/65` 與 100/101 對應合理，但 preset 寬度與 endian 尚未確認。
`Tn = 0x90 + 2*n` 無充分證據；time base、operand 分界與其他 bytes 均 UNKNOWN。
raw bytes 受 `test_all_observed_records` 保護，目前沒有語意測試。

## 後續實作計畫

1. Structural model：保存 header、實體 record 順序、offset、raw payload、trailer、CRC、footer。
   通用 parser 要保留未知 record/opaque bytes；本輪 `research.inspect` 是嚴格的假設探針，未知 framing 會報錯。
2. Lossless encoder：從 structural model 重組原始 bytes，先驗證三個樣本 byte-for-byte equality。
   保留已讀取的未知 bytes 不等於可以生成未知指令。
3. Semantic IR：加入 contact/coil/series/parallel 節點，並保留每個節點來源 offset、raw bytes 與 confidence。
   分段不確定時保留整段 opaque payload，不強制假設每兩個 bytes 就是一個 instruction。
4. 僅在最小差分樣本及 WinProLadder import 驗證後開放語意生成。
   未支援指令明確回報 UnsupportedInstruction；MCP 層待以上基礎成立後加入。

上述為第一輪規劃。目前已實作結構 Parser/Encoder、有限語意 IR 與 stdio MCP，
五份原始樣本通過逐 byte round-trip。詳見 [agent 指南](agent-guide.md)。
下一批樣本見 `sample-requests.md`。
