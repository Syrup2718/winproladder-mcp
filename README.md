<div align="center">
  <h1>WinProLadder MCP</h1>
  <p><strong>讓 AI 將控制需求轉成 WinProLadder <code>.ldr</code> 檔案</strong></p>
  <p>也能讀取、分析及安全地修改既有檔案</p>
  <p>
    <a href="https://github.com/Syrup2718/winproladder-mcp/releases/latest"><img alt="Release" src="https://img.shields.io/github/v/release/Syrup2718/winproladder-mcp"></a>
    <a href="LICENSE"><img alt="License" src="https://img.shields.io/github/license/Syrup2718/winproladder-mcp"></a>
    <a href="https://www.python.org/"><img alt="Python" src="https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white"></a>
    <a href="https://github.com/Syrup2718/winproladder-mcp/stargazers">
    <img alt="GitHub Stars" src="https://img.shields.io/github/stars/Syrup2718/winproladder-mcp">
    </a>
    <a href="https://github.com/Syrup2718/winproladder-mcp">
    <img alt="Repo Size" src="https://img.shields.io/github/repo-size/Syrup2718/winproladder-mcp">
    </a>
  </p>
  <p><strong>繁體中文</strong> · <a href="README.en.md">English</a></p>
</div>

<p align="center">
  <a href="docs/quickstart.md">快速開始</a> ·
  <a href="FEATURES.md">功能總覽</a> ·
  <a href="docs/supported-functions.md">FUNC 支援表</a> ·
  <a href="docs/README.md">完整文件</a>
</p>

> [!IMPORTANT]
> 本專案不是 FATEK 官方產品，不會連線或下載程式到 PLC。

## 主要功能

- 產生啟停、自保持、計時、計數、正反轉、星三角與順序控制。
- 支援自訂 Ladder IR，以及多種 FATEK 原生 FUNC 編解碼。
- 產檔前檢查 I/O、元件範圍、重複 writer、工作區政策及實際輸出 bytes。
- 提供有限的離線掃描模型與 acceptance cases。
- 讀取、比較、分析及安全地另存 `.ldr`。
- 依使用者要求另產生 CP950／Big5 元件註解 `.txt`。

完整範圍請看[功能總覽](FEATURES.md)與 [FUNC 支援表](docs/supported-functions.md)。

## 快速安裝

下載原始碼並在專案目錄執行：

### Windows PowerShell

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
```

### macOS / Linux

```sh
sh install.sh
```

安裝完成後，將 `.install/mcp-config.json` 或 `.install/mcp-config.toml` 中的
`winproladder` 設定加   入 MCP client，再重新連線。詳細說明見[安裝指南](docs/installation.md)。

## 使用範例

直接用自然語言描述控制需求與 I/O：

> X0 啟動、X1=1 停止、Y0 自保持，停止優先。驗證後產生 motor.ldr。

需要元件註解時一併說明：

> 另外新增元件註解：X0 是啟動按鈕，Y0 是馬達輸出。

MCP 會回傳可下載的 `.ldr`；明確要求註解時，另回傳 `.txt`。預設輸出位於
`artifacts/`，且不覆寫同名檔案。

## 驗證邊界

本專案負責離線產生、解析與驗證檔案。WinProLadder GUI 匯入、PLC 下載及實機測試由使用者在目標環境完成。離線模型通過不等於實體設備已驗證。

## 文件

| 類別 | 文件 |
| --- | --- |
| 入門 | [5 分鐘快速開始](docs/quickstart.md) · [安裝指南](docs/installation.md) |
| 功能 | [功能總覽](FEATURES.md) · [FUNC 支援表](docs/supported-functions.md) |
| 參考 | [使用與參數參考](docs/reference.md) · [完整文件索引](docs/README.md) |
| 驗證與開發 | [驗證方式與證據等級](docs/verification.md) · [貢獻指南](CONTRIBUTING.md) |

版本內容與後續變更統一記錄在 [CHANGELOG](CHANGELOG.md)。

## 授權

本專案原創程式碼與文件採用 [MIT License](LICENSE)，Copyright © 2026 syrup2718。
