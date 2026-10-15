# 開發指南

[首頁](../README.md) · [文件索引](README.md) · [功能清單](../FEATURES.md)

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
uv run python -m pytest
uv run ruff check .
uv run python -m mypy
uv run python -m winproladder_mcp.setup check
uv run python scripts/verify_release.py --root <新的驗證目錄>
```

`check` 測試真實 stdio MCP 連線、自保持模板、需求驗收及兩種二進位下載介面。完整測試涵蓋樣本雜湊、CRC、無損往返、邏輯真值表、時序與工具檔案輸出。

`verify_release.py` 透過真正的 stdio MCP 生成所有控制配方及多控制、暫停流程、自訂條件、Timer/Counter 情境；逐檔檢查 CRC、SHA-256、無損往返、解碼後掃描行為與下載 bytes。也驗證重名不覆蓋、驗收失敗不產檔。每次建立 `artifacts/release-<時間>-<識別碼>/manifest.json`，保留 `.ldr` 與設計紀錄，且將每個檔案的 GUI 匯入狀態明確設為待驗證。GUI 驗證需使用該份 manifest 的檔案及 SHA-256，不以另一份同名檔代替。

`verify_release.py` 使用獨立驗證目錄，避免將本工作區嚴格政策與歷史配方驗收混為一談。

## 安裝包驗證

只有使用者明確要求製作安裝包時才執行本節；例行修改不打包、不變更版本。

`uv build` 產生 `dist/*.whl` 及 `dist/*.tar.gz`。交付前在專案以外的新目錄建立 Python 3.12 環境，以 `uv pip install --python <環境的 python.exe> <wheel 路徑>` 安裝。使用該環境執行 `winproladder-setup check`，並把 `scripts/verify_release.py` 複製至該目錄，用該環境執行 `python verify_release.py --root <新工作目錄>`。確認套件載入位置位於新環境的 `site-packages`，避免 editable install 或 repo 的 `src/` 掩蓋打包問題。

建置產物與驗證 manifest 保留在本機，發布需另外執行；不要在套件中夾帶 `.codex/config.toml`、工作輸出或暫存資料。日常使用優先採用 [原始碼安裝](quickstart.md)。

## 架構

- `profiles.py`：集中定義 HeaderProfile、原始樣本檔頭及精確反向識別；service／ir 保留既有匯入介面。
- `ldr.py`：容器解析、CRC 與 Record；`research.py`：原始差分檢查。
- `logic.py` / `ir.py`：條件 AST、語意 IR、原始編解碼。
- `instruction_catalog.py`：獨立樣本 payload 與 opcode 表，按樣本順序集中管理。
- `registers.py` / `floating.py` / `peripheral.py`：word bank、浮點常數及周邊運算元。
- `capabilities.py` / `design.py` / `manual_reference.py`：目前能力、設計流程與手冊資料。
- `optimize.py` / `layout.py`：局部布林簡化、接圖展平與資源配置。
- `control.py` / `sequence.py` / `system.py`：高階配方與流程。
- `timing.py` / `acceptance.py`：掃描模型與生成前驗收。
- `service.py`：檔案範圍及生成（保留 capabilities 匯入相容介面）；`server.py`：MCP；`setup.py`：設定及連線檢查。

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

`control_functions.py` 負責 test16 的 WDT、HSC0、DIV48、SUM、PID 編碼／解碼；IR 定義與範圍檢查保存在 `ir.py`，避免為可執行模型假裝支援硬體行為。

`integer_functions.py` 負責 test17 整數運算編碼／解碼，CRC16 MD=1 的手冊差異由分析結果及能力說明明確揭露。

`analog_functions.py`、`thermal_functions.py` 分別處理 test18、test19；`process_functions.py` 負責多個功能家族共用的控制輸入、狀態輸出與 operand 分派。

完整本機檔案盤點可執行 `uv run python scripts/audit_workspace.py --output tmp/workspace-audit-new.json`。JSON 報告只含路徑、大小、雜湊與檢查結果，不輸出連線設定內容；Git、環境依賴與快取只計數，不逐一審查第三方程式。文件中的 artifacts／dist／tmp 連結是本機證據，Git 原始碼副本不包含這些檔案。

`table_functions.py`集中test22的FUN105～112運算元編解碼與完整資源範圍，由共用ProcessFunction控制及狀態處理接入。

`matrix_functions.py`集中test23的FUN120～127 operand編解碼和矩陣範圍；共用ProcessFunction增加四路輸入解碼。

`transfer_functions.py`集中test24的MOV／TOGG、SORT／Z-WR、矩陣位元指令；WY8輸出span與Z-WR直接N編碼在此獨立處理。

`packing_functions.py`集中FUN42～49的operand順序、count／index檢查、部分word讀寫與BUNIT動態跨度。

`shift_functions.py`集中FUN50～57：BDIST動態byte跨度、移位／旋轉N形式、Gray單word與DECOD跨word／bank末端截取分析。

`conversion_functions.py`集中FUN06及58～64：ENCOD跨word、顯示／ASCII保留資料、時間多word轉換及精確ASC字串區塊。

功能家族的 operand 編解碼由 `process_functions.py` 共用分派表選取；opcode 使用 bytes 索引，新增時會檢查重複 action／opcode 及缺少的 metadata。新增家族需加入 `_OPERAND_MODULES` 與四份 metadata 表，保持編碼和解碼使用同一個模組。
