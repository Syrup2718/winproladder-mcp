# 文件索引

[首頁](../README.md) · [功能清單](../FEATURES.md) · [貢獻指南](../CONTRIBUTING.md)

## 使用指南

| 文件 | 內容 |
| --- | --- |
| [跨平台安裝](installation.md) | Windows、macOS、Linux 安裝與疑難排解 |
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

研究紀錄保留編碼證據與當時測試結果。本機產物不隨 Git 提供。

| 文件 | 指令／主題 |
| --- | --- |
| [算術與邊沿](fun11-14-arithmetic.md) | FUN11～14 |
| [線性轉換](fun33-lcnv.md) | FUN33 LCNV |
| [test8／test9](test8-test9-functions.md) | MC／MCE、DIFU／DIFD、UDCTR、INC／DEC、CMP、AND |
| [test10](test10-functions.md) | XOR、XNR、ZNCMP、→BCD、→BIN |
| [test11](test11-functions.md) | 比較接點與浮點 FUNC |
| [test12](test12-functions.md) | 浮點除法、比較、區間比較與平方根 |
| [test13](test13-functions.md) | 三角函數、取負值、絕對值、自然對數與指數 |
| [test14](test14-functions.md) | FLOG、FPOW、反三角函數、ERR 與 IMDIO |
| [test15](test15-functions.md) | TKEY、HKEY、DSW、7SGDL、MUXI |
| [test16](test16-functions.md) | DIV48、SUM、PID、WDT 與高速計數器 |
| [test17](test17-functions.md) | 整數運算與 CRC16 |
| [test18](test18-functions.md) | 類比轉換、位元存取與跳躍樣本 |
| [test19](test19-functions.md) | 積算型計時器與溫控 |
| [test20](test20-functions.md) | ASCWR、RAMP、RAMP2、R→T |
| [test21](test21-functions.md) | FUN101～104 表格指令 |
| [test22](test22-functions.md) | FUN105～112 表格指令 |
| [test23](test23-functions.md) | FUN120～127 矩陣指令 |
| [test24](test24-functions.md) | MOV、MOV/、TOGG、SORT、Z-WR、矩陣位元功能 |
| [test25](test25-functions.md) | FUN42～49 位元搬移、交換與資料組合 |
| [test26](test26-functions.md) | FUN50～57 分配、移位、旋轉、格雷碼與解碼 |
| [test27](test27-functions.md) | FUN06 BSHF 與 FUN58～64 轉換功能 |
| [test28](test28-functions.md) | 脈波、速度與字串 |
| [test29](test29-functions.md) | ASCII 與數字標籤 |
| [test30](test30-functions.md) | 記憶體指令與英數標籤 |

## 版本與歷史

| 文件 | 範圍 |
| --- | --- |
| [未發版變更](unreleased.md) | 0.11.0 之後的原始碼更新 |
| [0.11.0 版本紀錄](release-0.11.0.md) | 該版本的功能與驗證快照 |
| [FUN15／16 舊假說](fun15-16-probe.md) | 已被新樣本推翻，僅供研究追溯 |
| [2026-10-13 目錄盤點](folder-audit-2026-10-13.md) | 本機維護歷史 |
| [2026-10-15 專案優化](project-optimization-2026-10-15.md) | 重構範圍、效能量測與驗證 |
| [2026-10-15 修復](repair-2026-10-15.md) | 修復與驗證紀錄 |
| [GUI 交接清單](gui-handoff-2026-10-16.md) | WinProLadder 匯入與補充取樣 |

手冊以標題與頁碼引用，PDF 不隨儲存庫提供。
