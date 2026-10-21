# 原始 WinProLadder 樣本

[首頁](../README.md) · [文件索引](../docs/README.md)

此目錄保存 **31 份原始匯出、219 個網路記錄**，用途是確認 `.ldr` 的解析、重建與原生指令編碼沒有退化。

內容涵蓋：

- 基本接點、線圈、Timer、Counter 與串並聯接圖
- 整數、浮點、比較、資料轉換及表格／矩陣功能
- 高速計數、脈波、周邊 I/O、積算計時及狀態功能
- 多種 CPU 檔頭、metadata、未知記錄與不完整工程案例

這些檔案是回歸測試資料，不是現場控制範本。能解析也不表示整份工程可重新生成；來源 bytes、檔名與截圖均保持不變，生成結果另存於 `artifacts/`。

樣本雜湊由 [test_sample_integrity.py](../tests/test_sample_integrity.py) 固定。支援能力請查詢 MCP 的 `get_instruction_capabilities`，GUI 與 PLC 證據邊界見[驗證範圍](../docs/verification.md)。
