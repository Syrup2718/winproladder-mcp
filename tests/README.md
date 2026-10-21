# 測試

[首頁](../README.md) · [驗證範圍](../docs/verification.md)

執行完整測試：

```powershell
uv run python -m pytest -q
```

測試全部使用本機暫存工作區，不連線或下載程式到 PLC。

| 分類 | 內容 |
| --- | --- |
| 樣本與格式 | 原始雜湊、CRC、容器解析、逐 byte 往返 |
| 編譯與政策 | Ladder IR、接圖、I/O 契約、M→M 政策、writer 檢查 |
| 配方與模型 | 控制配方、順序控制、Timer/Counter、acceptance |
| 原生指令 | test8～test30 的 operand、邊界、反例與資源跨度 |
| MCP 與交付 | stdio 工具、ResourceLink、`.ldr` 與元件註解下載 |
| 安裝與文件 | 安裝流程、設定、文件連結與範例 |

`fixtures/` 保存缺陷重現與人工匯入基準；`test_testN_functions.py` 對應同名原始樣本。不要為了通過測試修改原始樣本或降低政策。

測試通過只代表所測的編碼、政策及模型成立，不會自動取得 WinProLadder GUI 或實體 PLC 驗證狀態。
