# test21：FUN101～104 表格指令

> 指令研究紀錄：參數與編碼依據保留於下文。測試數及產物狀態屬當次紀錄；目前能力請以功能清單為準。本機產物不隨 Git 發布。

[首頁](../README.md) · [文件索引](README.md) · [功能清單](../FEATURES.md)

此功能納入 0.11.0 之後的未發版原始碼更新。

來源：[原始檔](../samples/test21.ldr)、[截圖](../samples/screenshots/test21.png)、[可重用IR](../examples/test21_functions.json)。五個網路均可解碼並原樣重建，新增精確 `FBe-40MC-test21` 檔頭，保留4030 metadata。

| FUN | action | 運算元 | 控制／狀態 |
| --- | --- | --- | --- |
| 101 T→R | `table_to_reg` | source=Ts、length=L、pointer=Pr、destination=Rd | enable／increment／clear；done／error |
| 102 T→T | `table_to_table` | source=Ts、destination=Td、length=L、pointer=Pr | 同上 |
| 103 BT_M | `block_table_move` | source=Ts、destination=Td、length=L | enable |
| 104 T_SWP | `table_swap` | source=Ta、destination=Tb、length=L | enable |

目前編碼範圍為16-bit非P、直接R/D暫存器、常數L。101／102長度2～2048；103／104長度2～256。R0～3839、R5000～8071、D0～4095可讀寫，R3840～3903僅來源可讀；整段表格不得跨越已支援 bank。T_SWP 兩張表都要可寫。其他手冊允許的字組、D/P、暫存器L及間接定址尚未有本次編碼證據，不等同PLC不允許。

## 手冊與接線核對

依使用者提供的《進階篇應用指令.pdf》7-96～99頁：

- 101／102：CLR先清除Pr，且可獨立於EN執行；搬移後Pr=L−1時END成立，否則INC為1才遞增。Pr超出0～L−1時ERR成立。
- 101只搬移Ts[Pr]到Rd；102搬移Ts[Pr]到Td[Pr]。資源分析追蹤所有可能被索引的表格元素。
- 103一次搬移整表；104一次互換兩表，分析同時記錄兩側讀寫。
- 7-96頁印刷表格把K欄的2～2048列在Pr行、L行則空白；同頁範例卻為L=9、Pr=R19。本次依GUI匯出及同頁範例支援常數L，不推論常數Pr的編碼。7-97頁同系列明列L=2～2048。

**CLR更正**：test21 N002的X5→CLR為`6005`，證明使用一般接點極性；`7FE8`為FALSE。N000／N001均為INC=TRUE、CLR=FALSE，N002為INC=TRUE、CLR=X5。先前test20將CLR一律反相的推論已移除，對應IR範例與測試已更新。歷史LDR和驗證報告不改寫；相同bytes現在有修正後的語意解讀。

M3作為101的END，接著控制102的EN，屬於允許的原生function結果與控制，沒有新增中繼M或X/Y。

## 編碼證據

- 101：`F408 Ts (L−1) Pr Rd`。
- 102：`F40A Ts Td (L−1) Pr`，N001／N002提供兩組對照。
- 103：`F4CE Ts Td (L−1)`。
- 104：`F4C2 Ta Tb (L−1)`。

不同位址、長度、控制布林式及狀態線圈組合為外推，通過往返與邊界測試不代表已經GUI或PLC確認。未知形式維持opaque，不猜測D/P opcode。

## 驗證

完整MCP重建檔（本機產物：`artifacts/test21_mcp_roundtrip.ldr`）與驗證報告（本機產物：`artifacts/test21_verification.json`）。檢查來源、lowered IR、decoded bytes的政策和I/O契約；核對完整檔案bytes、CRC、SHA-256及MCP resource下載。原檔五個網路的暫存器和控制接線完整保留。

離線驗證是格式、資源及架構檢查；沒有獨立PLC執行模型，MCP內建掃描模擬明確拒絕這些新指令。新生成檔未經WinProLadder GUI匯入或實體PLC驗證。

本次完整測試 **823項通過**；Ruff與30個原始碼檔案的mypy檢查通過。22份原始樣本、146個網路可解碼並逐byte重建。MCP產出389 bytes，與test21原始檔完整一致，SHA-256為 `1bea9772444fbb0e05b1d21a6b9518c0f212a059f33ad92ac187c187e54ac3f0`。
