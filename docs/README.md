# 文件索引

[首頁](../README.md) · [功能清單](../FEATURES.md) · [貢獻指南](../CONTRIBUTING.md)

第一次使用請從快速開始閱讀。功能表描述目前實作；指令研究文件保存參數、原始 bytes 與歷史驗證依據。手冊合法範圍與本專案已實作的編碼範圍分開記錄。

## 使用指南

| 文件 | 內容 |
| --- | --- |
| [快速開始](quickstart.md) | 原始碼安裝、client 連線、產檔、匯入與問題排除 |
| [Agent 操作指南](agent-guide.md) | 19 個工具、需求整理、I/O 契約與二進位交付 |
| [功能與參數](reference.md) | 配方、順序控制、Ladder IR、時間單位與模擬 |
| [功能清單](../FEATURES.md) | 依 FUNC 編號排列的實作範圍與限制 |
| [驗證範圍](verification.md) | 編碼、模型、MCP、GUI 與實體 PLC 的區別 |

## 開發與格式

| 文件 | 內容 |
| --- | --- |
| [開發指南](development.md) | 架構、環境、測試及指令擴充 |
| [貢獻指南](../CONTRIBUTING.md) | 問題回報、樣本證據與 Pull Request |
| [專案目錄](folders.md) | 儲存庫與本機產物的界線 |
| [LDR 格式](ldr-format.md) | 容器、record、CRC 與未知欄位 |
| [邏輯簡化](logic-optimization.md) | 布林最佳化、接圖與政策限制 |
| [手冊範圍與 RTC](manual-limits-rtc.md) | 運算元、版本差異與萬年曆 |
| [計時器證據](timer-evidence.md) | 時基、普通 T 與積算計時 |
| [樣本目錄](../samples/README.md) | 原始匯出、網路數與對照證據 |
| [IR 範例](../examples/README.md) | 可讀的結構化樣本及生成限制 |
| [測試導覽](../tests/README.md) | 測試分類與覆蓋 |
| [維護腳本](../scripts/README.md) | 產檔、自我檢查及盤點入口 |

## 指令研究紀錄

保留樣本編號以便與 `.ldr`、截圖及測試交叉核對。此區文件中的測試數為歷史結果；本機產物路徑不作公開下載連結。

| 文件 | 指令／主題 |
| --- | --- |
| [算術與邊沿](fun11-14-arithmetic.md) | FUN11～14 |
| [線性轉換](fun33-lcnv.md) | FUN33 LCNV |
| [test8／test9](test8-test9-functions.md) | MC／MCE、DIFU／DIFD、UDCTR、INC／DEC、CMP、AND |
| [test10](test10-functions.md) | test10：XOR、XNR、ZNCMP、→BCD、→BIN |
| [test11](test11-functions.md) | test11：比較接點與浮點 FUNC |
| [test12](test12-functions.md) | test12：浮點除法、比較、區間比較與平方根 |
| [test13](test13-functions.md) | test13：三角函數、取負值、絕對值、自然對數與指數 |
| [test14](test14-functions.md) | test14：FLOG、FPOW、反三角函數、ERR 與 IMDIO |
| [test15](test15-functions.md) | test15：TKEY、HKEY、DSW、7SGDL、MUXI |
| [test16](test16-functions.md) | test16：DIV48、SUM、PID、WDT 與高速計數器 |
| [test17](test17-functions.md) | test17：整數運算與 CRC16 |
| [test18](test18-functions.md) | test18：類比轉換、位元存取與跳躍樣本 |
| [test19](test19-functions.md) | test19：積算型計時器與溫控 |
| [test20](test20-functions.md) | test20：ASCWR、RAMP、RAMP2、R→T |
| [test21](test21-functions.md) | test21：FUN101～104 表格指令 |
| [test22](test22-functions.md) | test22：FUN105～112 表格指令 |
| [test23](test23-functions.md) | test23：FUN120～127 矩陣指令 |
| [test24](test24-functions.md) | test24：MOV、MOV/、TOGG、SORT、Z-WR、矩陣位元功能 |
| [test25](test25-functions.md) | test25：FUN42～49 位元搬移、交換與資料組合 |
| [test26](test26-functions.md) | test26：FUN50～57 分配、移位、旋轉、格雷碼與解碼 |
| [test27](test27-functions.md) | test27：FUN06 BSHF 與 FUN58～64 轉換功能 |

## 版本與歷史

| 文件 | 範圍 |
| --- | --- |
| [未發版變更](unreleased.md) | 0.11.0 之後的原始碼更新 |
| [0.11.0 版本紀錄](release-0.11.0.md) | 該版本的功能與驗證快照 |
| [FUN15／16 舊假說](fun15-16-probe.md) | 已被新樣本推翻，僅供研究追溯 |
| [2026-10-13 目錄盤點](folder-audit-2026-10-13.md) | 本機維護歷史 |
| [2026-10-15 專案優化](project-optimization-2026-10-15.md) | 重構範圍、效能量測與驗證 |

原廠 PDF 未隨儲存庫提供。研究文件以手冊標題及印刷頁碼引用；不同手冊版本的差異保留於各指令紀錄。
