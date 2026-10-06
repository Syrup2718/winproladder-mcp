# 開發指南

## 目錄

本機交付檔與歷史資料位置見 [資料夾導覽](folders.md)。

```text
src/winproladder_mcp/  MCP、IR、編譯器、配方與模擬器
tests/                單元與 MCP 整合測試
tests/fixtures/       缺陷重現與匯入基準
samples/              不可變的原始 LDR 與對照截圖
examples/             可重用的 IR JSON
scripts/              範例生成與診斷入口
docs/                 操作與技術文件
artifacts/            本機生成檔案（不納入 Git）
tmp/                  本機研究暫存（不納入 Git）
```

`.venv`、快取、coverage 與 dist 為本機環境或建置產物；`.codex/config.toml` 為本機連線設定，不納入 Git。不要搬動 samples 或 fixtures 而未同步修改測試路徑。

## 檢查

```powershell
uv sync --locked
uv run pytest
uv run ruff check .
uv run mypy
uv build
uv run winproladder-setup check
uv run python scripts/verify_release.py --root .
```

`check` 測試真實 stdio MCP 連線、自保持模板、需求驗收及兩種二進位下載介面。完整測試涵蓋樣本雜湊、CRC、無損往返、邏輯真值表、時序與工具檔案輸出。

`verify_release.py` 透過真正的 stdio MCP 生成所有控制配方及多控制、暫停流程、自訂條件、Timer/Counter 情境；逐檔檢查 CRC、SHA-256、無損往返、解碼後掃描行為與下載 bytes。也驗證重名不覆蓋、驗收失敗不產檔。每次建立 `artifacts/release-<時間>-<識別碼>/manifest.json`，保留 `.ldr` 與設計紀錄，且將每個檔案的 GUI 匯入狀態明確設為待驗證。GUI 驗證需使用該份 manifest 的檔案及 SHA-256，不以另一份同名檔代替。

## 安裝包驗證

`uv build` 產生 `dist/*.whl` 及 `dist/*.tar.gz`。交付前在專案以外的新目錄建立 Python 3.12 環境，以 `uv pip install --python <環境的 python.exe> <wheel 路徑>` 安裝。使用該環境執行 `winproladder-setup check`，並把 `scripts/verify_release.py` 複製至該目錄，用該環境執行 `python verify_release.py --root <新工作目錄>`。確認套件載入位置位於新環境的 `site-packages`，避免 editable install 或 repo 的 `src/` 掩蓋打包問題。

建置產物與驗證 manifest 保留在本機，發布需另外執行；不要在套件中夾帶 `.codex/config.toml`、工作輸出或暫存資料。使用者的 wheel 安裝流程見 [入門指南](quickstart.md)。

## 架構

- `ldr.py`：容器解析、CRC 與 Record；`research.py`：原始差分檢查。
- `logic.py` / `ir.py`：條件 AST、語意 IR、原始編解碼。
- `optimize.py` / `layout.py`：局部布林簡化、接圖展平與資源配置。
- `control.py` / `sequence.py` / `system.py`：高階配方與流程。
- `timing.py` / `acceptance.py`：掃描模型與生成前驗收。
- `service.py`：檔案範圍及生成；`server.py`：MCP；`setup.py`：設定及連線檢查。

原始編解碼與生成最佳化必須分離，避免 read/export 改變既有 bytes。新增功能需涵蓋 schema、編譯、解碼、能力回報與測試；未實作的模擬指令必須明確拒絕。

## 格式研究

```powershell
uv run python -m winproladder_mcp.research inspect samples/test.ldr
uv run python -m winproladder_mcp.research hexdump samples/test.ldr
uv run python -m winproladder_mcp.research diff samples/w1.ldr samples/test2.ldr
```

每次改變一項指令、位址或參數，保留原始匯出檔與畫面；新增 CRC、payload、往返及反例測試，再更新 [格式規格](ldr-format.md)。不以手冊功能編號推算 binary opcode。

原始樣本不得修改。未知 header、trailer、opcode 應保留，不以零值或不認識為由丟棄。新檔使用 exclusive create，不覆寫；錯誤應在寫檔前檢出。所有開發測試維持離線，不對實體 PLC 下載或操作。

## 範例生成

```powershell
uv run python scripts/generate_control_examples.py --root . --prefix demo
uv run python scripts/generate_design_examples.py --root . --prefix custom
```

透過真實 MCP 生成到 artifacts；重跑需換 prefix。`smoke_mcp.py` 用於檢查既有本機設定，`build_start_stop_candidate.py` 為固定 binary 模板診斷，不是一般生成入口。
