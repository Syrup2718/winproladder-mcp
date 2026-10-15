# 快速開始

[首頁](../README.md) · [文件索引](README.md) · [功能清單](../FEATURES.md)

本指南以 Windows PowerShell 與原始碼安裝為例。需要 Git、uv，以及支援本機 stdio MCP 的 client。Python 版本由專案設定選擇。

## 1. 安裝與自我檢查

```powershell
git clone https://github.com/Syrup2718/winproladder-mcp.git
cd winproladder-mcp
uv sync --locked
uv run python -m winproladder_mcp.setup check
```

看到 `PASS` 表示暫存工作目錄中的 MCP 連線、需求生成、模型驗收及下載檢查通過。這不是 GUI 匯入或實體 PLC 驗證。若使用 GitHub ZIP，解壓縮後從 `uv sync --locked` 開始。

## 2. 設定 MCP client

```powershell
uv run python -m winproladder_mcp.setup config --format json
```

此命令只列印設定，不修改設定檔。將輸出的 `mcpServers.winproladder` 合併至 client 的 MCP 設定，保留原有 server，再重新建立連線。若 client 使用 TOML，可執行：

```powershell
uv run python -m winproladder_mcp.setup config --format codex
```

設定包含 Python 與工作目錄的絕對路徑，搬動專案後需重新產生。Client 會啟動伺服器，不必另外開啟 server 終端。用 `get_capabilities` 確認實際載入的能力與工作區政策。

## 3. 產生第一個檔案

向 Agent 提出：

> 使用 WinProLadder MCP，X0 啟動馬達 Y0，放開 X0 後保持。X1=1 時停止，啟停同時成立時停止優先。請產生 motor.ldr，驗證啟動、保持、停止及同時按下的行為，交付檔案與 I/O 表。

交付內容：

| 項目 | 用途 |
| --- | --- |
| `artifacts/motor.ldr` | 二進位階梯圖資源 |
| `artifacts/motor.ldr.design.json` | 高階配方的參數、I/O、假設與雜湊 |
| MCP 回應 | 檔案資源 URI、CRC／解碼與可用的驗收結果 |

Client 無法存取 server 本機路徑時，使用 `get_ldr_artifact` 或 `resources/read` 取得原始二進位資源。MCP URI 不是 HTTPS 下載網址；詳見[Agent 指南](agent-guide.md)。重做時使用 `motor_v2.ldr` 等新檔名。

## 4. 匯入 WinProLadder

在目標工程內使用 **Import Ladder Diagram** 選取 `.ldr`。預設檔頭為已取樣的 FBs-20MC；其他樣本檔頭不代表所有機型、指令與工程設定均相容。依實際工程核對機型、I/O 與計時設定。

WinProLadder 位於 VM 時，可自行將輸出複製至已設定的共用資料夾。也可將 MCP root 指向該資料夾，例如：

```powershell
uv run python -m winproladder_mcp.setup config --format json --root C:\LadderWork
```

`C:\LadderWork` 是示例，必須先建立並視需要設定 VM 分享。檔案將輸出至該 root 的 `artifacts/`。`--output-dir` 必須位於 root 內。

工作區政策由 root 下的 `.winproladder-policy.json` 載入。更換 root 時應一併保留所需政策，不能藉由換目錄繞過生成限制。編譯與下載本身不需要 VM。

## 更新原始碼

先保留本機修改，再更新來源並執行：

```powershell
uv sync --locked
uv run python -m winproladder_mcp.setup check
```

重新連接 MCP，讓 client 載入更新後的程序。不要將歷史安裝包的版本與目前原始碼功能混用；安裝包是否提供應以實際發布資產為準，本指南不假設已發布至 PyPI。

## 常見問題

| 現象 | 處理方式 |
| --- | --- |
| 找不到工具 | 執行 `check`，核對 client 的 command／args，重新連線。 |
| 搬動目錄後無法啟動 | 重建環境並重新產生設定。 |
| Windows 阻擋命令啟動器 | 使用本指南的 `python -m winproladder_mcp.setup` 命令。 |
| 同名檔案已存在 | 使用新檔名；工具不覆蓋既有輸出。 |
| 無法讀取既有檔案 | 將 `.ldr` 放入 root，例如 `inputs/motor.ldr`。 |
| I/O 契約不符 | 核對需求中的完整 X/Y 清單，包含 word I/O 所涵蓋的位元。 |
| 需求驗收失敗 | 核對有效極性、優先權、掃描順序、時間單位與支援形式。 |
| 指令無法生成或模擬 | 查閱[功能清單](../FEATURES.md)；編碼與模擬是不同能力。 |

如需回報問題，請依[貢獻指南](../CONTRIBUTING.md)提供最小重現與驗證層級。
