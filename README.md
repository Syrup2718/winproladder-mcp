# WinProLadder MCP

讓 AI 根據控制需求，產生可匯入 WinProLadder 的 `.ldr` 檔案。

支援控制配方、順序控制、自訂階梯圖，以及既有檔案的讀取、分析與修改。產檔不需要 VM 或 PLC。

[功能清單](FEATURES.md) · [快速開始](docs/quickstart.md) · [文件](docs/README.md)

## 安裝

準備 Git、uv，在 PowerShell 執行：

```powershell
git clone https://github.com/Syrup2718/winproladder-mcp.git
cd winproladder-mcp
uv sync --locked
uv run python -m winproladder_mcp.setup check
uv run python -m winproladder_mcp.setup config --format json
```

將輸出的設定加入 MCP client，重新連線。需要 TOML 格式時改用 `--format codex`。

## 使用

向 AI 提出需求，例如：

> X0 啟動、X1=1 停止、Y0 自保持，停止優先。請驗證後產生 motor.ldr。

檔案預設存於 `artifacts/`，也可透過 MCP 下載。在 WinProLadder 使用 **Import Ladder Diagram** 匯入。

## 注意事項

- X/Y 由需求指定，不自動新增 I/O 或外部時脈。
- 各指令的支援範圍不同，詳見[功能清單](FEATURES.md)。
- 離線測試不等於 GUI 或實體 PLC 驗證。

版本 **0.11.0**；後續更新見[變更紀錄](docs/unreleased.md)。開發與提交方式見[貢獻指南](CONTRIBUTING.md)。本專案並非 FATEK 官方產品。
