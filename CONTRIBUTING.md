# 貢獻指南

[首頁](README.md) · [開發指南](docs/development.md)

## 回報問題

提供版本、環境、最小重現、預期結果與實際錯誤。涉及 `.ldr` 時，附可分享的檔案、機型、WinProLadder 版本及畫面；請移除私有資料。

## 修改與檢查

遵守 [AGENTS.md](AGENTS.md)，修改後執行：

```powershell
uv sync --locked
uv run python -m pytest -q
uv run ruff check .
uv run python -m mypy
uv run python -m winproladder_mcp.setup check
```

Pull Request 說明改了什麼、如何驗證，以及仍有什麼限制。

## 新增指令

1. 核對手冊語意、範圍與時間單位。
2. 保留原始匯出與截圖，逐項確認編碼。
3. 補齊模型、編解碼、資源及 I/O 檢查。
4. 測試原始 bytes、邊界與錯誤形式。
5. 更新功能表、能力回報與範例。

不以 FUNC 編號猜 opcode；未確認的形式不得宣稱支援。編碼、模擬、GUI 與 PLC 驗證分開記錄。

## 提交原則

- 保留原始樣本，生成檔另存。
- 文件使用儲存庫相對連結；本機產物與原廠 PDF 不隨 Git 提交。
- 手冊引用保留標題及頁碼。
- 未安排發布時，不升版或打包。
