# 資料夾導覽

## 常用入口

- [交付檔與驗證紀錄](../artifacts/README.md)：各次生成的 .ldr、設計資料與驗證 JSON。
- [安裝包](../dist/README.md)：最後打包版本 v0.10.0；舊版按版本放在 dist/archive/。只有使用者明確要求才打包或更新版本。
- [功能文件索引](README.md)：功能範圍、操作流程與編碼研究。

## 各目錄用途

| 目錄 | 用途 |
| --- | --- |
| src/winproladder_mcp/ | 正式 MCP 程式碼 |
| tests/、tests/fixtures/ | 測試與基準檔 |
| samples/、samples/screenshots/ | 使用者提供的原始 .ldr 與截圖，保留原名 |
| examples/ | 可重用 JSON 範例 |
| scripts/ | 維護用生成、檢查入口 |
| docs/ | 使用與技術文件 |
| artifacts/ | 生成檔與報告；保留路徑以維持既有 MCP 資源及下載連結 |
| dist/ | 目前版安裝包 |
| dist/archive/<版本>/ | 歷史 wheel 與原始碼安裝包 |
| tmp/research-history/2026-10-06/ | 先前歸檔的一次性研究與環境紀錄 |
| tmp/research-history/test11/ | test11 實作歷史與套件驗證腳本 |
| tmp/research-history/cache-2026-10-06/ | 歸檔保存的測試／型別／格式檢查快取 |
| tmp/mypy-pure/ | 本機型別檢查工具依賴 |
| tmp/wheel-v*/ | 各版隔離安裝驗證環境，保留原位避免絕對路徑失效 |
| tmp/pdfs/ | 手冊研究暫存 |
| .venv/ | 開發環境 |
| .codex/ | 本機 MCP 連線設定 |

2026-10-06 整理：檔案移動前後皆核對 SHA-256；移動清單保存於 tmp/research-history/2026-10-06/organization-manifest.json。沒有刪除原始資料、修改控制邏輯或搬動 VM 共用目錄。

歷史研究腳本保留原內容作為紀錄，可能依賴當時的目錄、套件或版本，不作為目前可直接執行的入口。正式操作請使用 scripts/ 與 MCP 工具。artifacts/、dist/、tmp/ 為本機資料，不隨 Git 發布。

本次補充整理：v0.9.0 已歸檔至 dist/archive/0.9.0/；test11 研究資料與舊快取移入 research-history，未刪除檔案。36 個檔案移動後均核對 SHA-256，清單為 tmp/research-history/organization-2026-10-06-02.json。交付索引已重新掃描完整目錄，包含所有 test11 與倒數相關檔案。既有 .ldr、原始樣本與 VM 共享資料位置不變。
