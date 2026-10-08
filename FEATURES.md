# WinProLadder MCP 現有功能總覽

版本：**v0.10.0**。整理日期：**2026-10-08**。

未發版更新：新增 [test14 FUN216～220、74 IMDIO 與浮點 ERR 接線](docs/test14-functions.md)。新增 [test13 FUN209～215](docs/test13-functions.md) 與 FBs-44MN 檔頭。依手冊擴充一般 M0..1911 與直接暫存器 bank；新增 `get_manual_reference`／`inspect_rtc_snapshot`，詳見 [手冊與 RTC](docs/manual-limits-rtc.md)。新增 FUN205 FDIV、206 FCMP、207 FZCP、208 FSQR、binary32 常數及 FBs-40MA 樣本檔頭，詳見 [test12](docs/test12-functions.md)。六種比較接點已開放首段／後續串聯位置；12 種位置寫法已由使用者確認試檔 GUI 正確。版本號仍為 v0.10.0，未重製安裝包。本文件依目前原始碼、MCP 工具與既有驗證紀錄整理。

## 1. 能完成什麼

使用者提出控制需求 → 連接 MCP 的 AI Agent 解讀需求與 I/O → MCP 編譯、檢查 → 取得真正的 **WinProLadder `.ldr` 二進位檔案**。

自然語言由 Agent 解讀；MCP 負責結構化設計、編碼、檔案與支援範圍內的模擬。產檔不需要啟動 WinProLadder 或 VM。目前支援已取樣的 FBs-20MC、FBs-24MA、FBs-32MA、FBs-40MA、FBs-44MN 檔頭，不代表支援全部 CPU、軟體版本或指令變體。

「支援指令」表示能讀取、編碼並產檔；不代表所有運算元、D/P 形式、狀態腳位或 PLC 執行行為都已驗證。

## 2. 原生 FUNC 清單

| FUNC | 名稱／用途 | MCP action | 已實作範圍與主要限制 |
| --- | --- | --- | --- |
| 00 | MC 主控開始 | `mc` | EN、編號 0..127；須配對，不接受巢狀或交錯區域 |
| 01 | MCE 主控結束 | `mce` | 對應 MC 編號 |
| 04 | DIFU 上升沿微分 | `difu` | trigger 條件、Y/M 目的位址 |
| 05 | DIFD 下降沿微分 | `difd` | trigger 條件、Y/M 目的位址 |
| 07P | UDCTR 加減計數 | `udctr` | PLS、U/D、CLR；PV 為 0..32767 常數，CV 為可寫 R/D；不支援 CUP 接線 |
| 11 | ＋ 加法 | `arithmetic` / `add` | 16-bit；Sa 為 R/D，Sb 為 0..32767 常數，D 為可寫 R/D |
| 12 | − 減法 | `arithmetic` / `sub` | 同上 |
| 13 | × 乘法 | `arithmetic` / `mul` | 同上；目的地佔兩個連續 word |
| 14 | ÷ 除法 | `arithmetic` / `div` | 同上；商／餘數佔兩個 word，拒絕常數除零 |
| 15 | ＋1 原生加一 | `increment` | EN、R/D 目的位址 |
| 16 | −1 原生減一 | `decrement` | EN、R/D 目的位址 |
| 17 | CMP 數值比較 | `compare` | R/D Sa、Sb，EN、U/S；相等／大於／小於接普通 Y/M 線圈 |
| 18 | AND 位元且 | `bitwise` / `and` | R/D Sa、Sb、目的位址及 EN |
| 19 | OR 位元或 | `bitwise` / `or` | 同上；保留舊 `register_or` 介面 |
| 20 | →BCD 二進位轉 BCD | `word_conversion` / `to_bcd` | **目前僅接受 0..9999 常數來源**，不支援暫存器來源形式 |
| 21 | →BIN BCD 轉二進位 | `word_conversion` / `to_bin` | word 來源及可寫目的地；不接受常數來源 |
| 33 | LCNV 線性轉換 | `lcnv` | Md、S、Ts、D、L；Md=0..3、L=1..64；超出原樣本的參數組合屬外推 |
| 35 | XOR 位元互斥或 | `exclusive_logic` / `xor` | word Sa、Sb、可寫目的地；不支援 D=0 腳位接線 |
| 36 | XNR 位元互斥或反相 | `exclusive_logic` / `xnr` | 同上；支援樣本中的 T1 數值來源 |
| 37 | ZNCMP 區間比較 | `zone_compare` | R/D 來源；上下限為 -32768..32767 常數；區間內／高於上限／低於下限接普通線圈 |
| 74 | IMDIO 即時 I/O 更新 | `imdio` | start=X/Y、count=1..36；整段 I/O 契約，限主機點位 |
| 170 | = 相等比較接點 | `comparison_chain` / `eq` | 首段／後續串聯皆可；位置試檔已經使用者 GUI 確認 |
| 171 | > 大於比較接點 | `comparison_chain` / `gt` | 首段／後續串聯皆可；位置試檔已經使用者 GUI 確認 |
| 172 | < 小於比較接點 | `comparison_chain` / `lt` | 首段／後續串聯皆可；位置試檔已經使用者 GUI 確認 |
| 173 | <> 不等比較接點 | `comparison_chain` / `ne` | 首段／後續串聯皆可；位置試檔已經使用者 GUI 確認 |
| 174 | >= 大於等於比較接點 | `comparison_chain` / `ge` | 首段／後續串聯皆可；位置試檔已經使用者 GUI 確認 |
| 175 | <= 小於等於比較接點 | `comparison_chain` / `le` | 首段／後續串聯皆可；位置試檔已經使用者 GUI 確認，可用常數 Sb=0..32767 |
| 200 | I→F 整數轉浮點 | `float_operation` / `i_to_f` | 來源 1 word，結果 2 words |
| 201 | F→I 浮點轉整數 | `float_operation` / `f_to_i` | 來源 2 words，結果 1 word |
| 202 | FADD 浮點加法 | `float_operation` / `add` | 各來源及結果都是 2 words |
| 203 | FSUB 浮點減法 | `float_operation` / `sub` | 同上 |
| 204 | FMUL 浮點乘法 | `float_operation` / `mul` | 同上 |
| 205 | FDIV 浮點除法 | `float_operation` / `div` | 暫存器或浮點常數來源；拒絕常數除零 |
| 206 | FCMP 浮點比較 | `float_compare` | equal／greater／less 普通 Y/M 線圈 |
| 207 | FZCP 浮點區間比較 | `float_zone_compare` | S 為暫存器，上下限可為暫存器或常數；within／above／below 線圈 |
| 208 | FSQR 浮點平方根 | `float_operation` / `sqrt` | 暫存器或常數來源，結果 2 words |
| 209～211 | FSIN／FCOS／FTAN | `float_operation` / `sin`、`cos`、`tan` | 16-bit 角度 -18000～18000，單位 0.01 度；結果為浮點雙字組 |
| 212～213 | FNEG／FABS | `float_operation` / `neg`、`abs` | destination 原地讀寫雙字組，不提供 sa／sb |
| 214～215 | FLN／FEXP | `float_operation` / `ln`、`exp` | 浮點來源／結果；這兩個指令的 D bank 上限為 D3999 |
| 216～220 | FLOG／FPOW／FASIN／FACOS／FATAN | `float_operation` / `log`、`pow`、`asin`、`acos`、`atan` | pow 的 sa 為指數、sb 為底數；反三角結果為弧度 |
| — | FOR 迴圈開始 | `for` | 次數為 1..16383 常數；單層迴圈 |
| — | NEXT 迴圈結束 | `next` | 必須與 FOR 配對 |
| — | BREAK 跳出迴圈 | `break` | EN 條件；必須位於迴圈內 |

補充限制：

- 比較接點支援六種關係的首段／後續串聯位置，位置試檔已獲 GUI 確認，其他運算元組合仍需驗證；仍不支援 OR、混合普通接點或 D 型；精確新增 WS0、WM0、C2；R5000..8071 已依手冊與編碼錨點擴充。WM0 的 M0..M15 讀取納入架構政策。
- 浮點暫存器範圍為 R0..3839、R5000..8071、D0..4095；完整雙字组不得跨界。算術與比較支援有限 binary32 常數，轉換指令仍限暫存器。F5/F6 常數格式已取樣，F7 為推導；支援普通浮點 ERR 線圈，FLOG 已取樣，其他 ERR 形式屬推導。不支援 P／間接。詳見 [test12](docs/test12-functions.md)。

- 整數加減乘除尚不支援 Sa 常數、Sb 暫存器／負常數、狀態旗標接線、D/P 形式或間接定址。
- CMP、ZNCMP 的結果線圈目前不接受 SET／RESET／反相模式。
- ZNCMP 尚不支援暫存器上下限或 ERR 接線，lower 不得大於 upper。
- →BCD／→BIN 尚不支援 ERR 接線；LCNV 不支援 33P、間接定址、暫存器 L 或轉換表自動初始化。
- 除明列的 07P.UDCTR 外，不可將其他 D/P 變體視為已支援。
- **上表 action 目前均未提供內建執行模擬**；可產檔與可模擬是不同能力。

## 3. 基本階梯圖元件

| 元件／功能 | 支援內容 |
| --- | --- |
| 接點 | X、Y、M、T、C 常開／常閉接點 |
| 條件 | AND、OR、NOT、括號、TRUE/FALSE，以及 `&`、`|`、`!` 寫法 |
| 接線 | 串聯、並聯、多輸出；支援範圍內自動化簡條件與整理接圖 |
| 線圈 | 普通、反相、SET、RESET；Y/M 位址仍受架構政策限制 |
| 原生邊沿接點 | 單一 X 上升沿／下降沿，直接接 Y/M 線圈；與 DIFU/DIFD function 分開實作 |
| Timer | 原生 T、EN、常數 preset、TUP 輸出；目前編碼模型只有 `.01S` 時基 |
| Counter | 原生 C、PLS、CLR、常數 preset、CUP 輸出 |
| 空網路 | 讀取與保留空網路 |
| 設計說明 | 回傳 symbols、network_notes；高階產檔另附設計 JSON，尚未寫入 LDR 註解區段 |

單份 IR 支援 1..1000 網路。接點／線圈及 T/C 的編碼範圍為 0..255，這不是實際 PLC 硬體點數保證。

### Word 位址

- 既有直接 R/D：R0..3839、唯讀輸入區 R3840..3903、R5000..8071、D0..4095；多 word 結果不能跨越已支援 bank 邊界。
- XOR／XNR／→BIN 等新增 word 指令可讀 T0..255 數值；不把它解讀為 T 接點，且不開放 T 作目的地。
- 新增 word 類型目前僅確認 WX0、WY0，其他 WX/WY 編號尚未開放。比較接點另有精確 WS0、WM0、C2、R5111 支援，不代表整個 bank 已開放。
- WX0 涵蓋 X0..X15；WY0 涵蓋 Y0..Y15。I/O 檢查與寫入重疊分析會展開全部位元；WX0 不可寫入。

### 時間參數

高階配方的 `delay_ms`／`gap_ms` 使用毫秒；目前要求 10 ms 倍數。低階 Timer IR 的 `preset` 則是目前編碼模型採用的時基刻度，不能與毫秒參數混用。回應會列出刻度、假設時基及名義時間，但 **LDR 解碼尚不能確認目的工程的時基配置**，`configuration_verified=false`；不把名義時間宣稱為 GUI／PLC 實測時間。

普通 T 停用即清零。目前沒有原生保持型計時，也不會擅自新增 X 當外部時脈。

## 4. 高階控制配方與順序控制

`generate_control_ldr` 提供以下 11 種配方：

| 配方 | 用途 |
| --- | --- |
| `start_stop` | 啟動／停止與自保持 |
| `set_reset` | 設定／復歸控制 |
| `toggle` | 輸入觸發切換 |
| `rising_edge` | 上升沿脈波 |
| `falling_edge` | 下降沿脈波 |
| `on_delay` | 延遲啟動 |
| `off_delay` | 延遲停止 |
| `pulse` | 定時脈波 |
| `counter` | 脈波計數與復歸 |
| `forward_reverse` | 正反轉互鎖 |
| `star_delta` | 星三角順序 |

這是配方介面清單，**不保證每個參數組合都能在目前政策下產檔**。部分配方會合成內部 M 網路，若構成 M→M 就會被拒絕；不能停用政策來輸出。配方也不必然採用同名原生 FUNC。

- `generate_system_ldr`：最多組合 24 個獨立控制配方，自動分配內部 M/T/C，允許共用輸入、拒絕資源衝突；不是跨配方製程協調器。
- `generate_sequence_ldr`：1..16 步，可設定各步輸出、計時、完成條件、逾時、reset、abort；每掃描最多轉移一步，同樣受架構政策檢查。
- 順序控制預設使用原生 T。原生計時暫停續跑尚未支援；只有需求明確指定外部 clock 時，才能使用外部脈波模式，不自動補一個 X。

## 5. MCP 工具清單（17 個）

| 工具 | 用途 |
| --- | --- |
| `get_capabilities` | 查詢版本、功能、限制、政策與輸出位置 |
| `get_design_guide` | 取得需求轉設計流程、範例與 Ladder schema |
| `generate_ldr` | 自訂條件／原生指令產生 .ldr，主要產檔入口 |
| `generate_control_ldr` | 使用單一控制配方產檔 |
| `generate_system_ldr` | 組合多個獨立控制配方 |
| `generate_sequence_ldr` | 順序流程產檔 |
| `create_ldr` | 從低階 IR 建立新檔；未驗證形式須明確標示 |
| `create_start_stop` | 固定 X0 啟動、X1 停止、Y0 自保持模板，僅用於符合此 I/O 的需求 |
| `get_ldr_artifact` | 取得 .ldr 原始 bytes、SHA-256 與下載資源 |
| `inspect_ldr` | 查看容器、bytes、位移與 CRC |
| `read_ldr` | 按畫面順序讀取網路，未知指令保留為 opaque |
| `analyze_ldr` | 解釋網路、列出元件讀寫與重複寫入 |
| `compare_ldr` | 比較兩份檔案的新增／刪除／修改網路 |
| `validate_ladder` | 預覽結構、接圖簡化、資源用量與架構政策結果 |
| `simulate_ladder` | 在支援的布林／T/C 範圍內執行掃描模型 |
| `export_ldr` | 匯出新檔並保留原始內容；嚴格政策下仍可能拒絕未知或違規網路 |
| `modify_network` | 插入、替換或刪除網路，另存新檔，索引 0 對應 N000 |

傳輸方式為本機 stdio。除工具外，提供 `winproladder://capabilities` 與 `winproladder://artifacts/{name}` 資源；後者是 MCP 二進位檔案資源，不是 HTTP 網址。

## 6. 產檔與架構規則

- 主要生成工具必填 `io_contract`，只使用需求指定的 X/Y。原始設計和生成 bytes 的 I/O 都會檢查，超出即拒絕。
- 本工作區 `.winproladder-policy.json` 啟用 `forbid_m_to_m=true`。M 接點不能驅動 M 線圈，包含 SET／RESET、function 結果、MC 隱含控制及編譯器 helpers。
- 數值與狀態設計應使用原生暫存器；不以改名或偽裝的繼電器鏈繞過政策。
- 寫出前檢查來源、接圖轉換後程式及實際 bytes 解碼结果。無法符合要求時回報限制，不自行增加 I/O。
- 新檔採不覆寫方式建立；操作限於指定工作目錄，預設輸出至 `artifacts/`。
- 提供的 acceptance 案例若失敗即不產檔；沒有提供驗收案例不代表已驗證行為。
- 未知格式可保留作讀取研究，但無法證明符合嚴格架構政策時不能直接輸出。

## 7. 模擬、測試與驗證程度

| 層次 | 目前狀態 |
| --- | --- |
| 獨立離線核對 | 原始樣本 bytes、CRC、逐 byte 往返、I/O 引用、政策、負數與邊界檢查；不等同 PLC 行為 |
| MCP 內建模擬 | 布林接點／線圈、SET／RESET、單一 X 邊沿；指定 scan_ms 時支援有限的非保持 T/C 掃描模型 |
| MCP 真實呼叫 | 已測試 stdio 連線、需求產檔、資源下載與 SHA-256 核對 |
| WinProLadder GUI | 僅部分歷史檔案有人工匯入紀錄；test8～test14 新生成檔未因此自動取得 GUI 驗證 |
| 實體 PLC | 未執行實機驗證 |

內建模擬每次最多 256 scans；有時間模型時 scan_ms 為 1..60000 ms。T 時間模型限預設 `.01S` 的 T0..49 及支援的 preset 範圍，不模擬 PLC 非同步時脈相位。數值比較接點、原生 action、暫存器運算、MC/MCE、DIFU/DIFD、UDCTR 與迴圈均未提供執行模型。

v0.10.0 打包時為 **443 項通過**；目前未發版原始碼為 **559 項通過**。原始樣本目前 **15 份、104 networks** 可語意解碼與重建。這是現有樣本覆蓋，不代表所有程式都符合政策或所有指令變體皆有效。test11 的比較接點與浮點指令同樣區分離線、MCP 模擬、GUI 與實機驗證。

## 8. 仍未支援

- MOV 等尚未取得可靠編碼的原生 FUNC。
- 原生保持型計時 FUN87～89。
- 未明列的 32-bit／P 形式、間接定址、運算元種類與狀態接線。
- 多數硬體專用指令、通訊與定位功能。
- 全指令 PLC 執行模擬、自動 GUI 匯入驗證、實體 PLC 連線／下載。
- 從 .ldr 完整確認目的工程時間基準與所有 CPU 設定。

## 9. 使用方式與檔案位置

對已連接 MCP 的 Agent 提出需求，例如：

> 使用 WinProLadder MCP，X0 啟動 Y0 並自保持，X1 為 ON 時停止，停止優先。請產生 .ldr 並驗證啟動、保持、停止的行為。

Agent 應先核對需求 I/O 與目前功能，再選擇生成工具，最後交付 .ldr 和驗證狀態。使用者不需要手寫 JSON。

| 資料 | 位置 |
| --- | --- |
| 原始程式 | `src/winproladder_mcp/` |
| 原始樣本與截圖 | `samples/`、`samples/screenshots/` |
| 生成檔與驗證紀錄 | `artifacts/` |
| 目前版安裝包 | `dist/`，目前為 v0.10.0 |
| 歷史安裝包 | `dist/archive/<版本>/` |
| 本機 VM 共享目錄 | `C:/VM_Share` |

相關文件：[入門流程](docs/quickstart.md)、[資料夾導覽](docs/folders.md)、[FUNC test8/test9](docs/test8-test9-functions.md)、[FUNC test10](docs/test10-functions.md)、[詳細參數](docs/reference.md)。

功能與欄位若有後續變更，以實際連線 MCP 回傳的 `get_capabilities`、`get_design_guide` 及工作區政策為準。
