# WinProLadder MCP

將控制需求轉成可匯入 WinProLadder 的 `.ldr` 候選檔案，提供讀取、編輯、邏輯簡化與掃描模擬。自然語言由連接的 Agent 解讀，MCP 負責編譯與檢查。

目標格式：WinProLadder v3.28 / FBs-20MC。本專案不連接實體 PLC，也不涵蓋完整 FATEK 指令集。

## 安裝

準備 Git 與 [uv](https://docs.astral.sh/uv/getting-started/installation/)，在 PowerShell 執行：

```powershell
git clone https://github.com/Syrup2718/winproladder-mcp.git
cd winproladder-mcp
uv sync --locked
uv run winproladder-setup check
uv run winproladder-setup config --format codex
```

也可下載 GitHub ZIP，解壓縮後從 `uv sync --locked` 開始。Python 版本固定為 3.12。

將產生的設定區段合併至 `.codex/config.toml`；其他 stdio MCP client 使用 `--format json`。保留既有 server 設定，重新建立 MCP 連線後生效。設定含本機絕對路徑，搬動專案後需重新產生。

`check` 在暫存目錄測試 MCP 連線與自保持檔案生成。Client 會啟動本機 server，不需另開常駐終端；本工具本身不需要 API key。

## 使用

> 使用 WinProLadder MCP 建立 X0 啟動、X1=1 停止、Y0 自保持電路，輸出 motor.ldr。

生成檔案預設位於 `artifacts/`，使用 WinProLadder 的 Import Ladder Diagram 匯入。分析現有檔案時，先放到專案內，例如 `inputs/motor.ldr`。所有輸出使用新檔名，不覆蓋既有檔案。

支援 11 種控制配方、多控制組合、最多 16 步暫停／續跑流程，以及自訂布林條件、Timer/Counter、暫存器 OR、單層迴圈。生成時自動簡化條件與接圖。

暫停／續跑依賴外部時脈輸入，不是原生保持型計時器。模擬或 CRC 通過不代表 GUI 匯入、PLC 執行或機械安全驗證通過。

## 文件

- [Agent 操作指南](docs/agent-guide.md)：工具選擇、生成流程、檔案交付。
- [功能與參數](docs/reference.md)：配方、IR、時序模型與限制。
- [開發指南](docs/development.md)：目錄、測試、格式研究與擴充原則。
- [文件索引](docs/README.md)：格式、最佳化與驗證依據。

更新前保留本機修改及 inputs/artifacts；更新程式後執行 `uv sync --locked`、`uv run winproladder-setup check`，重新建立 MCP 連線。
