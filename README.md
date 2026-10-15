# WinProLadder MCP

使用者向 Agent 提出控制需求，Agent 呼叫本 MCP，取得真正的 WinProLadder `.ldr` 二進位檔案。自然語言由連接的 Agent 解讀；MCP 提供配方、編譯、邏輯簡化、掃描驗收與檔案下載，不需要使用者手寫 JSON。

已取樣檔頭：FBs-20MC、FBs-24MA、FBs-32MA、FBs-40MA、FBs-44MN、FBs-60MC、FBn-26MC。本專案不連接實體 PLC，也不涵蓋完整 FATEK 指令集。

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

將產生的設定區段合併至使用者的 `~/.codex/config.toml`，或已信任專案的 `.codex/config.toml`；其他 stdio MCP client 使用 `--format json`。保留既有 server 設定，重新建立 MCP 連線後生效。設定含本機絕對路徑，搬動專案後需重新產生。Codex 設定方式見 [OpenAI 官方文件](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)。

`check` 在暫存目錄測試真實 MCP 連線、需求生成、動作驗收與二進位下載。Client 會啟動本機 server，不需另開常駐終端；MCP 本身不需要 API key，也不需要安裝 WinProLadder。

## 使用

> 使用 WinProLadder MCP 建立 X0 啟動、X1=1 停止、Y0 自保持電路。停止優先，放開啟動後繼續運轉。驗證啟動、保持及停止，再交付 motor.ldr 檔案。

生成檔案預設位於 `artifacts/`；回應包含路徑、SHA-256 與 MCP 檔案資源連結。Client 可用 `get_ldr_artifact` 取得原始檔案內容，即使無法直接存取 server 的本機路徑也能交付檔案。高階配方另附 `.ldr.design.json`，記錄 I/O、參數與假設。

在 WinProLadder 使用 Import Ladder Diagram 匯入 `.ldr`。分析現有檔案時，先放到工作目錄內，例如 `inputs/motor.ldr`。所有輸出使用新檔名，不覆蓋既有檔案。VM 共用目錄、安裝包與疑難排解見 [完整入門流程](docs/quickstart.md)。

目前支援布林階梯圖、T/C、11 種控制配方、順序控制，以及已取樣的算術、比較、浮點與 I/O 指令。完整指令按 FUNC 編號列於 [FEATURES](FEATURES.md)，參數與驗證證據由[文件索引](docs/README.md)查閱。

目前原始碼版本為 **0.11.0**，累積功能與驗證範圍見 [0.11.0版本紀錄](docs/release-0.11.0.md)。最後安裝包仍為0.10.0，不包含此次新增功能；使用目前原始碼可取得更新。後續test18～test27功能保持0.11.0版本，見[未發版變更](docs/unreleased.md)；未製作新安裝包。

X/Y 必須由需求明確指定，生成工具強制檢查 `io_contract`，不自動新增輸入、輸出或外部時脈。一般計時使用 T；FUN87～89 積算型計時已支援底層暫存器 PV 形式，尚未整合高階順序產生器與執行模擬，詳見 [計時器核對紀錄](docs/timer-evidence.md)。每次提供 `acceptance` 時，同時驗證需求模型與從生成檔案解碼的模型，失敗即不產檔。GUI 匯入及實體 PLC 執行是另外的驗證層級；未經 GUI 匯入的輸出標為候選檔。

## 文件

- [現有功能總覽](FEATURES.md)：完整 FUNC、19 個 MCP 工具、配方、模擬與限制。
- [資料夾導覽](docs/folders.md)：交付檔、安裝包、原始樣本及研究資料的位置。
- [Agent 操作指南](docs/agent-guide.md)：工具選擇、生成流程、檔案交付。
- [完整入門流程](docs/quickstart.md)：第一次產檔、VM 共用目錄、wheel 安裝。
- [功能與參數](docs/reference.md)：配方、IR、時序模型與限制。
- [開發指南](docs/development.md)：目錄、測試、格式研究與擴充原則。
- [文件索引](docs/README.md)：格式、最佳化與驗證依據。

更新前保留本機修改及 inputs/artifacts；更新程式後執行 `uv sync --locked`、`uv run winproladder-setup check`，重新建立 MCP 連線。
