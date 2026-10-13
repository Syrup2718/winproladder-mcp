# 資料夾導覽

| 位置 | 用途與入口 |
| --- | --- |
| `src/winproladder_mcp/` | 正式程式；模組分工見 [開發指南](development.md) |
| `tests/`、`tests/fixtures/` | [測試分類](../tests/README.md)與不可覆寫的基準檔 |
| `samples/`、`samples/screenshots/` | [原始樣本](../samples/README.md)，保留使用者提供的檔名與內容 |
| `examples/` | [可重用 JSON 範例](../examples/README.md) |
| `scripts/` | [維護入口](../scripts/README.md)；已被推翻的猜測歸入 `scripts/research/` |
| `docs/` | [使用、技術與歷史文件索引](README.md) |
| `artifacts/` | [生成檔與驗證報告](../artifacts/README.md)，保留既有下載與 MCP 資源路徑 |
| `dist/`、`dist/archive/` | [最後安裝包與歷史版本](../dist/README.md)，只有明確要求才重新打包 |
| `tmp/research-history/` | 一次性研究，按日期或主題歸檔 |
| `tmp/organization-2026-10-08/` | 2026-10-08 整理前的雜湊、移動清單及整理後核對結果 |
| `tmp/mypy-pure/`、`tmp/wheel-v*/` | 本機工具與隔離驗證環境，保留原位避免環境內絕對路徑失效 |
| `tmp/pdfs/` | 手冊研究暫存 |
| `.venv/`、`.codex/` | 開發環境與本機 MCP 連線設定 |

## 整理紀錄

2026-10-08：將 test12～15、comparison-positions、manual-rtc 共六組研究資料移至 `tmp/research-history/`；歷史 FUN15／16 猜測腳本移至 `scripts/research/`，並修正其專案根目錄定位。每次移動均核對檔案雜湊。正式指令常數與能力回報分別集中到 `instruction_catalog.py`、`capabilities.py`，原有匯入介面保留。

之前的整理紀錄仍在 `tmp/research-history/2026-10-06/organization-manifest.json` 與 `tmp/research-history/organization-2026-10-06-02.json`。test11 研究保存在該歷史目錄；可重建的舊檢查快取仍保留，2026-10-13刪除動作被自動審核拒絕。

歷史腳本可能依賴當時的路徑、套件或輸出，只作證據保存；目前操作請使用正式 MCP 工具及 `scripts/` 維護入口。`artifacts/`、`dist/`、`tmp/` 是本機資料，不隨 Git 發布。

2026-10-13：test16～20 與版本研究歸入 `tmp/research-history/`；21 個移動檔案逐一比對 SHA-256。盤點與移動紀錄在 `tmp/organization-2026-10-13/`，詳見 [本次檢查報告](folder-audit-2026-10-13.md)。
