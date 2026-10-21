# 開發指南

[文件索引](README.md) · [貢獻指南](../CONTRIBUTING.md)

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

```powershell
uv run python -m pytest -q
uv run ruff check .
uv run python -m mypy
uv run python -m winproladder_mcp.setup check
```

`setup check` 會啟動真實 stdio MCP，驗證工具列舉、`.ldr` 產生、acceptance、SHA-256、資源下載及元件註解檔。

需要完整發布驗證時，使用新的空工作目錄：

```powershell
uv run python scripts/verify_release.py --root <new-directory>
```

## 核心模組

| 模組 | 責任 |
| --- | --- |
| `ldr.py`、`profiles.py` | 容器、CRC、record 與檔頭 |
| `logic.py`、`ir.py` | 條件 AST、語意 IR、編解碼 |
| `layout.py`、`optimize.py` | 接圖、配置與局部簡化 |
| `control.py`、`sequence.py`、`system.py` | 高階產生器 |
| `runtime.py`、`acceptance.py` | 有界模型與驗收 |
| `service.py`、`server.py` | 檔案邊界與 MCP 介面 |
| `capabilities.py` | 對外支援範圍 |

原始 bytes 往返與生成最佳化必須分離；read/export 不應改變未知資料。

## 新增指令

1. 先核對手冊的 operand、模式、單位及 CPU 差異。
2. 使用 WinProLadder 匯出樣本確認實際 bytes，不以 FUNC 編號猜 opcode。
3. 實作 schema、編碼、解碼、資源引用與 I/O 檢查。
4. 加入原始 bytes、邊界、反例及 MCP 交付測試。
5. 更新 capabilities 與對應工程證據文件。

缺少 serialization 不代表 PLC 指令本身不合法；文件應分開描述 PLC 語意與本專案 codec 限制。

## 格式研究

```powershell
uv run python -m winproladder_mcp.research inspect samples/test.ldr
uv run python -m winproladder_mcp.research hexdump samples/test.ldr
uv run python -m winproladder_mcp.research diff samples/w1.ldr samples/test2.ldr
```

原始樣本與 fixtures 不可為了通過測試而改寫。未知 header、trailer 或 opcode 必須保留或明確拒絕。

## 發布

日常修改不升版、不打包。只有明確安排發布時才更新版本；只有明確要求安裝包時才執行 `uv build`。發布前應在乾淨環境安裝產物並重新執行 MCP 自我檢查。
