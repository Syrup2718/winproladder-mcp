# 測試導覽

在根目錄執行 `uv run python -m pytest -q`。測試使用暫存工作目錄，不下載程式到實體 PLC。

| 分類 | 主要檔案 |
| --- | --- |
| 原始證據 | `test_sample_integrity.py`、`test_ldr.py`、`test_research.py` |
| 原生指令 | `test_test8_functions.py`～`test_test15_functions.py`、`test_lcnv.py`、`test_arithmetic_edges.py` |
| 編譯與接圖 | `test_ir.py`、`test_inferred_compiler.py`、`test_blocks.py`、`test_actions.py`、`test_layout.py`、`test_optimize.py` |
| 架構與 I/O | `test_architecture.py`、`test_io_and_native_timing.py` 及各原生指令的完整跨度測試 |
| 時序與配方 | `test_timing.py`、`test_timer_units.py`、`test_sequence.py`、`test_system.py`、`test_control.py`、`test_acceptance.py` |
| MCP 與交付 | `test_mcp.py`、`test_recipe_mcp.py`、`test_service.py`、`test_artifacts.py`、`test_full_generation.py`、`test_design_report.py` |
| 安裝與文件 | `test_setup.py`、`test_release.py`、`test_documentation.py`、`test_manual_reference.py` |

`fixtures/` 保留既有缺陷重現與人工匯入基準，不能因整理而改寫。`test_testN_functions.py` 的 N 對應原始 `samples/testN.ldr`，保留名稱便於追溯。

測試通過表示所測編碼、政策及模型通過，不會自動取得 GUI 或 PLC 驗證。樣本覆蓋與各次驗證邊界見[驗證依據](../docs/verification.md)。

`test_test16_functions.py` 涵蓋 DIV48／SUM／PID／WDT／HSC0 的精確重建、完整跨度、多腳位政策及未知形式拒絕。

`test_test17_functions.py` 涵蓋整數運算、MEAN 動態 N、EXT 雙字組、DIV48 單輸入及 CRC16 引用不確定性。

`test_test18_functions.py` 包含類比與位元存取、雙輸入政策、動態表格跨度及未解碼跳躍不得重定位的檢查。

`test_test19_functions.py` 涵蓋積算型計時單位與CV、TPCTL完整跨度與WR獨占、雙輸入及狀態政策、全樣本拒絕和CALL僅解析邊界。

`test_test20_functions.py`涵蓋三路輸入與狀態政策、RAMP時間／Tn、RAMP2 OR區與WR4、ASCWR未知範圍、表格L−1和CLR極性及完整樣本衝突。

`test_example_scripts.py` 透過 subprocess 執行兩支範例腳本，覆蓋有／無專案政策的 I/O 契約與政策拒絕結果。`test_documentation.py` 檢查正式文件連結；完整本機輸出連結由 `scripts/audit_workspace.py` 額外檢查。

`test_test21_functions.py` 覆蓋 FUN101～104 完整原樣生成、CLR 正反接點與常數、整表讀寫、M 政策、邊界與未編碼形式拒絕。
