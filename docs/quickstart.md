# 快速開始

**繁體中文** | [English](quickstart.en.md)

[首頁](../README.md) · [安裝指南](installation.md) · [功能總覽](../FEATURES.md)

## 1. 安裝

在專案目錄執行對應腳本：

```powershell
# Windows
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
```

```sh
# macOS / Linux
sh install.sh
```

看到 `PASS` 與 `Setup complete` 後，將 `.install/mcp-config.json` 或
`.install/mcp-config.toml` 中的 `winproladder` 設定加入 MCP client，然後重新連線。

## 2. 描述需求

說清楚 I/O、有效極性、優先權與時間：

> X0 啟動 Y0，放開後保持；X1=1 時停止，停止優先。驗證後產生 motor.ldr。

MCP 會檢查需求中允許的 X/Y，不會自行增加輸入、輸出或外部時脈。

## 3. 下載檔案

結果會提供 `.ldr` 下載連結，預設也存入 `artifacts/`。高階配方另有
`.ldr.design.json`，記錄設計假設與元件配置。同名檔不會被覆寫。

需要元件註解時明確提出：

> 新增元件註解：X0 是啟動按鈕，Y0 是馬達輸出。

此時會另外收到 CP950／Big5 編碼的 `.txt`，不會修改 `.ldr`。

## 4. 使用端驗收

將 `.ldr` 匯入 WinProLadder，核對機型、I/O 與時間設定，再依需要下載至 PLC 測試。這些步驟由使用者完成；離線 acceptance 不等於 GUI 或實機驗證。

## 常見問題

| 問題 | 建議 |
| --- | --- |
| Client 看不到工具 | 重新執行安裝腳本，更新設定後重新連線 |
| I/O 檢查失敗 | 核對位址、極性及 `io_contract` |
| 指令不能產生或模擬 | 查閱[功能總覽](../FEATURES.md)；編碼與模擬範圍不同 |
| 同名檔已存在 | 使用新的輸出檔名 |

進階參數見[使用參考](reference.md)。
