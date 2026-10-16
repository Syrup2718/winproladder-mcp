# 快速開始

[首頁](../README.md) · [文件索引](README.md)

## 安裝與連線

依 [README](../README.md) 執行安裝腳本。看到 `PASS` 和 `Setup complete` 後，將 `.install/mcp-config.json` 的 `mcpServers.winproladder` 加入 client 設定並重新連線；需要 TOML 的 client 使用 `.install/mcp-config.toml`。

設定使用安裝環境的絕對路徑，不需要啟用 venv 或修改 PATH。詳細步驟、指定工作資料夾及手動安裝見[安裝指南](installation.md)。

## 產檔

向 Agent 說：

> X0 啟動 Y0，放開 X0 後保持。X1=1 時停止，停止優先。請驗證並交付 motor.ldr。

- `.ldr` 預設存於 `artifacts/`。
- 高階配方另附 `.ldr.design.json`，記錄參數與 I/O。
- 無法存取本機路徑時，用 `get_ldr_artifact` 下載。
- 同名檔案不覆蓋，重做時換新檔名。

在 WinProLadder 使用 **Import Ladder Diagram** 匯入。預設檔頭為 FBs-20MC；匯入前核對工程機型、I/O 與計時設定。測試通過不代表已經 GUI 或實機驗證。

## VM 與工作目錄

將輸出複製到 VM 共用資料夾即可。若要把工作目錄直接放在共用資料夾，可在安裝時指定 `-Workspace`（Windows）或第一個參數（macOS/Linux），詳見[安裝指南](installation.md)。新的工作目錄會建立嚴格 relay 政策；既有政策保持原樣。

## 更新

保留本機修改，更新原始碼後重新執行同一安裝命令，再重新連接 MCP。若搬動專案，需刪除搬過去的 `.install/venv`，重新執行安裝並更新 client 設定；虛擬環境不能直接跨電腦複製。

## 常見問題

| 問題 | 處理 |
| --- | --- |
| 找不到工具 | 執行 `check`，核對設定並重新連線。 |
| 無法讀取檔案 | 將 `.ldr` 放入 root，例如 `inputs/motor.ldr`。 |
| I/O 或驗收失敗 | 核對位址、極性、優先權與時間單位。 |
| 指令不能生成或模擬 | 查閱[功能清單](../FEATURES.md)，兩者支援範圍不同。 |

工具操作見 [Agent 指南](agent-guide.md)；回報問題見[貢獻指南](../CONTRIBUTING.md)。
