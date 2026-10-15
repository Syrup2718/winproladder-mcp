# 維護腳本

[首頁](../README.md) · [文件索引](../docs/README.md)

在專案根目錄以 `uv run python scripts/<名稱>.py` 執行。生成腳本可能寫入 artifacts，先看 `--help` 並使用新名稱；一般開發不需要逐一執行。

| 腳本 | 用途 |
| --- | --- |
| [verify_release.py](verify_release.py) | 真實 MCP 生成、下載與驗收；使用新的獨立驗證 root，名稱不表示會打包 |
| [generate_control_examples.py](generate_control_examples.py) | 控制配方範例產檔 |
| [generate_design_examples.py](generate_design_examples.py) | 自訂 IR 範例產檔 |
| [smoke_mcp.py](smoke_mcp.py) | 本機 MCP 設定診斷 |
| [build_start_stop_candidate.py](build_start_stop_candidate.py) | 固定自保持 binary 模板診斷 |

`research/build_fun15_16_probe.py` 是已被 test8 推翻的假說工具，僅保留研究歷史，不作為目前功能入口。其他一次性本機研究位於 `tmp/research-history/`。

測試與型別檢查命令見[開發指南](../docs/development.md)。安裝包與版本變更須由使用者明確要求。

[ audit_workspace.py ](audit_workspace.py) 可盤點檔案、重複內容、文件連結、JSON／Python 語法及 LDR CRC；只寫入新報告，不搬移或刪除檔案：

```powershell
uv run python scripts/audit_workspace.py --output tmp/workspace-audit-new.json
```

兩支範例生成腳本使用明確的示範 I/O 契約；不代表使用者實際接線。受政策拒絕的配方會回報 `policy_rejected`，不會停用政策。
