# 文件索引

## 使用與目前能力

| 文件 | 用途 |
| --- | --- |
| [現有功能總覽](../FEATURES.md) | 目前原始碼功能、FUNC、工具與限制 |
| [快速開始](quickstart.md) | 安裝與第一個檔案 |
| [Agent 操作指南](agent-guide.md) | 從需求到檔案的工具流程 |
| [功能與參數](reference.md) | 配方、IR、模擬及支援限制 |
| [手冊範圍與 RTC](manual-limits-rtc.md) | 運算元上限、手冊差異、萬年曆程序與快照檢查 |
| [0.11.0版本紀錄](release-0.11.0.md) | 本次升版功能、驗證及打包狀態 |
| [未發版變更](unreleased.md) | 最後安裝包之後的原始碼更新 |

## 指令與格式證據

| 文件 | 用途 |
| --- | --- |
| [計時器證據](timer-evidence.md) | 計時器編碼與時間契約 |
| [算術與邊沿](fun11-14-arithmetic.md) | FUN11～14、原生接點、後續功能推理 |
| [test8／test9 原生 function](test8-test9-functions.md) | DIFU／DIFD、MC／MCE、UDCTR、INC／DEC、CMP、AND |
| [test10 原生 function](test10-functions.md) | XOR、XNR、ZNCMP、→BCD、→BIN，整字 I/O 契約 |
| [FUN33 LCNV](fun33-lcnv.md) | 線性轉換編碼與限制 |
| [test11 原生 function](test11-functions.md) | 比較接點170～175、浮點200～204、字組範圍 |
| [test12 原生 function](test12-functions.md) | 浮點205～208、常數、擴充字組與比較線圈 |
| [test13 原生 function](test13-functions.md) | 三角函數209～211、原地212～213、對數／指數214～215 |
| [test14 原生 function](test14-functions.md) | 浮點216～220、ERR、IMDIO 整段 I/O |
| [test15 原生 function](test15-functions.md) | TKEY／HKEY／DSW／7SGDL／MUXI、KL／WR／I/O |
| [test16 原生 function](test16-functions.md) | DIV48、SUM、PID、WDT／RSWDT、HSC0 讀寫 |
| [test17 原生 function](test17-functions.md) | MEAN／SQRT／NEG／ABS／EXT／CRC16、單輸入 DIV48 |
| [test18 原生 function](test18-functions.md) | ADCNV、MLC、BITRD／BITWR、精確LBL／JMP樣本 |
| [test19 原生 function](test19-functions.md) | 積算型計時87～89、TPCTL、CALL解析及手冊版本差異 |
| [test20 原生 function](test20-functions.md) | ASCWR、RAMP、RAMP2、R→T、時間單位與工作區衝突 |
| [LDR 格式](ldr-format.md) | Record、CRC、指令編碼與未知欄位 |
| [驗證依據](verification.md) | 樣本覆蓋、匯入基準與驗證邊界 |

## 維護與歷史

| 文件 | 用途 |
| --- | --- |
| [資料夾導覽](folders.md) | 原始碼、交付檔、安裝包與研究資料分類 |
| [開發指南](development.md) | 專案結構、測試及新增功能 |
| [邏輯簡化](logic-optimization.md) | 簡化規則、接圖策略與資源預覽 |
| [FUN15／16 舊試檔](fun15-16-probe.md) | 已被 test8 推翻的歷史假說 |

首次安裝請見 [專案首頁](../README.md)。目前參數以 `get_capabilities`、`get_design_guide` 回傳的 schema 為準。

- [2026-10-13 全資料夾檢查與整理](folder-audit-2026-10-13.md)

- [test21：FUN101～104 表格搬移與互換](test21-functions.md)

- [test22：FUN105～112 搜尋、表格、QUEUE／STACK及BKCMP](test22-functions.md)

- [test23：FUN120～127 矩陣運算與位元讀寫](test23-functions.md)

- [test24：MOV／MOV/／TOGG、SORT／Z-WR、矩陣位元操作](test24-functions.md)

- [test25：FUN42～49 搬移、交換及資料結合／分配](test25-functions.md)

- [test26：FUN50～57 分配、移位、旋轉、格雷碼、解碼](test26-functions.md)

- [test27：FUN06及58～64 編碼、顯示、ASCII與時間轉換](test27-functions.md)
