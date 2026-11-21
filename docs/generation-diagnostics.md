# LDR 產生失敗診斷與安全恢復

[文件索引](README.md) · [專案架構](../ARCHITECTURE.md) · [驗證範圍](verification.md)

產生工具會保留既有安全閘門，並在可處理的失敗回應加入 `generation_code` 與
`diagnosis`。診斷不會重試相同的不支援編碼，也不會建立部分 `.ldr`。

## 診斷資料

`diagnosis` 包含失敗階段、Network 索引、指令、operand、原因、重試條件、已驗證替代方案、
下一步、artifact 是否建立，以及來源 IR／lowered IR／輸出 bytes／GUI／PLC 的驗證狀態。
失敗時 `artifact_created=false`；原始請求保持不變。

| 代碼 | 現有實際來源 | 狀態 |
| --- | --- | --- |
| `INVALID_IR` | Ladder schema、必要欄位或請求結構錯誤 | 公開請求可觸發 |
| `UNSUPPORTED_INSTRUCTION` | action discriminator 不在目前 IR schema | 公開請求可觸發 |
| `UNSUPPORTED_OPERAND` | 已知指令但 bank、mode、常數、跨度或 I/O operand 不支援 | 公開請求可觸發 |
| `UNSUPPORTED_NETWORK_STRUCTURE` | 不完整／巢狀流程、writer 衝突或無法依政策接圖 | validation／lowering 可觸發 |
| `MISSING_ENCODING_EVIDENCE` | CALL、受限 JMP、TDSP 等只有解析錨點或 relocation 未解 | 公開 validation 可觸發 |
| `ENCODING_FAILURE` | 已通過 validation 後 encoder 仍失敗 | 防禦閘門；正常合法 IR 不應觸發 |
| `ARTIFACT_VALIDATION_FAILURE` | 輸出 bytes 無法回讀、政策／I/O／acceptance 重播不一致 | 防禦閘門 |
| `IMPORT_UNVERIFIED` | 嚴格 Service 路徑拒絕未具 exact GUI anchor 的 composition | 嚴格候選閘門；一般 MCP 候選仍明示未驗證 |

I/O 與 architecture 的既有 MCP 錯誤碼會保留；`diagnosis.generation_code` 另外指出其產生
階段分類。檔名衝突、路徑或下載錯誤不屬於「不支援 Ladder」診斷，繼續使用既有 artifact
錯誤碼。

## 允許的自動恢復

只有既有、已有測試的處理會自動執行：

- Pydantic IR 預設值與 canonical schema 正規化。
- `lower_ladder` 的布林恆等式、去重、吸收、共同因子與已驗證 connected layout。

目前沒有另一種已具證據、可自動替換的等效 instruction encoding；正常 codec 只編碼原始
請求已支援的 form，不會把它宣稱為替代恢復。

成功結果的 `generation_recovery` 會列出實際套用的方法；來源、lowered program 與輸出 bytes
仍各自驗證。若 lowering 需要政策禁止的 helper，恢復會失敗並停止，不會繞過政策。

## 不允許的恢復

不猜 opcode／binary layout、不刪除 Network、不改寫互鎖與安全條件、不用重試繞過政策，
也不會把新 artifact 標示為 GUI 或 PLC verified。缺少編碼證據時，下一步是提供最小原生
WinProLadder 匯出、CPU/profile、WinProLadder 版本及單一 operand 差異樣本。
