# 開發指南

[文件索引](README.md) · [專案架構](../ARCHITECTURE.md) · [Agent 指南](agent-guide.md) · [貢獻指南](project/CONTRIBUTING.md)

## 開發環境

```powershell
uv sync --locked
```

主要目錄：

```text
src/winproladder_mcp/  MCP、IR、編解碼、配方與模擬
tests/                 單元與 stdio MCP 整合測試
samples/               不可變的原始 .ldr 與截圖
examples/              IR JSON 範例
scripts/               驗證、診斷與範例工具
docs/                  使用與工程文件
```

本機產物放在 `artifacts/`、`tmp/`、`.venv/` 或 `.install/`，不應混入原始樣本。

## 必要檢查

一般修改執行統一的快速驗證。專案目前沒有可靠的受影響測試選擇器，因此 `--quick`
仍會執行完整測試：

```powershell
uv run python scripts/validate.py --quick
```

合併前或 CI 的 Linux job 執行完整驗證：

```powershell
uv run python scripts/validate.py --full
```

兩種模式都會檢查 Ruff format、Ruff lint、strict mypy 與測試。`--full` 另要求 90%
總 coverage、啟動真實 stdio MCP self-check，並以 workspace audit `--check` 阻擋原始碼、
文件與 `samples/`／`tests/` LDR 的完整性錯誤。本機輸出中的歷史 broken links 不會阻擋驗證。

每一步的命令、結果、耗時及 log 路徑會寫入 `tmp/validation/latest.json`；各步驟的
redacted logs 位於同一次 run 的子目錄。即使其中一步失敗，驗證仍會完成其餘步驟並以
非零狀態結束。`setup check` 會驗證工具列舉、`.ldr` 產生、acceptance、SHA-256、資源下載
及元件註解檔。

需要完整發布驗證時，使用新的空工作目錄：

```powershell
uv run python scripts/verify_release.py --root <new-directory>
```

## 架構與生成契約

模組責任、依賴方向、LDR 產生管線與驗證層級以根目錄
[ARCHITECTURE.md](../ARCHITECTURE.md) 為唯一架構依據。Ladder 生成限制、手冊證據與交付規則
以 [Agent 操作指南](agent-guide.md) 為準，本頁只記錄開發與驗證流程。

## 新增指令

1. 先核對手冊的 operand、模式、單位及 CPU 差異。
2. 使用 WinProLadder 匯出樣本確認實際 bytes，不以 FUNC 編號猜 opcode。
3. 實作 schema、編碼、解碼、資源引用與 I/O 檢查。
4. 加入原始 bytes、邊界、反例及 MCP 交付測試。
5. 更新 capabilities 與對應工程證據文件。

PLC 語意與 serialization 支援的區分以 [Agent 操作指南](agent-guide.md#指令與格式證據) 為準。

## 格式研究

```powershell
uv run python -m winproladder_mcp.research inspect samples/test.ldr
uv run python -m winproladder_mcp.research hexdump samples/test.ldr
uv run python -m winproladder_mcp.research diff samples/w1.ldr samples/test2.ldr
```

原始樣本與 fixtures 不可為了通過測試而改寫。未知 header、trailer 或 opcode 必須保留或明確拒絕。

## 發布

日常修改不升版、不打包。只有明確安排發布時才更新版本；只有明確要求安裝包時才執行 `uv build`。發布前應在乾淨環境安裝產物並重新執行 MCP 自我檢查。
