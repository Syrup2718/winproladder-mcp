# 從需求取得第一個 .ldr

## 連接 MCP

依 [README](../README.md) 安裝並執行 `uv run winproladder-setup check`。出現 `PASS` 即表示 MCP 子程序、需求生成、動作驗收及檔案下載皆通過。

`uv run winproladder-setup config --format codex` 只列印設定，不修改任何設定檔。將完整的 `[mcp_servers.winproladder]` 區段合併至 Codex 設定後重新連線。其他支援本機 stdio 的 MCP client 使用 `--format json`，採用輸出的 `command` 與 `args`；不需另開終端執行 server。

## 提出需求並取得檔案

可直接對連接 MCP 的 Agent 說：

> 使用 WinProLadder MCP，X0 啟動馬達 Y0，放開 X0 後保持。X1 為 1 時停止，啟停同時成立時停止優先。請產生 motor.ldr，驗證啟動、保持、停止及同時按下的行為，並交付檔案與 I/O 表。

Agent 會讀取設計指南，選擇控制配方並呼叫生成工具。交付結果包含：

- `motor.ldr`：實際二進位階梯圖資源檔，預設在工作目錄的 `artifacts/`。
- `motor.ldr.design.json`：高階配方的設計紀錄，包含 I/O、預設參數、假設及雜湊。
- 驗證結果：CRC／解碼檢查，以及有提供驗收案例時的 `acceptance` 與 `compiled_acceptance`。

若 Agent 只提供 server 路徑而 client 無法存取，讓 Agent 呼叫 `get_ldr_artifact`，使用回應的 embedded binary resource 保存 `.ldr`。也可直接讀取生成回應提供的 MCP resource URI；這是 MCP 檔案資源，並非一般 HTTPS 下載網址。Agent 端的詳細交付方法見 [操作指南](agent-guide.md)。

重做相同需求時使用 `motor_v2.ldr` 等新檔名。檔案不會被覆蓋，驗收失敗也不會留下新的 `.ldr`。

## WinProLadder 與 VM

`.ldr` 是階梯圖資源匯入檔；在 WinProLadder 工程中執行 **Import Ladder Diagram**，選取交付檔案。目標格式為 WinProLadder v3.28 / FBs-20MC。

如果 WinProLadder 位於 VM，可把 `.ldr` 複製到 VMware 共用目錄，或將 MCP 工作目錄直接設為共用目錄：

```powershell
uv run winproladder-setup config --format codex --root C:\VM_Share
```

合併新設定並重新連線後，檔案會生成於 `C:\VM_Share\artifacts\`。這台開發 VM 的實際共享設定為 host `C:\VM_Share`、guest share name `VM_Share`；其他電腦請換成其實際路徑。若使用 `C:\VM\_Share`，須先確認該目錄存在且已由 VM 分享。`--root` 必須存在，`--output-dir` 如有指定則必須位於 root 內。

編譯與下載不需要 VM。每個新輸出是否已經 GUI 匯入，應依該檔案的驗證紀錄判斷；模型測試不能取代實際 PLC 執行驗證。

## 使用 wheel 安裝包

取得本專案產出的 `winproladder_mcp-0.5.0-py3-none-any.whl` 後，可不保留原始碼。以下以將 wheel 放在 `C:\LadderWork` 為例：

```powershell
cd C:\LadderWork
uv venv --python 3.12 .venv
uv pip install --python .venv\Scripts\python.exe .\winproladder_mcp-0.5.0-py3-none-any.whl
.\.venv\Scripts\winproladder-setup.exe check
.\.venv\Scripts\winproladder-setup.exe config --format codex --root C:\LadderWork
```

將最後一行輸出的設定合併到 client 設定，保留此虛擬環境與工作目錄。首次安裝需要取得 Python 與套件相依項；完成後 MCP 產檔不呼叫外部 API。此流程不假設套件已發布到 PyPI。

## 常見問題

| 現象 | 處理方式 |
| --- | --- |
| 找不到 MCP 工具 | 重跑 `check`；確認 client 使用完整的 `command`／`args`，重新連線。 |
| 搬動目錄後無法啟動 | 在新位置重新安裝環境，重新執行 `config`，更新 client 設定。 |
| 已有同名檔案 | 使用新檔名，例如 `motor_v2.ldr`。 |
| 無法讀取現有 `.ldr` | 先放入 `--root` 內，再用相對路徑或該目錄內的絕對路徑。 |
| 驗收失敗 | 由 Agent 檢查輸入有效極性、同時命令優先權、掃描順序與時間單位；修正後再生成。 |
| 需求包含未支援指令 | 由 Agent 查閱 `get_capabilities`；不可將未實作功能假裝成可用輸出。 |

支援的配方、IR 與時序限制見 [功能參考](reference.md)。
