# WinProLadder MCP

將控制需求轉換為可匯入 WinProLadder 的 `.ldr` 階梯圖資源檔。

WinProLadder MCP 是本機執行的 Model Context Protocol（MCP）伺服器。連接的 AI Agent 負責理解需求；本專案提供結構化設計、指令編碼、I/O 檢查、支援範圍內的模擬與二進位檔案交付。產檔不需要啟動 WinProLadder、VM 或連接 PLC。

[快速開始](docs/quickstart.md) · [功能清單](FEATURES.md) · [文件索引](docs/README.md) · [貢獻指南](CONTRIBUTING.md)

## 工作流程

```text
控制需求與指定 I/O → AI Agent → MCP 驗證與編譯 → .ldr 檔案 → WinProLadder 匯入
```

- 11 種控制配方、自訂階梯圖與最多 16 步順序控制。
- 已取樣的計時、算術、比較、浮點、資料搬移及原生功能指令。
- 讀取、分析、比較與修改既有 `.ldr`，保留可辨識範圍以外的原始資料供分析。
- 生成時檢查指定的 X/Y 契約、完整暫存器跨度與工作區政策。
- 透過 MCP 資源或下載工具交付原始 bytes、SHA-256 與驗證結果。

本專案不是完整 PLC 開發環境。各指令的可用運算元、編碼形式及模擬能力不同，請以[功能清單](FEATURES.md)與執行中伺服器的 `get_capabilities` 為準。

## 安裝與連接

主要開發環境為 Windows／PowerShell，使用 Python 3.12 與 uv。先安裝 Git 和 uv，再執行：

```powershell
git clone https://github.com/Syrup2718/winproladder-mcp.git
cd winproladder-mcp
uv sync --locked
uv run python -m winproladder_mcp.setup check
uv run python -m winproladder_mcp.setup config --format json
```

`check` 會在暫存目錄測試實際 MCP 連線、需求產檔、驗收與下載。最後一行只輸出設定；將 `mcpServers.winproladder` 合併至支援本機 stdio 的 MCP client 設定，再重新連線。需要 TOML 設定時可改用 `--format codex`。

Client 會啟動 server，不必另開常駐終端。MCP 本身不需要 API key；AI Agent 的模型與帳號由所用 client 管理。完整連線與更新步驟見[快速開始](docs/quickstart.md)。

## 第一個需求

連線後，向 Agent 提出：

> 使用 WinProLadder MCP 建立 X0 啟動、X1=1 停止、Y0 自保持電路。停止優先，放開啟動後繼續運轉。請驗證啟動、保持及停止行為，交付 motor.ldr 與 I/O 表。

輸出預設存放於工作目錄的 `artifacts/`。高階配方另附 `.ldr.design.json` 設計紀錄。若 client 無法存取 server 的路徑，可使用 `get_ldr_artifact` 下載二進位資源。

在 WinProLadder 工程內使用 **Import Ladder Diagram** 匯入 `.ldr`；它不是完整工程檔。相同檔名不會被覆蓋。

## 支援狀態

原始碼版本為 **0.11.0**，後續功能以[未發版變更](docs/unreleased.md)記錄。歷史版本內容見[版本紀錄](docs/release-0.11.0.md)。本儲存庫不包含本機安裝包或生成產物；依上方方式使用原始碼即可取得目前實作。

- X/Y 必須來自需求；不自動新增實體 I/O 或外部時脈。
- 原生功能可使用 M 控制及 M 狀態，但禁止無意義的 M→M 複製與中繼鏈。
- FUN60 任意字串、FUN65／66 通用標籤及跳躍、FUN67 生成仍有明確限制。
- 離線編碼、模型模擬、GUI 匯入與實體 PLC 驗證分開記錄；測試通過不代表全部指令或任意工程均已實機驗證。

詳見[功能清單](FEATURES.md)、[驗證範圍](docs/verification.md)與[指令研究紀錄](docs/README.md)。

## 文件與開發

| 入口 | 內容 |
| --- | --- |
| [快速開始](docs/quickstart.md) | 安裝、連線、第一個檔案、更新與問題排除 |
| [Agent 指南](docs/agent-guide.md) | 19 個工具、I/O 契約與交付流程 |
| [參數參考](docs/reference.md) | 配方、IR、時間單位與模擬範圍 |
| [開發指南](docs/development.md) | 架構、測試及格式擴充 |
| [貢獻指南](CONTRIBUTING.md) | 問題回報、樣本與 Pull Request |
| [文件索引](docs/README.md) | 指令證據、格式及歷史紀錄 |

本專案以實際匯出樣本研究檔案格式，並非 FATEK 官方產品。原廠手冊與 WinProLadder 軟體不隨儲存庫提供。
