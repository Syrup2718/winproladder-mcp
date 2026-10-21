# v1.0.0 版本紀錄 — 2026-10-21

[首頁](../README.md) · [文件索引](README.md) · [功能清單](../FEATURES.md) · [驗證範圍](verification.md)

v1.0.0 將目前原始碼整理為穩定的離線 WinProLadder `.ldr` 產生、解析、分析與修改服務。這次更新專案版本與文件，未建立 wheel、sdist、installer、Git tag 或 release。

## 正式支援範圍

- 從高階控制配方、順序規格或自訂 Ladder IR 產生 `.ldr`。
- 讀取、解碼、分析、修改及重新輸出既有 `.ldr`，未知記錄在允許的無損流程中保持原始資料。
- 在寫檔前檢查 schema、I/O 契約、資源跨度、工作區政策、來源程式、lowered program 及解碼後輸出。
- 對已建模的布林、Timer/Counter、直接 R/D 數值運算及部分原生功能執行有界離線驗收。
- 透過 MCP stdio 提供能力查詢、設計指南、生成、模擬、讀取、分析、修改及檔案下載。
- 使用者明確要求新增元件註解時，依 `REF`／`COMMENT`／`DESCRIPTION` 格式另產生 CP950／Big5 `.txt`。

每項原生指令只承諾[功能清單](../FEATURES.md)所列的 operand、模式及狀態腳位。PLC 手冊允許但尚未取得 `.ldr` 編碼證據的形式，不會被錯誤標示為 PLC 不支援。

## 責任邊界

本專案負責產出及離線驗證 `.ldr`。以下項目不屬於 v1.0.0 的交付承諾：

- 自動操作 WinProLadder GUI 或保證 GUI 匯入結果。
- 連線、下載或控制實體 PLC。
- 保證未列出的 CPU、WinProLadder 版本、指令變體或硬體配置。
- 以離線模型取代 WinProLadder syntax check、使用端驗收或現場安全驗證。

既有 GUI 匯入紀錄與使用者提供的匯出樣本仍作為編碼證據，但不是每次產檔的必要步驟。使用者取得 `.ldr` 後，應依目標工程自行完成 GUI 匯入、PLC 下載與實機驗證。

## v0.11.0 之後納入的內容

- 擴充 test18～30 的原生功能、檔頭與樣本編解碼；目前保護 31 份原始樣本、219 個 networks。
- 高階控制配方改用原生 DIFU/DIFD、TOGG 與 R 狀態；sequence 使用暫存器狀態機並整合 FUN87 暫停續跑。
- 新增來源與 emitted bytes 的 acceptance、`require_acceptance`、三階段 writer 報告及高階產生器嚴格 writer 檢查。
- 修正 sequence、off-delay 與 pulse 的重複 M writer，不改變使用者 I/O 或時間契約。
- 將指令證據與警告規則自核心 IR 拆分，集中 profiles、operand 分派與 opcode 索引，並改善大型程式解析及模擬效能。
- 新增 compact MCP 回覆、指令族群清單及單族群能力查詢，完整高階設計保留在 sidecar JSON。
- 新增獨立元件註解產生工具；格式與提供的 123-byte CP950 樣本逐 byte 相同，不修改 `.ldr`。
- 加入 Windows、macOS、Linux 安裝入口、鎖定依賴、MCP stdio 自我檢查及三平台 CI 設定。
- 整理文件、研究紀錄、支援限制與離線／GUI／PLC 驗證層級。

詳細指令形式與手冊差異見 [test18](test18-functions.md) 至 [test30](test30-functions.md)，高階產生器修正見[修復紀錄](repair-2026-10-15.md)。

## 相容性承諾

v1 系列將 MCP 工具名稱、必要輸入欄位及既有成功回應的主要欄位視為公開介面。新增選填欄位、工具或更精確的拒絕規則可在次要版本加入；移除／重新命名公開工具、把選填欄位改為必填，或破壞既有有效輸入，原則上留給下一個主版本。安全政策與已證實的編碼錯誤不保證保留錯誤行為。

## 驗證快照

- 完整測試：1537 項通過。
- 靜態檢查：Ruff 與 strict mypy 通過。
- MCP 整合：stdio 連線、工具列舉、需求產檔、acceptance、SHA-256 與下載通過。
- 樣本：31 份、219 networks，由完整性雜湊、解析、語意解碼與重建測試保護。

以上是離線與 MCP 整合驗證；不代表本版所有輸出已逐一完成 GUI 匯入或實體 PLC 驗證。
