# test23：FUN120～127 矩陣指令

> 指令研究紀錄：參數與編碼依據保留於下文。測試數及產物狀態屬當次紀錄；目前能力請以功能清單為準。本機產物不隨 Git 發布。

[首頁](../README.md) · [文件索引](README.md) · [功能清單](../FEATURES.md)

2026-10-14原始碼更新，維持0.11.0，不製作安裝包。

來源：[原始檔](../samples/test23.ldr)、[截圖](../samples/screenshots/test23.png)、[IR範例](../examples/test23_functions.json)。460 bytes、8網路；新增精確 `HB1-32M-test23` 檔頭，保留1055 metadata。

| FUN | action | 運算元 | 輸入／狀態 |
| --- | --- | --- | --- |
| 120 MAND | `matrix_and` | source=Ma、source_b=Mb、destination=Md、length=L | enable |
| 121 MOR | `matrix_or` | 同上 | enable |
| 122 MXOR | `matrix_xor` | 同上 | enable |
| 123 MXNR | `matrix_xnr` | 同上 | enable |
| 124 MINV | `matrix_invert` | source=Ms、destination=Md、length_register=L | enable |
| 125 MCMP | `matrix_compare` | source=Ma、source_b=Mb、length=L、pointer=Pr | enable／from_head／different；found／done／error |
| 126 MBRD | `matrix_bit_read` | source=Ms、length=L、pointer=Pr | enable／increment／clear；output／done／error |
| 127 MBWR | `matrix_bit_write` | destination=Md、length=L、pointer=Pr | enable／input_bit／increment／clear；done／error |

## 單位、長度與指標

依《進階篇應用指令.pdf》7-113～121頁，矩陣由16-bit word構成，L是word數，合法範圍2～256。因此MCMP、MBRD、MBWR的位元指標範圍是0～16L−1，並不是0～L−1。例：N005的L=2涵蓋32 bits；N006的L=5涵蓋80 bits。

MCMP從FHD指定的表頭或Pr+1開始搜尋，D/S=1找不同、0找相同。FND表示找到，END表示抵達最後位元；超出指標範圍設ERR。MBRD／MBWR會先依CLR清除Pr，執行讀／寫後判斷END，尚未抵達最後才依INC遞增。CLR能獨立於EN執行。MBWR四路控制分別編碼，不把INB和INC或CLR混用。

MINV樣本使用R1作為長度暫存器，並未提供R1的運行值。靜態分析保守涵蓋來源R100～R355、目的R110～R365，並記錄R1讀取。這不表示每次一定寫256 words。若256-word最壞範圍跨越bank，現行分析會拒絕；不代表特定較小L在PLC上非法。L暫存器目前限手冊允許且已有編碼的HR／ROR／DR。

## 編碼範圍

目前支援樣本非P形式、直接R/D：R0～3839、R5000～8071、D0～4095；R3840～3903僅來源可讀。120～123、125～127為常數L，儲存L−1；124為暫存器L，直接儲存暫存器地址。MINV常數L、其他指令暫存器L、P、間接定址及其他word bank是尚未實作的編碼，不等同PLC禁止。

120～127的opcode依序為F4D2、F4D3、F4D4、F4D5、F4D6、F412、F40E、F42A。來源與目的相同的原地運算可使用，不合成中繼M。M控制原生function及其M狀態符合目前政策；普通M複製仍禁止。

各矩陣完整讀寫範圍會納入分析。MBWR只變更目標位元，因此同時記錄目的word的讀寫，以保留其他位元。原樣本不同網路共享R10、R20等資料，MINV也可能寫入後續網路使用的暫存器；本次保留全部地址，沒有把範例改造成另一套控制流程。

## 驗證

MCP重建檔（本機產物：`artifacts/test23_mcp_roundtrip.ldr`）、驗證報告（本機產物：`artifacts/test23_verification.json`）。實際stdio MCP生成及resource下載後，460 bytes與原檔完全一致。SHA-256：`31642eb09039ab57dd5c3d09491865a24ba6e6266aa92f1452b50be7234faa34`。

離線驗證涵蓋原檔bytes、CRC、完整範圍、來源／lowered／decoded政策、I/O契約與四路控制分離。沒有獨立PLC執行模型，MCP內建模擬明確拒絕新矩陣指令；未進行GUI匯入或實體PLC驗證。

完整測試 **946項通過**；Ruff與32個原始碼檔案的mypy通過。24份原始樣本、163個網路可語意解碼並逐byte重建；本機盤點未發現內容結構、文件連結或LDR CRC錯誤。
