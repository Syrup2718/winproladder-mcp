# 文件

[回到首頁](../README.md)

## 使用

| 文件 | 內容 |
| --- | --- |
| [快速開始](quickstart.md) | 產生第一個 `.ldr` 與元件註解檔 |
| [安裝指南](installation.md) | 平台、MCP client 設定與疑難排解 |
| [功能總覽](../FEATURES.md) | 支援能力、限制與工具分組 |
| [FUNC 支援表](supported-functions.md) | 原生指令的解析、產生與模擬狀態 |
| [使用參考](reference.md) | 配方、順序控制、自訂 IR 與驗收 |
| [驗證範圍](verification.md) | 離線、GUI 與實體 PLC 驗證的差異 |

## 開發

| 文件 | 內容 |
| --- | --- |
| [Agent 指南](agent-guide.md) | MCP 工具選擇與交付規則 |
| [開發指南](development.md) | 環境、測試與新增指令流程 |
| [LDR 格式](ldr-format.md) | 容器、record、CRC 與未知資料保留 |
| [邏輯最佳化](logic-optimization.md) | 接圖簡化及安全限制 |
| [手冊與 RTC](manual-limits-rtc.md) | 運算元範圍與萬年曆參考 |
| [計時器](timer-evidence.md) | 普通 T 與 FUN87～89 的支援邊界 |

版本變更見 [CHANGELOG](../CHANGELOG.md)。細部指令能力請使用 MCP 的
`list_instruction_families` 與 `get_instruction_capabilities` 查詢；回歸樣本與
測試證據留在 `samples/`、`examples/` 與 `tests/`，不再各自建立公開說明頁。
