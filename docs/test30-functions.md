# test30：記憶體指令與英數標籤

[原始匯出](../samples/test30.ldr) · [截圖](../samples/screenshots/test30.png) · [IR 範例](../examples/test30_functions.json)

8 個網路，FBs-32MC 原始標頭。編譯後與原檔逐位元組一致。

| FUN | action | 已實作形式 |
|---|---|---|
| 65 LBL | `lbl` | 1～6 個 ASCII 英數字元；A、B1、JY1、1WX 有原始樣本，4～6字元與小寫為推導 |
| 160 RW-FR | `file_register` | Sa=`source`、Sb=`file_base` F0～8191、Pr=`pointer`、L=`length` 1～511；EN、R/W=`read_mode`、INC、ERR |
| 161P WR-MP | `memory_pack_write` | S、Pr、WR 直接 R/D；Bk=`bank` 1、Os=`offset` 0、L 1～128；EN、INC；ACT、ERR、DN；`pulse=true` |
| 162 RD-MP | `memory_pack_read` | D、Pr 直接 R/D；bank=1、offset=0、L 1～128；EN、INC、ERR；非P |
| 190 STAT | `system_status` | Gp=`group` 0、D 直接 R/D；EN |

## 手冊與限制

依《進階篇應用指令》7-59、7-137～142、7-149～150（PDF同頁碼）。

- 一般標籤不接受手冊保留的中斷名稱（尚缺RTI程式區支援）。LBL 用於標記，不代表已解決 JMP／CALL 的額外資料；其生成限制不變。
- RW-FR 的 R/W=1讀取、0寫入，Pr 為記錄索引，實際檔案位置為 Sb+Pr×L。INC 完成後遞增 Pr。
- WR-MP 工作區佔2字；可能跨多次掃描，ACT表示執行中。來源／指標與工作區不得重疊。
- 記憶匣是外部狀態；目前不模擬其內容。指標有效範圍需由執行時資料決定。
- RW-FR 分析保守列出整個 F bank；STAT 寫入長度取決於實際擴充模組，保守列出 D 起點至所在 bank 尾端。這些不是實際寫入長度。分析標示不完整，避免誤稱精確範圍。
- STAT Gp=1～3在手冊為保留，Gp=0需要 PLC OS V4.62以上。生成不表示已檢查實際CPU／韌體。
- 手冊允許的 Bk=0、其他 Os、暫存器長度、間接定址、其他 D/P 形式尚無編碼證據；不是 PLC 不允許。FUN162／190依各自手冊使用 D0～3999；161為D0～4095。

## 編碼證據

LBL 固定8 bytes：EF、首字元、後續7-bit字元配對為大端序word、零補齊。B1=`ef42188000000000`、JY1=`ef4a2cb100000000`、1WX=`ef312bd800000000`。

樣本 opcode：RW-FR F51E、WR-MP F35B、RD-MP F75D、STAT F472。Bk／Gp未出現獨立word，因此只開放已觀察的值，不猜其他值如何改變opcode。長度直接保存原值。

## 驗證

來源 IR、lowered IR、輸出解碼與原始 bytes 比對；新增邊界、非法形式、工作區衝突及標籤測試。離線序列化驗證不等於執行模型；未做這些指令的 MCP 模擬、GUI匯入或實體PLC驗證。

實際透過新啟動的 MCP stdio server 產生 `test30_mcp_roundtrip.ldr`，450 bytes 與原始匯出完全一致；resource／下載內容亦一致。新指令與標籤專項42項通過；Ruff及mypy（39個來源檔）通過。

完整回歸：1487項通過（48.80秒）。
