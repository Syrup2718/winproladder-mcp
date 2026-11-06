# 變更紀錄

**繁體中文** | [English](CHANGELOG.en.md)

本文件只保留對使用者有影響的版本變更。細部修復與編碼證據由 Git 歷史及自動測試追蹤。

## 未發行

- compact 回應改為程式預設，並在能力、設計與 artifact 回應標示 `response_mode`；
  可用 `--full-responses` 明確要求完整內容。
- 驗證證據拆分為本次 artifact、既有 payload anchor 與實體 PLC 三個層級，移除容易
  誤讀的泛稱 `import_verified`。
- 產檔錯誤提供穩定錯誤碼與 `written=false`；同名檔案另提供建議名稱。
- 高階控制回報只列出該 recipe 實際參與編譯的欄位與假設；無 timer 時不再回傳
  timer 設定警語。
- 高階產生工具接受 `target_profile`；未指定時在精簡摘要前置顯示假設 profile，timer
  程式另標示時間基準尚未驗證。
- 將使用者提供的 FBs-32MC 回存樣本版面整合至 PDW 型號白名單，並對應既有
  `FBs-32MC-test30` Ladder profile；新增解析、重建及完整專案產生回歸測試。

## 1.1.0 — 2026-11-05

- 新增實驗性 `.pdw` 檢查、範本生成與二進位下載，共提供 26 項 MCP 工具。
- 新增共用 Ladder 編譯器的可變長度 PDW 產生器，支援 FBs-20MC／40MC／60MC 本機範本。
- 支援主程式分區、區域／網路註解及 CP950／Big5 元件註解與說明。
- 支援保留、選用、排序及重複使用本機樣本已有的擴充模組紀錄；未知參數保持原樣。
- 寫檔前檢查來源、lowered program 與解碼後的實際輸出，保留 I/O、政策及 acceptance 檢查。
- 私人範本由使用者本機提供；repository 不包含私人 PDW 樣本或遮罩。
- 新增英文 README、英文功能總覽、英文使用文件及中英共用的 FUNC 支援表。
- 調整一些文字排版。
- 工作區稽核摘要分開顯示原始內容與本機產物的失效連結。
- 更新鎖定的 `certifi` 與 `PyJWT` 傳遞依賴，以修正已知安全公告。
- 將公開 MCP 介面由 22 項精簡為 19 項：移除已被高階產生器取代的 `create_ldr`、`create_start_stop`，並將指令族群列表合併到 `get_instruction_capabilities`。

PDW 仍為實驗功能：24MC／32MC 已有樣本但尚未整合；FUNC199 僅不透明辨識，
流程控制生成、未知模組參數初始化及硬體相容性驗證尚未提供。
特定輸出已有使用者 GUI 開啟回報，不能推及所有新輸出；未完成實體 PLC 驗證。

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
