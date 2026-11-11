# Agent 操作指南

[文件索引](README.md) · [專案架構](../ARCHITECTURE.md) · [使用參考](reference.md)

## 工作區不可違反的契約

- 每次 Ladder 操作都必須讀取根目錄 `.winproladder-policy.json`，不可為了產檔而停用、
  繞過或放寬政策。
- 禁止無意義的 M→M relay 複製、冗餘中繼鏈、自保持／複製 SET/RESET 目的地，以及
  lowering 自動產生的 relay helper。M 控制原生 function，且該 function 產生 M 結果或
  狀態位元則允許；普通 relay rung 不會因位於 MC 內或被命名為 function 而取得例外。
- 數值與步序狀態使用原生暫存器。無條件比較可產生供 Y 輸出或 timer/register EN 使用的
  M 狀態位元；不可用改名或等價 relay 鏈掩飾被禁止的設計。
- 保留使用者現有的 I/O、極性、優先權、復歸與時間契約，不可自行增加輸入、輸出或
  外部時脈。
- 必須分別檢查來源 IR、lowered program，以及實際輸出 bytes 重新解碼後的程式。

數字倒數顯示的每個 50 ms digit slot 必須維持亮 40 ms、滅 10 ms，順序為秒、十分之一秒。
即使相鄰數字相同（例如 9.9 或 0.0），也不可省略 blank interval。

## 指令與格式證據

判斷 instruction mode、operand 範圍、單位、D/P 變體或 PLC 行為前，先查閱使用者提供的
`C:/Fatek/FBe進階篇/進階篇應用指令.pdf`；需要時再查基本篇與 RTC 手冊。若手冊與 GUI
匯出樣本仍有差異，記錄精確頁碼與 bytes 證據。

PLC 文件語意與本專案 `.ldr` serialization 是兩個不同層級。缺少 encoder 只能表示目前
實作不支援產檔，不能推論 PLC operand、mode 或 instruction 本身不合法。

## 建議流程

1. 讀取 `get_capabilities`；需要特定指令時再查 `get_instruction_capabilities`。
2. 從需求整理 I/O、有效極性、優先權、時間、復歸與驗收條件。
3. 只把使用者指定的 X/Y 放入 `io_contract`，不可自行增加 I/O 或外部時脈。
4. 優先使用高階配方；自訂 IR 可先執行 `validate_ladder`。
5. 把 acceptance 與產檔放在同一次請求，回傳實際檔案連結與驗證狀態。
6. 使用者明確要求元件註解時，再呼叫 `generate_component_comments` 並交付獨立 `.txt`。

## 工具選擇

| 工具 | 用途 |
| --- | --- |
| `get_manual_reference` | 手冊範圍、版本差異與 RTC 程序 |
| `inspect_rtc_snapshot` | 檢查提供的 RTC 值，不連線 PLC |
| `get_capabilities` | 能力、限制與工作區政策 |
| `get_instruction_capabilities` | 未指定 family 時列出族群；指定後查詢詳細限制 |
| `get_design_guide` | 設計流程、範例與 schema |
| `get_ldr_artifact` | 下載生成的 `.ldr` |
| `get_pdw_artifact` | 下載生成的 `.pdw`（v1.1.0 實驗功能） |
| `inspect_pdw` | 檢查取樣主機、模組、分區與註解（v1.1.0 實驗功能） |
| `generate_pdw` | 範本一／兩列 X→Y 等長替換（v1.1.0 實驗功能） |
| `generate_project_pdw` | 共用 Ladder 編譯器，產生可變長度 PDW、分區及註解（v1.1.0 實驗功能） |
| `generate_component_comments` | 產生元件註解 `.txt` |
| `generate_control_ldr` | 單一控制配方 |
| `generate_system_ldr` | 多個獨立配方 |
| `generate_sequence_ldr` | 順序控制 |
| `generate_ldr` | 自訂 Ladder IR |
| `validate_ladder` | 預覽結構、資源與政策結果 |
| `simulate_ladder` | 執行支援範圍內的掃描模型 |
| `inspect_ldr` | 查看容器、payload 與 CRC |
| `read_ldr` | 解碼網路 |
| `analyze_ldr` | 說明網路與元件引用 |
| `compare_ldr` | 比較兩份檔案 |
| `modify_network` | 修改網路並另存 |
| `export_ldr` | 無損另存 |

## 交付規則

完整 Ladder 的 PDW 使用 `generate_project_pdw`，舊 `generate_pdw` 保留簡單等長介面；
兩者支援範圍見 [PDW 文件](pdw-format.md)。
私人範本留在 repository 外，將 MCP 的 root 設為私人資料夾；不要為了讀取範本
放寬路徑限制，也不要把 `.ldr` 的指令支援範圍套用到 PDW。

- `.ldr`、設計 sidecar 與元件註解檔都使用新的檔名，不覆寫。
- 使用 MCP 回傳的 ResourceLink，不自行拼接下載 URI。
- 高階 sidecar 中的 `symbols` 與 `network_notes` 不是 `.ldr` 內嵌註解。
- acceptance 通過只代表支援模型與輸出 bytes 一致，不代表 GUI 或 PLC 已驗證。
- 未知網路不猜測語意；若無法證明符合政策，拒絕修改或重新生成。
- 交付新產生的 `.ldr` 時，檔案連結放在回覆最前面，並分別標示獨立離線模型、MCP
  內建模擬、WinProLadder GUI 匯入與實體 PLC 驗證狀態。

停止按鈕的「實體常閉」與 PLC 讀值極性是不同概念。條件必須依使用者描述的 PLC 值建立，不能自行反轉。
