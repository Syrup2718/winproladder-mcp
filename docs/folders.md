# 專案目錄

[文件索引](README.md) · [功能清單](../FEATURES.md)

## 儲存庫內容

| 位置 | 用途 |
| --- | --- |
| `src/winproladder_mcp/` | MCP、模型、編解碼與驗證服務；見[架構](development.md) |
| [tests](../tests/README.md) | 自動測試、缺陷重現與人工匯入基準 |
| [samples](../samples/README.md) | 原始 `.ldr` 匯出與對照截圖 |
| [examples](../examples/README.md) | Ladder IR 範例與樣本解碼結果 |
| [scripts](../scripts/README.md) | 生成、連線及資料夾盤點工具 |
| [docs](README.md) | 使用、參考、開發與研究文件 |
| `pyproject.toml`、`uv.lock` | 套件設定與鎖定依賴 |
| `.winproladder-policy.json` | 工作區生成政策 |

## 本機資料

以下目錄不隨 Git 發布，也不是安裝後必然存在的內容。

| 位置 | 用途 |
| --- | --- |
| `artifacts/` | 生成的 `.ldr`、設計紀錄與驗證報告 |
| `tmp/` | 手冊擷取、研究與隔離驗證暫存 |
| `dist/` | 明確執行打包後的安裝包 |
| `.venv/`、工具快取 | 可由環境設定重建的本機依賴 |
| `.codex/config.toml` | 本機 MCP client 設定 |

使用者匯入檔可放入自行建立的 `inputs/`；提交變更前檢查 Git 狀態，避免將私有工程或本機設定加入版本控制。

本機生成產物在研究文件中僅以路徑文字記錄；GitHub 使用者應從[樣本](../samples/README.md)、[IR 範例](../examples/README.md)及測試重現。歷史整理事件見[文件索引](README.md)。
