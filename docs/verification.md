# 驗證範圍

**繁體中文** | [English](verification.en.md)

[文件索引](README.md) · [功能清單](project/FEATURES.md)

本專案分開記錄序列化、離線模型、WinProLadder GUI 與實體 PLC 驗證。任何一層通過都
不會自動證明下一層。

| 層級 | 公開專案確認內容 | 不代表 |
| --- | --- | --- |
| Schema／政策 | IR、I/O contract、writer 與 workspace policy 合法 | WinProLadder 會接受檔案 |
| 容器與編碼 | framing、CRC、解碼回讀及參數語意一致 | 指令在 PLC 上執行正確 |
| 離線模型 | 支援子集的 acceptance case 通過 | 完整 PLC scan 或硬體語意 |
| GUI 顯示 | 特定產物由使用者在 GUI 開啟並顯示 | 另存再開啟或所有參數變體 |
| GUI round-trip | 特定產物另存並重新開啟 | 實體 PLC 行為 |
| PLC | 指定機型與現場條件的實測 | 未測組合或其他 CPU |

## 公開測試與私有證據

公開測試只使用合成或由本專案程式化產生的資料，涵蓋 CRC、容器往返、Common FUN
參數化生成、解碼語意、MCP stdio、ResourceLink 與安全拒絕。原始 WinProLadder 匯出、
客戶檔案、GUI 截圖、手冊及 native byte-anchor suite 保存在 repository 外，不是安裝、
執行或公開測試的依賴。

`sample-backed` 只表示該形式曾與私有原生匯出比對；`inferred` 表示依已知編碼規則延伸；
`GUI display verified` 只涵蓋特定產物的顯示。除非另有明確紀錄，本專案不宣稱 GUI
round-trip 或 PLC verified。

目前私有驗證紀錄涵蓋 **131 個 Common evidence keys** 的至少一個代表 form，均曾由
WinProLadder GUI 顯示；這不是 131 個不同 FUN 編號，也不涵蓋每一種合法參數。尚無公開
證據可宣稱這些產物完成 GUI 另存再開啟，亦無實體 PLC 執行驗證。

精確支援範圍請看 [FUNC 支援表](supported-functions.md)，並以執行中的
`get_instruction_capabilities` 回應為準。
