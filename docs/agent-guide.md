# Agent 操作指南

[文件索引](README.md) · [使用參考](reference.md)

## 建議流程

1. 讀取 `get_capabilities`；需要特定指令時再查 `get_instruction_capabilities`。
2. 從需求整理 I/O、有效極性、優先權、時間、復歸與驗收條件。
3. 只把使用者指定的 X/Y 放入 `io_contract`，不可自行增加 I/O 或外部時脈。
4. 優先使用高階配方；自訂 IR 可先執行 `validate_ladder`。
5. 把 acceptance 與產檔放在同一次請求，回傳實際檔案連結與驗證狀態。
6. 使用者明確要求元件註解時，再呼叫 `generate_component_comments` 並交付獨立 `.txt`。

本工作區禁止無意義 M→M 複製、冗餘中繼及自動 relay helpers；原生 function 的 M 控制與 M 結果／狀態不在此限。數值與步序狀態應使用暫存器。

## 工具選擇

| 工具 | 用途 |
| --- | --- |
| `get_manual_reference` | 手冊範圍、版本差異與 RTC 程序 |
| `inspect_rtc_snapshot` | 檢查提供的 RTC 值，不連線 PLC |
| `get_capabilities` | 能力、限制與工作區政策 |
| `list_instruction_families` | 列出指令族群 |
| `get_instruction_capabilities` | 查詢單一指令族群 |
| `get_design_guide` | 設計流程、範例與 schema |
| `get_ldr_artifact` | 下載生成的 `.ldr` |
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
| `create_start_stop` | 固定 X0/X1/Y0 自保持模板 |
| `create_ldr` | 底層建立工具 |

## 交付規則

- `.ldr`、設計 sidecar 與元件註解檔都使用新的檔名，不覆寫。
- 使用 MCP 回傳的 ResourceLink，不自行拼接下載 URI。
- 高階 sidecar 中的 `symbols` 與 `network_notes` 不是 `.ldr` 內嵌註解。
- acceptance 通過只代表支援模型與輸出 bytes 一致，不代表 GUI 或 PLC 已驗證。
- 未知網路不猜測語意；若無法證明符合政策，拒絕修改或重新生成。

停止按鈕的「實體常閉」與 PLC 讀值極性是不同概念。條件必須依使用者描述的 PLC 值建立，不能自行反轉。
