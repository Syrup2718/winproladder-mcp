# v0.11.0 版本紀錄 — 2026-10-08

[文件索引](README.md) · [功能清單](../FEATURES.md)

原始碼升版至0.11.0，收錄0.10.0之後累積的功能及整理。這次只更新版本，尚未製作0.11.0安裝包；最後安裝包仍為0.10.0。

## 相較0.10.0的新增功能

| 功能 | 內容與證據 |
| --- | --- |
| 比較接點170～175 | 首段／串聯位置皆支援；指定六網路試檔的12種位置已由使用者確認 GUI 正確，見 [test11](test11-functions.md) |
| 手冊與 RTC | 依手冊擴充一般 M、直接 R/D 範圍；新增手冊查詢與 RTC 數值快照檢查。RTC 校時產檔尚未實作，見 [手冊範圍](manual-limits-rtc.md) |
| 浮點205～208 | FDIV、FCMP、FZCP、FSQR、binary32 常數、FBs-40MA 檔頭，見 [test12](test12-functions.md) |
| 浮點209～215 | 三角函數、取負／絕對值、自然對數／指數、FBs-44MN 檔頭，見 [test13](test13-functions.md) |
| 浮點216～220、74 | FLOG、FPOW、反三角函數、浮點 ERR 與 IMDIO，見 [test14](test14-functions.md) |
| I/O76～80 | TKEY、HKEY、DSW、7SGDL、MUXI，完整 I/O／KL／WR 檢查，見 [test15](test15-functions.md) |
| 控制與運算23／24／30／90～93 | DIV48、SUM、PID、WDT／RSWDT、HSC0 精確讀寫、FBs-60MC 檔頭，見 [test16](test16-functions.md) |
| 整數25～29／31、DIV48新形式 | MEAN、SQRT、NEG、ABS、EXT、CRC16 MD=1 編碼、FBn-26MC，見 [test17](test17-functions.md) |

完整功能依編號排列於 [FEATURES](../FEATURES.md)。歷史報告保留當時的測試數、版本與驗證狀態；它們不取代目前能力清單。

## 2026-10-08 整理

- 首頁、功能表、文件索引、目錄導覽分別負責使用入口、目前能力、技術證據與檔案位置，移除逐次追加的長段落。
- 校正工具數為19，統一一般 M0～1911、F6／ERR 等現行說明；原始 byte 證據與人工確認紀錄保持不變。
- 指令常數集中於 `instruction_catalog.py`，能力回報集中於 `capabilities.py`；保留原 `ir`／`service` 匯入介面。
- 一次性研究歸入 `tmp/research-history/`，舊猜測腳本放在 `scripts/research/`。既有交付檔、樣本、安裝包與環境路徑保留。

例行修改不打包、不更新版本。使用者明確要求後才進行這些動作。

## 驗證與已知限制

663項測試通過；18份原始樣本、124筆網路可解碼重建。保留原始樣本、既有交付檔及工作區禁止 M→M 的政策。新指令沒有因升版取得 GUI 或實體 PLC 驗證；CRC16 MD=1及 DIV48 單輸入形式的語意差異仍依 test17 文件揭露。

本機 Windows 應用程式控制阻擋 `winproladder-setup` 啟動器（4551）；使用 `uv run python -m winproladder_mcp.setup check` 已通過真實 MCP 連線、19工具、需求產檔、SHA-256與二進位下載檢查。未修改系統安全設定。
