# 功能總覽

[首頁](README.md) · [快速開始](docs/quickstart.md) · [參數參考](docs/reference.md)

本頁說明 v1.0.0 的公開能力與邊界。精確 schema 與個別指令限制請查詢 MCP 的
`get_capabilities`、`list_instruction_families` 和 `get_instruction_capabilities`。

## 產出內容

| 產物 | 用途 |
| --- | --- |
| `.ldr` | WinProLadder 階梯圖檔案 |
| `.ldr.design.json` | 高階產生器的設計、假設與元件配置 |
| `.txt` | 使用者明確要求時產生的元件註解表 |

元件註解檔固定使用 `REF`、`COMMENT`、`DESCRIPTION` 三欄，Tab 分隔、CRLF 換行及 CP950／Big5 編碼。

## 產生方式

| 類型 | 適合情境 |
| --- | --- |
| 單一控制配方 | 啟停、SET/RESET、切換、邊沿、延遲、脈衝、計數、正反轉、星三角 |
| 順序控制 | 最多 16 步，支援普通 T、FUN87 暫停續跑或明確指定的外部脈波 |
| 系統組合 | 最多 24 個彼此獨立的控制配方，自動配置內部資源 |
| 自訂 Ladder IR | 布林條件、Timer/Counter、暫存器及已支援的原生 FUNC |

所有主要產生工具都要求明確的 `io_contract`。MCP 不會自行新增 X/Y、外部時脈或現場接線。

## 原生指令支援

目前支援的形式分布於下列家族：

| 家族 | FUNC 範圍與範例 |
| --- | --- |
| 基本控制 | MC/MCE、DIFU/DIFD、UDCTR、MOV、TOGG |
| 整數與比較 | FUN11～37，加減乘除、CMP、BCD/BIN、PID、區間比較 |
| 位元與資料轉換 | FUN40～65，位元／byte／nibble 操作、移位、Gray、ASCII、時間轉換 |
| 流程與周邊 | FOR/NEXT、IMDIO、鍵盤、七段顯示、PWM、速度偵測 |
| 計時與硬體功能 | FUN86～98，積算計時、WDT、HSC、RAMP；部分功能僅編碼 |
| 表格與矩陣 | FUN100～130，搬移、搜尋、QUEUE/STACK、矩陣運算 |
| 記憶體與狀態 | FUN160～162、190 |
| 比較接點與浮點 | FUN170～175、200～220 |

「支援」只代表列出的 operand 與模式已有編解碼或模型。未取樣的 D/P、間接定址、CPU 專用形式及其他運算元組合不會自動視為可用。CALL 目前僅解析；JMP 只保留已確認的完整樣本形式。

逐 FUNC 的精確 operand、模式與證據狀態請直接查詢 `get_instruction_capabilities`；公開文件不重複維護逐次測試紀錄。

## 讀取與分析

- 檢查 `.ldr` 結構、CRC、原始 payload 與檔頭。
- 以顯示順序解碼可辨識的網路，未知記錄保留為 opaque。
- 列出元件讀寫、Timer 設定、重複 writer 及資源範圍。
- 比較兩份 `.ldr` 的新增、刪除與替換網路。
- 修改或匯出時一律建立新檔，不覆寫來源。

## 安全與品質檢查

- 僅允許需求中宣告的實體 X/Y。
- 禁止無意義的 M→M relay copies、冗餘中繼與自動 relay helpers。
- 允許 M 控制原生 function，並由 function 產生 M 結果或狀態。
- 高階工具預設拒絕跨網路重複 normal coil writer。
- 寫檔前檢查來源、lowered program 及解碼後輸出。
- acceptance 失敗時不建立檔案；可用 `require_acceptance=true` 強制要求案例。

工作區規則由 `.winproladder-policy.json` 控制，本儲存庫預設啟用嚴格政策。

## MCP 工具

v1.0.0 提供 22 個工具，分為四組：

- 產生：`generate_control_ldr`、`generate_sequence_ldr`、`generate_system_ldr`、`generate_ldr`、`create_ldr`、`create_start_stop`、`generate_component_comments`
- 驗證：`validate_ladder`、`simulate_ladder`
- 讀取與修改：`inspect_ldr`、`read_ldr`、`analyze_ldr`、`compare_ldr`、`modify_network`、`export_ldr`、`get_ldr_artifact`
- 說明與查詢：`get_capabilities`、`get_design_guide`、`list_instruction_families`、`get_instruction_capabilities`、`get_manual_reference`、`inspect_rtc_snapshot`

詳細參數與選用方式見 [Agent 操作指南](docs/agent-guide.md)。

## 已知限制

- 不是完整 PLC 模擬器；只有列出的布林、數值、Timer/Counter 與部分原生功能具模型。
- 不操作 WinProLadder GUI，也不連線、下載或控制 PLC。
- `.ldr` 無法完整證明目標工程的 CPU、時間基準及硬體配置。
- 部分指令只支援特定樣本形式、只解析或只編碼。
- 元件註解是獨立 `.txt`，不會嵌入 `.ldr`。

目前保存 31 份原始 WinProLadder 匯出、共 219 個網路作為回歸證據。驗證層級與既有人工確認見[驗證說明](docs/verification.md)。
