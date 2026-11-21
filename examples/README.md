# 範例

[首頁](../README.md) · [使用參考](../docs/reference.md)

這些 JSON 可作為 `generate_ldr` 的 `ladder` 參數。實際產檔仍要提供 I/O 契約並通過工作區政策。

## 入門範例

| 檔案 | 內容 |
| --- | --- |
| [start-stop.json](start-stop.json) | X0/X1/Y0 自保持 |
| [timer-observed.json](timer-observed.json) | Timer 樣本語意 |
| [counter-observed.json](counter-observed.json) | Counter 樣本語意 |

Timer/Counter 樣本用於重現格式，不是現場製程範本。一般需求請優先使用高階控制配方；目前 schema 與支援邊界以 MCP 的 `get_design_guide` 和 `get_instruction_capabilities` 為準。
