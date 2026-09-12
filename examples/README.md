# IR 範例

JSON 可作為 `generate_ldr` 的 ladder 參數；完整配方與 schema 由 `get_design_guide` 提供。

| 檔案 | 內容 |
| --- | --- |
| start-stop.json | 自保持電路 |
| timer-observed.json | T1 / preset 256，EN 接母線，TUP 無輸出 |
| counter-observed.json | C1 / preset 10，PLS/CLR 均接母線，CUP 無輸出 |

Timer/Counter 檔案用於重現樣本，不是直接可用的製程設計。一般控制使用高階配方並明確指定輸入條件。

批次生成範例請見 [開發指南](../docs/development.md)，工具用法見 [Agent 指南](../docs/agent-guide.md)。
