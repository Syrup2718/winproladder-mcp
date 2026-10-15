# 快速開始

[首頁](../README.md) · [文件索引](README.md)

## 安裝與連線

依 [README](../README.md) 安裝。`check` 顯示 `PASS` 後，產生 client 設定：

```powershell
uv run python -m winproladder_mcp.setup config --format json
```

將 `mcpServers.winproladder` 加入 client 設定並重新連線。此命令只列印設定，不修改檔案；TOML 格式使用 `--format codex`。

## 產檔

向 Agent 說：

> X0 啟動 Y0，放開 X0 後保持。X1=1 時停止，停止優先。請驗證並交付 motor.ldr。

- `.ldr` 預設存於 `artifacts/`。
- 高階配方另附 `.ldr.design.json`，記錄參數與 I/O。
- 無法存取本機路徑時，用 `get_ldr_artifact` 下載。
- 同名檔案不覆蓋，重做時換新檔名。

在 WinProLadder 使用 **Import Ladder Diagram** 匯入。預設檔頭為 FBs-20MC；匯入前核對工程機型、I/O 與計時設定。測試通過不代表已經 GUI 或實機驗證。

## VM 與工作目錄

將輸出複製到 VM 共用資料夾即可。也可指定已存在的共用目錄：

```powershell
uv run python -m winproladder_mcp.setup config --format json --root C:\LadderWork
```

`C:\LadderWork` 為示例，請換成實際路徑。輸出位於其 `artifacts/`；更換 root 時一併保留所需的 `.winproladder-policy.json`。

## 更新

保留本機修改，更新原始碼後執行：

```powershell
uv sync --locked
uv run python -m winproladder_mcp.setup check
```

重新連接 MCP。若搬動專案，需重新產生 client 設定。

## 常見問題

| 問題 | 處理 |
| --- | --- |
| 找不到工具 | 執行 `check`，核對設定並重新連線。 |
| 無法讀取檔案 | 將 `.ldr` 放入 root，例如 `inputs/motor.ldr`。 |
| I/O 或驗收失敗 | 核對位址、極性、優先權與時間單位。 |
| 指令不能生成或模擬 | 查閱[功能清單](../FEATURES.md)，兩者支援範圍不同。 |

工具操作見 [Agent 指南](agent-guide.md)；回報問題見[貢獻指南](../CONTRIBUTING.md)。
