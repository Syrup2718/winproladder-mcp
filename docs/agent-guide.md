# Agent 使用指南

這是可執行的本機 stdio MCP v0.3，支援經樣本研究的 WinProLadder v3.28 / FBs-20MC 格式。
新主流程優先參考 [v0.3 生成指南](v0.3-generation.md)：get_design_guide → generate_ldr。
generate_ldr 自動啟用推導編碼，不需要使用者處理 allow_unverified 或補樣本。
以下保留安裝及 legacy tools 說明；位址和編碼能力以 v0.3 指南為準。
「MCP 工具流程已實作」不等於「WinProLadder 全部指令已支援」。
不用 OpenAI API key；由 MCP client 啟動 Python 子行程。

## 連接

在專案目錄執行 `uv sync --locked`，然後 `uv run winproladder-setup check`。
執行 `uv run winproladder-setup config --format codex`，會輸出這台機器的絕對路徑設定。
將輸出的 server 區段合併到 `.codex/config.toml`（此本機檔案不納入 Git）。
若已有 `[mcp_servers.winproladder]`，更新該區段，勿重複新增。
重新載入支援專案設定的 Codex client，並確認專案為信任狀態。
工具在 client 下次建立 MCP 連線時載入，不保證出現在已開啟的對話工具清單。
搬動 repo 或更換工作機器需調整 command、args 與 cwd。

其他 stdio MCP client 執行 `uv run winproladder-setup config --format json`，
將產生的 server entry 合併到 client 的設定；
不要整份覆蓋已有 servers。不同 client 的設定檔位置由該 client 決定。

手動啟動可用：

```powershell
uv run --locked winproladder-mcp --root .
```

這會等待 MCP JSON-RPC stdin，不是互動式 CLI，也不會開 HTTP port。
路徑存取範圍是 `--root`；預設新檔輸出到 `ROOT/artifacts/`。
可指定 `--output-dir` 為 root 下的獨立子目錄，不能設為 samples/src/tests/docs/隱藏目錄。
所有寫入接受檔名，不接受任意 output path，而且絕不覆蓋既有檔案。

設定依據：[Codex 官方 MCP 文件](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)。
協定實作使用 [官方 Python MCP SDK](https://github.com/modelcontextprotocol/python-sdk)。

## 工具工作流

1. `get_capabilities`：取得可用工具、IR schema、位址子集、輸出目錄及範例。
2. `inspect_ldr(path)`：讀 framing、CRC、offset、raw payload、opaque tail。
   CRC 錯誤會列出 false；結構損壞則回 MCP tool error。
3. `read_ldr(path)`：用顯示順序回傳 N000 起的 logic，未知 payload 整段保留為 opaque。
   CRC 不符時拒絕語意讀取；header 非已採樣版本時不解讀語意。
4. `validate_ladder(ladder)`：檢查輸入及編碼支援度。`valid` 不代表 WinProLadder syntax check。
5. `simulate_ladder(ladder, inputs, initial)`：最多 256 次布林掃描，輸出 trace。
   每次 inputs 是 X 輸入快照，沒給的 X 重置 false；未提供的初始元件也是 false。
   Y/M 狀態逐 scan 保留，依 network 順序更新。T/C 僅可作固定初值接點，不運行 Timer/Counter。
   含 block 的 ladder 會明確拒絕模擬；不會略過 block 後回傳看似完整的 trace。
6. `create_ldr(output_name, ladder, allow_unverified)`：產生新檔、長度及 CRC。
7. `export_ldr(path, output_name)`：結構 parse→encode 的逐 byte 複製，包括 opaque 與來源錯誤 CRC。
   這個工具不是修復工具；有問題會附 warning。
8. `modify_network(path, output_name, operation, index, network, allow_unverified)`：
   `replace/insert/delete`；index 0 為 N000，insert 的 index 可等於數量以追加。
   delete 時省略 network，且不可刪到完全沒有 network。
   修改寫入另一檔，其他原始 payload/trailer/CRC 保留。
9. `create_start_stop(output_name, stop_input_active_high=true)`：直接產生已成功匯入的自保持案例。
10. `analyze_ldr(path)`：network 說明及元件讀寫交叉引用，回報不完整的分析範圍。
11. `compare_ldr(left_path, right_path)`：對齊原始 records 的新增/刪除/修改。
12. `get_design_guide()`：自然語言需求到 IR 的流程、schema 和完整範例。
13. `generate_ldr(output_name, ladder)`：優先使用的生成工具；自動編譯推導規則並回傳檔案及設計摘要。

完整可解碼的 `read_ldr` 結果另帶 `ladder`，可直接傳入生成工具。
有 opaque network 時 `ladder=null`，請用 modify_network 保留其他未知資料。

範例工具呼叫：

```json
{"output_name": "motor.ldr", "stop_input_active_high": true}
```

其逻輯為 `(Y0 OR X0) AND NOT X1 → Y0`。X1=1 代表停止。
若實體常閉 Stop 接線導致按下時 X1=0，應選 false，將梯形圖接點改為 NO；
此變體需 `allow_unverified=true`，尚未經使用者匯入確認。

## IR 與能力範圍

`examples/start-stop.json` 可直接作為 `generate_ldr` 的 ladder 參數。
一個 network 用 steps 左到右摺疊：第一個 `load`，後面 `and/or`，最後 coils。
例如 load A、or B、and C 表示 `(A OR B) AND C`，沒有 AND 優先規則。
`A AND (B OR C)` 不可寫成 load A、and B、or C；後者是 `(A AND B) OR C`。
v0.3 可改用 condition 字串表達巢狀拓樸；與 steps 不可並用。空 network 使用 `{"empty": true}`。

| 元件 | 支援位置 | 本版位址範圍 |
| --- | --- | --- |
| X/Y/M/T/C NO、NC | 條件式、load / and / or、子分支 | 0–255（推導） |
| 普通／反相 Y/M coil | 最後，可多個 | 0–255（推導） |
| Timer / Counter block | enable 或 pulse/clear 條件式 | 0–255（推導） |

上表是推導編碼範圍，不是 PLC 元件容量。
Timer/Counter 透過 network.block 指定 type/address/preset；preset 範圍0–65535，
Timer time_base 固定0.01s。get_capabilities.block_templates 保留8個來源證據，並非生成白名單。
邊沿接點與其他尚未實作的指令整段 opaque；
可無損匯出並保留，但不能由 IR 生成。`allow_unverified` 也不會繞過 unsupported 限制。

只有完整單 network payload `41 00 A0 00 90 01 C1 00` 有使用者成功匯入紀錄。
其他可編碼組合由 generate_ldr 直接生成候選並回傳未匯入驗證狀態。
只有 legacy create_ldr/modify_network 流程仍須設定 `allow_unverified=true`。
不要把 tool success、CRC 成功或布林模擬當成 PLC runtime 驗證。

## 錯誤與資料保留

- 不可辨識的 resource record 起點：保留該位置到檔尾為 opaque，不搜尋內嵌 marker。
- 已辨識的 record 長度錯誤、截斷：回傳含 offset 的錯誤，不重新猜邊界。
- 未知 trailer 或 opaque tail：可 export，禁止 edit；未知 payload 本身可在其他 network 被修改時保持不變。
- 路徑逃逸、同名輸出、unsupported 指令及無效 schema：回 MCP `isError=true`。
- 來源 16 MiB、IR 1000 networks、每 network 256 steps/32 coils 為本版限制。
- 無 GUI、無 PLC 通訊、無 PLC 寫入。

## 驗證

```powershell
uv run pytest
uv run ruff check .
uv run mypy
uv build
```

`tests/test_mcp.py` 會以真正的 stdio MCP client 啟動子行程，
測試 initialize、list_tools、resource、全部 tools 與錯誤回傳。
`tests/test_ldr.py` 驗證五個原始 .ldr 的逐 byte round-trip 與未知資料保存。
`tests/test_ir.py` 核對已解碼 payload 往返及自保持 IR 的真值表／按鈕序列。
