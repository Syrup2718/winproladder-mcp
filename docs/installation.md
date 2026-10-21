# 安裝指南

[首頁](../README.md) · [快速開始](quickstart.md)

## 系統需求

- Windows、macOS 或 Linux
- 可寫入的專案目錄
- 首次安裝需要網路

安裝腳本會準備 uv、Python 3.12、獨立環境與鎖定依賴；不需要管理員權限，也不修改系統 PATH。

## 自動安裝

Windows PowerShell：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
```

macOS / Linux：

```sh
sh install.sh
```

安裝完成前會執行真實 stdio MCP 自我檢查，包括工具清單、`.ldr` 產生、acceptance、SHA-256、檔案下載及元件註解輸出。

## 連接 MCP client

安裝器會建立兩份設定片段：

- `.install/mcp-config.json`：`mcpServers` 格式
- `.install/mcp-config.toml`：`mcp_servers` 格式

選擇符合 client 的格式，只合併 `winproladder` 項目，不要覆蓋原有設定。設定含本機絕對路徑；移動專案或換電腦後必須重新安裝並更新設定。

## 自訂工作資料夾

預設輸出到專案的 `artifacts/`。也可指定獨立工作資料夾：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -Workspace "C:\Ladder Work"
```

```sh
sh install.sh "$HOME/Ladder Work"
```

新工作區會建立嚴格的 `.winproladder-policy.json`；既有政策不會被覆寫或放寬。

## 手動安裝

已安裝 uv 的開發者可使用：

```sh
uv sync --locked --python 3.12
uv run python -m winproladder_mcp.setup check
uv run python -m winproladder_mcp.setup config --format json
```

## 更新與移除

- 更新原始碼後重新執行相同安裝命令，並重新連接 client。
- 移動專案時不要複製舊 `.install/venv`；在新位置重新安裝。
- 移除時先刪除 client 設定中的 `winproladder`，再刪除 `.install`。使用者產物請自行保留。

## 疑難排解

| 問題 | 處理方式 |
| --- | --- |
| 網路、Proxy 或憑證錯誤 | 使用組織核准的代理與憑證後重試，不要關閉 TLS 驗證 |
| PowerShell 腳本被封鎖 | 依組織政策執行，或改用上方 uv 手動流程 |
| `--locked` 失敗 | 確認 `pyproject.toml` 與 `uv.lock` 來自同一版本 |
| Client 無法啟動 | 確認設定中的絕對路徑仍存在，重新安裝並連線 |
| 中文顯示異常 | 設定檔為 UTF-8；請用支援 UTF-8 的編輯器查看 |

安裝設定預設啟用 `--compact-responses`，只精簡回覆內容，不縮減 schema 或驗證步驟。
