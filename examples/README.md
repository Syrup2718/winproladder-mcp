# IR 範例

JSON 可作為 `generate_ldr` 的 ladder 參數；完整配方與 schema 由 `get_design_guide` 提供。

| 檔案 | 內容 |
| --- | --- |
| start-stop.json | 自保持電路 |
| timer-observed.json | T1 / preset 256，EN 接母線，TUP 無輸出 |
| counter-observed.json | C1 / preset 10，PLS/CLR 均接母線，CUP 無輸出 |

Timer/Counter 檔案用於重現樣本，不是直接可用的製程設計。一般控制使用高階配方並明確指定輸入條件。

批次生成範例請見 [開發指南](../docs/development.md)，工具用法見 [Agent 指南](../docs/agent-guide.md)。

- [test16 原生指令](test16_functions.json)：七網路完整 IR；使用方式與限制見 [test16](../docs/test16-functions.md)。

- [test17 原生指令](test17_functions.json)：八網路 IR；[支援形式與 CRC16 限制](../docs/test17-functions.md)。

- [test18 IR](test18_functions.json)：[支援範圍與跳躍限制](../docs/test18-functions.md)。

- [test19 IR](test19_functions.json)：完整解析樣本，function的M→M已允許，僅解析CALL仍使全檔不能直接生成；[可生成子集與限制](../docs/test19-functions.md)。

- [test20 IR](test20_functions.json)：完整解析樣本，RAMP2工作區與表格重疊；請分開生成，[詳細說明](../docs/test20-functions.md)。
