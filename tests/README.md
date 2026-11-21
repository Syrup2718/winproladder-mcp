# 測試

[首頁](../README.md) · [驗證範圍](../docs/verification.md)

執行完整測試：

```powershell
uv run python -m pytest -q
```

測試全部使用本機暫存工作區，不連線或下載程式到 PLC。

| 分類 | 內容 |
| --- | --- |
| 容器格式 | 合成文件、CRC、容器解析與逐 byte 往返 |
| 編譯與政策 | Ladder IR、接圖、I/O 契約、M→M 政策、writer 檢查 |
| 配方與模型 | 控制配方、順序控制、Timer/Counter、acceptance |
| 原生指令 | 參數化 operand、邊界、反例、CRC 與解碼回讀 |
| MCP 與交付 | stdio 工具、ResourceLink、`.ldr` 與元件註解下載 |
| 安裝與文件 | 安裝流程、設定、文件連結與範例 |

`fixtures/` 只保存可公開、專案自行建立的結構資料。原始 WinProLadder 匯出、客戶檔案、
截圖及 byte-anchor 測試保存在 repository 外的 private evidence suite。

測試通過只代表所測的編碼、政策及模型成立，不會自動取得 WinProLadder GUI 或實體 PLC 驗證狀態。
