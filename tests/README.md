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
