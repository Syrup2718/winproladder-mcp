# WinProLadder MCP

Reverse-engineering and tooling project for FATEK WinProLadder `.ldr` files.

A working local stdio MCP server with lossless LDR parsing/encoding, a conservative
semantic IR, file editing tools, and a user-import-verified start/stop template.
Target profile: WinProLadder v3.28 / FBs-20MC. This is not full instruction coverage.

目前 v0.3 以「使用者說需求，agent 交付 .ldr」為主流程：支援括號邏輯、
參數化 Timer/Counter 推導及自動生成。詳見 [v0.3 生成流程](docs/v0.3-generation.md)。

## 從 GitHub 安裝（Windows PowerShell）

先安裝 [uv](https://docs.astral.sh/uv/getting-started/installation/)。有 Git 可執行：

```powershell
git clone https://github.com/Syrup2718/winproladder-mcp.git
cd winproladder-mcp
```

也可以在 GitHub 選 Code → Download ZIP，解壓縮後在該資料夾開啟 PowerShell。
接著執行：

```powershell
uv sync --locked
uv run winproladder-setup check
uv run winproladder-setup config --format codex
```

`uv sync` 會準備 Python 3.12 及依賴。`check` 會在暫存工作區啟動真正 MCP、
產生並核對自保持檔案，可重複執行且不覆蓋你的檔案。

將 `config` 輸出的區段合併至專案 `.codex/config.toml`，再重新載入 Codex MCP 連線。
已有同名 server 時更新該區段，勿重複新增或覆蓋其他設定。
其他支援本機 stdio 的 MCP client 改用 `--format json`，合併進該 client 的 MCP 設定。
本機路徑會自動產生，不需要固定放在 C:\\Fatek；移動專案後請重新產生設定。

連線後可以對 agent 說：

> 請使用 WinProLadder MCP，建立 X0 啟動、X1=1 停止、Y0 自保持電路，輸出 motor.ldr。

Agent 可用 get_design_guide 取得設計指南，再呼叫 generate_ldr 輸出。
使用者不必手寫 JSON 或提供 binary 樣本；推導組合會生成並標示驗證狀態。

產出位於 `artifacts/motor.ldr`，再到 WinProLadder 的 Import Ladder Diagram 匯入。
讀取自己的檔案時，先放進此專案資料夾（例如 `inputs/example.ldr`），再要求 agent 分析。
若輸出已存在，請指定新檔名。一般使用不需要 API key，也不需手動保持一個 server 終端開啟，
client 會啟動它。此版本是本機 stdio，不是可直接貼入網頁 ChatGPT 的 HTTPS connector URL。

詳細工具參數、停止按鈕極性及能力限制見 [agent guide](docs/agent-guide.md)。

更新時：Git clone 使用者先保留自己的修改，再執行 `git pull`、`uv sync --locked`、
`uv run winproladder-setup check`，然後重啟 MCP 連線。ZIP 使用者下載新版到新目錄，
重新安裝並產生設定，另行保留 inputs/artifacts。

Tools: `get_capabilities`, `inspect_ldr`, `read_ldr`, `validate_ladder`,
`simulate_ladder`, `create_ldr`, `create_start_stop`, `export_ldr`, `modify_network`.
Preferred workflow: `get_design_guide` → `generate_ldr`.
Additional analysis tools: `analyze_ldr`, `compare_ldr` (13 tools total).
New files go to `artifacts/`; existing files and original samples are never overwritten.
Nested Boolean branches and parameterized .01s Timer/Counter blocks use inferred encoding.
Unknown instruction families and edge contacts remain opaque/preserved.

## Development setup

Install [uv](https://docs.astral.sh/uv/), then run:

```powershell
uv sync
uv run pytest
uv run ruff check .
uv run mypy
```

The project pins Python 3.12 in `.python-version`; `uv sync` can install that
Python version when it is not already available.

## Repository layout

```text
src/winproladder_mcp/  Python package
samples/               Immutable ground-truth WinProLadder exports
tests/                 Automated tests
docs/                  Reverse-engineered format documentation
```

Do not edit existing `.ldr` samples. Add a new minimal sample when testing a new
instruction or varying one binary property.

## Read-only binary research

```powershell
uv run python -m winproladder_mcp.research inspect samples/test.ldr
uv run python -m winproladder_mcp.research hexdump samples/test.ldr
uv run python -m winproladder_mcp.research diff samples/w1.ldr samples/test2.ldr
```

`inspect` tests the currently observed framing and reports CRC validity; it is
not a semantic ladder parser. `diff` compares absolute byte offsets, so insertions
shift subsequent comparisons. These commands print to stdout and do not write files.
See [format findings](docs/ldr-format.md) and [requested samples](docs/sample-requests.md).
# Latest instruction expansion

v0.4 adds **11 common control recipes and up to 16-step pause/resume sequences**.
Use `generate_control_ldr` or `generate_sequence_ldr`; missing recipe parameters
receive disclosed draft defaults. [Usage, clock dependency and limits](docs/v0.4-controls.md).

Generation now supports executable Boolean acceptance cases: failed requirements
prevent file creation. See [acceptance and VMware exchange workflow](docs/acceptance-workflow.md).

`test5.ldr` adds inferred 16-bit register OR and single-level FOR/BREAK/NEXT
generation, decoding, cross-references and loop validation. See
[test5 evidence and usage](docs/test5-analysis.md). The complete manual instruction
set is not yet supported; unsupported variants are rejected rather than guessed.
