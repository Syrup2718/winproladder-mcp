# test15：TKEY、HKEY、DSW、7SGDL、MUXI

2026-10-08 未發版原始碼更新；版本保持 0.10.0，沒有製作安裝包。

依據 `samples/test15.ldr`、`samples/screenshots/test15.png` 與本機 `C:/Fatek/FBe進階篇/進階篇應用指令.pdf` 第 7-67～73 頁。原檔 391 bytes、5 網路，沿用精確檔頭 `FBs-44MN-test13`；SHA-256 為 `587d2bcff2794470be5524cf85355f2d74f303cf9d7213a4f26f6d3f92c73c1f`。

## 五種原生 action

| FUNC | action.type | 運算元 | 狀態輸出 |
| --- | --- | --- | --- |
| 76 TKEY | `tkey` | input、destination、key_start | pressed=KPR |
| 77 HKEY | `hkey` | input、output、destination、key_start、work | pressed=NKP、function_pressed=FKP |
| 78 DSW | `dsw` | input、output、destination、work | done=DN、error=ERR |
| 79 7SGDL | `7sgdl` | source、output、mode、work | done=DN |
| 80 MUXI | `muxi` | input、output、rows、destination、work | done=DN |

均使用 enable（預設 TRUE）。狀態輸出格式為普通 Y/M 線圈清單，不接受 SET／RESET／反相。缺少必要參數、提供別種指令的參數或不存在的旗號會拒絕。

```json
{"action":{"type":"tkey","input":"X0","destination":"R1000","key_start":"M0"}}
{"action":{"type":"hkey","input":"X10","output":"Y5","destination":"R1200","key_start":"M100","work":"R3000","pressed":[{"device":"M","address":10}]}}
{"action":{"type":"dsw","input":"X1","output":"Y3","destination":"R3999","work":"R1222","done":[{"device":"M","address":11}]}}
{"action":{"type":"7sgdl","source":"V","output":"Y120","mode":0,"work":"R3001"}}
{"action":{"type":"muxi","input":"X10","output":"Y20","rows":2,"destination":"D4095","work":"D22","done":[{"device":"M","address":12}]}}
```

## 完整範圍與原生行為

- TKEY：input 開始 10 個 X，key_start 開始 10 個 KL，destination 一個 word，儲存最多四位十進位數字。
- HKEY：4 個 X、4 個 Y 形成 4×4 鍵盤；KL 連續 16 個位元，前 10 個數字鍵、後 6 個功能鍵；destination 一個 word，WR 一個 word。
- DSW：4 個 X、4 個 Y；destination 一個 word，WR 連續兩個 word。樣本 WR=R1222，必須同時保留 R1223。
- 7SGDL：source 一個 BCD word；output 開始 8 個 Y（4 個資料位與 4 個閂鎖位），WR 一個 word。mode=0～3 指定資料／閂鎖極性，不是位數或更新週期。本指令不自動實現使用者的 50 ms／40 ms／10 ms 數字顯示契約。
- MUXI：input 開始 8 個 X，output 開始 rows 個 Y，rows=2～8。結果為 8×rows bits，占 `ceil(rows/2)` 個 word；WR 一個 word。樣本 rows=2，故 D4095 單 word 合法；rows=3 則需兩個 word，不能再用 D4095 作起點。

輸入／掃描輸出起點依手冊表限定 X/Y0～240；KL 目前支援 Y0～240 或一般 M0～1896 起點，並檢查整段是否越界。未因樣本 M100 或 Y120 限制其他合法起點。

原始程式使用 X0～X17；Y3～Y8、Y20～Y21、Y120～Y127。`io_contract` 必須列出整段。這些點位來自指令參數，不是新增外部時脈或另加控制 I/O。

WR 與來源／目的地重疊會拒絕，也會檢查 WR 被其他網路讀寫的衝突。樣本的 Y5/Y6 被 HKEY 與 DSW 共同寫入，分析會保留多重寫入提示；這是格式樣本，不擅自搬動位址來改成另一份控制程式。

KL 隱含輸出與明接的 KPR／NKP／FKP／DN／ERR 全部納入 M 資源保留及 M→M 政策。因此 TKEY 即使沒有明接 KPR，只要 EN 使用 M 接點而 KL 寫 M，也會被拒絕。來源、lowered 與 decoded 三層均檢查。

## 新位址與編碼

本樣本直接提供 R3999=`023E`、V=`0388`，作為本類指令的精確特殊 word 支援。沒有將未取樣的整個特殊 R 區、其他索引暫存器或 RTC 編碼視為完成。WR 使用既有可寫直接 R/D bank；其他 word 形式僅使用現有 codec 支援範圍。

| 網路 | 原始 payload |
| --- | --- |
| N000 | `4fe8f4ea000011d00810` |
| N001 | `4fe8f6ec000a01051360087421706ffcc81a` |
| N002 | `4fe8f6ee00010103023e138c6ffcc81b` |
| N003 | `4fe8f6fc0388017800002172` |
| N004 | `4fe8f6fa000a011400025ffe402c6ffcc81c` |

opcode 分別為 F4EA、F6EC、F6EE、F6FC、F6FA。沒有僅按 FUNC 編號推算 opcode。第一、第二狀態旗號使用 6FFC、6FFD；第二旗號接線及其他參數組合屬推導形式。

## 驗證與限制

`test15_native_functions_roundtrip.ldr` 透過目前原始碼 MCP stdio 讀取、生成、resource 下載後，與原始 391 bytes 完全相同。592 項測試通過，包含連續 I/O、KL、WR、MUXI 奇偶列數、政策、邊界、未知格式及原始樣本 CRC／逐 byte 重建。

目前支援已取樣的 16-bit 形式；D／P、間接、常數來源與任意特殊 word 形式尚未實作。掃描輸出的電晶體硬體與接線仍需符合手冊。

已完成離線格式及靜態範圍檢查；沒有獨立掃描／硬體行為模型，MCP 內建模擬明確拒絕這些 action。新檔未經 GUI 匯入或實體 PLC 驗證。詳細 MCP 紀錄為 `artifacts/test15_verification.json`。
