# 使用參考

**繁體中文** | [English](reference.en.md)

[文件索引](README.md) · [功能總覽](../FEATURES.md)

## 控制配方

`generate_control_ldr` 支援：

- `start_stop`、`set_reset`、`toggle`
- `rising_edge`、`falling_edge`
- `on_delay`、`off_delay`、`pulse`、`counter`
- `forward_reverse`、`star_delta`

`signal` 與 `output` 必填。需要 `stop`、`reset` 或 `reverse` 的配方也必須明確提供相應條件。多輸出配方使用的每個 Y 都要列入 `io_contract.outputs`。

`generate_system_ldr` 可組合最多 24 個獨立配方並配置內部 M/T/C；它不負責跨配方的製程協調。

## 順序控制

`generate_sequence_ldr` 支援 1～16 步，每步可設定輸出、時間、完成條件及逾時。

- 預設使用原生 T，時間須為 10 ms 的倍數。
- 有 pause 且沒有外部 clock 時，使用 FUN87 與暫存器狀態。
- 只有需求明確指定 clock 時，才使用外部脈波模式。
- 每次掃描最多轉移一步；完成與逾時同時發生時，完成優先。

## 自訂 Ladder IR

最小範例：

```json
{"networks": [{"condition": "(Y0 OR X0) AND NOT X1", "coils": [{"device": "Y", "address": 0}]}]}
```

條件支援 AND／OR／NOT、`&`／`|`／`!`、括號與 TRUE／FALSE。所有主要產生工具都要提供 I/O 契約；來源、lowered program 與輸出 bytes 會分別檢查。

Timer 範例：

```json
{"networks": [{"block": {"type": "timer", "address": 0, "preset": 100, "enable": "X0"}}]}
```

Timer `preset` 是時基刻度，不是毫秒。`.01S` 時基下 `preset=100` 代表 1 秒；MCP 無法單靠 `.ldr` 確認目標工程的時間基準。

完整 schema 由 `get_design_guide` 提供；個別原生 FUNC 的 operand 與模式請用 `get_instruction_capabilities` 查詢。

## 元件註解

使用者明確要求「新增元件註解」時，呼叫 `generate_component_comments`。每筆資料包含：

| 欄位 | 說明 |
| --- | --- |
| `ref` | 元件編號，例如 X0、Y0、M0、D1 |
| `comment` | 短註解，可留空 |
| `description` | 補充說明，可留空 |

輸出是獨立 `.txt`：`REF`／`COMMENT`／`DESCRIPTION`、Tab 分隔、CRLF、CP950／Big5。重複 REF、控制字元或無法以 CP950 表示的文字會被拒絕。

## 模擬與 acceptance

`simulate_ladder` 最多執行 256 次掃描。未提供 `scan_ms` 時只模擬布林邏輯；提供後可模擬支援範圍內的 Timer/Counter 與 FUN87～89。

產生工具可附 1～32 個 acceptance cases。案例會先檢查來源模型，再重播實際輸出 bytes；任何斷言失敗都不寫檔。`require_acceptance=true` 可強制要求案例。

模型不是 PLC 模擬器。不支援的原生 function 會明確拒絕，不會回傳部分 trace。

## 檔案操作

- `inspect_ldr`：結構、payload、CRC
- `read_ldr`：依顯示順序解碼
- `analyze_ldr`：網路說明與元件交叉引用
- `compare_ldr`：比較兩份檔案
- `modify_network`：插入、替換或刪除網路並另存
- `export_ldr`：保留未知資料並另存

所有寫入都限制在工作區輸出目錄，且不覆寫既有檔案。未知記錄可保留與分析；無法證明符合目前政策時不會重新生成。
