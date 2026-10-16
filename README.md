# WinProLadder MCP

讓 AI 根據控制需求，產生可匯入 WinProLadder 的 `.ldr` 檔案。

支援控制配方、順序控制、自訂階梯圖，以及既有檔案的讀取、分析與修改。產檔不需要 VM 或 PLC。

[功能清單](FEATURES.md) · [快速開始](docs/quickstart.md) · [文件](docs/README.md)

## 安裝

下載本專案 ZIP 並解壓（或 git clone），在資料夾內執行：

**Windows（PowerShell）**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
```

**macOS / Linux（終端機）**

```sh
sh install.sh
```

自動準備 uv、Python 3.12、獨立環境與鎖定依賴，並驗證 MCP 連線及產檔。無須先安裝 Git、Python，也無須管理員權限；首次安裝需要網路。

完成後，將 `.install/mcp-config.json` 的伺服器項目加入 MCP client；需要 TOML 的 client 使用 `.install/mcp-config.toml`，再重新連線。安裝器不會覆蓋 client 的其他設定。

MCP 服務以 Windows、macOS、Linux 為目標；WinProLadder GUI 匯入仍需 Windows。不是所有舊版系統或 CPU 都受支援，詳見[安裝與疑難排解](docs/installation.md)。

## 使用

向 AI 提出需求，例如：

> X0 啟動、X1=1 停止、Y0 自保持，停止優先。請驗證後產生 motor.ldr。

檔案預設存於 `artifacts/`，也可透過 MCP 下載。在 WinProLadder 使用 **Import Ladder Diagram** 匯入。

## 注意事項

- X/Y 由需求指定，不自動新增 I/O 或外部時脈。
- 各指令的支援範圍不同，詳見[功能清單](FEATURES.md)。
- 離線測試不等於 GUI 或實體 PLC 驗證。

版本 **0.11.0**；後續更新見[變更紀錄](docs/unreleased.md)。開發與提交方式見[貢獻指南](CONTRIBUTING.md)。本專案並非 FATEK 官方產品。
