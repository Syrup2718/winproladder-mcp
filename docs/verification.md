# 驗證範圍

[文件索引](README.md) · [功能清單](../FEATURES.md)

本專案將編碼、模型與實際軟體／設備驗證分開記錄。新功能不能因為通過 CRC 或沿用某個機型檔頭，就自動取得 GUI 或 PLC 驗證狀態。

## 驗證層級

| 層級 | 確認內容 | 不代表 |
| --- | --- | --- |
| 容器與編碼 | 長度、CRC、原始 bytes 往返、可辨識記錄 | 指令實際運行正確 |
| 靜態檢查 | schema、參數範圍、I/O、暫存器跨度、工作區政策 | 所有硬體條件與動態資料已知 |
| 獨立離線模型 | 特定需求或演算法的另行建模 | MCP 已內建相同模擬 |
| MCP 內建模擬 | 已實作的布林與 Timer/Counter 掃描模型 | 任意原生 function 都可模擬 |
| MCP 整合 | 真實 stdio 呼叫、檔案生成、資源下載、SHA-256 | WinProLadder 已匯入 |
| GUI 匯入 | 指定檔案在指定工程的人工確認 | 所有變體或實體 PLC 行為 |
| 實體 PLC | 指定機型、工程與現場條件下的執行 | 未測組合的行為 |

## 樣本與測試

[樣本目錄](../samples/README.md)列出 **31 份匯出、219 個網路**。原始雜湊由 `tests/test_sample_integrity.py` 保護；格式往返、語意解碼、生成政策與 MCP 交付分別測試。樣本解碼覆蓋不等於全部樣本可通過生成政策。

測試分類與命令見[測試導覽](../tests/README.md)。指令研究文件中的測試數屬於該次開發紀錄，不是持續更新的全套測試數；請重新執行測試取得所在 commit 的結果。

## 已有人工確認

- 自保持模板：`(Y0 OR X0) AND NOT X1 → Y0`，281 bytes，payload `4100A0009001C100`，record CRC `0x5048`。其他位址、極性或檔頭不自動繼承此狀態。
- 交通燈匯入基準：`tests/fixtures/traffic_light-connected-verified.ldr`，25 網路、713 bytes，SHA-256 `a4694aa8db73737ada925742ebc6ba164aee52e56137bd5ae201017c203b3b94`。包含歷史輔助 M 結構，保留作缺陷與匯入對照，不代表符合現行生成政策。
- 比較接點：2026-10-07 回報指定 FUN170～175 試檔的首段／串聯位置正確；具體 hash 與範圍見 [test11](test11-functions.md)。

其他 GUI 截圖用於辨識原始匯出，不能當成重建檔或新參數變體的匯入驗證。未記錄實體 PLC 驗證的項目不得標示為已驗證。

## 重現方式

```powershell
uv run python -m pytest -q
uv run python -m winproladder_mcp.setup check
```

`setup check` 使用暫存工作目錄。若需保存整合驗證產物，可依[開發指南](development.md)執行 `scripts/verify_release.py`；此腳本名稱不表示會打包或發布。

研究文件中提到的 `artifacts/` 報告是本機歷史產物，不隨 Git 發布。可公開追溯的依據為儲存庫中的樣本、測試、IR 範例與已記錄雜湊。指令層級限制由[功能表](../FEATURES.md)及[研究索引](README.md)查閱。
