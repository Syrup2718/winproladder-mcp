# Agent 操作指南

## 生成流程

本工作區的 `.winproladder-policy.json` 啟用 `forbid_m_to_m`：禁止 M 接點驅動 M
線圈，包含自保持、複製、SET/RESET、功能塊狀態輸出及編譯器自動產生的中繼 M。
數值與步序應改以原生暫存器處理；無 M 輸入的比較指令可輸出 M 狀態，再控制
Y、計時器或暫存器指令。不可改名或停用規則來繞過限制。

`get_capabilities`／`get_design_guide` 回傳工作區規則，`validate_ladder` 同時檢查
原始及展開後的網路。產檔服務會再次檢查真正輸出的 bytes；修改、匯出也經過最後
檢查。違規或無法解析的網路會拒絕輸出，既有檔仍可讀取及分析。規則檔每次操作
重新讀取；升級程式碼後，已啟動的 MCP 程序需重新載入一次。

沒有規則檔的其他工作區保留相容行為；本工作區已永久啟用此限制。

1. 讀取 `get_capabilities` 與 `get_design_guide`，確認支援範圍及 schema。
2. 把需求整理成 I/O、有效極性、動作順序、優先權、時間與復歸條件。只把使用者指定的 X/Y 寫入必填的 `io_contract.inputs`／`outputs`，不可為了通過檢查擴增允許清單。不得自動新增 X/Y 或外部時脈。
3. 選擇下表的生成工具。不要求操作者手寫 JSON，亦不為已支援的參數組合要求 binary 樣本。
4. 自訂 IR 可先呼叫 `validate_ladder` 預覽簡化結果及 M 用量；以 `simulate_ladder` 或 `acceptance` 檢查啟動、保持、停止、互鎖與時序。
5. 生成實際檔案並回傳路徑、I/O、假設及驗證狀態。未經 GUI 匯入的檔案標為候選檔，不把模型測試當作實機驗證。

## 工具選擇

| 工具 | 用途 |
| --- | --- |
| `get_capabilities` | 能力、限制、工作目錄與 schema |
| `get_design_guide` | 設計流程與 IR 範例 |
| `get_ldr_artifact` | 取得生成檔的二進位內容與 SHA-256，供 client 下載保存 |
| `generate_control_ldr` | 單一控制配方 |
| `generate_system_ldr` | 最多 24 個獨立配方，只自動分配內部 M/T/C |
| `generate_sequence_ldr` | 最多 16 步原生 T 計時；原生暫停保留尚未支援 |
| `generate_ldr` | 自訂 Ladder IR，可附 acceptance |
| `validate_ladder` | 不寫檔，回傳檢查、optimized_ladder、layout |
| `simulate_ladder` | 布林或指定 scan_ms 的 Timer/Counter 模型 |
| `inspect_ldr` | 原始結構、payload、CRC 與未知資料 |
| `read_ldr` | 按顯示順序解碼；全部可辨識時回傳 ladder |
| `analyze_ldr` | 網路說明、元件讀寫交叉引用 |
| `compare_ldr` | 對齊 record 差異 |
| `modify_network` | insert/replace/delete，另存新檔 |
| `export_ldr` | 無損結構往返；不修復邏輯或錯誤 CRC |
| `create_start_stop` | 精確重建自保持模板 |
| `create_ldr` | 底層建立工具；未驗證組合需 allow_unverified |

一般生成使用 `generate_*`，不必額外設定 `allow_unverified`。`modify_network` 的 index 從 N000=0 起；修改需 `allow_unverified=true`，其他原始 records 保留。存在未知網路時，不猜測其語意或資源占用。

## 極性與掃描

`(Y0 OR X0) AND NOT X1 → Y0` 表示 X1=1 時停止，啟停同時成立時停止優先。若實體常閉停止按鈕在正常狀態讀入 1，必須使用符合該接線的條件，不能把實體 NC 與程式 NC 當作同一件事。

高階工具的 `signal`／`output`、順序工具的 `start` 必須明確指定。選配控制省略時為 FALSE，不套用任何 X；原生計時預設 `clock=null`。沒有指定 timeout 就不加逾時條件。FUN87～89 的編碼缺口見 [計時器核對紀錄](timer-evidence.md)。

同一掃描中 Y/M 隨網路順序更新。不要為縮短程式任意重排網路，或跨網路共用尚未檢查生命週期的暫存結果。

## 檔案與交付

Server 僅存取 `--root` 內的檔案；預設輸出為 `ROOT/artifacts/`，可用 `--output-dir` 指定 root 內獨立目錄。檔名必須為新的 `.ldr` 名稱，不接受任意輸出路徑。

高階配方會附 `.ldr.design.json`，保存參數、假設、配置與雜湊，並包含 `symbols` 與 `network_notes`。這些名稱是伴隨資料，不是已嵌入 LDR 的註解。生成回應的 `layout.helper_devices` 必須納入資源保留；將檔案匯入較大工程前需再次檢查位址衝突。

產檔工具同時提供 MCP ResourceLink。可用 `resources/read` 讀取 `winproladder://artifacts/{name}`，或呼叫 `get_ldr_artifact` 取得 embedded binary resource；無法讀取 server 本機路徑的 client 可將其中 Base64 blob 解碼為 `.ldr` 後交付使用者。下載使用回傳的 URI，不自行拼接含中文或空白的檔名。檔案重名會拒絕覆蓋，請換新檔名。

有提供 `acceptance` 時，生成前會分別驗證原始模型及從實際輸出 bytes 解碼的階梯圖。兩者任一不符即不寫檔；`compiled_acceptance` 回報後者結果，`artifact_validation` 回報 CRC 與可解碼網路數。

共享目錄可用 `--root C:\VM_Share`，檔案生成於其 `artifacts/`。編譯不需要 VMware、WinProLadder 或 PLC 連線；GUI 匯入是獨立驗證步驟。

詳細條件與時序限制見 [功能參考](reference.md)。
