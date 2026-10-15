# IR 範例

[首頁](../README.md) · [文件索引](../docs/README.md)

JSON 可作為 `generate_ldr` 的 ladder 參數；完整配方與 schema 由 `get_design_guide` 提供。

| 檔案 | 內容 |
| --- | --- |
| start-stop.json | 自保持電路 |
| timer-observed.json | T1 / preset 256，EN 接母線，TUP 無輸出 |
| counter-observed.json | C1 / preset 10，PLS/CLR 均接母線，CUP 無輸出 |

Timer/Counter 檔案用於重現樣本，不是直接可用的製程設計。一般控制使用高階配方並明確指定輸入條件。

批次生成範例請見 [開發指南](../docs/development.md)，工具用法見 [Agent 指南](../docs/agent-guide.md)。


## 原生指令樣本 IR

以下 JSON 是樣本的語意表示，並非全部都能作為完整製程直接生成。產檔仍須提供 I/O 契約並通過政策檢查。

| 範例 | 範圍與限制 |
| --- | --- |
| [test16 原生指令](test16_functions.json) | 七網路完整 IR；使用方式與限制見 [test16](../docs/test16-functions.md)。 |
| [test17 原生指令](test17_functions.json) | 八網路 IR；[支援形式與 CRC16 限制](../docs/test17-functions.md)。 |
| [test18 IR](test18_functions.json) | [支援範圍與跳躍限制](../docs/test18-functions.md)。 |
| [test19 IR](test19_functions.json) | 完整解析樣本，function的M→M已允許，僅解析CALL仍使全檔不能直接生成；[可生成子集與限制](../docs/test19-functions.md)。 |
| [test20 IR](test20_functions.json) | 完整解析樣本，RAMP2工作區與表格重疊；請分開生成，[詳細說明](../docs/test20-functions.md)。 |
| [test21 原始樣本 IR](test21_functions.json) | FUN101～104，保留 X0／X5 與 M3／M4；CLR 使用一般極性。 |
| [test22原始樣本IR](test22_functions.json) | FUN105～112；BKCMP需要完整Y5～Y14契約。 |
| [test23原始樣本IR](test23_functions.json) | 矩陣運算、MINV暫存器L、四路MBWR。 |
| [test24 原始樣本 IR](test24_functions.json) | MOV／MOV/／TOGG、SORT／Z-WR、矩陣位元操作；WY8契約須包含Y8～Y23。 |
| [test25原始IR](test25_functions.json) | FUN42～49；BUNIT使用length_register，WX0／WY0契約包含全部16點。 |
| [test26原始IR](test26_functions.json) | FUN50～57；移位N分count／length_register，DECOD採source_index與bit_length。 |
| [test27原始IR](test27_functions.json) | FUN06與58～64；ENCOD count為掃描點數，7SG count=N代表N+1位；ASC限ABCDEF。 |

- [test28 IR](test28_functions.json)：完整解析資料；PWM錯誤設定及CALL／TDSP限制見[test28](../docs/test28-functions.md)。

- [test29 IR](test29_functions.json)：兩組ASCII字串、六個數字標籤。

- [test30：記憶體指令與英數標籤](../docs/test30-functions.md)。
