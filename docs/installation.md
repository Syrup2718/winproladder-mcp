# 跨平台安裝

[首頁](../README.md) · [文件索引](README.md)

## 快速安裝

下載原始碼 ZIP 並解壓，或使用 Git clone。在解壓後有 `pyproject.toml` 的資料夾開啟終端機。

Windows PowerShell：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
```

macOS / Linux：

```sh
sh install.sh
```

腳本使用現有 uv；若找不到，從 Astral 官方下載 uv 至 `.install/uv`，不修改 shell profile 或系統 PATH。uv 會使用相容的 Python 3.12，必要時自動下載，並依 `uv.lock` 安裝正式依賴至 `.install/venv`，不安裝開發工具。此流程不需要 Git、預先安裝 Python、管理員權限或 sudo。來源目錄必須可寫入。

安裝後自動執行真正的 stdio MCP 自我檢查：連線、工具清單、需求產檔、驗收、SHA-256 及二進位下載。任何一步失敗都回傳非零退出碼；只有成功後才產生 client 設定。檢查產物放在暫存工作區，不覆蓋使用者的 `.ldr`。

首次安裝需網路連線到 Astral、Python 下載來源與套件索引；macOS/Linux 須具備 `sh` 與 `curl` 或 `wget`。不宣稱離線首次安裝或所有作業系統、CPU 均可用。Python/uv 的實際平台限制見 [uv 安裝文件](https://docs.astral.sh/uv/getting-started/installation/)與 [Python 管理文件](https://docs.astral.sh/uv/guides/install-python/)。腳本使用的本地安裝選項見 [uv installer options](https://docs.astral.sh/uv/reference/installer/)。

## 連接 MCP client

安裝完成會顯示兩個檔案：

- `.install/mcp-config.json`：使用 `mcpServers` 格式的 client。
- `.install/mcp-config.toml`：使用 `mcp_servers` 格式的 client。

選擇一種格式，將其中的 `winproladder` 項目合併到 client 設定，再重新連線。不要整份覆蓋已有其他 MCP 的設定。安裝器只輸出獨立設定片段，不直接修改任何 client 設定。

設定使用安裝環境 Python 的絕對路徑，因此 GUI client 不必繼承終端機 PATH，也不必啟用虛擬環境。請保留來源目錄及 `.install`。設定含本機路徑，不適合直接交給另一台電腦使用。

## 工作資料夾

預設以原始碼目錄為工作資料夾，輸出位於 `artifacts/`。可指定另一個路徑，包含空格或中文；不存在時自動建立。

Windows：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -Workspace "C:\Ladder Work"
```

macOS / Linux：

```sh
sh install.sh "$HOME/Ladder Work"
```

相對路徑以呼叫終端機的目前目錄為準。新工作區會建立 `.winproladder-policy.json`，啟用 `forbid_m_to_m` 與 `allow_function_m_to_m`。既有政策原樣保留，若格式錯誤則明確報錯，不自行放寬規則。

## 平台與驗證範圍

| 功能 | Windows | macOS / Linux |
| --- | --- | --- |
| MCP 服務、讀檔、產檔與內建離線模型 | 目標支援 | 目標支援 |
| 快速安裝腳本 | `install.ps1` | `install.sh` |
| WinProLadder GUI 匯入 | 另裝 WinProLadder | 將檔案交給 Windows 電腦或 VM |
| 實體 PLC 驗證 | 需要另外安排 | 需要另外安排 |

已加入 Windows、macOS、Ubuntu 的 CI 工作流程：完整測試、靜態檢查、安裝腳本及 MCP 自我檢查。本次本機實測為 Windows；其他平台必須以 CI 實際執行結果為準，新增工作流程不代表已在其他系統通過。CI 使用預裝 uv；Windows 首次下載 uv 的分支已在本機另行驗證，macOS/Linux 下載分支尚待實測。

## 更新、搬移與移除

更新原始碼前保留本機修改，更新後重新執行相同安裝命令（保留原本的工作資料夾參數）。重跑會更新鎖定依賴、重新檢查並重寫兩個安裝器產生的設定片段；不清除 `.ldr`、工作區政策或 client 設定。重新連接 client。

搬動目錄或換電腦時，不要沿用舊 `.install/venv`。移除搬過去的該虛擬環境後重新安裝，再更新 client 的絕對路徑。

移除時，先刪除 client 中的 `winproladder` 設定，再刪除本專案的 `.install`。自行保留工作區、政策和產物。uv 下載的共用 Python 與快取可能留在使用者資料夾，安裝器不會刪除其他工具可能共用的資料。

## 手動方式與疑難排解

已安裝 uv 的開發者也可使用：

```sh
uv sync --locked --python 3.12
uv run python -m winproladder_mcp.setup check
uv run python -m winproladder_mcp.setup config --format json
```

| 問題 | 處理 |
| --- | --- |
| 網路、Proxy 或憑證錯誤 | 設定組織要求的代理與受信任憑證後重跑；不要關閉 TLS 驗證。 |
| 公司政策禁止 PowerShell 腳本 | 由管理者確認允許方式，或使用核准的 uv 執行手動命令。上方 Bypass 僅針對該次程序，不更改永久設定。 |
| 找不到 uv、Python 或平台不相容 | 保留完整錯誤訊息並查閱 uv 官方平台說明；舊系統或特殊 CPU 不保證支援。 |
| `--locked` 失敗 | 確認 `pyproject.toml` 與 `uv.lock` 來自同一份原始碼；不要為了安裝直接刪除鎖檔。 |
| 檢查通過但 client 無法啟動 | 確認使用新產生的設定、絕對路徑仍存在，並重啟連線。 |
| Windows 終端機中文顯示亂碼 | 設定檔使用 UTF-8；以編輯器查看實際路徑，勿直接複製亂碼。 |

## 減少 AI 上下文用量

新產生的 client 設定預設帶 `--compact-responses`。既有使用者可重新執行安裝，將新設定合併到 client 並重新連線；或直接把這個參數加進既有 server args。

- 能力與設計指南預設回傳摘要，不重送整份 Ladder schema；需要指令細節時呼叫對應工具並傳 `detail=true`。
- 產檔回覆省略重複的 design、design_summary、network_notes、symbols；完整高階設計仍保存在 `.ldr.design.json`。驗收結果、警告、I/O、時基、SHA-256 及下載連結保留。
- 將 acceptance 與產檔放在同一次請求，避免再對同一份程式做相同模擬。需要二進位交付時才下載，不要把 base64 放進聊天文字。
- 原始 server 命令未指定該參數時維持完整回覆。診斷低階產檔的完整 metadata 可移除該參數並重新連線。

此模式減少工具回覆的文字量，不縮減工具輸入 schema、不跳過驗收。實際 token／費用差異取決於模型與 client；部分 client 會同時傳入文字和 structuredContent，因此保留兩者以維持相容性，並同步精簡兩者。
