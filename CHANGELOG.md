# 變更紀錄

本文件只保留對使用者有影響的版本變更。細部修復與編碼證據由 Git 歷史及自動測試追蹤。

## Unreleased

- 新增英文 README、英文功能總覽與中英共用的 FUNC 支援表。

## 1.0.0 — 2026-10-21

- 提供 WinProLadder `.ldr` 的產生、解析、分析、修改與二進位下載。
- 支援高階控制配方、順序控制、自訂 Ladder IR 與 22 項 MCP 工具。
- 寫檔前檢查 schema、I/O 契約、資源跨度、工作區政策及解碼後輸出。
- 新增 compact 能力查詢、acceptance 報告與嚴格 writer 檢查。
- 新增 CP950／Big5 元件註解 `.txt` 產生功能。
- 完成 Windows、macOS、Linux 安裝入口與鎖定依賴。
- 專案採用 MIT License，版權持有人為 syrup2718。
- 精簡公開範例，將測試專用 IR 移至測試 fixtures。

此版本的測試、靜態檢查與 MCP 整合均已通過。這些結果屬於離線驗證，
不代表所有輸出都已完成 WinProLadder GUI 匯入或實體 PLC 驗證。
